"""Generate JSON Schema + UI Schema from GIS metadata (RF-303).

The SRS requires forms to be data rather than coded screens. This goes a step further,
the way Field Maps does: forms are *derived* from the layer schema instead of being
authored by hand, so a new business unit produces forms without anyone writing code.

Generation rules, each traceable to something in the source material:

* A coded-value domain becomes an ``enum`` plus ``x-catalog-ref`` — never inlined
  values, because domains that vary per business unit must be refreshed from the GIS
  (RF-304) and a copy baked into a form would go stale silently.
* A range domain becomes ``minimum`` / ``maximum``.
* A field the capture manual marks CORE becomes ``required``; so does a non-nullable one.
* CONNECTIVITY and SYSTEM fields are omitted entirely — they belong to the network engine
  and to audit, and a technician has no business editing them (ADR-001).
* A one-to-many relationship becomes a repeatable table, which is how the Puesto/Unidad
  pattern of this data model renders naturally.
* A subtype that overrides a field's domain becomes an ``if/then`` branch, because the
  same field legitimately takes different values depending on the subtype.

The generator **proposes**; a functional administrator reviews and approves before
publication. That is the same "AI proposes, human decides" rule applied to configuration
(SRS rule 0.5), and it is why nothing here writes to the form registry directly.
"""

from __future__ import annotations

from typing import Any

from app.model_profile.amd import AssetType, AttributeType
from app.model_profile.metadata import GisMetadata
from app.model_profile.resolver import ModelResolver, ResolutionError

JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"

#: Canonical attribute type -> JSON Schema type.
_JSON_TYPES: dict[AttributeType, str] = {
    AttributeType.STRING: "string",
    AttributeType.NUMBER: "number",
    AttributeType.INTEGER: "integer",
    AttributeType.BOOLEAN: "boolean",
    AttributeType.DATE: "string",
    AttributeType.ENUM: "string",
}


class FormGenerationError(Exception):
    """Raised when metadata and profile disagree beyond what generation can bridge."""


class GeneratedForm:
    """A generated form proposal, pending human approval."""

    def __init__(
        self,
        asset_type_key: str,
        schema: dict[str, Any],
        ui_schema: dict[str, Any],
        warnings: list[str],
    ) -> None:
        self.asset_type_key = asset_type_key
        self.schema = schema
        self.ui_schema = ui_schema
        #: Things a human should look at before approving. Never silently dropped.
        self.warnings = warnings

    @property
    def requires_review(self) -> bool:
        return bool(self.warnings)

    def as_dict(self) -> dict[str, Any]:
        return {
            "asset_type": self.asset_type_key,
            "schema": self.schema,
            "ui_schema": self.ui_schema,
            "warnings": self.warnings,
        }


