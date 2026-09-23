"""Shared fixtures.

The whole suite runs twice in CI: once per data-model profile. Tests must therefore
never assume a particular profile's real names — if one does, it will fail under
alt-synthetic, which is exactly the early warning ADR-004 wants.
"""

from __future__ import annotations

import os

import pytest

from app.model_profile.amd import load_asset_model
from app.model_profile.profile import load_profile
from app.model_profile.resolver import ModelResolver
from app.settings import get_settings

ALL_PROFILE_IDS = ["cnel-gye", "alt-synthetic"]


@pytest.fixture(autouse=True)
def _isolate_profile_caches():
    """Clear the profile and AMD caches around every test.

    `load_profile` and `load_asset_model` are lru_cached, so they hand back the same
    mutable object to every caller. A test that modifies a profile to exercise a failure
    path would otherwise corrupt every test that ran after it — order-dependent failures
    that look like flakiness. Clearing here makes that impossible rather than merely
    discouraged.
    """
    load_profile.cache_clear()
    load_asset_model.cache_clear()
    yield
    load_profile.cache_clear()
    load_asset_model.cache_clear()


@pytest.fixture(autouse=True)
def _no_blind_draw_unless_asked():
    """Turn the blind sample off for the suite, and let a test switch it on (RF-111a).

    The draw is random by design — a supervisor who could predict which order is measured is not
    being measured — and a random draw inside a shared code path is a suite that fails one run in
    ten. It did: a test that executes the pre-review and then reads the report found it withheld,
    which is correct behaviour and a useless test failure.

    Off by default rather than seeded, because "seeded" still means every test that runs the
    pre-review depends on how many draws happened before it. The tests that care about the draw set
    the rate themselves, and they are clearer for saying so.
    """
    settings = get_settings()
    original = settings.blind_sample_rate
    settings.blind_sample_rate = 0.0
    yield
    settings.blind_sample_rate = original


@pytest.fixture
def active_profile_id() -> str:
    """The profile under test, honouring SIGEC_PROFILE as CI sets it."""
    return os.environ.get("SIGEC_PROFILE", "cnel-gye")


@pytest.fixture
def resolver(active_profile_id: str) -> ModelResolver:
    return ModelResolver(load_profile(active_profile_id))


@pytest.fixture(params=ALL_PROFILE_IDS)
def any_resolver(request: pytest.FixtureRequest) -> ModelResolver:
    """Parametrised over every profile, for behaviour that must hold for all of them."""
    return ModelResolver(load_profile(request.param))


@pytest.fixture
def amd():
    return load_asset_model()


# --- GIS metadata fixtures ---------------------------------------------------------
# Stand in for what the arcpy agent uploads (ADR-008). Every real name is DERIVED from the
# profile: the fixture works for any profile, cannot drift from the YAML, keeps real field
# names out of test code (RF-305), and exports a layer and field for everything the profile
# maps — which is what the agent really does, and what the completeness diagnostic expects.

#: Canonical attributes treated as mandatory in the simulated capture manual.
_CORE_ATTRIBUTES = frozenset({"code", "material", "feeder_code", "rated_kva", "technology"})

_ALIASES = {
    "code": "Código",
    "material": "Material",
    "height_m": "Altura",
    "feeder_code": "Alimentador",
    "install_date": "Fecha de instalación",
    "rated_kva": "Potencia",
    "phases": "Fases",
    "mounting": "Tipo de montaje",
    "technology": "Tecnología",
    "power_w": "Potencia",
    "fuse_rating": "Capacidad del fusible",
    "voltage_level": "Voltaje",
}

#: Range domain injected on the one numeric attribute that should carry limits.
_RANGE_DOMAIN = "HeightRange"


