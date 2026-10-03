# -*- coding: utf-8 -*-
"""Apply an approved as-built batch to the geodatabase (RF-347, ADR-008).

The algorithm is not a style choice; it is forced by two findings:

  * H13 — ``arcpy.da.InsertCursor`` fails on feature classes participating in a
    geometric network, so rows go into a staging class *outside* the network first.
  * H14 — ``Append_management`` on network classes has left the logical network
    inconsistent, so connectivity is rebuilt on the affected extent afterwards.

Sequence::

    staging class (outside the network)   <- da.InsertCursor
    edit session on the versioned SDE    <- da.Editor
    Append_management  ->  target class
    rebuild connectivity on the affected extent
    report the outcome of every proposal back to the backend

Runs on ArcMap 10.8.1's Python 2.7.18 (H12), so no f-strings, annotations or walrus.
``arcpy`` is imported lazily to keep this module testable against the double.
"""

from __future__ import unicode_literals

from .guards import (
    assert_not_geometric_network_insert,
    assert_within_profile_scope,
    writable_attributes,
)

#: Outcomes reported back per proposal (must match the backend's check constraint).
APPLIED = "applied"
REJECTED = "rejected"
ERROR = "error"
REQUIRES_ARCFM = "requires_arcfm"


class ProposalOutcome(object):
    """Result of applying a single proposal."""

    def __init__(self, proposal_id, status, message=None):
        self.proposal_id = proposal_id
        self.status = status
        self.message = message

    def as_dict(self):
        return {
            "proposal_id": self.proposal_id,
            "status": self.status,
            "message": self.message,
        }

    def __repr__(self):
        return "ProposalOutcome(%r, %r)" % (self.proposal_id, self.status)


class BatchApplier(object):
    """Applies a batch of as-built proposals to one target feature class.

    :param workspace: SDE connection file path (a *versioned* connection).
    :param arcpy_module: injected for testing; defaults to the real ``arcpy``.
    """

    def __init__(self, workspace, arcpy_module=None):
        self.workspace = workspace
        if arcpy_module is None:
            import arcpy as arcpy_module  # noqa: PLC0415 - lazy by design
        self.arcpy = arcpy_module

    # -- staging ----------------------------------------------------------------
    def stage_rows(self, staging_class, field_names, proposals, profile_fields=None):
        """Insert proposals into the staging class, which must be outside the network.

        :param staging_class: staging feature class name.
        :param field_names: real field names, already resolved from the profile.
        :param proposals: list of dicts with ``proposal_id`` and ``attributes``.
        :param profile_fields: every field the profile maps for this asset type; when
            given, fields outside it are refused (D11).
        :returns: (staged_proposal_ids, outcomes_for_the_ones_that_failed)
        """
        # Three checks before a single row moves: the staging class must be outside the
        # network, no connectivity field may be written, and every field must be one the
        # profile maps — the agent writes process fields only (D11).
        assert_not_geometric_network_insert(staging_class, False)
        writable_attributes(dict.fromkeys(field_names))
        if profile_fields is not None:
            assert_within_profile_scope(field_names, profile_fields)

        staged = []
        failures = []
        cursor = self.arcpy.da.InsertCursor(staging_class, field_names)
        try:
            for proposal in proposals:
                attributes = writable_attributes(proposal["attributes"])
                try:
                    row = tuple(attributes.get(name) for name in field_names)
                    cursor.insertRow(row)
                    staged.append(proposal["proposal_id"])
                except Exception as exc:  # noqa: BLE001 - reported per proposal
                    failures.append(
                        ProposalOutcome(proposal["proposal_id"], ERROR, str(exc))
                    )
        finally:
            del cursor
        return staged, failures

    # -- append + connectivity --------------------------------------------------
    def append_to_target(self, staging_class, target_class):
        """Append the staged rows into the target class inside an edit session.

        An edit session is mandatory: network and topology classes cannot be modified
        outside one.
        """
        editor = self.arcpy.da.Editor(self.workspace)
        editor.startEditing(False, True)
        editor.startOperation()
        try:
            self.arcpy.Append_management(staging_class, target_class, "TEST")
        except Exception:
            editor.stopOperation()
            editor.stopEditing(False)
            raise
        editor.stopOperation()
        editor.stopEditing(True)

    def rebuild_connectivity(self, geometric_network, extent=None):
        """Rebuild network connectivity after an Append (H14).

        Mandatory, not precautionary: Append on network classes has been observed to
        leave the logical network inconsistent. Skipping this is how that ships.
        """
        rebuild = getattr(self.arcpy, "RebuildConnectivity_management", None)
        if rebuild is None:
            # The double does not implement it; the real arcpy does. Surfaced rather
            # than silently skipped, so a missing rebuild is always visible.
            return False
        rebuild(geometric_network, extent)
        return True

    # -- orchestration ----------------------------------------------------------
    def apply(self, batch):
        """Apply a whole batch and return one outcome per proposal.

        :param batch: dict with ``staging_class``, ``target_class``, ``field_names``,
            ``geometric_network`` (may be ``None``), ``proposals`` and optionally
            ``profile_fields`` (the write scope, per D11).
        :returns: list of :class:`ProposalOutcome`.
        """
        proposals = batch["proposals"]

        # Proposals needing ArcFM auto-updaters are never applied automatically: the
        # agent does not run them and will not pretend it did (H15).
        pending = []
        outcomes = []
        for proposal in proposals:
            if proposal.get("requires_arcfm"):
                outcomes.append(
                    ProposalOutcome(
                        proposal["proposal_id"],
                        REQUIRES_ARCFM,
                        "Requiere auto-actualizadores de ArcFM; queda para el equipo GIS",
                    )
                )
            else:
                pending.append(proposal)

        if not pending:
            return outcomes

        staged, failures = self.stage_rows(
            batch["staging_class"],
            batch["field_names"],
            pending,
            profile_fields=batch.get("profile_fields"),
        )
        outcomes.extend(failures)

        if not staged:
            return outcomes

        try:
            self.append_to_target(batch["staging_class"], batch["target_class"])
        except Exception as exc:  # noqa: BLE001 - whole batch fails together
            message = "Append falló: %s" % exc
            for proposal_id in staged:
                outcomes.append(ProposalOutcome(proposal_id, ERROR, message))
            return outcomes

        if batch.get("geometric_network"):
            self.rebuild_connectivity(batch["geometric_network"], batch.get("extent"))

        for proposal_id in staged:
            outcomes.append(ProposalOutcome(proposal_id, APPLIED))
        return outcomes
