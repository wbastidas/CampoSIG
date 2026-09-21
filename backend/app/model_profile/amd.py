"""Asset Model Descriptor: the platform's canonical vocabulary (RF-300, ADR-004).

Nothing here knows about any real geodatabase. Asset types, attributes and semantic
roles are named in the platform's own terms; a profile maps them to real names at
runtime (see resolver.py).
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class AttributeRole(StrEnum):
    """Semantic roles. Code asks for a role, never for a field name."""

    BUSINESS_KEY = "business_key"
    NETWORK_GROUPING = "network_grouping"
    VOLTAGE_LEVEL = "voltage_level"


class AttributeType(StrEnum):
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    DATE = "date"
    ENUM = "enum"


class Capability(StrEnum):
    """What the platform may do with an asset type."""

    INSPECTABLE = "inspectable"
    PHOTOGRAPHABLE = "photographable"
    WORK_TARGET = "work_target"
    AI_VISION = "ai_vision"
    HAS_UNITS = "has_units"


class CanonicalAttribute(BaseModel):
    key: str
    type: AttributeType
    required: bool = False
    role: AttributeRole | None = None
    unit: str | None = None
    enum_ref: str | None = None

    @field_validator("enum_ref")
    @classmethod
    def enum_needs_ref(cls, value: str | None, info: Any) -> str | None:
        if info.data.get("type") is AttributeType.ENUM and not value:
            raise ValueError(f"attribute '{info.data.get('key')}' is enum but has no enum_ref")
        return value


class AssetType(BaseModel):
    key: str
    geometry: str
    label_key: str | None = None
    capabilities: list[Capability] = Field(default_factory=list)
    attributes: list[CanonicalAttribute] = Field(default_factory=list)

    def attribute(self, key: str) -> CanonicalAttribute | None:
        return next((a for a in self.attributes if a.key == key), None)

    def attribute_with_role(self, role: AttributeRole) -> CanonicalAttribute | None:
        return next((a for a in self.attributes if a.role is role), None)

    def has(self, capability: Capability) -> bool:
        return capability in self.capabilities


class AssetModel(BaseModel):
    """The whole canonical vocabulary."""

    version: int
    asset_types: list[AssetType]
    enums: dict[str, list[str]] = Field(default_factory=dict)

    def asset_type(self, key: str) -> AssetType:
        found = next((t for t in self.asset_types if t.key == key), None)
        if found is None:
            known = ", ".join(sorted(t.key for t in self.asset_types))
            raise KeyError(f"unknown asset type '{key}'; known types: {known}")
        return found

    @property
    def asset_type_keys(self) -> list[str]:
        return [t.key for t in self.asset_types]


@lru_cache
def load_asset_model(path: str | None = None) -> AssetModel:
    """Load and validate the canonical vocabulary."""
    default = Path(__file__).resolve().parents[3] / "profiles" / "amd" / "core.yaml"
    location = Path(path) if path else default
    data = yaml.safe_load(location.read_text(encoding="utf-8"))
    return AssetModel.model_validate(data)
