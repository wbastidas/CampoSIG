"""Assisted matching: propose a data-model profile from a metadata snapshot (RF-301).

The promise of ADR-004 is that installing against another utility — or another business
unit with its own geodatabase — is configuration, not programming. Until now that promise
had an engine (`resolver.py`), a validator (`validate_against_amd`) and no way in: somebody
still had to write a profile by hand, guessing which of two hundred classes was the one the
canonical `support_structure` meant.

This module closes that gap. It reads a metadata snapshot the agent exported and proposes
bindings, with the evidence for each one written out in Spanish so a functional
administrator can judge it.

Three design rules, each from a way this goes wrong:

* **A proposal is never a binding.** Same rule as an AI-extracted value: it is written as a
  proposal, and a person accepts it. An importer that silently picked the wrong class would
  produce a profile that *works* — forms render, syncs run — while field data lands on the
  wrong feature class. That failure is invisible for weeks.
* **Ambiguity is reported, not resolved.** When two classes score within a hair of each
  other, the honest answer is "these two look alike, choose", not a coin flip dressed as a
  recommendation.
* **Bookkeeping and connectivity fields are never candidates.** A geometric-network field is
  refused outright (ADR-001), and so is an audit column, because `OBJECTID` is otherwise an
  excellent-looking match for a canonical business key.

Nothing here knows a real name: every real name arrives at runtime inside the snapshot, and
the vocabulary it matches against lives in `profiles/amd/` (RF-305).
"""

from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

from app.model_profile.amd import (
    AssetModel,
    AssetType,
    AttributeType,
    CanonicalAttribute,
    Capability,
    load_asset_model,
)
from app.model_profile.metadata import (
    DomainType,
    FieldCategory,
    GisDomain,
    GisField,
    GisLayerMetadata,
    GisMetadata,
)
from app.model_profile.profile import (
    DataModelProfile,
    ProfileHeader,
    WritePath,
    validate_against_amd,
)
from app.model_profile.resolver import NEVER_WRITE_FIELDS
from app.voice.lexicon import load_spoken_vocabulary
from app.voice.normalizer import strip_accents

#: Below this, a candidate is not worth showing: it would be noise in a list an
#: administrator has to read class by class.
MIN_CANDIDATE_SCORE = 0.30

#: Two candidates this close are ambiguous. The number is deliberately generous — the cost
#: of asking is one click, and the cost of a wrong binding is a season of bad data.
AMBIGUITY_MARGIN = 0.10

#: How many candidates travel to the screen. Enough to contain the right answer when the
#: first one is wrong; short enough to read.
MAX_CANDIDATES = 5


# --- vocabulary --------------------------------------------------------------------
class MatchingVocabulary(BaseModel):
    """The written vocabulary of the canonical layer, typed."""

    version: int
    locale: str
    asset_terms: dict[str, dict[str, list[str]]] = Field(default_factory=dict)
    attribute_terms: dict[str, list[str]] = Field(default_factory=dict)
    housekeeping_terms: list[str] = Field(default_factory=list)

    def strong_for(self, asset_type_key: str) -> list[str]:
        return self.asset_terms.get(asset_type_key, {}).get("strong", [])

    def weak_for(self, asset_type_key: str) -> list[str]:
        return self.asset_terms.get(asset_type_key, {}).get("weak", [])


@lru_cache
def load_matching_vocabulary(path: str | None = None) -> MatchingVocabulary:
    default = Path(__file__).resolve().parents[3] / "profiles" / "amd" / "matching-es-EC.yaml"
    location = Path(path) if path else default
    return MatchingVocabulary.model_validate(
        yaml.safe_load(location.read_text(encoding="utf-8"))
    )


# --- name folding ------------------------------------------------------------------
_SPLIT_RE = re.compile(r"[^0-9a-z]+")
#: Two boundaries, and deliberately not a third. A lower-case letter followed by an
#: upper-case one is a word boundary (`codigoActivo`), and so is the end of an acronym
#: before a capitalised word (`GISLayer`). A digit followed by a capital is NOT: in
#: `XFMR3F` — the kind of name the ten-character field limit produced — splitting there
#: invents two tokens out of one abbreviation.
_CAMEL_RE = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def fold(text: str) -> str:
    """Accent-free, lower-case, separator-free form of a name."""
    return _SPLIT_RE.sub("", strip_accents(text).lower())


