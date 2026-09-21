"""GIS metadata the arcpy agent uploads (RF-349, RF-302, RF-304).

The agent runs `arcpy.da.ListDomains` and `arcpy.Describe` on the ArcMap machine and
posts the result here as JSON (ADR-008). This module is the backend's typed view of that
payload — it never talks to ArcSDE itself.

Field categories come straight from the customer's capture manual, documented in
`docs/modelo-datos-cnel/`. They matter because they decide what a technician ever sees:
SYSTEM and CONNECTIVITY fields are audit and network-engine concerns, so they are never
rendered on a form.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class FieldCategory(StrEnum):
    """Why a field exists, which decides whether it reaches a form."""

    #: Listed as mandatory in the customer's capture manual: the real required fields.
    CORE = "core"
    #: Used by the network engine for tracing. Never written, never shown.
    CONNECTIVITY = "connectivity"
    #: Audit and technical metadata maintained by the geodatabase. Never shown.
    SYSTEM = "system"
    #: Everything else. Not unnecessary — just not declared mandatory by the manual.
    OTHER = "other"

    @property
    def visible_on_forms(self) -> bool:
        return self in (FieldCategory.CORE, FieldCategory.OTHER)


class DomainType(StrEnum):
    CODED_VALUE = "coded_value"
    RANGE = "range"


class GisDomain(BaseModel):
    """A geodatabase domain: the source of truth for a field's valid values."""

    name: str
    domain_type: DomainType
    #: Stored code -> human-readable name, as the editor sees it.
    coded_values: dict[str, str] = Field(default_factory=dict)
    range_min: float | None = None
    range_max: float | None = None
    #: Domains that differ per business unit are refreshed every sync and never cached
    #: as constants (RF-304).
    volatile_by_business_unit: bool = False

    @property
    def codes(self) -> list[str]:
        return list(self.coded_values)


class GisField(BaseModel):
    name: str
    alias: str | None = None
    type: str
    nullable: bool = True
    length: int | None = None
    domain: str | None = None
    category: FieldCategory = FieldCategory.OTHER

    @property
    def label(self) -> str:
        """What a human should read. Aliases often repeat the technical name."""
        if self.alias and self.alias.upper() != self.name.upper():
            return self.alias
        return self.name


class GisSubtype(BaseModel):
    """A subtype, which can change a field's domain.

    Common in this model — the same field takes a different domain depending on the
    subtype — which is why forms need conditional schemas rather than a flat list.
    """

    code: int
    name: str
    #: field name -> domain name, overriding the field's default domain.
    domain_overrides: dict[str, str] = Field(default_factory=dict)


class GisRelationship(BaseModel):
    """A relationship class. One-to-many becomes a repeatable table on the form."""

    name: str
    origin_layer: str
    destination_layer: str
    cardinality: str
    origin_primary_key: str | None = None
    origin_foreign_key: str | None = None
    composite: bool = False

    @property
    def is_one_to_many(self) -> bool:
        return self.cardinality.lower().replace(" ", "_") in {
            "one_to_many",
            "onetomany",
        }


class GisLayerMetadata(BaseModel):
    name: str
    geometry_type: str | None = None
    subtype_field: str | None = None
    fields: list[GisField] = Field(default_factory=list)
    subtypes: list[GisSubtype] = Field(default_factory=list)

    def field(self, name: str) -> GisField | None:
        upper = name.upper()
        return next((f for f in self.fields if f.name.upper() == upper), None)

    def visible_fields(self) -> list[GisField]:
        return [f for f in self.fields if f.category.visible_on_forms]


class GisMetadata(BaseModel):
    """Everything the agent exported in one sync."""

    profile_id: str
    exported_at: str | None = None
    agent_version: str | None = None
    domains: list[GisDomain] = Field(default_factory=list)
    layers: list[GisLayerMetadata] = Field(default_factory=list)
    relationships: list[GisRelationship] = Field(default_factory=list)

    def domain(self, name: str) -> GisDomain | None:
        return next((d for d in self.domains if d.name == name), None)

    def layer(self, name: str) -> GisLayerMetadata | None:
        upper = name.upper()
        return next((layer for layer in self.layers if layer.name.upper() == upper), None)

    def relationships_from(self, layer_name: str) -> list[GisRelationship]:
        upper = layer_name.upper()
        return [r for r in self.relationships if r.origin_layer.upper() == upper]

    @property
    def volatile_domains(self) -> list[GisDomain]:
        """Domains that must be refreshed on every sync (RF-304)."""
        return [d for d in self.domains if d.volatile_by_business_unit]
