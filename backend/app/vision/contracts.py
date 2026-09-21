"""What a vision model returns, and the interfaces it sits behind (CLAUDE.md rule 12).

The models themselves — a D-FINE detector and a MobileNetV3 state classifier, both ONNX
int8 — run on the phone. Nothing in the platform calls them directly: the app programs
against ``ObjectDetector`` and ``StateClassifier``, and the server programs against the
predictions they produce. That seam is what lets the models be replaced, or be missing
entirely on a device that has not downloaded its package yet, without anything else
changing.

Every prediction carries its model name and version. A proposal whose model is unknown is
not traceable, and an untraceable AI value is one nobody can audit later (RF-052).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class BoundingBox:
    """Normalized to the image, so a box survives resizing and re-encoding."""

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        for name, value in (
            ("x", self.x),
            ("y", self.y),
            ("width", self.width),
            ("height", self.height),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"la caja tiene '{name}' fuera de [0, 1]: {value}")

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass(frozen=True)
class Prediction:
    """One thing a model claims to see."""

    #: A key of the vision taxonomy: a detection class, a finding, or a classifier label.
    class_key: str
    confidence: float
    box: BoundingBox | None = None
    #: For an attribute classifier: which classifier produced this label.
    classifier_key: str | None = None
    model_name: str = "unknown"
    model_version: str = "0"

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confianza fuera de [0, 1]: {self.confidence}")


@dataclass(frozen=True)
class ImageAnalysis:
    """Everything the on-device models said about one photograph."""

    #: The evidence this came from. Predictions with no evidence behind them cannot be
    #: reviewed, so the link is required rather than optional.
    evidence_key: str
    predictions: tuple[Prediction, ...] = ()
    #: True when the device had no model package and produced nothing. Distinct from "the
    #: models ran and saw nothing", which is information.
    models_unavailable: bool = False

    def of_class(self, class_key: str) -> Prediction | None:
        """The most confident prediction of a class, if any."""
        matching = [p for p in self.predictions if p.class_key == class_key]
        return max(matching, key=lambda p: p.confidence) if matching else None

    @property
    def class_keys(self) -> set[str]:
        return {p.class_key for p in self.predictions}


class ObjectDetector(Protocol):
    """Finds assets and findings in a photograph."""

    def detect(self, image: bytes, *, evidence_key: str) -> ImageAnalysis: ...


class StateClassifier(Protocol):
    """Classifies the state or an attribute of an already-located asset."""

    def classify(
        self, image: bytes, *, evidence_key: str, box: BoundingBox | None = None
    ) -> ImageAnalysis: ...