def tokens_of(name: str) -> list[str]:
    """Split a class or field name into comparable tokens.

    Handles the three conventions that coexist in one geodatabase: `CamelCase`,
    `SNAKE_CASE` and the all-caps run left over from the ten-character field-name limit of
    older geodatabases. The last one cannot be split without a dictionary, which is why
    substring evidence exists below.
    """
    spaced = _CAMEL_RE.sub(" ", name)
    return [t for t in _SPLIT_RE.split(strip_accents(spaced).lower()) if t]


# --- evidence ----------------------------------------------------------------------
class Evidence(BaseModel):
    """One reason a candidate scored what it scored, in words an administrator reads."""

    signal: str
    detail: str
    weight: float


def _term_score(name: str, terms: list[str], *, strong: bool) -> tuple[float, str | None]:
    """Best lexical agreement between a name and a list of terms, with the term that won.

    Four ways a term can appear, in descending order of how much it proves:
    an exact token, a substring of the glued name, a token that is a truncation of the
    term, and a term that is a truncation of a token.
    """
    name_tokens = set(tokens_of(name))
    glued = fold(name)
    best = 0.0
    winner: str | None = None
    full, partial = (1.0, 0.6) if strong else (0.45, 0.3)

    for term in terms:
        folded = fold(term)
        if not folded:
            continue
        score = 0.0
        if folded in name_tokens:
            score = full
        elif len(folded) >= 4 and folded in glued:
            score = partial
        elif len(folded) >= 5 and any(
            len(token) >= 3 and folded.startswith(token) for token in name_tokens
        ):
            # `ALIM` for `alimentador`: the abbreviation convention of every utility.
            score = partial * 0.9
        if score > best:
            best, winner = score, term
    return best, winner


# --- geometry ----------------------------------------------------------------------
_GEOMETRIES = ("multipoint", "polyline", "polygon", "point", "line")


def normalise_geometry(value: str | None) -> str | None:
    """Reduce any spelling of a geometry type to the canonical word, or None."""
    if not value:
        return None
    folded = fold(value)
    for candidate in _GEOMETRIES:
        if candidate in folded:
            return "polyline" if candidate == "line" else candidate
    return None


def geometry_agrees(canonical: str, layer_geometry: str | None) -> bool | None:
    """True, False, or None when the snapshot did not say."""
    actual = normalise_geometry(layer_geometry)
    if actual is None:
        return None
    return actual == normalise_geometry(canonical)


# --- field eligibility --------------------------------------------------------------
_TYPE_COMPATIBILITY: dict[AttributeType, frozenset[str]] = {
    AttributeType.STRING: frozenset({"string", "text", "char", "varchar"}),
    AttributeType.NUMBER: frozenset(
        {"double", "single", "float", "number", "integer", "smallinteger", "long", "short"}
    ),
    AttributeType.INTEGER: frozenset({"integer", "smallinteger", "long", "short"}),
    AttributeType.BOOLEAN: frozenset({"smallinteger", "short", "integer", "string"}),
    AttributeType.DATE: frozenset({"date", "datetime", "timestamp"}),
    # An enum lives wherever its domain lives, which is a string or an integer code.
    AttributeType.ENUM: frozenset(
        {"string", "text", "integer", "smallinteger", "long", "short"}
    ),
}

#: A code kept as a number is common and workable, but it is not what the canonical type
#: asked for, so it costs something and the evidence says why.
_LOOSE_TYPE_PENALTY = 0.15


def type_agrees(attribute: CanonicalAttribute, field: GisField) -> bool:
    return fold(field.type) in _TYPE_COMPATIBILITY[attribute.type]


def is_housekeeping(field: GisField, vocabulary: MatchingVocabulary) -> bool:
    """Audit and geometry columns the geodatabase maintains for itself.

    Checked by name rather than only by category because a snapshot from an agent that
    never categorised its fields is exactly the snapshot where `OBJECTID` would win the
    business key.
    """
    folded = fold(field.name)
    return any(folded == fold(term) for term in vocabulary.housekeeping_terms)


def field_is_eligible(field: GisField, vocabulary: MatchingVocabulary) -> str | None:
    """None when the field may be proposed; otherwise the reason it may not be."""
    if field.category is FieldCategory.CONNECTIVITY:
        return "es un campo de conectividad de la red geométrica y la plataforma nunca lo escribe"
    if field.category is FieldCategory.SYSTEM:
        return "es un campo de sistema que mantiene la geodatabase"
    if is_housekeeping(field, vocabulary):
        return "es una columna de control de la geodatabase, no un atributo del activo"
    return None


