"""La pasarela de modelos: alias, admisión por perfil y degradación (M19, RF-200 a RF-205).

La propiedad que sostiene todo lo demás está en RF-204 y en la regla 17: **una persona nunca queda
bloqueada por un modelo**. Su criterio de aceptación es literal —con el servicio de modelos
detenido, el supervisor puede revisar y aprobar OT, con aviso— y por eso la política de admisión es
una función pura: así se puede afirmar sobre todas las combinaciones de alias y perfil a la vez, en
vez de sobre el camino de una petición.

Lo demás que se prueba aquí son las tres cosas que el SRS afirma y que la aritmética podría
contradecir en silencio: que en 16 GB el juez y el VLM no coexisten (RF-203), que el entrenamiento
no toma la GPU en horario laboral (RF-202), y que una llamada que espera JSON no se degrada a texto
libre (RF-201).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest

from app.inference.admission import Admission, Placement, admit, may_coexist, used_vram
from app.inference.client import (
    GatewayMetrics,
    GrammarNotSupportedError,
    ModelGateway,
    ModelUnavailableError,
)
from app.inference.registry import Degradation, Priority, RegistryError, load_registry
from app.inference.scheduler import is_night, next_night_start, order_queue, slot_for

REGISTRY = load_registry()

#: Every alias and every profile, so the properties below are asserted over the whole matrix rather
#: than over the pair somebody happened to think of.
ALL_ALIASES = sorted(REGISTRY.aliases)
ALL_PROFILES = sorted(REGISTRY.profiles)


def ok_transport(text: str = '{"ok": true}') -> Any:
    def send(path: str, body: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        return 200, {
            "choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7},
        }

    return send


# --- la propiedad que importa ---------------------------------------------------------
@pytest.mark.parametrize("alias", ALL_ALIASES)
@pytest.mark.parametrize("profile", ALL_PROFILES)
@pytest.mark.parametrize("reachable", [True, False])
def test_rf_204_ninguna_combinacion_deja_a_una_persona_esperando(
    alias: str, profile: str, reachable: bool
) -> None:
    """Regla 17 y RF-204, sobre toda la matriz.

    No hay un resultado que signifique «espere a que haya modelo»: o corre ahora, o queda para la
    noche, o se omite con aviso. Las tres dejan trabajar a quien está en pantalla.
    """
    decision = admit(alias, profile, gateway_reachable=reachable, registry=REGISTRY)
    assert decision.placement in tuple(Placement)
    assert decision.blocks_a_person is False
    assert decision.reason, "una decisión sin motivo es una que nadie puede cuestionar"


@pytest.mark.parametrize("alias", ALL_ALIASES)
@pytest.mark.parametrize("profile", ALL_PROFILES)
def test_rf_204_con_el_servicio_caido_nada_queda_interactivo(alias: str, profile: str) -> None:
    decision = admit(alias, profile, gateway_reachable=False, registry=REGISTRY)
    assert decision.placement is not Placement.INTERACTIVE
    assert not decision.runs_now


def test_rf_204_un_hecho_permanente_decide_antes_que_uno_temporal() -> None:
    """El VLM en el perfil A no vuelve mañana.

    Decir «el servicio de modelos no responde; pasa al lote nocturno» de un alias que ese hardware
    no puede ejecutar le promete al supervisor un informe que nunca llega. El orden de los chequeos
    es lo que lo impide, y sin este test se invertiría en cualquier refactor.
    """
    on_cpu_only = admit("vlm-audit", "A", gateway_reachable=False, registry=REGISTRY)
    assert on_cpu_only.placement is Placement.UNAVAILABLE
    assert "GPU" in on_cpu_only.reason

    with_a_gpu = admit("vlm-audit", "C", gateway_reachable=False, registry=REGISTRY)
    assert with_a_gpu.placement is Placement.NIGHT_BATCH


# --- lo que el SRS afirma por perfil ---------------------------------------------------
def test_srs_7_9_el_perfil_a_no_ejecuta_el_vlm() -> None:
    """«VLM desactivado» en la tabla de perfiles."""
    assert admit("vlm-audit", "A", registry=REGISTRY).placement is Placement.UNAVAILABLE


def test_rnf_026_en_el_perfil_b_el_vlm_pasa_al_lote_nocturno() -> None:
    """Distinto del perfil A a propósito: aquí la auditoría no se pierde, espera."""
    assert admit("vlm-audit", "B", registry=REGISTRY).placement is Placement.NIGHT_BATCH


def test_rnf_027_en_el_perfil_a_el_juez_pasa_al_lote_nocturno() -> None:
    assert admit("llm-judge", "A", registry=REGISTRY).placement is Placement.NIGHT_BATCH


def test_el_extractor_de_dictado_corre_en_linea_en_los_tres_perfiles() -> None:
    """Es interactivo por definición: un técnico dictando está esperando en pantalla."""
    for profile in ALL_PROFILES:
        assert admit("form-extractor", profile, registry=REGISTRY).runs_now


def test_rf_204_una_propuesta_de_dictado_tarde_se_omite_y_no_se_encola() -> None:
    """Y por eso su degradación es `skip` y no `night_batch`.

    Una propuesta de dictado que llega mañana no le sirve a nadie: el técnico ya escribió el campo
    y siguió. Encolarla sería acumular trabajo que nadie va a leer.
    """
    alias = REGISTRY.alias("form-extractor")
    assert alias.when_busy is Degradation.SKIP
    assert alias.when_unsupported is Degradation.SKIP


# --- RF-203: VRAM -----------------------------------------------------------------------
def test_rf_203_en_16_gb_el_juez_y_el_vlm_no_coexisten() -> None:
    """Lo que RF-203 dice explícitamente, y que la aritmética simple contradiría.

    6,5 + 9 = 15,5 «cabe» en 16 GB, y no cabe: lo que sobra no alcanza para la caché KV de ninguno
    de los dos. La reserva declarada del perfil es lo que hace cierta la regla, en vez de una lista
    de pares prohibidos que se queda vieja al cambiar un modelo detrás de su alias.
    """
    assert may_coexist("llm-judge", "vlm-audit", "B", REGISTRY) is False
    assert may_coexist("llm-judge", "vlm-audit", "C", REGISTRY) is True


def test_rf_203_el_segundo_alias_espera_en_vez_de_provocar_un_out_of_memory() -> None:
    """Cargarlo y fallar se lleva por delante el camino interactivo en horario laboral."""
    decision = admit("vlm-audit", "B", resident=frozenset({"llm-judge"}), registry=REGISTRY)
    assert decision.placement is Placement.NIGHT_BATCH
    assert "VRAM" in decision.reason or "interactiva" in decision.reason


def test_rf_203_un_alias_ya_residente_no_se_cuenta_dos_veces() -> None:
    """Volver a pedir lo que ya está cargado no consume VRAM otra vez."""
    assert admit("llm-judge", "B", resident=frozenset({"llm-judge"}), registry=REGISTRY).runs_now


def test_la_vram_usada_es_la_suma_de_los_residentes() -> None:
    assert used_vram(frozenset({"llm-judge", "embed"}), REGISTRY) == pytest.approx(8.0)
    assert used_vram(frozenset(), REGISTRY) == 0.0


# --- RF-202: ventanas y prioridades -----------------------------------------------------
@pytest.mark.parametrize(
    ("moment", "night"),
    [
        ("2026-09-22T10:00", False),  # martes por la mañana: horario de inferencia
        ("2026-09-22T07:00", False),  # el límite de apertura pertenece al día
        ("2026-09-22T06:59", True),  # un minuto antes, todavía es noche
        ("2026-09-22T19:00", True),  # el límite de cierre pertenece a la noche
        ("2026-09-22T23:30", True),
        ("2026-09-26T12:00", True),  # sábado al mediodía: el fin de semana es noche entera
        ("2026-09-27T12:00", True),  # domingo
        ("2026-09-21T12:00", False),  # lunes, para que el fin de semana no sea el caso único
    ],
)
def test_rf_202_la_ventana_se_decide_por_hora_y_por_dia(moment: str, night: bool) -> None:
    """Los dos límites y el fin de semana, que es donde una comparación mal puesta se esconde."""
    assert is_night(datetime.fromisoformat(moment), REGISTRY.windows) is night


def test_rf_202_el_entrenamiento_no_toma_la_gpu_en_horario_laboral() -> None:
    """El criterio de aceptación de RF-202, literal."""
    working_hours = datetime(2026, 9, 22, 10, 0, tzinfo=UTC)
    slot = slot_for(Priority.TRAINING, working_hours, REGISTRY)
    assert slot.may_run is False
    assert slot.waits_until == datetime(2026, 9, 22, 19, 0, tzinfo=UTC)
    assert "entrenamiento" in slot.reason


def test_rf_202_el_entrenamiento_si_corre_de_noche_y_el_fin_de_semana() -> None:
    assert slot_for(Priority.TRAINING, datetime(2026, 9, 22, 21, 0), REGISTRY).may_run
    saturday = datetime(2026, 9, 26, 12, 0)
    assert saturday.weekday() == 5
    assert slot_for(Priority.TRAINING, saturday, REGISTRY).may_run


def test_rf_202_lo_interactivo_corre_a_cualquier_hora() -> None:
    """Una persona en pantalla no espera a una ventana."""
    for moment in (datetime(2026, 9, 22, 10, 0), datetime(2026, 9, 22, 23, 0)):
        assert slot_for(Priority.INTERACTIVE, moment, REGISTRY).may_run


def test_rf_202_el_orden_de_las_colas_es_el_del_archivo_y_es_estable() -> None:
    """Estable dentro de una clase: dos pre-revisiones encoladas con un minuto de diferencia se
    sirven en ese orden. Una cola que reordena iguales hace la espera impredecible sin ganar nada.
    """
    order = order_queue(
        [
            ("entrena", Priority.TRAINING),
            ("pre-1", Priority.PRE_REVIEW),
            ("interactiva", Priority.INTERACTIVE),
            ("pre-2", Priority.PRE_REVIEW),
            ("retranscribe", Priority.RETRANSCRIPTION),
        ],
        REGISTRY,
    )
    assert order == ["interactiva", "pre-1", "pre-2", "retranscribe", "entrena"]


def test_la_espera_de_un_viernes_por_la_tarde_es_la_misma_noche() -> None:
    friday = datetime(2026, 9, 25, 15, 0)
    assert friday.weekday() == 4
    assert next_night_start(friday, REGISTRY.windows) == datetime(2026, 9, 25, 19, 0)


def test_una_hora_que_ya_es_de_noche_no_espera() -> None:
    moment = datetime(2026, 9, 22, 22, 0)
    assert next_night_start(moment, REGISTRY.windows) == moment


# --- RF-200 y RF-201: el cliente --------------------------------------------------------
def test_rf_200_el_alias_viaja_como_nombre_de_modelo() -> None:
    """Lo que hace que cambiar el modelo detrás de un alias no toque el código de los agentes."""
    sent: list[Mapping[str, Any]] = []

    def capture(path: str, body: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        sent.append(body)
        return 200, {"choices": [{"message": {"content": "hola"}}]}

    gateway = ModelGateway(capture, "C", REGISTRY)
    answer = gateway.complete("llm-judge", [{"role": "user", "content": "x"}])

    assert sent[0]["model"] == "llm-judge"
    # Y el modelo real solo aparece en la respuesta, para la trazabilidad de la procedencia.
    assert answer.model == REGISTRY.alias("llm-judge").model
    assert answer.text == "hola"


def test_rf_201_la_gramatica_viaja_en_la_peticion() -> None:
    sent: list[Mapping[str, Any]] = []

    def capture(path: str, body: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        sent.append(body)
        return 200, {"choices": [{"message": {"content": "{}"}}]}

    ModelGateway(capture, "C", REGISTRY).complete(
        "form-extractor", [{"role": "user", "content": "x"}], grammar='root ::= "{}"'
    )
    assert "grammar" in sent[0]


def test_rf_201_un_alias_sin_salida_restringida_rechaza_la_llamada() -> None:
    """No se degrada a texto libre: quien pidió JSON va a parsear la respuesta.

    Prosa de un modelo donde se esperaba JSON produce un registro malo cada varios cientos, que es
    la clase de fallo más difícil de notar.
    """
    gateway = ModelGateway(ok_transport(), "C", REGISTRY)
    with pytest.raises(GrammarNotSupportedError, match="RF-201"):
        gateway.complete("asr-server", [{"role": "user", "content": "x"}], json_schema={"a": 1})


def test_rf_204_un_transporte_que_revienta_degrada_en_vez_de_propagar() -> None:
    def broken(path: str, body: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        raise ConnectionError("conexión rechazada")

    gateway = ModelGateway(broken, "C", REGISTRY)
    with pytest.raises(ModelUnavailableError) as raised:
        gateway.complete("llm-judge", [{"role": "user", "content": "x"}])

    assert isinstance(raised.value.admission, Admission)
    assert raised.value.admission.placement is Placement.NIGHT_BATCH
    assert gateway.metrics.failures["llm-judge"] == 1
    assert gateway.metrics.degraded["llm-judge"] == 1


def test_rf_204_un_500_del_servicio_tambien_degrada() -> None:
    def failing(path: str, body: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        return 503, {"error": "modelo cargando"}

    with pytest.raises(ModelUnavailableError, match="503"):
        ModelGateway(failing, "C", REGISTRY).complete("llm-judge", [])


def test_rf_204_un_alias_que_el_perfil_no_ejecuta_no_llega_al_transporte() -> None:
    """Degrada antes de gastar un tiempo de espera en averiguar lo que la configuración ya dice."""
    calls: list[str] = []

    def counted(path: str, body: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        calls.append(path)
        return 200, {"choices": [{"message": {"content": "x"}}]}

    with pytest.raises(ModelUnavailableError):
        ModelGateway(counted, "A", REGISTRY).complete("vlm-audit", [])
    assert calls == []


def test_rf_205_las_metricas_cuentan_llamadas_y_tokens() -> None:
    metrics = GatewayMetrics()
    gateway = ModelGateway(ok_transport(), "C", REGISTRY, metrics)
    gateway.complete("llm-judge", [])
    gateway.complete("llm-judge", [])

    assert metrics.calls["llm-judge"] == 2
    assert metrics.prompt_tokens == 22
    assert metrics.completion_tokens == 14


def test_rf_203_el_cliente_recuerda_que_alias_estan_cargados() -> None:
    gateway = ModelGateway(ok_transport(), "B", REGISTRY)
    gateway.complete("llm-judge", [])
    assert gateway.resident == frozenset({"llm-judge"})

    # Y con el juez cargado, el VLM ya no entra en línea (RF-203).
    assert gateway.admission_for("vlm-audit").placement is Placement.NIGHT_BATCH

    gateway.unload("llm-judge")
    assert gateway.resident == frozenset()


def test_una_respuesta_sin_opciones_es_una_indisponibilidad_no_un_indexerror() -> None:
    def empty(path: str, body: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        return 200, {"choices": []}

    with pytest.raises(ModelUnavailableError, match="sin ninguna opción"):
        ModelGateway(empty, "C", REGISTRY).complete("llm-judge", [])


def test_un_usage_ausente_no_rompe_la_llamada() -> None:
    """Cada runtime omite o renombra algo en `usage`; una métrica peor no es una llamada fallida."""

    def terse(path: str, body: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        return 200, {"choices": [{"message": {"content": "listo"}}]}

    answer = ModelGateway(terse, "C", REGISTRY).complete("llm-judge", [])
    assert answer.text == "listo"
    assert answer.prompt_tokens == 0


# --- el registro ------------------------------------------------------------------------
def test_rf_200_ningun_nombre_de_modelo_aparece_fuera_del_registro() -> None:
    """La regla 13, verificada donde se puede verificar.

    Si el nombre de un modelo apareciera en el código de un agente, cambiar de runtime dejaría de
    ser una edición de configuración. Se comprueba contra los nombres que el propio registro
    declara, así que añadir un alias extiende la comprobación sola.
    """
    import subprocess

    names = sorted({alias.model for alias in REGISTRY.aliases.values()})
    root = str(__import__("pathlib").Path(__file__).resolve().parents[2] / "app")
    leaked: list[str] = []
    for name in names:
        found = subprocess.run(
            ["grep", "-rn", "--include=*.py", name, root],
            capture_output=True,
            text=True,
            check=False,
        )
        if found.stdout.strip():
            leaked.append(f"{name}: {found.stdout.splitlines()[0]}")
    assert not leaked, "nombres de modelo fuera del registro: " + "; ".join(leaked)


def test_el_registro_rechaza_un_perfil_que_no_podria_funcionar() -> None:
    """Una configuración incoherente falla al cargar, no en la primera llamada de la noche."""
    import tempfile
    from pathlib import Path

    import yaml

    data = yaml.safe_load(
        (Path(__file__).resolve().parents[3] / "infra" / "inference" / "aliases.yaml").read_text(
            encoding="utf-8"
        )
    )
    # El perfil sin GPU declara interactivo un alias que exige GPU.
    data["profiles"]["A"]["interactive_aliases"].append("vlm-audit")
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
        yaml.safe_dump(data, handle)
        broken = handle.name

    with pytest.raises(RegistryError, match="no corre en CPU"):
        load_registry(broken)


def test_el_registro_rechaza_una_ventana_de_dia_sin_duracion() -> None:
    """Una ventana que termina antes de empezar haría noche todas las horas — y eso es cómo el
    entrenamiento toma la GPU a las diez de la mañana."""
    import tempfile
    from pathlib import Path

    import yaml

    data = yaml.safe_load(
        (Path(__file__).resolve().parents[3] / "infra" / "inference" / "aliases.yaml").read_text(
            encoding="utf-8"
        )
    )
    data["windows"]["day_starts_at"] = "19:00"
    data["windows"]["day_ends_at"] = "07:00"
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
        yaml.safe_dump(data, handle)
        broken = handle.name

    with pytest.raises(Exception, match="antes de empezar"):
        load_registry(broken)
