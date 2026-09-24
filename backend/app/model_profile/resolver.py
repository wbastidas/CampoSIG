"""The single point in the codebase that knows real field and class names (ADR-004).

Every other module speaks the canonical vocabulary and comes here to translate. That is
what makes installing against a different data model a configuration task (RF-301), and
it is enforced by scripts/check_data_model_leak.py (RF-305).

If you find yourself wanting a real field name somewhere else, that is the signal to add
a method here instead.
"""

from __future__ import annotations

from functools import lru_cache

from app.model_profile.amd import (
    AssetModel,
    AssetType,
    AttributeRole,
    Capability,
    load_asset_model,
)
from app.model_profile.profile import (
    AssetBinding,
    DataModelProfile,
    WritePath,
    load_profile,
    validate_against_amd,
)
from app.settings import get_settings

#: Geometric-network fields the platform never writes (ADR-001). Kept as a literal here
#: and in the agent's guard rather than read from a profile: a safety check a profile
#: could switch off is not a safety check. These are Esri platform fields, identical in
#: every geometric network, so they are not customer schema.
NEVER_WRITE_FIELDS = frozenset(
    {
        "ANCILLARYROLE",
        "ENABLED",
        "ELECTRICTRACEWEIGHT",
        "CIRCUITSOURCEGUID",
        "PARENTCIRCUITSOURCEGUID",
    }
)


class ResolutionError(Exception):
    """Raised when the active profile cannot answer a resolution request."""


class ConnectivityWriteError(Exception):
    """Raised on any attempt to write a geometric-network connectivity field."""


class ModelResolver:
    """Resolves canonical keys to the real names of the active profile."""

    def __init__(self, profile: DataModelProfile, amd: AssetModel | None = None) -> None:
        self.profile = profile
        self.amd = amd or load_asset_model()

    # -- structure --------------------------------------------------------------
    def asset_type(self, asset_type_key: str) -> AssetType:
        return self.amd.asset_type(asset_type_key)

    def binding(self, asset_type_key: str) -> AssetBinding:
        binding = self.profile.bindings.get(asset_type_key)
        if binding is None:
            raise ResolutionError(
                f"el perfil '{self.profile.id}' no tiene binding para '{asset_type_key}'"
            )
        return binding

    def layer(self, asset_type_key: str) -> str:
        """Real layer / feature class name for a canonical asset type."""
        return self.binding(asset_type_key).layer

    def field(self, asset_type_key: str, attribute_key: str) -> str:
        """Real field name for a canonical attribute."""
        binding = self.binding(asset_type_key)
        bound = binding.attributes.get(attribute_key)
        if bound is None:
            raise ResolutionError(
                f"'{asset_type_key}.{attribute_key}' no está mapeado en el perfil "
                f"'{self.profile.id}'"
            )
        return bound.field

    def field_for_role(self, asset_type_key: str, role: AttributeRole) -> str:
        """Real field name for a semantic role — the preferred way to ask.

        Code that wants the business key asks for the role, so it keeps working when a
        different installation calls that field something else entirely.
        """
        attribute = self.asset_type(asset_type_key).attribute_with_role(role)
        if attribute is None:
            raise ResolutionError(f"'{asset_type_key}' no declara un atributo con rol '{role}'")
        return self.field(asset_type_key, attribute.key)

    def fields(self, asset_type_key: str) -> dict[str, str]:
        """Canonical attribute key -> real field name, for everything mapped."""
        return {key: bound.field for key, bound in self.binding(asset_type_key).attributes.items()}

    # -- values -----------------------------------------------------------------
    def to_source_value(self, asset_type_key: str, attribute_key: str, canonical: str) -> object:
        """Translate a canonical enum value into the code the real domain uses."""
        mapping = self._value_map(asset_type_key, attribute_key)
        if canonical not in mapping:
            raise ResolutionError(
                f"valor canónico '{canonical}' no está en el value_map de "
                f"'{asset_type_key}.{attribute_key}'"
            )
        return mapping[canonical]

    def to_canonical_value(self, asset_type_key: str, attribute_key: str, source: object) -> str:
        """Translate a real domain code back into the canonical enum value."""
        mapping = self._value_map(asset_type_key, attribute_key)
        for canonical, code in mapping.items():
            if code == source:
                return canonical
        raise ResolutionError(
            f"código '{source}' no corresponde a ningún valor canónico de "
            f"'{asset_type_key}.{attribute_key}'"
        )

    def _value_map(self, asset_type_key: str, attribute_key: str) -> dict[str, object]:
        attribute = self.asset_type(asset_type_key).attribute(attribute_key)
        if attribute is None or not attribute.enum_ref:
            raise ResolutionError(f"'{asset_type_key}.{attribute_key}' no es un enum")
        bound = self.binding(asset_type_key).attributes.get(attribute_key)
        map_name = (bound.value_map if bound else None) or attribute.enum_ref
        mapping = self.profile.value_maps.get(map_name)
        if mapping is None:
            raise ResolutionError(
                f"el perfil '{self.profile.id}' no define el value_map '{map_name}'"
            )
        return mapping

    # -- write safety -----------------------------------------------------------
    def participates_in_geometric_network(self, asset_type_key: str) -> bool:
        return self.binding(asset_type_key).participates_in_geometric_network

    def write_path(self, asset_type_key: str) -> WritePath:
        """Which route edits take. Network participants are always staging (ADR-001).

        Enforced here rather than trusted from the profile: a profile that declared a
        network class as ``direct`` would be a way to corrupt the network by editing a
        YAML file.
        """
        binding = self.binding(asset_type_key)
        if binding.participates_in_geometric_network:
            return WritePath.STAGING_ONLY
        return binding.write_path

    def assert_writable(self, field_names: list[str]) -> None:
        """Refuse any write touching a connectivity field, in any route."""
        offending = sorted(n for n in field_names if n and n.upper() in NEVER_WRITE_FIELDS)
        if offending:
            raise ConnectivityWriteError(
                "La plataforma nunca escribe campos de conectividad: "
                f"{', '.join(offending)}. Los mantiene el trace de ArcFM (ADR-001)."
            )

    def volatile_domain_fields(self, asset_type_key: str) -> list[str]:
        """Fields whose domain varies per business unit, so never cached as constants."""
        return [
            bound.field
            for bound in self.binding(asset_type_key).attributes.values()
            if bound.volatile_by_business_unit
        ]

    # -- diagnostics ------------------------------------------------------------
    def problems(self) -> list[str]:
        """Profile completeness diagnostic (RF-302)."""
        return validate_against_amd(self.profile, self.amd)

    def asset_types_with(self, capability: Capability) -> list[str]:
        """Canonical asset types with a capability, restricted to what the profile maps."""
        return [
            t.key
            for t in self.amd.asset_types
            if t.has(capability) and t.key in self.profile.bindings
        ]


@lru_cache
def get_resolver() -> ModelResolver:
    """Resolver for the profile named by settings (SIGEC_PROFILE)."""
    settings = get_settings()
    return ModelResolver(load_profile(settings.profile))