# --- attribute candidates -----------------------------------------------------------
class ValueMapProposal(BaseModel):
    """Canonical enum value → the domain code proposed for it."""

    value_map_name: str
    domain: str
    mapping: dict[str, str] = Field(default_factory=dict)
    #: Canonical values with no plausible code. These are what blocks publication later,
    #: so they are surfaced now rather than at the end.
    unmapped: list[str] = Field(default_factory=list)
    #: Domain codes no canonical value claimed. Not a problem — the utility's catalogue is
    #: allowed to be richer than the canonical one — but worth seeing.
    unclaimed: list[str] = Field(default_factory=list)


class FieldCandidate(BaseModel):
    field: str
    label: str
    score: float
    evidence: list[Evidence] = Field(default_factory=list)
    domain: str | None = None
    volatile_by_business_unit: bool = False
    value_map: ValueMapProposal | None = None


class AttributeProposal(BaseModel):
    attribute_key: str
    attribute_type: AttributeType
    required: bool
    candidates: list[FieldCandidate] = Field(default_factory=list)
    #: Fields that matched by name and were refused anyway, with the reason. Shown because
    #: "why is OBJECTID not offered for the code?" is asked once per installation.
    refused: list[str] = Field(default_factory=list)

    @property
    def best(self) -> FieldCandidate | None:
        return self.candidates[0] if self.candidates else None

    @property
    def ambiguous(self) -> bool:
        return (
            len(self.candidates) > 1
            and self.candidates[0].score - self.candidates[1].score < AMBIGUITY_MARGIN
        )


class RelatedProposal(BaseModel):
    as_: str = Field(alias="as")
    relationship: str
    target_layer: str
    cardinality: str

    model_config = {"populate_by_name": True}


class LayerCandidate(BaseModel):
    layer: str
    score: float
    evidence: list[Evidence] = Field(default_factory=list)


class AssetProposal(BaseModel):
    asset_type_key: str
    geometry: str
    candidates: list[LayerCandidate] = Field(default_factory=list)
    #: Attribute proposals computed against the leading candidate. They are recomputed when
    #: an administrator chooses a different class.
    attributes: list[AttributeProposal] = Field(default_factory=list)
    related: list[RelatedProposal] = Field(default_factory=list)
    participates_in_geometric_network: bool = False

    @property
    def best(self) -> LayerCandidate | None:
        return self.candidates[0] if self.candidates else None

    @property
    def ambiguous(self) -> bool:
        return (
            len(self.candidates) > 1
            and self.candidates[0].score - self.candidates[1].score < AMBIGUITY_MARGIN
        )

    @property
    def gaps(self) -> list[str]:
        """What a person still has to decide, in Spanish, for this asset type."""
        problems: list[str] = []
        if self.best is None:
            problems.append(
                f"no se encontró ninguna clase que se parezca a '{self.asset_type_key}'"
            )
            return problems
        if self.ambiguous:
            names = ", ".join(c.layer for c in self.candidates[:2])
            problems.append(
                f"'{self.asset_type_key}': dos clases puntúan casi igual ({names}); "
                "hay que elegir"
            )
        for attribute in self.attributes:
            if attribute.best is None and attribute.required:
                problems.append(
                    f"'{self.asset_type_key}.{attribute.attribute_key}' es obligatorio y "
                    "ningún campo se le parece"
                )
            elif attribute.ambiguous:
                fields = ", ".join(c.field for c in attribute.candidates[:2])
                problems.append(
                    f"'{self.asset_type_key}.{attribute.attribute_key}': "
                    f"{fields} puntúan casi igual"
                )
            best = attribute.best
            if best and best.value_map and best.value_map.unmapped:
                missing = ", ".join(best.value_map.unmapped)
                problems.append(
                    f"'{self.asset_type_key}.{attribute.attribute_key}': el dominio "
                    f"'{best.value_map.domain}' no ofrece código para {missing}"
                )
        return problems


class ProfileProposal(BaseModel):
    """Everything the importer has to say about one snapshot."""

    profile_id: str
    assets: list[AssetProposal] = Field(default_factory=list)
    #: Classes in the snapshot no canonical type claimed. Informational: a geodatabase has
    #: hundreds of classes and the canonical vocabulary covers six.
    unclaimed_layer_count: int = 0

    @property
    def gaps(self) -> list[str]:
        return [gap for asset in self.assets for gap in asset.gaps]

    def asset(self, key: str) -> AssetProposal:
        found = next((a for a in self.assets if a.asset_type_key == key), None)
        if found is None:
            raise KeyError(f"la propuesta no cubre el tipo de activo '{key}'")
        return found


