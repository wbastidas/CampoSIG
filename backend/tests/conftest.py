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

ALL_PROFILE_IDS = ["cnel-gye", "alt-synthetic"]


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
# Stand in for what the arcpy agent uploads (ADR-008). Every real name is DERIVED from
# the profile rather than written here: the fixture then works for any profile, cannot
# drift from the YAML, and keeps real field names out of test code (RF-305).


def build_metadata(profile_id: str):
    """GIS metadata matching a profile, as the agent would have exported it.

    Derived from the profile so the fixture stays honest: if a profile renames a field,
    this follows automatically instead of silently testing against a stale name.
    """
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
    binding = profile.bindings["support_structure"]
    resolver = ModelResolver(profile)

    def real(attribute: str) -> str:
        return resolver.field("support_structure", attribute)

    def domain_of(attribute: str) -> str | None:
        bound = binding.attributes.get(attribute)
        return bound.domain if bound else None

    # Coded values come from the profile's own value_map, so the codes a test sees are
    # exactly the ones the resolver can translate.
    material_map = profile.value_maps.get("material.support", {})
    material_domain = domain_of("material") or "MaterialDomain"
    feeder_domain = domain_of("feeder_code") or "FeederDomain"
    height_domain = "HeightRange"

    domains = [
        GisDomain(
            name=material_domain,
            domain_type=DomainType.CODED_VALUE,
            coded_values={str(code): str(canonical) for canonical, code in material_map.items()},
        ),
        GisDomain(
            name=feeder_domain,
            domain_type=DomainType.CODED_VALUE,
            coded_values={"04BH070T11": "Alimentador de ejemplo"},
            volatile_by_business_unit=True,
        ),
        GisDomain(
            name=height_domain,
            domain_type=DomainType.RANGE,
            range_min=6.0,
            range_max=20.0,
        ),
    ]

    fields = [
        GisField(
            name=real("code"),
            alias="Código",
            type="String",
            nullable=False,
            length=32,
            category=FieldCategory.CORE,
        ),
        GisField(
            name=real("material"),
            alias="Material",
            type="String",
            domain=material_domain,
            category=FieldCategory.CORE,
        ),
        GisField(
            name=real("height_m"),
            alias="Altura",
            type="Double",
            domain=height_domain,
            category=FieldCategory.OTHER,
        ),
        GisField(
            name=real("feeder_code"),
            alias="Alimentador",
            type="String",
            domain=feeder_domain,
            category=FieldCategory.CORE,
        ),
        # One field of each category a technician must never see. The connectivity field
        # name is taken from the constant rather than written out, so this fixture needs
        # no exemption from the leak check.
        GisField(
            name=sorted(NEVER_WRITE_FIELDS)[0],
            type="SmallInteger",
            category=FieldCategory.CONNECTIVITY,
        ),
        GisField(name="AUDIT_USER", type="String", category=FieldCategory.SYSTEM),
    ]

    relationships = [
        GisRelationship(
            name=related.relationship,
            origin_layer=binding.layer,
            destination_layer=related.target_layer,
            cardinality="One To Many",
            origin_primary_key="GLOBALID",
        )
        for related in binding.related
    ]

    return GisMetadata(
        profile_id=profile_id,
        domains=domains,
        layers=[GisLayerMetadata(name=binding.layer, geometry_type="Point", fields=fields)],
        relationships=relationships,
    )


@pytest.fixture
def metadata_spec(active_profile_id: str) -> dict:
    """Real names for the active profile, derived — for tests that must assert on them."""
    from app.model_profile.profile import load_profile

    profile = load_profile(active_profile_id)
    binding = profile.bindings["support_structure"]
    return {
        "layer": binding.layer,
        "code_field": binding.attributes["code"].field,
        "material_field": binding.attributes["material"].field,
        "material_domain": binding.attributes["material"].domain or "MaterialDomain",
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
