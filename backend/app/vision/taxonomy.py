"""The vision taxonomy, validated against the canonical vocabulary (addendum 6.2, SRS annex B).

A visual class points at a canonical asset type, and the resolver takes it from there to the
real field of whichever business unit is being served. That indirection is what makes the
claim "adding a business unit does not require retraining vision" true rather than hopeful:
what changes is the profile, not the weights.

The validation is the useful part. A classifier that proposes ``fiberglass`` for an attribute
whose canonical enumeration never had that value is not a bad prediction — it is a value that
cannot be written anywhere, and the failure would surface as an unexplainable rejection long
after the model shipped. So it is caught at load time.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from app.model_profile.amd import AssetModel, load_asset_model


class TaxonomyError(Exception):
    """Raised when the taxonomy cannot be reconciled with the canonical vocabulary."""


class DetectionClass(BaseModel):
    key: str
    label: str
    #: The canonical asset type this class is an instance of, or None when the thing is
    #: worth seeing but is not an asset in its own right (an insulator, a crossarm).
    asset_type: str | None = None
    min_confidence: float | None = None


class AttributeClassifier(BaseModel):
    """A classifier that proposes the value of one canonical attribute."""

    key: str
    label: str
    asset_type: str
    attribute: str
    #: classifier label -> canonical enum value.
    values: dict[str, str] = Field(default_factory=dict)
    min_confidence: float | None = None

    def canonical_value(self, label: str) -> str | None:
        return self.values.get(label)


class FindingClass(BaseModel):
    """Something to report rather than something to record on the asset."""

    key: str
    label: str
    severity: str = "media"
    min_confidence: float | None = None


class ResolutionPair(BaseModel):
    """A before/after pair that demonstrates the work was done."""

    before: str
    #: None means "the finding is simply gone in the after photo".
    after: str | None = None
    resolves: str


class VisionTaxonomy(BaseModel):
    version: int
    domain: str
    default_min_confidence: float = 0.6
    detection_classes: list[DetectionClass] = Field(default_factory=list)
    attribute_classifiers: list[AttributeClassifier] = Field(default_factory=list)
    finding_classes: list[FindingClass] = Field(default_factory=list)
    resolution_pairs: list[ResolutionPair] = Field(default_factory=list)

    def detection(self, key: str) -> DetectionClass | None:
        return next((c for c in self.detection_classes if c.key == key), None)

    def finding(self, key: str) -> FindingClass | None:
        return next((c for c in self.finding_classes if c.key == key), None)

    def classifier(self, key: str) -> AttributeClassifier | None:
        return next((c for c in self.attribute_classifiers if c.key == key), None)

    def classifiers_for(self, asset_type_key: str) -> list[AttributeClassifier]:
        return [c for c in self.attribute_classifiers if c.asset_type == asset_type_key]

    def threshold(self, key: str) -> float:
        """The confidence a prediction of this class must clear to be shown at all."""
        for collection in (self.detection_classes, self.finding_classes):
            found = next((c for c in collection if c.key == key), None)
            if found is not None:
                return found.min_confidence or self.default_min_confidence
        classifier = self.classifier(key)
        if classifier is not None:
            return classifier.min_confidence or self.default_min_confidence
        # An unknown class has no threshold it can clear. Refusing beats guessing a default
        # for a model output nobody declared.
        return 1.1

    def resolution_for(self, before_key: str) -> ResolutionPair | None:
        return next((p for p in self.resolution_pairs if p.before == before_key), None)


def validate_against_amd(taxonomy: VisionTaxonomy, amd: AssetModel | None = None) -> list[str]:
    """Problems between the taxonomy and the canonical vocabulary, in readable Spanish.

    Returned rather than raised so the admin screen can show every gap at once, the same way
    the profile diagnostic does (RF-302).
    """
    model = amd or load_asset_model()
    problems: list[str] = []
    known_types = set(model.asset_type_keys)

    for detection in taxonomy.detection_classes:
        if detection.asset_type and detection.asset_type not in known_types:
            problems.append(
                f"la clase visual '{detection.key}' apunta al tipo de activo "
                f"'{detection.asset_type}', que no existe en el vocabulario canónico"
            )

    for classifier in taxonomy.attribute_classifiers:
        if classifier.asset_type not in known_types:
            problems.append(
                f"el clasificador '{classifier.key}' apunta al tipo de activo "
                f"'{classifier.asset_type}', que no existe en el vocabulario canónico"
            )
            continue
        asset_type = model.asset_type(classifier.asset_type)
        attribute = asset_type.attribute(classifier.attribute)
        if attribute is None:
            problems.append(
                f"el clasificador '{classifier.key}' apunta al atributo "
                f"'{classifier.asset_type}.{classifier.attribute}', que no existe"
            )
            continue
        if not attribute.enum_ref:
            problems.append(
                f"el clasificador '{classifier.key}' propone valores para "
                f"'{classifier.attribute}', que no es un campo de catálogo"
            )
            continue
        canonical_values = set(model.enums.get(attribute.enum_ref, []))
        unknown = sorted(set(classifier.values.values()) - canonical_values)
        if unknown:
            problems.append(
                f"el clasificador '{classifier.key}' propone valores que no existen en "
                f"'{attribute.enum_ref}': {', '.join(unknown)}"
            )

    known_predictions = {c.key for c in taxonomy.detection_classes} | {
        c.key for c in taxonomy.finding_classes
    }
    for pair in taxonomy.resolution_pairs:
        if pair.before not in known_predictions:
            problems.append(
                f"el par de resolución parte de '{pair.before}', que no es una clase conocida"
            )
        if pair.after is not None and pair.after not in known_predictions:
            problems.append(
                f"el par de resolución termina en '{pair.after}', que no es una clase conocida"
            )
    return problems


@lru_cache
def load_taxonomy(path: str | None = None) -> VisionTaxonomy:
    """Load, validate and cache the vision taxonomy.

    :raises TaxonomyError: if it cannot be reconciled with the canonical vocabulary. This
        one *does* raise: a taxonomy that points at attributes which do not exist would let
        a model propose values nothing can store, and starting the service in that state
        only moves the failure to somewhere less visible.
    """
    default = Path(__file__).resolve().parents[3] / "profiles" / "amd" / "vision-taxonomy.yaml"
    location = Path(path) if path else default
    data = yaml.safe_load(location.read_text(encoding="utf-8"))
    taxonomy = VisionTaxonomy.model_validate(data)
    problems = validate_against_amd(taxonomy)
    if problems:
        raise TaxonomyError(
            "la taxonomía de visión no concuerda con el vocabulario canónico: "
            + "; ".join(problems)
        )
    return taxonomy