# --- scoring ------------------------------------------------------------------------
#: How much each signal contributes to a class candidate. Name and structure weigh the
#: same on purpose: a class called `POSTE` with none of the expected columns is as
#: suspicious as one with every column and an unrecognisable name.
WEIGHT_NAME = 0.50
WEIGHT_ATTRIBUTES = 0.35
WEIGHT_GEOMETRY = 0.15

#: How complete the structural evidence must be for a class whose name says nothing to
#: still be a candidate. High on purpose: it is the escape hatch for a schema in a
#: language the vocabulary does not cover, not a way in for a coincidence.
COVERAGE_WITHOUT_A_NAME = 0.85

#: And how many *distinguishing* attributes that coverage has to rest on. Every class in an
#: electrical geodatabase has a code and belongs to a feeder, so matching those two proves
#: nothing about which kind of asset it holds. A canonical type whose whole attribute set is
#: universal can therefore only be identified by its class name — which is the honest answer,
#: and is why `service_point` is not offered a class on structure alone.
MIN_DISTINCTIVE_MATCHES = 2


def _attribute_terms(
    attribute_key: str, vocabulary: MatchingVocabulary, spoken_cues: dict[str, list[str]]
) -> list[str]:
    """Written terms, spoken cues and the canonical key itself, deduplicated.

    The canonical key is included because an installation whose schema is in English gets
    matched for free, and because it is the one term guaranteed to exist.
    """
    terms = list(vocabulary.attribute_terms.get(attribute_key, []))
    terms.extend(spoken_cues.get(attribute_key, []))
    terms.extend(attribute_key.split("_"))
    seen: set[str] = set()
    ordered: list[str] = []
    for term in terms:
        folded = fold(term)
        if folded and folded not in seen:
            seen.add(folded)
            ordered.append(term)
    return ordered


def propose_value_map(
    attribute: CanonicalAttribute,
    domain: GisDomain,
    amd: AssetModel,
    enum_synonyms: dict[str, dict[str, list[str]]],
) -> ValueMapProposal:
    """Map canonical enum values onto a domain's codes by their display names.

    Greedy and global rather than per-value: assigning the best pair first stops a
    mediocre match stealing the code that a better one needed. Every canonical value that
    finds nothing is listed, because that list is exactly what refuses publication later.
    """
    enum_ref = attribute.enum_ref or ""
    canonical_values = amd.enums.get(enum_ref, [])
    proposal = ValueMapProposal(value_map_name=enum_ref, domain=domain.name)

    if domain.domain_type is not DomainType.CODED_VALUE:
        proposal.unmapped = list(canonical_values)
        return proposal

    synonyms = enum_synonyms.get(enum_ref, {})
    scored: list[tuple[float, str, str]] = []
    for value in canonical_values:
        terms = [*synonyms.get(value, []), value, *value.split("_")]
        for code, display in domain.coded_values.items():
            by_label, _ = _term_score(display, terms, strong=True)
            by_code, _ = _term_score(code, terms, strong=True)
            score = max(by_label, by_code)
            if score >= 0.4:
                scored.append((score, value, code))

    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    taken_values: set[str] = set()
    taken_codes: set[str] = set()
    for _score, value, code in scored:
        if value in taken_values or code in taken_codes:
            continue
        proposal.mapping[value] = code
        taken_values.add(value)
        taken_codes.add(code)

    proposal.unmapped = [v for v in canonical_values if v not in proposal.mapping]
    proposal.unclaimed = [c for c in domain.coded_values if c not in taken_codes]
    return proposal