class FormGenerator:
    """Derives form schemas from the canonical vocabulary plus real GIS metadata."""

    def __init__(self, resolver: ModelResolver, metadata: GisMetadata) -> None:
        self.resolver = resolver
        self.metadata = metadata

    def generate(self, asset_type_key: str) -> GeneratedForm:
        asset_type = self.resolver.asset_type(asset_type_key)
        layer_name = self.resolver.layer(asset_type_key)
        layer = self.metadata.layer(layer_name)
        warnings: list[str] = []

        if layer is None:
            # Not fatal: generation proceeds from the profile alone, but a human must
            # know the metadata was missing rather than discover it in the field.
            warnings.append(
                f"la capa '{layer_name}' no está en los metadatos sincronizados; "
                "el formulario se generó solo desde el perfil"
            )

        properties: dict[str, Any] = {}
        required: list[str] = []
        ui_order: list[str] = []

        for attribute in asset_type.attributes:
            try:
                field_name = self.resolver.field(asset_type_key, attribute.key)
            except ResolutionError:
                warnings.append(
                    f"'{attribute.key}' no está mapeado en el perfil y queda fuera del formulario"
                )
                continue

            gis_field = layer.field(field_name) if layer else None
            prop, field_warnings = self._property_for(
                asset_type_key, asset_type, attribute.key, gis_field
            )
            warnings.extend(field_warnings)
            properties[attribute.key] = prop
            ui_order.append(attribute.key)

            is_required = attribute.required or self._is_required_in_gis(gis_field)
            if is_required:
                required.append(attribute.key)

        # One-to-many relationships become repeatable tables.
        related_props, related_warnings = self._related_tables(asset_type_key, layer_name)
        properties.update(related_props)
        ui_order.extend(related_props)
        warnings.extend(related_warnings)

        schema: dict[str, Any] = {
            "$schema": JSON_SCHEMA_DIALECT,
            "$id": f"forms/generated/{asset_type_key}/0.1.0",
            "title": asset_type.label_key or asset_type_key,
            "type": "object",
            "properties": properties,
            "x-asset-type": asset_type_key,
            "x-profile": self.resolver.profile.id,
            "x-generated": True,
        }
        if required:
            schema["required"] = sorted(required)

        conditionals = self._subtype_conditionals(asset_type_key, layer)
        if conditionals:
            schema["allOf"] = conditionals

        return GeneratedForm(asset_type_key, schema, self._ui_schema(ui_order), warnings)

    # -- per-field ---------------------------------------------------------------
    def _property_for(
        self,
        asset_type_key: str,
        asset_type: AssetType,
        attribute_key: str,
        gis_field: Any,
    ) -> tuple[dict[str, Any], list[str]]:
        attribute = asset_type.attribute(attribute_key)
        if attribute is None:  # pragma: no cover - guarded by the caller
            raise FormGenerationError(f"unknown attribute '{attribute_key}'")

        warnings: list[str] = []
        prop: dict[str, Any] = {"type": _JSON_TYPES[attribute.type]}

        if attribute.type is AttributeType.DATE:
            prop["format"] = "date"
        if attribute.unit:
            prop["x-unit"] = attribute.unit
        if gis_field is not None:
            prop["title"] = gis_field.label
            if gis_field.length and attribute.type is AttributeType.STRING:
                prop["maxLength"] = gis_field.length

        # Voice and vision annotations the SRS requires per field (section 4.1).
        prop["x-voice"] = True
        if "ai_vision" in [c.value for c in asset_type.capabilities]:
            prop["x-vision-source"] = f"{asset_type_key}.{attribute_key}"

        # Domain handling applies to every domain-backed field, not only enums: a
        # plain string field can sit on a domain that varies per business unit, and it
        # needs the same refresh signal (RF-304).
        if gis_field is not None and gis_field.domain:
            prop, domain_warnings = self._apply_domain(prop, gis_field.domain)
            warnings.extend(domain_warnings)

        if attribute.enum_ref:
            prop, enum_warnings = self._apply_enum(
                prop, asset_type_key, attribute_key, attribute.enum_ref, gis_field
            )
            warnings.extend(enum_warnings)

        return prop, warnings

    def _apply_enum(
        self,
        prop: dict[str, Any],
        asset_type_key: str,
        attribute_key: str,
        enum_ref: str,
        gis_field: Any,
    ) -> tuple[dict[str, Any], list[str]]:
        """Enum values stay canonical; the real codes are resolved at write time.

        The form speaks the canonical vocabulary so that the same form definition works
        against any profile. `x-catalog-ref` tells the renderer where to fetch the
        display labels, which come from the synced domain rather than from the form.
        """
        warnings: list[str] = []
        canonical_values = self.resolver.amd.enums.get(enum_ref, [])
        prop["enum"] = canonical_values
        prop["x-catalog-ref"] = enum_ref

        # Domain presence, volatility and range were already applied by _apply_domain.
        # What is enum-specific is checking the profile can translate every domain code.
        if gis_field is not None and gis_field.domain:
            domain = self.metadata.domain(gis_field.domain)
            if domain is not None:
                unmapped = self._unmapped_domain_codes(
                    asset_type_key, attribute_key, canonical_values, domain
                )
                if unmapped:
                    warnings.append(
                        f"el dominio '{domain.name}' tiene códigos sin valor canónico: "
                        f"{', '.join(unmapped)}. Revisar el value_map del perfil"
                    )
        return prop, warnings

    def _unmapped_domain_codes(
        self,
        asset_type_key: str,
        attribute_key: str,
        canonical_values: list[str],
        domain: Any,
    ) -> list[str]:
        """Domain codes the profile cannot translate — a real gap a human must see.

        Codes are compared as strings: a domain code may be an integer in the geodatabase
        and arrive as a string through the agent's JSON, and a type mismatch there would
        report every code as unmapped — noise that would train people to ignore warnings.
        """
        mapped: set[str] = set()
        for value in canonical_values:
            try:
                source = self.resolver.to_source_value(asset_type_key, attribute_key, value)
            except ResolutionError:
                # Absence is exactly what this method measures, so it is not an error.
                continue
            mapped.add(str(source))
        return sorted(str(code) for code in domain.codes if str(code) not in mapped)

    def _apply_domain(
        self, prop: dict[str, Any], domain_name: str
    ) -> tuple[dict[str, Any], list[str]]:
        """Apply everything that follows from a field sitting on a domain.

        Shared by enum and non-enum fields, because volatility and range are properties
        of the domain, not of how the form happens to render the field.
        """
        prop["x-domain"] = domain_name
        domain = self.metadata.domain(domain_name)
        if domain is None:
            return prop, [
                f"el dominio '{domain_name}' está referenciado por un campo pero "
                "ausente de los metadatos sincronizados"
            ]
        if domain.volatile_by_business_unit:
            # Tells the renderer to always fetch fresh values instead of trusting a
            # copy shipped with the form (RF-304).
            prop["x-volatile-catalog"] = True
        if domain.range_min is not None:
            prop["minimum"] = domain.range_min
        if domain.range_max is not None:
            prop["maximum"] = domain.range_max
        return prop, []

    @staticmethod
    def _is_required_in_gis(gis_field: Any) -> bool:
        """CORE in the capture manual, or non-nullable in the geodatabase."""
        if gis_field is None:
            return False
        return gis_field.category.value == "core" or not gis_field.nullable

    # -- relationships -----------------------------------------------------------
    def _related_tables(
        self, asset_type_key: str, layer_name: str
    ) -> tuple[dict[str, Any], list[str]]:
        """One-to-many relationships become repeatable tables (the Puesto/Unidad case)."""
        properties: dict[str, Any] = {}
        warnings: list[str] = []
        for related in self.resolver.binding(asset_type_key).related:
            declared = [
                r
                for r in self.metadata.relationships_from(layer_name)
                if r.name.upper() == related.relationship.upper()
            ]
            if not declared:
                warnings.append(
                    f"la relación '{related.relationship}' del perfil no aparece en los "
                    "metadatos sincronizados"
                )
            elif not declared[0].is_one_to_many:
                # A one-to-one relationship is a nested object, not a table. Flagged
                # rather than guessed, because getting it wrong changes data entry.
                warnings.append(
                    f"la relación '{related.relationship}' no es uno-a-muchos "
                    f"({declared[0].cardinality}); revisar si corresponde una tabla"
                )
            properties[related.as_] = {
                "type": "array",
                "title": related.as_.replace("_", " "),
                "x-repeatable-table": True,
                "x-relationship": related.relationship,
                "items": {"type": "object", "properties": {}},
            }
        return properties, warnings

    # -- subtypes ----------------------------------------------------------------
    def _subtype_conditionals(self, asset_type_key: str, layer: Any) -> list[dict[str, Any]]:
        """Subtypes that override a field's domain become if/then branches."""
        if layer is None or not layer.subtypes or not layer.subtype_field:
            return []

        real_to_canonical = {
            field: key for key, field in self.resolver.fields(asset_type_key).items()
        }
        subtype_key = real_to_canonical.get(layer.subtype_field)
        if subtype_key is None:
            # The subtype field is not part of the canonical vocabulary, so it cannot
            # drive a branch on this form.
            return []

        branches: list[dict[str, Any]] = []
        for subtype in layer.subtypes:
            overrides = {
                real_to_canonical[field]: {"x-domain": domain}
                for field, domain in subtype.domain_overrides.items()
                if field in real_to_canonical
            }
            if not overrides:
                continue
            branches.append(
                {
                    "if": {"properties": {subtype_key: {"const": subtype.code}}},
                    "then": {"properties": overrides},
                }
            )
        return branches

    # -- UI ----------------------------------------------------------------------
    @staticmethod
    def _ui_schema(order: list[str]) -> dict[str, Any]:
        return {
            "ui:order": order,
            "ui:options": {"label": True},
            # Field-level widgets are the administrator's call; the generator only
            # proposes an order (RF-303).
        }
