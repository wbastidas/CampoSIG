"""Form catalogue: blocks and per-work-type definitions (SRS 4.1, 4.2).

The mobile app shows a different form depending on the work to be done, and none of those
forms is coded. A work type names a definition; a definition lists reusable blocks in order;
a block is a fragment of JSON Schema. Adding a work type is a YAML file.

Two sources meet in one form:

* **blocks** carry what does not depend on the data model — header, times, safety,
  activities, evidence, closure;
* the **generator** (``app.forms.generator``) contributes the sections that describe an
  asset, derived from the real domains of that business unit's geodatabase.

A block declaring ``source: asset_metadata`` receives the generated properties at
composition time. That is why an inspection in one business unit offers that unit's own
feeder and material codes without anyone copying them anywhere.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class Area(StrEnum):
    """User areas of the SRS (section 1.3)."""

    SSO = "sso"
    OPERACION = "operacion"
    MANTENIMIENTO = "mantenimiento"
    APG = "apg"
    INGENIERIA = "ingenieria"


class BlockSource(StrEnum):
    STATIC = "static"
    #: Properties injected by the metadata-derived generator at composition time.
    ASSET_METADATA = "asset_metadata"


class BlockRule(BaseModel):
    """A conditional rule, expressed as JSON Logic.

    JSON Logic rather than a bespoke language so backend, web and mobile evaluate rules
    identically (SRS stack 7.2) — a rule that behaves differently on the phone than on the
    server is a rule nobody can trust.
    """

    when: dict[str, Any]
    require: list[str] = Field(default_factory=list)
    message: str | None = None
    blocks_execution: bool = False
    requires_role: str | None = None


class BlockHeader(BaseModel):
    code: str
    title: str
    required: bool = True
    source: BlockSource = BlockSource.STATIC


class FormBlock(BaseModel):
    """A reusable block of fields."""

    block: BlockHeader
    fields: dict[str, Any] = Field(default_factory=dict)
    rules: list[BlockRule] = Field(default_factory=list)

    @property
    def code(self) -> str:
        return self.block.code


class PhotoMinimums(BaseModel):
    before: int = 0
    after: int = 0


class FormHeader(BaseModel):
    code: str
    version: str
    title: str
    area: Area
    blocks: list[str]
    min_photos: PhotoMinimums = Field(default_factory=PhotoMinimums)
    requires_ats: bool = False
    #: True for the ATS itself: without it approved, execution is not enabled.
    gates_execution: bool = False
    track_route: bool = False
    applies_to_asset_types: list[str] = Field(default_factory=list)
    #: Competencies a crew must hold to execute this form's work (RF-005, RF-021). Declared here
    #: rather than in code because a form *is* the per-work-type data, and because the areas have to
    #: validate this list against their own practice — like the forms themselves, it is a baseline
    #: built from the sector's, not a rule the platform invented.
    #:
    #: Empty means «no hard requirement», and that is a decision, not an omission: inventing a
    #: safety requirement would make the assisted assignment refuse crews for no reason, and the
    #: planner would learn to ignore it.
    requires_competencies: list[str] = Field(default_factory=list)


class FormDefinition(BaseModel):
    form: FormHeader

    @property
    def code(self) -> str:
        return self.form.code

    @property
    def version(self) -> str:
        return self.form.version


class CatalogError(Exception):
    """Raised when the catalogue on disk is inconsistent."""


def forms_root() -> Path:
    return Path(__file__).resolve().parents[3] / "forms"


@lru_cache
def load_blocks() -> dict[str, FormBlock]:
    """Every block, keyed by its code. Duplicate codes are an error, not a last-wins."""
    blocks: dict[str, FormBlock] = {}
    for path in sorted((forms_root() / "blocks").rglob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        block = FormBlock.model_validate(data)
        if block.code in blocks:
            raise CatalogError(
                f"el bloque '{block.code}' está definido dos veces; el segundo es {path.name}"
            )
        blocks[block.code] = block
    return blocks


@lru_cache
def load_definitions() -> dict[str, FormDefinition]:
    """Every form definition, keyed by its code."""
    definitions: dict[str, FormDefinition] = {}
    for path in sorted((forms_root() / "definitions").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        definition = FormDefinition.model_validate(data)
        if definition.code in definitions:
            raise CatalogError(f"el formulario '{definition.code}' está definido dos veces")
        definitions[definition.code] = definition
    return definitions


def get_definition(code: str) -> FormDefinition:
    definitions = load_definitions()
    if code not in definitions:
        available = ", ".join(sorted(definitions))
        raise CatalogError(f"formulario '{code}' no existe; disponibles: {available}")
    return definitions[code]


def definitions_for_asset_type(asset_type_key: str) -> list[FormDefinition]:
    """Which work-type forms apply to an asset type."""
    return [
        definition
        for definition in load_definitions().values()
        if asset_type_key in definition.form.applies_to_asset_types
    ]


def definitions_for_area(area: Area) -> list[FormDefinition]:
    return [d for d in load_definitions().values() if d.form.area is area]


def validate_catalog() -> list[str]:
    """Problems a functional administrator must fix. Empty means the catalogue is sound."""
    problems: list[str] = []
    blocks = load_blocks()
    for definition in load_definitions().values():
        for code in definition.form.blocks:
            if code not in blocks:
                problems.append(
                    f"el formulario '{definition.code}' referencia el bloque '{code}', "
                    "que no existe"
                )
        if len(set(definition.form.blocks)) != len(definition.form.blocks):
            problems.append(f"el formulario '{definition.code}' repite un bloque")

        # A form requiring "after" photos but lacking the evidence block could never
        # collect them — a contradiction worth catching before it reaches a technician.
        needs_photos = definition.form.min_photos.before or definition.form.min_photos.after
        if needs_photos and "B09" not in definition.form.blocks:
            problems.append(
                f"el formulario '{definition.code}' exige fotos pero no incluye el bloque "
                "de evidencias B09"
            )
    return problems
