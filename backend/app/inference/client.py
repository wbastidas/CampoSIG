"""The OpenAI-compatible gateway client (RF-200, RF-201, RF-204).

Every server-side LLM and VLM call goes through here, by alias (rule 13). What that buys is in
RF-200's acceptance criterion: changing the model behind an alias requires no change in the agents'
code. What it costs is one indirection, which is cheap next to a migration between runtimes.

RF-201 is the `grammar` and `json_schema` arguments: a call that expects JSON must constrain the
decoder rather than hope and parse. An alias that cannot constrain its output refuses the request
instead of returning prose somebody would then try to `json.loads`.

RF-204 is the whole reason :class:`ModelUnavailableError` exists and nothing here retries forever. A
model service that is down, slow or out of memory raises, the caller degrades, and a person carries
on working. The one thing this module must never do is make somebody wait: there is no blocking
retry loop, no unbounded timeout, and no queue inside a request.

The transport is injected. A test that needed a model server would be a test nobody runs, and the
interesting behaviour here is what happens when the server misbehaves — which is easiest to arrange
with a fake.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.inference.admission import Admission, admit
from app.inference.registry import InferenceRegistry, load_registry

#: What a transport must look like: take the path and the JSON body, return status and body.
#: Deliberately not `httpx.Client`: the gateway speaks one endpoint and a narrow contract, and
#: typing it this way is what lets the tests drive the failures that matter.
Transport = Callable[[str, Mapping[str, Any]], tuple[int, Mapping[str, Any]]]

CHAT_PATH = "/v1/chat/completions"

#: Hard ceiling on one call. Past this the answer is not worth waiting for: a supervisor looking
#: at a review screen would rather see "the report is not available" than a spinner.
DEFAULT_TIMEOUT_SECONDS = 30.0


class ModelUnavailableError(Exception):
    """The model service could not answer. Callers degrade; nobody waits.

    Carries the admission decision when there is one, so the caller can tell a supervisor whether
    the work was queued for tonight or dropped — "no está disponible" without which of the two is
    an answer that invites somebody to keep refreshing.
    """

    def __init__(self, reason: str, admission: Admission | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.admission = admission


class GrammarNotSupportedError(Exception):
    """Raised when a call wants constrained output from an alias that cannot constrain it.

    Refused rather than downgraded to free text (RF-201): a caller that asked for JSON is a caller
    that will parse the answer, and prose from a model is the failure mode that produces one bad
    record out of every few hundred — the hardest kind to notice.
    """


@dataclass(frozen=True)
class Completion:
    """What the gateway returned, plus what it cost."""

    alias: str
    model: str
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    #: Latency in milliseconds, for the metrics of RF-205.
    latency_ms: int = 0


@dataclass
class GatewayMetrics:
    """Counters for the observability dashboard (RF-205).

    In memory and per process: this is what a scrape endpoint reads, not a billing record. The
    degradation counters are the ones worth an alert — a profile that silently sends everything to
    the night queue is a profile somebody should look at.
    """

    calls: dict[str, int] = field(default_factory=dict)
    failures: dict[str, int] = field(default_factory=dict)
    degraded: dict[str, int] = field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def record_call(self, alias: str, completion: Completion) -> None:
        self.calls[alias] = self.calls.get(alias, 0) + 1
        self.prompt_tokens += completion.prompt_tokens
        self.completion_tokens += completion.completion_tokens

    def record_failure(self, alias: str) -> None:
        self.failures[alias] = self.failures.get(alias, 0) + 1

    def record_degradation(self, alias: str) -> None:
        self.degraded[alias] = self.degraded.get(alias, 0) + 1


class ModelGateway:
    """Calls models by alias, and degrades instead of blocking.

    :param profile: the server profile this deployment runs on (SRS 7.9).
    :param transport: how requests reach the gateway. Injected so the failures that matter are
        testable without a model server.
    """

    def __init__(
        self,
        transport: Transport,
        profile: str,
        registry: InferenceRegistry | None = None,
        metrics: GatewayMetrics | None = None,
    ) -> None:
        self.transport = transport
        self.profile = profile
        self.registry = registry or load_registry()
        self.metrics = metrics or GatewayMetrics()
        # Which aliases are loaded right now, for RF-203. Tracked rather than asked because the
        # gateway does not expose it, and the admission policy needs an answer either way.
        self._resident: set[str] = set()

    @property
    def resident(self) -> frozenset[str]:
        return frozenset(self._resident)

    def admission_for(self, alias: str, *, reachable: bool = True) -> Admission:
        return admit(
            alias,
            self.profile,
            gateway_reachable=reachable,
            resident=self.resident,
            registry=self.registry,
        )

    def complete(
        self,
        alias_name: str,
        messages: Sequence[Mapping[str, Any]],
        *,
        grammar: str | None = None,
        json_schema: Mapping[str, Any] | None = None,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> Completion:
        """One chat completion, by alias.

        :raises GrammarNotSupportedError: when constrained output is asked of an alias that cannot.
        :raises ModelUnavailableError: when the profile will not run it now, or the service did not
            answer. Either way the caller degrades and the person keeps working (RF-204).
        """
        alias = self.registry.alias(alias_name)

        if (grammar or json_schema) and not alias.supports_grammar:
            raise GrammarNotSupportedError(
                f"'{alias_name}' no admite decodificación restringida y la llamada espera JSON "
                "(RF-201); no se pide texto libre para luego intentar parsearlo"
            )

        decision = self.admission_for(alias_name)
        if not decision.runs_now:
            self.metrics.record_degradation(alias_name)
            raise ModelUnavailableError(decision.reason, decision)

        body: dict[str, Any] = {
            # The alias travels as the model name: that is the whole point of an
            # OpenAI-compatible gateway, and it is why no agent knows a model name.
            "model": alias_name,
            "messages": list(messages),
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if grammar:
            # llama.cpp's extension. A gateway in front of vLLM maps it to XGrammar.
            body["grammar"] = grammar
        if json_schema:
            body["response_format"] = {"type": "json_schema", "json_schema": json_schema}

        try:
            status, payload = self.transport(CHAT_PATH, body)
        except Exception as cause:  # a transport failure is a degradation, not a crash
            self.metrics.record_failure(alias_name)
            fallback = self.admission_for(alias_name, reachable=False)
            self.metrics.record_degradation(alias_name)
            raise ModelUnavailableError(
                f"el servicio de modelos no respondió: {cause}", fallback
            ) from cause

        if status >= 400:
            self.metrics.record_failure(alias_name)
            fallback = self.admission_for(alias_name, reachable=False)
            self.metrics.record_degradation(alias_name)
            raise ModelUnavailableError(f"el servicio de modelos respondió {status}", fallback)

        completion = _read_completion(alias_name, alias.model, payload)
        self.metrics.record_call(alias_name, completion)
        self._resident.add(alias_name)
        return completion

    def unload(self, alias_name: str) -> None:
        """Forget that an alias is resident (RF-203).

        Called by whatever manages the turns on a 16 GB card. The gateway does the unloading; this
        records it, so the admission policy stops reserving VRAM for a model that left.
        """
        self._resident.discard(alias_name)


def _read_completion(alias: str, model: str, payload: Mapping[str, Any]) -> Completion:
    """Read an OpenAI-shaped response, tolerating the parts runtimes disagree about.

    llama.cpp, Ollama and vLLM each omit or rename something in `usage`. A missing token count is
    a worse metric, not a failed call, so it reads as zero rather than raising — the answer the
    caller asked for is in `choices`.
    """
    choices = payload.get("choices") or []
    if not isinstance(choices, Sequence) or not choices:
        raise ModelUnavailableError("el servicio de modelos respondió sin ninguna opción")
    first = choices[0]
    if not isinstance(first, Mapping):
        raise ModelUnavailableError("el servicio de modelos respondió con una opción ilegible")
    message = first.get("message")
    text = ""
    if isinstance(message, Mapping):
        content = message.get("content")
        text = content if isinstance(content, str) else ""

    usage = payload.get("usage")
    prompt_tokens = completion_tokens = 0
    if isinstance(usage, Mapping):
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)

    return Completion(
        alias=alias,
        model=model,
        text=text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
