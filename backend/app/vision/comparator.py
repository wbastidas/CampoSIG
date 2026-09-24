"""Before and after: does the photograph show the work that was claimed? (RF-048, I11)

A closing photograph is the one piece of evidence a supervisor actually looks at, and the
one a hurried technician is most tempted to reuse. Two failures matter and they are
different:

* **The same photograph submitted twice.** Caught by content hash, not by vision — an
  identical file is identical, and no model is needed to say so.
* **A genuinely different photograph that does not show the work done.** That is what this
  module is for: the finding that justified the order is still visible in the after shot.

The comparator never rejects anything. It produces a reading, with the evidence behind it,
for the person who decides. A model that closed work orders would be the single worst idea
in this platform.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.vision.contracts import ImageAnalysis
from app.vision.taxonomy import VisionTaxonomy, load_taxonomy


class Verdict(StrEnum):
    """What the pair of photographs supports."""

    #: A finding present before is resolved after, matching a declared resolution pair.
    RESOLVED = "resuelto"
    #: A finding present before is still present after.
    UNCHANGED = "sin_cambio"
    #: Something is visible after that was not visible before.
    NEW_FINDING = "hallazgo_nuevo"
    #: The models did not run, or produced nothing to compare.
    INCONCLUSIVE = "no_concluyente"


@dataclass
class Observation:
    verdict: Verdict
    class_key: str
    label: str
    detail: str
    confidence: float


@dataclass
class Comparison:
    observations: list[Observation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    #: True when the two photographs are byte-identical. Not a vision result at all — and
    #: the strongest signal in the module.
    identical_evidence: bool = False

    @property
    def verdict(self) -> Verdict:
        """The reading a supervisor sees first.

        Deliberately pessimistic: one unresolved finding outweighs three resolved ones,
        because the unresolved one is the reason someone has to go back.
        """
        if self.identical_evidence or not self.observations:
            return Verdict.INCONCLUSIVE
        verdicts = {observation.verdict for observation in self.observations}
        for candidate in (Verdict.UNCHANGED, Verdict.NEW_FINDING, Verdict.RESOLVED):
            if candidate in verdicts:
                return candidate
        return Verdict.INCONCLUSIVE

    @property
    def supports_closure(self) -> bool:
        """Whether the evidence supports what the technician claims, on its own terms.

        Never consulted as an approval: the review gate is a person (M11). This is what the
        review screen highlights, so the supervisor looks at the right photograph first.
        """
        return self.verdict is Verdict.RESOLVED


def compare(
    before: ImageAnalysis,
    after: ImageAnalysis,
    *,
    taxonomy: VisionTaxonomy | None = None,
    before_hash: str | None = None,
    after_hash: str | None = None,
) -> Comparison:
    """Compare the findings in a before and an after photograph.

    :param before_hash: content hashes, when known. Identical hashes short-circuit the whole
        comparison: the same file cannot show a before and an after.
    """
    tax = taxonomy or load_taxonomy()
    comparison = Comparison()

    if before_hash and after_hash and before_hash == after_hash:
        comparison.identical_evidence = True
        comparison.warnings.append(
            "la foto de antes y la de después son el mismo archivo; no pueden documentar "
            "un trabajo ejecutado"
        )
        return comparison

    if before.models_unavailable or after.models_unavailable:
        comparison.warnings.append(
            "una de las fotografías no se analizó porque el dispositivo no tenía el paquete "
            "de modelos; la comparación queda a criterio de quien revisa"
        )
        return comparison

    before_findings = {
        key: before.of_class(key) for key in before.class_keys if tax.finding(key) is not None
    }
    after_keys = after.class_keys

    for key, prediction in before_findings.items():
        if prediction is None:  # pragma: no cover - keys come from the predictions
            continue
        finding = tax.finding(key)
        assert finding is not None
        pair = tax.resolution_for(key)
        gone = key not in after_keys
        satisfied = pair is not None and (
            (pair.after is None and gone) or (pair.after is not None and pair.after in after_keys)
        )

        if satisfied and pair is not None:
            comparison.observations.append(
                Observation(
                    verdict=Verdict.RESOLVED,
                    class_key=key,
                    label=finding.label,
                    detail=pair.resolves,
                    confidence=prediction.confidence,
                )
            )
        elif gone:
            # Absent, but no declared pair says that absence means the work was done. A
            # finding can disappear because the photograph was taken from further away.
            comparison.observations.append(
                Observation(
                    verdict=Verdict.INCONCLUSIVE,
                    class_key=key,
                    label=finding.label,
                    detail=(
                        "ya no se ve en la foto de después, pero no hay un par declarado "
                        "que confirme que eso significa trabajo ejecutado"
                    ),
                    confidence=prediction.confidence,
                )
            )
        else:
            comparison.observations.append(
                Observation(
                    verdict=Verdict.UNCHANGED,
                    class_key=key,
                    label=finding.label,
                    detail="sigue visible en la fotografía de después",
                    confidence=prediction.confidence,
                )
            )

    for key in sorted(after_keys - set(before_findings)):
        finding = tax.finding(key)
        if finding is None or finding.severity == "ninguna":
            # A neutral class — a lamp that is lit — is not a new problem.
            continue
        prediction = after.of_class(key)
        assert prediction is not None
        comparison.observations.append(
            Observation(
                verdict=Verdict.NEW_FINDING,
                class_key=key,
                label=finding.label,
                detail="aparece en la foto de después y no estaba en la de antes",
                confidence=prediction.confidence,
            )
        )

    return comparison
