"""Where the gateway meets the rest of the backend (RF-204).

Two jobs, and the second one is the point:

* build a :class:`ModelGateway` from settings, so no caller constructs a transport;
* answer "what will not be available, and why" **without calling anything**.

The second matters because of where the answer is shown: on the supervisor's review screen, in a
request that must not wait on a model service. So the notices come from configuration and the
server profile — deployment facts, known instantly — and never from a health probe inside the
request. Probing is a worker's job; a review screen that waited two seconds to discover the GPU is
missing would have taken two seconds away from somebody for no information they could act on.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.inference.admission import Placement, admit
from app.inference.client import CHAT_PATH, DEFAULT_TIMEOUT_SECONDS, ModelGateway
from app.inference.registry import load_registry
from app.settings import get_settings

#: The aliases the pre-review graph needs (M17). Listed here rather than in the graph because the
#: review screen has to warn about them before the graph exists.
PRE_REVIEW_ALIASES = ("llm-judge", "vlm-audit")


@dataclass(frozen=True)
class Degradation:
    """One thing that will not happen, in words a supervisor can read."""

    alias: str
    purpose: str
    placement: str
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {
            "alias": self.alias,
            "purpose": self.purpose,
            "placement": self.placement,
            "reason": self.reason,
        }


def _http_transport(base_url: str) -> Any:
    """A transport over the configured gateway.

    Built lazily so httpx is not imported on a deployment that has no gateway.
    """
    import httpx

    def send(path: str, body: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        with httpx.Client(base_url=base_url, timeout=DEFAULT_TIMEOUT_SECONDS) as client:
            answer = client.post(path, json=dict(body))
            try:
                payload = answer.json()
            except ValueError:
                payload = {}
            return answer.status_code, payload if isinstance(payload, Mapping) else {}

    return send


def gateway() -> ModelGateway | None:
    """The gateway for this deployment, or None when none is configured.

    None rather than a client pointing at nothing: a connector that is not deployed yet is not an
    error, and callers already have to handle unavailability (RF-204). Returning a client that
    always fails would burn a timeout to learn what a setting already said.
    """
    settings = get_settings()
    if not settings.model_gateway_url:
        return None
    return ModelGateway(
        transport=_http_transport(settings.model_gateway_url),
        profile=settings.inference_profile,
    )


def pre_review_degradations() -> list[Degradation]:
    """What the pre-review will not do on this deployment, and why (RF-204).

    Computed from settings and the profile, with no network call — see the module docstring. An
    empty list means everything the pre-review needs runs in line.
    """
    settings = get_settings()
    registry = load_registry()
    configured = bool(settings.model_gateway_url)

    found: list[Degradation] = []
    for alias_name in PRE_REVIEW_ALIASES:
        alias = registry.alias(alias_name)
        decision = admit(
            alias_name,
            settings.inference_profile,
            gateway_reachable=configured,
            registry=registry,
        )
        if decision.placement is Placement.INTERACTIVE:
            continue
        reason = decision.reason
        if not configured:
            reason = "la pasarela de modelos no está configurada en este despliegue"
            reason += (
                "; pasa al lote nocturno"
                if decision.placement is Placement.NIGHT_BATCH
                else "; se omite con aviso"
            )
        found.append(
            Degradation(
                alias=alias_name,
                purpose=alias.purpose,
                placement=decision.placement.value,
                reason=reason,
            )
        )
    return found


__all__ = ["CHAT_PATH", "PRE_REVIEW_ALIASES", "Degradation", "gateway", "pre_review_degradations"]