def propose_attribute(
    asset_type: AssetType,
    attribute: CanonicalAttribute,
    layer: GisLayerMetadata,
    metadata: GisMetadata,
    amd: AssetModel,
    vocabulary: MatchingVocabulary,
    spoken_cues: dict[str, list[str]],
    enum_synonyms: dict[str, dict[str, list[str]]],
) -> AttributeProposal:
    """Rank the fields of one class as candidates for one canonical attribute."""
    proposal = AttributeProposal(
        attribute_key=attribute.key,
        attribute_type=attribute.type,
        required=attribute.required,
    )
    terms = _attribute_terms(attribute.key, vocabulary, spoken_cues)

    for field in layer.fields:
        name_score, winner = _term_score(f"{field.name} {field.alias or ''}", terms, strong=True)
        if name_score <= 0:
            continue

        refusal = field_is_eligible(field, vocabulary)
        if refusal is not None:
            proposal.refused.append(f"{field.name}: {refusal}")
            continue
        if not type_agrees(attribute, field):
            proposal.refused.append(
                f"{field.name}: es de tipo '{field.type}' y "
                f"'{attribute.key}' es '{attribute.type.value}'"
            )
            continue

        evidence = [
            Evidence(
                signal="nombre",
                detail=f"'{field.label}' coincide con el término «{winner}»",
                weight=name_score,
            )
        ]
        score = name_score * 0.80

        # A number where a string was asked for still works — a code is a code — but it is
        # not what the canonical type said, so it ranks below an exact agreement.
        if attribute.type is AttributeType.STRING and fold(field.type) != "string":
            score -= _LOOSE_TYPE_PENALTY
            evidence.append(
                Evidence(
                    signal="tipo",
                    detail=f"el código se guarda como '{field.type}', no como texto",
                    weight=-_LOOSE_TYPE_PENALTY,
                )
            )

        domain = metadata.domain(field.domain) if field.domain else None
        value_map: ValueMapProposal | None = None
        if attribute.type is AttributeType.ENUM:
            if domain is None:
                score -= 0.20
                evidence.append(
                    Evidence(
                        signal="dominio",
                        detail="el campo no tiene dominio; los valores no se pueden validar",
                        weight=-0.20,
                    )
                )
            else:
                value_map = propose_value_map(attribute, domain, amd, enum_synonyms)
                covered = len(value_map.mapping)
                total = len(amd.enums.get(attribute.enum_ref or "", [])) or 1
                bonus = 0.20 * (covered / total)
                score += bonus
                evidence.append(
                    Evidence(
                        signal="dominio",
                        detail=(
                            f"el dominio '{domain.name}' ofrece código para "
                            f"{covered} de {total} valores canónicos"
                        ),
                        weight=bonus,
                    )
                )

        if attribute.required and not field.nullable:
            score += 0.10
            evidence.append(
                Evidence(
                    signal="obligatoriedad",
                    detail="el campo no admite nulos, igual que el atributo canónico",
                    weight=0.10,
                )
            )

        proposal.candidates.append(
            FieldCandidate(
                field=field.name,
                label=field.label,
                score=round(max(score, 0.0), 4),
                evidence=evidence,
                domain=domain.name if domain else None,
                volatile_by_business_unit=bool(domain and domain.volatile_by_business_unit),
                value_map=value_map,
            )
        )

    proposal.candidates.sort(key=lambda c: (-c.score, c.field))
    del proposal.candidates[MAX_CANDIDATES:]
    return proposal


def distinctive_attribute_keys(amd: AssetModel) -> frozenset[str]:
    """Attribute keys that say something about *which kind* of asset a class holds.

    Anything present in more than half the canonical types is treated as universal: a code
    and a feeder describe every class in the model, so they cannot distinguish between them.
    """
    counts = Counter(
        attribute.key for asset_type in amd.asset_types for attribute in asset_type.attributes
    )
    limit = len(amd.asset_types) / 2
    return frozenset(key for key, seen in counts.items() if seen <= limit)


def _coverage(attributes: list[AttributeProposal]) -> float:
    """Weighted fraction of canonical attributes that found a field. Required ones count double."""
    weight = 0.0
    matched = 0.0
    for attribute in attributes:
        this = 2.0 if attribute.required else 1.0
        weight += this
        if attribute.best is not None:
            matched += this * min(attribute.best.score, 1.0)
    return matched / weight if weight else 0.0


