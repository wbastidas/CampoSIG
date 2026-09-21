"""Data-model profiles: map the canonical vocabulary onto a real schema (RF-301).

A profile is the only artifact that changes when the platform is installed against a
different geodatabase, business unit or GIS. Profiles live in `profiles/` — the only
place real class and field names may appear (RF-305).
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from app.model_profile.amd import AssetModel, load_asset_model


class WritePath(StrEnum):
    """How edits to an asset type reach the GIS (ADR-001, ADR-008).

    ``DIRECT`` is only ever honoured for classes outside the geometric network, and is
    off by default per installation (RF-345). The resolver enforces that, so a profile
    cannot opt a network class into direct writes.
    """

    STAGING_ONLY = "staging_only"
    DIRECT = "direct"


class AttributeBinding(BaseModel):
    field: str
    domain: str | None = None
    value_map: str | None = None
    # Domains that differ per business unit are never packaged as constants; they are
    # refreshed from the GIS on every metadata sync (RF-304, 01_Dominios.md warning).
    volatile_by_business_unit: bool = False


class RelatedBinding(BaseModel):
    as_: str = Field(alias="as")
    relationship: str
    target_layer: str
    cardinality: str = "one_to_many"

    model_config = {"populate_by_name": True}


class AssetBinding(BaseModel):
    layer: str
    participates_in_geometric_network: bool = False
    write_path: WritePath = WritePath.STAGING_ONLY
    attributes: dict[str, AttributeBinding] = Field(default_factory=dict)
    related: list[RelatedBinding] = Field(default_factory=list)


class ProfileHeader(BaseModel):
    id: str
    label: str | None = None
    provider: str
    arcgis_version: str | None = None
    spatial_reference: int
    geometric_network: str | None = None
    feature_dataset: str | None = None


class DataModelProfile(BaseModel):
    profile: ProfileHeader
    bindings: dict[str, AssetBinding]
    value_maps: dict[str, dict[str, object]] = Field(default_factory=dict)
    never_write_fields: list[str] = Field(default_factory=list)

    @property
    def id(self) -> str:
        return self.profile.id


def profiles_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "profiles"


@lru_cache
def load_profile(profile_id: str) -> DataModelProfile:
    """Load and validate a profile by id."""
    path = profiles_dir() / f"{profile_id}.yaml"
    if not path.exists():
        available = ", ".join(sorted(p.stem for p in profiles_dir().glob("*.yaml")))
        raise FileNotFoundError(f"profile '{profile_id}' not found; available: {available}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return DataModelProfile.model_validate(data)


class ProfileValidationError(Exception):
    """Raised when a profile does not satisfy the canonical vocabulary."""


def validate_against_amd(profile: DataModelProfile, amd: AssetModel | None = None) -> list[str]:
    """Check a profile covers the canonical vocabulary; return human-readable problems.

    This is the diagnostic the profile importer shows (RF-302) and what makes "configure,
    don't program" verifiable rather than aspirational.
    """
    model = amd or load_asset_model()
    problems: list[str] = []

    for asset_type in model.asset_types:
        binding = profile.bindings.get(asset_type.key)
        if binding is None:
            problems.append(f"tipo de activo '{asset_type.key}' sin binding en el perfil")
            continue
        for attribute in asset_type.attributes:
            bound = binding.attributes.get(attribute.key)
            if bound is None:
                if attribute.required:
                    problems.append(
                        f"'{asset_type.key}.{attribute.key}' es obligatorio y no está mapeado"
                    )
                continue
            if attribute.enum_ref:
                map_name = bound.value_map or attribute.enum_ref
                mapping = profile.value_maps.get(map_name)
                if mapping is None:
                    problems.append(
                        f"'{asset_type.key}.{attribute.key}' referencia el value_map "
                        f"'{map_name}', ausente del perfil"
                    )
                else:
                    missing = set(model.enums.get(attribute.enum_ref, [])) - set(mapping)
                    if missing:
                        problems.append(
                            f"value_map '{map_name}' no cubre: {', '.join(sorted(missing))}"
                        )

    unknown = set(profile.bindings) - set(model.asset_type_keys)
    problems.extend(
        f"binding '{key}' no corresponde a ningún tipo canónico" for key in sorted(unknown)
    )
    return problems
