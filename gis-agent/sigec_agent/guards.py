# -*- coding: utf-8 -*-
"""Invariants the arcpy agent must never violate (ADR-008).

Runs on ArcMap 10.8.1's Python 2.7.18 (finding H12), so this module is written to
parse on both 2.7 and 3.x: no f-strings, no annotations, no walrus.

These are not style preferences. Each one prevents a way of corrupting the corporate
geodatabase that has already been observed in practice:

  * Connectivity fields are computed by ArcFM's trace, not by us. Writing them puts
    the logical network out of step with the topology, silently (ADR-001, H5).
  * ``arcpy.da.InsertCursor`` fails outright on feature classes participating in a
    geometric network (H13), so inserts must go through a staging class plus Append.
  * ArcFM's auto-updaters can be suppressed from Python over COM. We never do: that
    would bypass the customer's business rules without anyone noticing (H15).

Scope of writes (decision D11): the agent writes the *process* fields — the ones the
profile maps, which by construction are the ones the field form produces — and nothing
else. Fields computed by ArcFM's auto-updaters are out of scope by decision, not by
limitation; ArcFM or a trace recomputes them afterwards. ``assert_within_profile_scope``
below is what makes that a check rather than an intention.
"""

from __future__ import unicode_literals

#: Fields maintained by the geometric network and ArcFM's auto-updaters. The platform
#: reads them and never writes them, in any route (ADR-001).
CONNECTIVITY_FIELDS = frozenset([
    "ANCILLARYROLE",
    "CIRCUITSOURCEGUID",
    "PARENTCIRCUITSOURCEGUID",
    "ENABLED",
    "ELECTRICTRACEWEIGHT",
])


class GuardViolation(Exception):
    """Raised when an operation would break one of the ADR-008 invariants."""


def assert_no_connectivity_fields(field_names):
    """Reject any attempt to write a connectivity field.

    :param field_names: iterable of field names about to be written.
    :raises GuardViolation: if one or more are connectivity fields.
    """
    offending = sorted(
        name for name in field_names if name and name.upper() in CONNECTIVITY_FIELDS
    )
    if offending:
        raise GuardViolation(
            "La plataforma nunca escribe campos de conectividad: %s. "
            "Los mantiene el trace de ArcFM (ADR-001, H5)." % ", ".join(offending)
        )


def assert_not_geometric_network_insert(feature_class, participates_in_network):
    """Reject a direct insert into a geometric-network feature class.

    ``arcpy.da.InsertCursor`` raises ``SystemError('error return without exception
    set')`` on these classes (H13). The supported path is a staging class outside the
    network followed by ``Append_management``.

    :param feature_class: target feature class name, for the message.
    :param participates_in_network: whether it participates, taken from the profile.
    :raises GuardViolation: if it does participate.
    """
    if participates_in_network:
        raise GuardViolation(
            "No se puede insertar directo en '%s': participa en la red geométrica y "
            "InsertCursor falla (H13). Use clase de staging fuera de la red + "
            "Append_management (ADR-008)." % feature_class
        )


def assert_no_autoupdater_suppression(module_names):
    """Reject any attempt to reach ArcFM's auto-updater COM interface.

    :param module_names: iterable of module or COM ProgID names being loaded.
    :raises GuardViolation: if any refers to ArcFM's dispatch interface.
    """
    banned = ("miner.", "mmautoupdater", "arcfm")
    offending = sorted(
        name
        for name in module_names
        if name and any(token in name.lower() for token in banned)
    )
    if offending:
        raise GuardViolation(
            "El agente nunca desactiva los auto-actualizadores de ArcFM ni usa COM: %s. "
            "Los lotes que los necesiten se marcan 'requiere ArcFM' y quedan para el "
            "equipo del cliente (ADR-008, H15)." % ", ".join(offending)
        )


def assert_within_profile_scope(field_names, profile_fields):
    """Reject any field the profile does not map (decision D11).

    The profile defines the write scope: a field absent from it is not part of the field
    process, so the agent has no business writing it. This is ADR-004's property applied
    to write safety — the agent cannot write what is not in its vocabulary.

    :param field_names: field names about to be written.
    :param profile_fields: the real field names the active profile maps for this type.
    :raises GuardViolation: if a field is outside the profile's scope.
    """
    allowed = set(profile_fields)
    outside = sorted(name for name in field_names if name and name not in allowed)
    if outside:
        raise GuardViolation(
            "Fuera del alcance del perfil: %s. El agente escribe solo los campos del "
            "proceso que el perfil mapea; lo calculado por ArcFM no es su "
            "responsabilidad (D11)." % ", ".join(outside)
        )


def writable_attributes(attributes):
    """Return ``attributes`` unchanged, having verified none is a connectivity field.

    Convenience wrapper for the apply path, so the check sits on the data flow rather
    than being something a caller has to remember.

    :param attributes: mapping of field name to value.
    :raises GuardViolation: if a connectivity field is present.
    """
    assert_no_connectivity_fields(attributes.keys())
    return attributes