def propose_layer(
    asset_type: AssetType,
    layer: GisLayerMetadata,
    metadata: GisMetadata,
    amd: AssetModel,
    vocabulary: MatchingVocabulary,
    spoken_cues: dict[str, list[str]],
    enum_synonyms: dict[str, dict[str, list[str]]],
) -> tuple[LayerCandidate, list[AttributeProposal]] | None:
    """Score one class as a candidate for one canonical asset type.

    Returns None when the class is disqualified — today that means its geometry is wrong,
    which is not a matter of degree: a canonical point asset cannot live on a polyline.
    """
    agreement = geometry_agrees(asset_type.geometry, layer.geometry_type)
    if agreement is False:
        return None

    evidence: list[Evidence] = []
    score = 0.0

    strong, strong_term = _term_score(
        layer.name, vocabulary.strong_for(asset_type.key), strong=True
    )
    weak, weak_term = _term_score(layer.name, vocabulary.weak_for(asset_type.key), strong=False)
    name_score = min(strong + weak * 0.5, 1.0)
    if strong_term:
        evidence.append(
            Evidence(
                signal="nombre",
                detail=f"el nombre de la clase contiene «{strong_term}»",
                weight=strong * WEIGHT_NAME,
            )
        )
    if weak_term:
        evidence.append(
            Evidence(
                signal="nombre",
                detail=f"el nombre también sugiere «{weak_term}»",
                weight=weak * 0.5 * WEIGHT_NAME,
            )
        )
    score += name_score * WEIGHT_NAME

    attributes = [
        propose_attribute(
            asset_type, attribute, layer, metadata, amd, vocabulary, spoken_cues, enum_synonyms
        )
        for attribute in asset_type.attributes
    ]
    coverage = _coverage(attributes)
    score += coverage * WEIGHT_ATTRIBUTES
    found = sum(1 for a in attributes if a.best is not None)
    evidence.append(
        Evidence(
            signal="estructura",
            detail=f"{found} de {len(attributes)} atributos canónicos encuentran un campo",
            weight=coverage * WEIGHT_ATTRIBUTES,
        )
    )

    if agreement is True:
        score += WEIGHT_GEOMETRY
        evidence.append(
            Evidence(
                signal="geometría",
                detail=f"la geometría es '{asset_type.geometry}', la que el tipo canónico pide",
                weight=WEIGHT_GEOMETRY,
            )
        )
    else:
        evidence.append(
            Evidence(
                signal="geometría",
                detail="el snapshot no declara la geometría de esta clase",
                weight=0.0,
            )
        )

    distinctive = distinctive_attribute_keys(amd)
    matched_distinctive = sum(
        1
        for attribute in attributes
        if attribute.attribute_key in distinctive and attribute.best is not None
    )
    if name_score <= 0 and (
        coverage < COVERAGE_WITHOUT_A_NAME or matched_distinctive < MIN_DISTINCTIVE_MATCHES
    ):
        # Neither the class name nor its structure says anything. Without this rule a class
        # of the wrong kind that merely has a code column and a feeder column clears the
        # score floor on the strength of the two most generic attributes in the vocabulary
        # — and every asset type ends up "matching" every point class.
        return None

    return (
        LayerCandidate(layer=layer.name, score=round(score, 4), evidence=evidence),
        attributes,
    )


def _propose_related(
    asset_type: AssetType, layer: GisLayerMetadata, metadata: GisMetadata
) -> list[RelatedProposal]:
    """One-to-many relationships that become a repeatable table on the form.

    The name of the repeatable block cannot be invented from the real class name without
    putting it into a form's property keys, which is precisely what RF-305 forbids. So the
    first one is called `units` — the pattern this capability exists for — and the rest get
    neutral names for the administrator to rename.
    """
    if not asset_type.has(Capability.HAS_UNITS):
        return []
    proposals: list[RelatedProposal] = []
    for index, relationship in enumerate(
        r for r in metadata.relationships_from(layer.name) if r.is_one_to_many
    ):
        proposals.append(
            # By alias: the field is `as_` in Python because `as` is a keyword, and the
            # profile document spells it `as`.
            RelatedProposal.model_validate(
                {
                    "as": "units" if index == 0 else f"related_{index + 1}",
                    "relationship": relationship.name,
                    "target_layer": relationship.destination_layer,
                    "cardinality": "one_to_many",
                }
            )
        )
    return proposals


def propose_profile(
    metadata: GisMetadata,
    amd: AssetModel | None = None,
    vocabulary: MatchingVocabulary | None = None,
) -> ProfileProposal:
    """Propose bindings for the whole canonical vocabulary from one metadata snapshot."""
    model = amd or load_asset_model()
    words = vocabulary or load_matching_vocabulary()
    spoken = load_spoken_vocabulary()
    proposal = ProfileProposal(profile_id=metadata.profile_id)
    claimed: set[str] = set()

    for asset_type in model.asset_types:
        scored: list[tuple[LayerCandidate, list[AttributeProposal]]] = []
        for layer in metadata.layers:
            result = propose_layer(
                asset_type,
                layer,
                metadata,
                model,
                words,
                spoken.attribute_cues,
                spoken.enum_synonyms,
            )
            if result and result[0].score >= MIN_CANDIDATE_SCORE:
                scored.append(result)

        scored.sort(key=lambda item: (-item[0].score, item[0].layer))
        top = scored[:MAX_CANDIDATES]
        best = top[0] if top else None
        if best:
            claimed.add(best[0].layer)

        layer_for_related = metadata.layer(best[0].layer) if best else None
        proposal.assets.append(
            AssetProposal(
                asset_type_key=asset_type.key,
                geometry=asset_type.geometry,
                candidates=[candidate for candidate, _ in top],
                attributes=best[1] if best else [],
                related=(
                    _propose_related(asset_type, layer_for_related, metadata)
                    if layer_for_related
                    else []
                ),
            )
        )

    proposal.unclaimed_layer_count = len(metadata.layers) - len(claimed)
    return proposal


