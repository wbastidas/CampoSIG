"""Compose a complete form from its blocks and the asset metadata (RF-303, SRS 4.1).

This is what the mobile app downloads: a different form per work type, assembled rather
than coded. The composer is the only place blocks and generated sections meet.

Composition order is the order the definition lists its blocks, because that is the order a
technician works in — safety before execution, evidence before closure. It is data, so a
functional administrator can change it without a release.
"""

from __future__ import annotations

import copy
from typing import Any, Protocol

from app.forms.catalog import (
    BlockSource,
    FormBlock,
    FormDefinition,
    get_definition,
    load_blocks,
)
from app.forms.generator import JSON_SCHEMA_DIALECT, FormGenerator
from app.model_profile.metadata import GisMetadata
from app.model_profile.resolver import ModelResolver

#: The field B04 carries the ATS reference in. Named here because the composer has to make
#: it mandatory when a form declares `requires_ats`, and the same literal in two places would
#: be two places to keep in step.
SAFETY_REFERENCE = "ats_reference"


class ComposedForm:
    """A complete, renderable form for one work type."""

    def __init__(
        self,
        definition: FormDefinition,
        schema: dict[str, Any],
        ui_schema: dict[str, Any],
        rules: list[dict[str, Any]],
        warnings: list[str],
    ) -> None:
        self.definition = definition
        self.schema = schema
        self.ui_schema = ui_schema
        #: Conditional rules, flattened from every block, evaluated identically on
        #: backend, web and mobile.
        self.rules = rules
        self.warnings = warnings

    @property
    def code(self) -> str:
        return self.definition.code

    @property
    def version(self) -> str:
        return self.definition.version

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "version": self.version,
            "title": self.definition.form.title,
            "area": self.definition.form.area.value,
            "schema": self.schema,
            "ui_schema": self.ui_schema,
            "rules": self.rules,
            "warnings": self.warnings,
        }


class FormShape(Protocol):
    """What a frozen version supplies: a definition and the blocks it referenced.

    A protocol rather than an import of `forms.registry`, so composition stays a pure function of
    data and does not drag the database layer into a module the tests exercise without one.
    """

    @property
    def definition(self) -> FormDefinition: ...

    @property
    def blocks(self) -> dict[str, FormBlock]: ...


#: Alias kept short because it appears in `compose`'s signature.
FrozenShape = FormShape


