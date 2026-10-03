"""From what a model saw to what a form offers (RF-140, I11).

The link is ``x-vision-source``, which the form generator already stamps on every field of
an asset type that declares the ``ai_vision`` capability. A classifier says
"support_structure.material is concrete"; the form field carrying that source is the one
that gets the proposal. Neither side has to know the other's field names — the canonical
key is the whole contract (ADR-004).

Everything here is a proposal. The same rule as voice, for the same reason: a value the
machine produced is not an answer until a person says it is (SRS rule 0.5, ADR-011).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.vision.contracts import BoundingBox, ImageAnalysis
from app.vision.taxonomy import VisionTaxonomy, load_taxonomy


@dataclass(frozen=True)
class VisionProposal:
    """One field value a vision model proposes."""

    field_key: str
    value: Any
    confidence: float
    #: Which evidence, and where in it. A proposal a reviewer cannot look at is not
    #: reviewable, and an unreviewable AI value should not exist.
    evidence_key: str
    box: BoundingBox | None
    rationale: str
    model_name: str
    model_version: str


@dataclass
class VisionFinding:
    """Something to report, which is not a value of any inventory field."""

    key: str
    label: str
    severity: str
    confidence: float
    evidence_key: str
    box: BoundingBox | None = None


@dataclass
class PrefillResult:
    proposals: list[VisionProposal] = field(default_factory=list)
    findings: list[VisionFinding] = field(default_factory=list)
    #: Predictions that were dropped, and why. Shown so a technician who can see a broken
    #: insulator in the photo is told the model saw it too but was not sure enough — which
    #: is very different from the model not having looked.
    discarded: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def values(self) -> dict[str, Any]:
        return {p.field_key: p.value for p in self.proposals}


def _vision_fields(schema: dict[str, Any]) -> dict[str, str]:
    """``x-vision-source`` → field key, for the fields of this form."""
    sources: dict[str, str] = {}
    for key, prop in schema.get("properties", {}).items():
        if not isinstance(prop, dict):
            continue
        source = prop.get("x-vision-source")
        if isinstance(source, str):
            sources[source] = key
    return sources


def prefill_from_analysis(
    analysis: ImageAnalysis,
    schema: dict[str, Any],
    *,
    taxonomy: VisionTaxonomy | None = None,
) -> PrefillResult:
    """Turn one photograph's predictions into field proposals and findings.

    Thresholds come from the taxonomy, per class, and are applied here rather than on the
    device: a device that shipped with a permissive threshold would otherwise keep proposing
    values nobody trusts, and the fix would need an app release instead of a config change.
    """
    tax = taxonomy or load_taxonomy()
    result = PrefillResult()

    if analysis.models_unavailable:
        # Distinct from "saw nothing". A technician must not read an empty result as the
        # photograph being clean.
        result.warnings.append(
            "este dispositivo no tiene el paquete de modelos de visión; la foto no se "
            "analizó y no hay nada que revisar"
        )
        return result

    sources = _vision_fields(schema)

    for prediction in analysis.predictions:
        # Whether the class is known comes first. An unknown class has no threshold it can
        # clear, so checking confidence first would file it away as "not confident enough" —
        # a misleading reason for what is really a device running a model the platform does
        # not know about.
        if not _is_known(prediction, tax):
            result.warnings.append(
                f"el modelo devolvió la clase '{prediction.class_key}', que no está en la "
                "taxonomía; revisar la versión del paquete de modelos del dispositivo"
            )
            continue

        threshold = tax.threshold(prediction.classifier_key or prediction.class_key)
        if prediction.confidence < threshold:
            result.discarded.append(
                f"'{prediction.class_key}' con confianza {prediction.confidence:.2f}, "
                f"por debajo del umbral {threshold:.2f}"
            )
            continue

        if prediction.classifier_key:
            proposal, problem = _attribute_proposal(prediction, analysis, sources, tax)
            if proposal is not None:
                result.proposals.append(proposal)
            if problem:
                result.warnings.append(problem)
            continue

        finding = tax.finding(prediction.class_key)
        if finding is not None:
            result.findings.append(
                VisionFinding(
                    key=finding.key,
                    label=finding.label,
                    severity=finding.severity,
                    confidence=prediction.confidence,
                    evidence_key=analysis.evidence_key,
                    box=prediction.box,
                )
            )
            continue

        # What remains is a detection of an object: useful for framing and for suggesting a
        # work order, but not a value of any field, so it proposes nothing here.

    return result


def _is_known(prediction: Any, taxonomy: VisionTaxonomy) -> bool:
    """Whether the taxonomy declares this prediction's class at all.

    A classifier's labels are known through the classifier, not as classes of their own:
    "concrete" is a label of `pole_material`, not a detection class. So a prediction that
    names a classifier is passed through here and judged by `_attribute_proposal`, which can
    say precisely what is wrong — an unknown classifier, or a label the classifier has no
    canonical value for — instead of the generic "not in the taxonomy".
    """
    if prediction.classifier_key:
        return True
    return (
        taxonomy.detection(prediction.class_key) is not None
        or taxonomy.finding(prediction.class_key) is not None
    )


def _attribute_proposal(
    prediction: Any,
    analysis: ImageAnalysis,
    sources: dict[str, str],
    taxonomy: VisionTaxonomy,
) -> tuple[VisionProposal | None, str | None]:
    """Map one classifier output onto a form field, or explain why it cannot be mapped."""
    classifier = taxonomy.classifier(prediction.classifier_key)
    if classifier is None:
        return None, (
            f"el dispositivo usó el clasificador '{prediction.classifier_key}', que no está "
            "en la taxonomía"
        )
    canonical = classifier.canonical_value(prediction.class_key)
    if canonical is None:
        return None, (
            f"'{classifier.key}' devolvió la etiqueta '{prediction.class_key}', que no tiene "
            "valor canónico; el modelo y la taxonomía están desalineados"
        )

    source = f"{classifier.asset_type}.{classifier.attribute}"
    field_key = sources.get(source)
    if field_key is None:
        # Not an error: a maintenance form may simply not ask for the material. Silence is
        # the right behaviour, so this is not even a warning.
        return None, None

    return (
        VisionProposal(
            field_key=field_key,
            value=canonical,
            confidence=prediction.confidence,
            evidence_key=analysis.evidence_key,
            box=prediction.box,
            rationale=f"{classifier.label}: «{prediction.class_key}» en la fotografía",
            model_name=prediction.model_name,
            model_version=prediction.model_version,
        ),
        None,
    )