# --- decisions ----------------------------------------------------------------------
class AssetDecision(BaseModel):
    """What a person decided for one canonical asset type.

    An attribute absent from ``attributes`` is deliberately unmapped, which is a legitimate
    answer: not every utility records the installation date of a pole. An attribute mapped
    to a field that does not exist is an error, and building the document says so.
    """

    layer: str
    attributes: dict[str, str] = Field(default_factory=dict)
    related: list[RelatedProposal] = Field(default_factory=list)
    participates_in_geometric_network: bool = False


class ProfileDecisions(BaseModel):
    header: ProfileHeader
    assets: dict[str, AssetDecision] = Field(default_factory=dict)


class DocumentError(Exception):
    """Raised when decisions name something the snapshot does not contain."""


def default_decisions(proposal: ProfileProposal, header: ProfileHeader) -> ProfileDecisions:
    """Pre-fill the decisions the evidence settles, and leave the rest empty.

    The point of assisted matching is that a person spends their attention on the hard
    cases. So an unambiguous leading candidate is pre-selected — and an ambiguous one is
    not, because pre-selecting a coin flip and calling it a default is how a wrong binding
    gets accepted by somebody clicking through.
    """
    decisions = ProfileDecisions(header=header)
    for asset in proposal.assets:
        if asset.best is None or asset.ambiguous:
            continue
        chosen = AssetDecision(layer=asset.best.layer, related=list(asset.related))
        for attribute in asset.attributes:
            if attribute.best is not None and not attribute.ambiguous:
                chosen.attributes[attribute.attribute_key] = attribute.best.field
        decisions.assets[asset.asset_type_key] = chosen
    return decisions


def build_profile_document(
    metadata: GisMetadata,
    decisions: ProfileDecisions,
    amd: AssetModel | None = None,
) -> dict[str, object]:
    """Turn accepted decisions into a profile document, ready to validate and version.

    Derived from the snapshot rather than from the proposal, so an administrator's own
    override gets its domain and value map computed exactly like a proposed one. There is
    no path by which a hand-picked field ends up with a value map nobody generated.
    """
    model = amd or load_asset_model()
    spoken = load_spoken_vocabulary()
    bindings: dict[str, object] = {}
    value_maps: dict[str, dict[str, object]] = {}

    for asset_key in model.asset_type_keys:
        decision = decisions.assets.get(asset_key)
        if decision is None:
            continue
        asset_type = model.asset_type(asset_key)
        layer = metadata.layer(decision.layer)
        if layer is None:
            raise DocumentError(
                f"'{asset_key}' apunta a la clase '{decision.layer}', "
                "que no está en los metadatos sincronizados"
            )

        attributes: dict[str, object] = {}
        for attribute_key, field_name in decision.attributes.items():
            attribute = asset_type.attribute(attribute_key)
            if attribute is None:
                raise DocumentError(
                    f"'{asset_key}.{attribute_key}' no existe en el vocabulario canónico"
                )
            field = layer.field(field_name)
            if field is None:
                raise DocumentError(
                    f"'{asset_key}.{attribute_key}' apunta al campo '{field_name}', "
                    f"que no está en la clase '{layer.name}'"
                )
            refusal = field_is_eligible(field, load_matching_vocabulary())
            if refusal is not None:
                # Reachable only by an override: the proposal never offers these. Refusing
                # here as well is what makes ADR-001 hold against a hand-edited draft.
                raise DocumentError(
                    f"'{asset_key}.{attribute_key}' no puede apuntar a '{field.name}': {refusal}"
                )

            domain = metadata.domain(field.domain) if field.domain else None
            binding: dict[str, object] = {"field": field.name}
            if domain is not None:
                binding["domain"] = domain.name
                if domain.volatile_by_business_unit:
                    binding["volatile_by_business_unit"] = True
            if attribute.type is AttributeType.ENUM and domain is not None:
                proposed = propose_value_map(attribute, domain, model, spoken.enum_synonyms)
                name = attribute.enum_ref or attribute_key
                existing = value_maps.get(name)
                if existing is not None and existing != dict(proposed.mapping):
                    # Two asset types share a canonical enum but map it onto different
                    # domains. Both are right; they just cannot share one table.
                    name = f"{name}@{asset_key}"
                value_maps[name] = dict(proposed.mapping)
                binding["value_map"] = name
            attributes[attribute_key] = binding

        bindings[asset_key] = {
            "layer": layer.name,
            "participates_in_geometric_network": decision.participates_in_geometric_network,
            # Never proposed as direct. RF-345 makes direct writes an opt-in decision per
            # class after GIS sign-off, and an importer is not where that gets decided.
            "write_path": WritePath.STAGING_ONLY.value,
            "attributes": attributes,
            "related": [
                {
                    "as": related.as_,
                    "relationship": related.relationship,
                    "target_layer": related.target_layer,
                    "cardinality": related.cardinality,
                }
                for related in decision.related
            ],
        }

    return {
        "profile": decisions.header.model_dump(mode="json", exclude_none=True),
        "bindings": bindings,
        "value_maps": value_maps,
        "never_write_fields": sorted(NEVER_WRITE_FIELDS),
    }