class FormComposer:
    """Assembles work-type forms for one business unit's data model.

    :param resolver: the business unit's model resolver (ADR-004, ADR-009).
    :param metadata: that unit's current metadata snapshot, or None before its first sync.
    """

    def __init__(self, resolver: ModelResolver, metadata: GisMetadata | None) -> None:
        self.resolver = resolver
        self.metadata = metadata
        self._generator = FormGenerator(resolver, metadata) if metadata else None

    def compose(
        self,
        form_code: str,
        asset_type_key: str | None = None,
        *,
        frozen: FrozenShape | None = None,
    ) -> ComposedForm:
        """Compose one form.

        :param form_code: e.g. ``F-MT-01``.
        :param asset_type_key: the asset the work targets. Required when the form has an
            asset-derived block; that block is what makes the form specific to the asset.
        :param frozen: a published version's definition and blocks (RF-032). Given, the **shape**
            comes from it instead of from the files, so publishing a new version does not change
            what an existing order composes. The unit's catalogue values still come from the
            current metadata, deliberately: an order executed today must name a feeder that exists
            today (RF-304).
        """
        definition = frozen.definition if frozen is not None else get_definition(form_code)
        blocks = frozen.blocks if frozen is not None else load_blocks()
        properties: dict[str, Any] = {}
        required: list[str] = []
        ui_order: list[str] = []
        ui_groups: list[dict[str, Any]] = []
        rules: list[dict[str, Any]] = []
        warnings: list[str] = []
        #: Accumulated across blocks and applied at the end. A field can appear in a static
        #: block and in the asset-derived section — `feeder_code` does — and the first
        #: definition wins. Its requiredness must not be lost with the discarded definition:
        #: being mandatory is a property of the field, not of the block that declared it.
        asset_required: list[str] = []

        resolved_asset = self._resolve_asset_type(definition, asset_type_key, warnings)

        for code in definition.form.blocks:
            block = blocks.get(code)
            if block is None:
                # Caught by validate_catalog too; reported rather than raised so one bad
                # block does not make every form for that work type unavailable.
                warnings.append(f"el bloque '{code}' no existe y se omitió")
                continue

            # A deep copy, not `dict(block.fields)`: the block library is cached, so the
            # nested field schemas are shared objects. Composition stamps per-work-type
            # values onto them (photo minimums, for instance), and a shallow copy would
            # write those into the cached block — corrupting every other form composed
            # afterwards. That bug is invisible in a single compose and obvious in a suite.
            block_properties = copy.deepcopy(block.fields)
            if block.block.source is BlockSource.ASSET_METADATA:
                generated, generated_required, generation_warnings = self._asset_properties(
                    resolved_asset
                )
                block_properties.update(generated)
                asset_required.extend(generated_required)
                warnings.extend(generation_warnings)

            group_keys: list[str] = []
            for field_name, field_schema in block_properties.items():
                if field_name in properties:
                    warnings.append(
                        f"el campo '{field_name}' aparece en más de un bloque; se conservó "
                        f"el primero y se ignoró el del bloque '{code}'"
                    )
                    continue
                properties[field_name] = field_schema
                ui_order.append(field_name)
                group_keys.append(field_name)

            if block.block.required and group_keys:
                required.extend(self._required_fields(block, group_keys))

            ui_groups.append(
                {"block": block.code, "title": block.block.title, "fields": group_keys}
            )
            rules.extend(rule.model_dump(exclude_none=True) for rule in block.rules)

        # What the generator determined is mandatory: a field the capture manual marks CORE,
        # or one the geodatabase declares non-nullable. Applied against the whole form so a
        # field defined by an earlier block still carries it.
        required.extend(key for key in asset_required if key in properties)

        properties = self._apply_photo_minimums(definition, properties, warnings)
        required.extend(self._safety_required(definition, properties, warnings))

        schema: dict[str, Any] = {
            "$schema": JSON_SCHEMA_DIALECT,
            "$id": f"forms/{definition.code}/{definition.version}",
            "title": definition.form.title,
            "type": "object",
            "properties": properties,
            "x-form-code": definition.code,
            "x-form-version": definition.version,
            "x-area": definition.form.area.value,
            "x-profile": self.resolver.profile.id,
            "x-requires-ats": definition.form.requires_ats,
            "x-gates-execution": definition.form.gates_execution,
        }
        if resolved_asset:
            schema["x-asset-type"] = resolved_asset
        if definition.form.track_route:
            schema["x-track-route"] = True
        if required:
            schema["required"] = sorted(set(required))

        ui_schema = {
            "ui:order": ui_order,
            # Blocks become sections, so the phone renders one step at a time instead of
            # one long scroll — the difference between usable and unusable with gloves on.
            "ui:groups": ui_groups,
        }
        return ComposedForm(definition, schema, ui_schema, rules, warnings)

    # -- helpers -----------------------------------------------------------------
    def _resolve_asset_type(
        self, definition: FormDefinition, asset_type_key: str | None, warnings: list[str]
    ) -> str | None:
        applies = definition.form.applies_to_asset_types
        if asset_type_key is None:
            if len(applies) == 1:
                # Unambiguous: a form for exactly one asset type needs no hint.
                return applies[0]
            if applies:
                warnings.append(
                    f"'{definition.code}' aplica a varios tipos de activo "
                    f"({', '.join(applies)}); sin indicar uno, las secciones derivadas del "
                    "activo quedan vacías"
                )
            return None
        if applies and asset_type_key not in applies:
            warnings.append(f"'{definition.code}' no declara aplicar al tipo '{asset_type_key}'")
        return asset_type_key

    def _asset_properties(
        self, asset_type_key: str | None
    ) -> tuple[dict[str, Any], list[str], list[str]]:
        """Properties, required keys and warnings derived from the unit's real metadata.

        The required keys travel with the properties deliberately: they are what the capture
        manual marks CORE and what the geodatabase declares non-nullable, and losing them
        would hand back a form with nothing mandatory at all.

        :returns: (properties, required_keys, warnings)
        """
        if asset_type_key is None:
            return {}, [], []
        if self._generator is None:
            return (
                {},
                [],
                [
                    "sin metadatos sincronizados de esta unidad: las secciones derivadas del "
                    "activo quedan vacías hasta que su agente arcpy corra"
                ],
            )
        generated = self._generator.generate(asset_type_key)
        # Related tables stay out: a work form captures the asset's condition, not its
        # full related-record structure, which belongs to the as-built flow.
        related = {r.as_ for r in self.resolver.binding(asset_type_key).related}
        properties = {
            key: value
            for key, value in generated.schema["properties"].items()
            if key not in related
        }
        required = [key for key in generated.schema.get("required", []) if key not in related]
        return properties, required, generated.warnings

    @staticmethod
    def _required_fields(block: FormBlock, group_keys: list[str]) -> list[str]:
        """Fields a required block makes mandatory.

        Only fields the block marks ``required`` at field level, plus those with a minimum
        item count. A required *block* does not make every field in it required — that
        would make most forms impossible to submit in the field.
        """
        required: list[str] = []
        for key in group_keys:
            schema = block.fields.get(key)
            if not isinstance(schema, dict):
                continue
            if schema.get("required") is True or schema.get("minItems"):
                required.append(key)
        return required

    @staticmethod
    def _safety_required(
        definition: FormDefinition, properties: dict[str, Any], warnings: list[str]
    ) -> list[str]:
        """What `requires_ats` makes mandatory (SRS 4.2, block B04).

        The flag used to travel to the phone as `x-requires-ats` and **nothing looked at it**: no
        block carried a field for the ATS reference, so a work order whose form «requires an ATS»
        could be closed without naming one. A declaration that nothing enforces is worse than no
        declaration, because the area believes it is covered.

        The warning is the other half: a form that requires an ATS and does not include B04 is a
        misconfiguration nobody would notice, and it is exactly the state every form was in.
        """
        if not definition.form.requires_ats:
            return []
        if SAFETY_REFERENCE not in properties:
            warnings.append(
                f"'{definition.code}' exige ATS pero no incluye el bloque B04, así que no hay "
                f"dónde anotar cuál: el campo '{SAFETY_REFERENCE}' no está en el formulario"
            )
            return []
        return [SAFETY_REFERENCE]

    @staticmethod
    def _apply_photo_minimums(
        definition: FormDefinition, properties: dict[str, Any], warnings: list[str]
    ) -> dict[str, Any]:
        """Stamp the per-work-type photo minimums onto the evidence arrays (SRS 4.8)."""
        minimums = {
            "photos_before": definition.form.min_photos.before,
            "photos_after": definition.form.min_photos.after,
        }
        for field_name, minimum in minimums.items():
            if not minimum:
                continue
            target = properties.get(field_name)
            if target is None:
                warnings.append(
                    f"'{definition.code}' exige {minimum} foto(s) en '{field_name}' pero el "
                    "formulario no incluye ese campo"
                )
                continue
            target["minItems"] = minimum
        return properties