def build_metadata(profile_id: str):
    """GIS metadata matching a profile, as the agent would have exported it."""
    from app.model_profile.amd import AttributeType
    from app.model_profile.metadata import (
        DomainType,
        FieldCategory,
        GisDomain,
        GisField,
        GisLayerMetadata,
        GisMetadata,
        GisRelationship,
    )
    from app.model_profile.profile import load_profile
    from app.model_profile.resolver import NEVER_WRITE_FIELDS

    profile = load_profile(profile_id)
    resolver = ModelResolver(profile)

    gis_types = {
        AttributeType.STRING: "String",
        AttributeType.NUMBER: "Double",
        AttributeType.INTEGER: "Integer",
        AttributeType.BOOLEAN: "SmallInteger",
        AttributeType.DATE: "Date",
        AttributeType.ENUM: "String",
    }

    # --- domains: one per value_map the profile declares, plus a range domain --------
    domains = [
        GisDomain(
            name=map_name,
            domain_type=DomainType.CODED_VALUE,
            coded_values={str(code): str(canonical) for canonical, code in mapping.items()},
        )
        for map_name, mapping in profile.value_maps.items()
    ]
    domains.append(
        GisDomain(name=_RANGE_DOMAIN, domain_type=DomainType.RANGE, range_min=6.0, range_max=20.0)
    )

    # Domains named directly by a binding (rather than through a value_map), marked
    # volatile where the profile says so (RF-304).
    seen = {d.name for d in domains}
    for binding in profile.bindings.values():
        for bound in binding.attributes.values():
            if bound.domain and bound.domain not in seen:
                seen.add(bound.domain)
                domains.append(
                    GisDomain(
                        name=bound.domain,
                        domain_type=DomainType.CODED_VALUE,
                        coded_values={"04BH070T11": "Alimentador de ejemplo"},
                        volatile_by_business_unit=bound.volatile_by_business_unit,
                    )
                )

    # --- one layer per mapped asset type -------------------------------------------
    layers = []
    relationships = []
    for asset_key, binding in profile.bindings.items():
        asset_type = resolver.asset_type(asset_key)
        fields = []
        for attribute_key, bound in binding.attributes.items():
            attribute = asset_type.attribute(attribute_key)
            domain = bound.domain
            if attribute is not None and attribute.enum_ref:
                # Enum attributes sit on the value_map's domain, so the codes a test sees
                # are exactly the ones the resolver can translate.
                domain = bound.value_map or attribute.enum_ref
            elif attribute_key == "height_m":
                domain = _RANGE_DOMAIN
            fields.append(
                GisField(
                    name=bound.field,
                    alias=_ALIASES.get(attribute_key),
                    type=gis_types[attribute.type] if attribute else "String",
                    nullable=attribute_key not in _CORE_ATTRIBUTES,
                    length=32 if attribute_key == "code" else None,
                    domain=domain,
                    category=(
                        FieldCategory.CORE
                        if attribute_key in _CORE_ATTRIBUTES
                        else FieldCategory.OTHER
                    ),
                )
            )

        # One field of each category a technician must never see. The connectivity field
        # name comes from the constant rather than being written out, so this fixture
        # needs no exemption from the leak check.
        fields.append(
            GisField(
                name=sorted(NEVER_WRITE_FIELDS)[0],
                type="SmallInteger",
                category=FieldCategory.CONNECTIVITY,
            )
        )
        fields.append(GisField(name="AUDIT_USER", type="String", category=FieldCategory.SYSTEM))

        layers.append(
            GisLayerMetadata(
                name=binding.layer,
                geometry_type=asset_type.geometry.title(),
                fields=fields,
            )
        )
        relationships.extend(
            GisRelationship(
                name=related.relationship,
                origin_layer=binding.layer,
                destination_layer=related.target_layer,
                cardinality="One To Many",
                origin_primary_key="GLOBALID",
            )
            for related in binding.related
        )

    return GisMetadata(
        profile_id=profile_id, domains=domains, layers=layers, relationships=relationships
    )


@pytest.fixture
def metadata_spec(active_profile_id: str) -> dict:
    """Real names for the active profile, derived — for tests that must assert on them."""
    from app.model_profile.profile import load_profile

    profile = load_profile(active_profile_id)
    binding = profile.bindings["support_structure"]
    material = binding.attributes["material"]
    return {
        "layer": binding.layer,
        "code_field": binding.attributes["code"].field,
        "material_field": material.field,
        "material_domain": material.value_map or "material.support",
        "feeder_domain": binding.attributes["feeder_code"].domain or "FeederDomain",
    }


@pytest.fixture
def gis_metadata(active_profile_id: str):
    return build_metadata(active_profile_id)


@pytest.fixture
def generator(resolver, gis_metadata):
    from app.forms.generator import FormGenerator

    return FormGenerator(resolver, gis_metadata)


@pytest.fixture(params=ALL_PROFILE_IDS)
def any_generator(request: pytest.FixtureRequest):
    """Generator parametrised over every profile — the ADR-004 verification."""
    from app.forms.generator import FormGenerator
    from app.model_profile.profile import load_profile

    resolver = ModelResolver(load_profile(request.param))
    return FormGenerator(resolver, build_metadata(request.param))