def validate_document(document: dict[str, object], amd: AssetModel | None = None) -> list[str]:
    """Every reason this document is not yet a working profile, in Spanish.

    Structural problems and completeness problems in one list, because an administrator
    fixing a draft cares about what is wrong, not about which layer noticed.
    """
    try:
        profile = DataModelProfile.model_validate(document)
    except ValidationError as exc:
        return [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
    return validate_against_amd(profile, amd)


def render_profile_yaml(document: dict[str, object]) -> str:
    """The document as the YAML that belongs in `profiles/`.

    A published profile lives in the database so a unit can adopt it without a deployment,
    and is exported here so it can be committed and reviewed like the configuration it is.
    A schema mapping that only ever existed in a production database is one nobody can
    diff when the data goes wrong.
    """
    header = (
        "# Generado por el importador de perfiles de SIGEC-Campo (RF-301).\n"
        "# Revisado y aceptado por una persona; los nombres reales viven aquí y solo aquí\n"
        "# (ADR-004, RF-305).\n\n"
    )
    return header + yaml.safe_dump(document, allow_unicode=True, sort_keys=False)


def propose_asset_against(
    metadata: GisMetadata,
    asset_type_key: str,
    layer_name: str,
    amd: AssetModel | None = None,
) -> AssetProposal:
    """Re-score one asset type against a class the administrator chose themselves.

    The screen needs this the moment somebody rejects the leading candidate: the attribute
    proposals on display belonged to the class that was rejected, and showing them against
    the new one is the difference between a tool and a form.
    """
    model = amd or load_asset_model()
    words = load_matching_vocabulary()
    spoken = load_spoken_vocabulary()
    asset_type = model.asset_type(asset_type_key)
    layer = metadata.layer(layer_name)
    if layer is None:
        raise DocumentError(
            f"la clase '{layer_name}' no está en los metadatos sincronizados"
        )

    scored = propose_layer(
        asset_type, layer, metadata, model, words, spoken.attribute_cues, spoken.enum_synonyms
    )
    if scored is None:
        # A deliberate choice against the geometry is still allowed — the administrator may
        # know something the snapshot does not — but it is scored at zero and the evidence
        # says why, rather than being quietly accepted.
        candidate = LayerCandidate(
            layer=layer.name,
            score=0.0,
            evidence=[
                Evidence(
                    signal="geometría",
                    detail=(
                        f"la clase es '{normalise_geometry(layer.geometry_type)}' y el tipo "
                        f"canónico pide '{asset_type.geometry}'"
                    ),
                    weight=0.0,
                )
            ],
        )
        attributes = [
            propose_attribute(
                asset_type,
                attribute,
                layer,
                metadata,
                model,
                words,
                spoken.attribute_cues,
                spoken.enum_synonyms,
            )
            for attribute in asset_type.attributes
        ]
    else:
        candidate, attributes = scored

    return AssetProposal(
        asset_type_key=asset_type_key,
        geometry=asset_type.geometry,
        candidates=[candidate],
        attributes=attributes,
        related=_propose_related(asset_type, layer, metadata),
    )
