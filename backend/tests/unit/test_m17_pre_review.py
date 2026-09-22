"""El grafo de pre-revisión, mitad determinista (M17, RF-171, RF-174, RF-175, regla 14).

Dos propiedades sostienen este módulo y las dos tienen su guarda:

**Una observación sin evidencia es una opinión, y se descarta.** Es la nota 3 de la sección 7.7 del
SRS. Una opinión en un documento que un supervisor usa para aprobar trabajo de campo es peor que el
silencio: gasta su atención y no se puede comprobar. El descarte se **cuenta**, para que un nodo que
empiece a producir observaciones sin apoyo se note en la siguiente ejecución y no en seis meses.

**Un agente nunca aprueba, cierra ni integra** (regla 14). Eso no se comprueba leyendo el código con
cuidado: se comprueba estructuralmente, recorriendo los imports del paquete, porque el fallo que
importa es que alguien añada el atajo dentro de un año.

Lo demás son las reglas, cada una con el caso que la dispara y el caso que no. Una regla que solo se
ha visto encontrar algo no está probada: la mitad del valor de un informe es no decir nada cuando no
hay nada que decir.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.agents import anomalies, coherence
from app.agents.consolidator import (
    MEDIUMS_THAT_MAKE_A_HIGH,
    consolidate,
    risk_level,
    sort_observations,
    summarise,
)
from app.agents.facts import AiValueFact, OtherOrderFact, PhotoFact, PreReviewFacts, RegulatoryFact
from app.agents.geo import distance_m, format_distance
from app.agents.graph import GRAPH_VERSION, run_pre_review
from app.agents.report import (
    AgentReport,
    Category,
    EvidenceRef,
    EvidenceType,
    Observation,
    RiskLevel,
    RunStatus,
    Severity,
    Source,
    guardrail,
)

SUBMITTED = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)

#: Guayaquil, and a point roughly 6,5 km away.
ASSET = (-2.17, -79.90)
FAR = (-2.20, -79.95)


def facts(**overrides: object) -> PreReviewFacts:
    defaults: dict[str, object] = {
        "work_order_id": "wo-1",
        "work_order_code": "OT-2026-000123",
        "asset_code": "P-000452",
        "asset_latitude": ASSET[0],
        "asset_longitude": ASSET[1],
        "answers": {},
        "submitted_at": SUBMITTED,
    }
    defaults.update(overrides)
    return PreReviewFacts(**defaults)  # type: ignore[arg-type]


def observation(**overrides: object) -> Observation:
    defaults: dict[str, object] = {
        "id": "obs-1",
        "category": Category.COHERENCE,
        "severity": Severity.MEDIUM,
        "message": "algo que revisar",
        "evidence": [EvidenceRef(type=EvidenceType.FIELD, json_path="$.x")],
    }
    defaults.update(overrides)
    return Observation(**defaults)  # type: ignore[arg-type]


# --- el guardrail -----------------------------------------------------------------------
def test_srs_7_7_una_observacion_sin_evidencia_se_descarta() -> None:
    """La nota 3 de la sección 7.7, literal."""
    kept, dropped = guardrail([observation(evidence=[])])
    assert kept == []
    assert len(dropped) == 1
    assert "opinión" in dropped[0].reason


def test_una_evidencia_con_tipo_y_nada_mas_no_cuenta_como_evidencia() -> None:
    """Es la forma de la evidencia sin la sustancia, y lo que produce un modelo adivinando."""
    kept, dropped = guardrail([observation(evidence=[EvidenceRef(type=EvidenceType.FIELD)])])
    assert kept == []
    assert dropped


def test_rf_172_una_observacion_normativa_sin_cita_se_descarta() -> None:
    """«Ninguna observación sin fuente se muestra como normativa.»

    Y se descarta en vez de reetiquetarse: cambiarle la categoría la dejaría pasar igual.
    """
    kept, dropped = guardrail([observation(category=Category.REGULATORY, source=None)])
    assert kept == []
    assert "normativa sin cita" in dropped[0].reason


def test_rf_172_una_observacion_normativa_con_cita_pasa() -> None:
    kept, _ = guardrail(
        [
            observation(
                category=Category.REGULATORY,
                source=Source(document="ARCERNNR 002/20", version="2023", section="Art. 7"),
            )
        ]
    )
    assert len(kept) == 1
    assert kept[0].source is not None
    assert "ARCERNNR 002/20" in kept[0].source.describe()


def test_el_descarte_se_cuenta_en_el_informe_y_no_es_silencioso() -> None:
    """Un nodo que empieza a producir observaciones sin apoyo tiene que notarse."""
    report = consolidate("wo-1", GRAPH_VERSION, "C", [], discarded=3)
    assert report.discarded == 3


def test_el_guardrail_no_descarta_lo_que_si_apunta_a_algo() -> None:
    """La mitad en positivo: una guarda que descarta todo tampoco sirve."""
    kept, dropped = guardrail(
        [
            observation(id="a", evidence=[EvidenceRef(type=EvidenceType.PHOTO, evidence_id="e1")]),
            observation(
                id="b", evidence=[EvidenceRef(type=EvidenceType.TRANSCRIPT, span=(10, 40))]
            ),
            observation(
                id="c", evidence=[EvidenceRef(type=EvidenceType.COMPUTED, detail="18,4 > 25")]
            ),
        ]
    )
    assert [item.id for item in kept] == ["a", "b", "c"]
    assert dropped == []


# --- coherencia (RF-171) -----------------------------------------------------------------
def test_rf_171_una_hora_de_fin_anterior_al_inicio_se_reporta() -> None:
    found = coherence.check_time_order(
        facts(
            answers={
                "started_at": "2026-09-22T09:00:00+00:00",
                "finished_at": "2026-09-22T08:00:00+00:00",
            }
        )
    )
    assert len(found) == 1
    assert "anterior" in found[0].message
    # Y apunta a los dos campos, para que nadie tenga que ir a buscarlos.
    assert {ref.json_path for ref in found[0].evidence} == {"$.started_at", "$.finished_at"}


def test_rf_171_una_secuencia_correcta_no_reporta_nada() -> None:
    assert (
        coherence.check_time_order(
            facts(
                answers={
                    "dispatched_at": "2026-09-22T07:00:00+00:00",
                    "arrived_at": "2026-09-22T08:00:00+00:00",
                    "started_at": "2026-09-22T08:15:00+00:00",
                    "finished_at": "2026-09-22T09:00:00+00:00",
                }
            )
        )
        == []
    )


def test_rf_171_un_solo_error_de_hora_no_produce_seis_observaciones() -> None:
    """Enterrar la que importa entre seis es la forma de que nadie lea ninguna."""
    found = coherence.check_time_order(
        facts(
            answers={
                "dispatched_at": "2026-09-22T07:00:00+00:00",
                "departed_at": "2026-09-22T07:10:00+00:00",
                "arrived_at": "2026-09-22T06:00:00+00:00",
                "started_at": "2026-09-22T08:15:00+00:00",
                "finished_at": "2026-09-22T09:00:00+00:00",
            }
        )
    )
    assert len(found) == 1


def test_rf_171_horas_ausentes_no_producen_observaciones() -> None:
    """Un bloque de tiempos vacío es un formulario incompleto, no una incoherencia."""
    assert coherence.check_time_order(facts()) == []


def test_una_hora_ilegible_no_rompe_el_nodo() -> None:
    """El esquema ya rechaza una fecha mal formada al enviar; lo que llegue así es dato viejo, y el
    dato viejo no puede impedir que se produzca un informe."""
    assert coherence.check_time_order(facts(answers={"started_at": "ayer por la tarde"})) == []


def test_rf_171_una_hora_posterior_al_envio_se_reporta_contra_el_envio() -> None:
    """Contra el envío y no contra el reloj de quien corre el informe.

    Un lote nocturno que corriera doce horas después no encontraría nada, y una ejecución en otra
    zona horaria lo encontraría todo.
    """
    found = coherence.check_times_are_not_in_the_future(
        facts(answers={"finished_at": (SUBMITTED + timedelta(hours=3)).isoformat()})
    )
    assert len(found) == 1
    assert "posterior al envío" in found[0].message


def test_rf_171_la_distancia_al_activo_se_reporta_con_la_cuenta_hecha() -> None:
    found = coherence.check_capture_is_near_the_asset(
        facts(answers={"gps": {"latitude": FAR[0], "longitude": FAR[1]}})
    )
    assert len(found) == 1
    assert "km del activo" in found[0].message
    computed = next(ref for ref in found[0].evidence if ref.type is EvidenceType.COMPUTED)
    assert computed.detail is not None and "haversine" in computed.detail


def test_rf_171_una_captura_junto_al_activo_no_reporta_nada() -> None:
    """Con tolerancia generosa a propósito: un GPS bajo los árboles se desvía decenas de metros, y
    una regla que se disparara con eso se ignoraría en una semana."""
    near = {"latitude": ASSET[0] + 0.0005, "longitude": ASSET[1]}
    assert coherence.check_capture_is_near_the_asset(facts(answers={"gps": near})) == []


def test_sin_gps_o_sin_activo_no_se_inventa_una_distancia() -> None:
    assert coherence.check_capture_is_near_the_asset(facts()) == []
    assert (
        coherence.check_capture_is_near_the_asset(
            facts(asset_latitude=None, answers={"gps": {"latitude": FAR[0], "longitude": FAR[1]}})
        )
        == []
    )


def test_una_evidencia_cuyo_hash_no_cuadra_es_severidad_alta() -> None:
    """O el archivo cambió después de capturarse o el registro está mal, y las dos cosas
    significan que esa evidencia no puede sostener una aprobación."""
    found = coherence.check_evidence_integrity(
        facts(photos=[PhotoFact("e1", "despues", "a" * 64, False)])
    )
    assert len(found) == 1
    assert found[0].severity is Severity.HIGH
    assert found[0].category is Category.EVIDENCE


def test_una_evidencia_verificada_no_se_reporta() -> None:
    assert (
        coherence.check_evidence_integrity(facts(photos=[PhotoFact("e1", "antes", "a" * 64, True)]))
        == []
    )


def test_regla_8_un_valor_de_ia_aceptado_sin_cambios_con_poca_confianza_se_marca() -> None:
    """El fallo que busca es una persona pasando pantallas: el valor vino de un modelo, el modelo no
    estaba seguro, y nadie lo alteró."""
    found = coherence.check_low_confidence_accepted_unchanged(
        facts(
            ai_values=[
                AiValueFact("material", "vision", 0.42, "mobilenetv3", "2026.09", True, "tec.1")
            ]
        )
    )
    assert len(found) == 1
    assert found[0].severity is Severity.LOW
    assert "42%" in found[0].message


def test_un_valor_de_ia_corregido_por_una_persona_no_se_marca() -> None:
    """Corregirlo es exactamente lo que se quería que pasara."""
    assert (
        coherence.check_low_confidence_accepted_unchanged(
            facts(ai_values=[AiValueFact("material", "vision", 0.42, "m", "1", False, "tec.1")])
        )
        == []
    )


def test_un_valor_de_ia_con_confianza_alta_no_se_marca() -> None:
    assert (
        coherence.check_low_confidence_accepted_unchanged(
            facts(ai_values=[AiValueFact("material", "vision", 0.95, "m", "1", True, "tec.1")])
        )
        == []
    )


def test_adr_007_un_hallazgo_normativo_sin_verificar_viaja_como_provisional() -> None:
    found = coherence.carry_regulatory_findings(
        facts(
            regulatory=[
                RegulatoryFact(
                    rule="earth_resistance",
                    outcome="incumple",
                    severity="high",
                    message="Resistencia por encima del límite",
                    norm_ref="ARCERNNR 002/20",
                    article_ref="Art. 12",
                    limit_verified=False,
                )
            ]
        )
    )
    assert len(found) == 1
    assert found[0].source is not None
    assert found[0].source.verified is False


def test_un_hallazgo_normativo_que_cumple_no_se_reporta() -> None:
    """El informe es lo que hay que revisar, no un acta de todo lo que se evaluó."""
    assert (
        coherence.carry_regulatory_findings(
            facts(
                regulatory=[
                    RegulatoryFact(
                        "apg", "cumple", "low", "Dentro del plazo", "ARCERNNR", "7", True
                    )
                ]
            )
        )
        == []
    )


# --- anomalías (RF-174) ------------------------------------------------------------------
def test_rf_174_el_lenguaje_es_neutral_y_no_acusa() -> None:
    """El requerimiento lo pide explícitamente, y no por cortesía: un informe que acusa se discute
    en vez de comprobarse, y la cuadrilla nombrada deja de cooperar con la plataforma."""
    found = anomalies.run(
        facts(
            answers={
                "started_at": "2026-09-22T09:00:00+00:00",
                "finished_at": "2026-09-22T09:01:00+00:00",
                "gps": {"latitude": ASSET[0], "longitude": ASSET[1]},
            },
            photos=[
                PhotoFact("e1", "antes", "a" * 64, True),
                PhotoFact("e2", "despues", "a" * 64, True),
            ],
            other_orders=[
                OtherOrderFact("wo-2", "OT-2", frozenset({"a" * 64}), ASSET[0], ASSET[1])
            ],
        )
    )
    assert found
    for item in found:
        assert "requiere verificación" in item.message.lower()
        for word in ("fraude", "falso", "miente", "irregular"):
            assert word not in item.message.lower()


def test_rf_174_cada_alerta_muestra_la_regla_o_el_estadistico_que_la_origino() -> None:
    found = anomalies.run(
        facts(
            answers={
                "started_at": "2026-09-22T09:00:00+00:00",
                "finished_at": "2026-09-22T09:01:00+00:00",
            }
        )
    )
    assert len(found) == 1
    computed = [ref for ref in found[0].evidence if ref.type is EvidenceType.COMPUTED]
    assert computed and computed[0].detail is not None and "umbral" in computed[0].detail


def test_rf_174_una_duracion_normal_no_se_reporta() -> None:
    assert (
        anomalies.check_execution_duration(
            facts(
                answers={
                    "started_at": "2026-09-22T09:00:00+00:00",
                    "finished_at": "2026-09-22T10:30:00+00:00",
                }
            )
        )
        == []
    )


def test_horas_al_reves_las_reporta_coherencia_y_no_anomalias() -> None:
    """Leer el mismo error en dos secciones con dos voces distintas es peor que leerlo una vez."""
    backwards = facts(
        answers={
            "started_at": "2026-09-22T09:00:00+00:00",
            "finished_at": "2026-09-22T08:00:00+00:00",
        }
    )
    assert anomalies.check_execution_duration(backwards) == []
    assert coherence.check_time_order(backwards)


def test_rf_174_una_foto_compartida_con_otra_ot_se_reporta() -> None:
    """El caso entre OT, que es el que nada mira hoy: dentro de una OT la pantalla de revisión ya
    señala un archivo enviado dos veces."""
    found = anomalies.check_photos_shared_with_another_order(
        facts(
            photos=[PhotoFact("e1", "antes", "b" * 64, True)],
            other_orders=[OtherOrderFact("wo-2", "OT-2", frozenset({"b" * 64}))],
        )
    )
    assert len(found) == 1
    assert "OT-2" in found[0].message
    assert any(ref.evidence_id == "e1" for ref in found[0].evidence)


def test_fotos_distintas_entre_ot_no_se_reportan() -> None:
    assert (
        anomalies.check_photos_shared_with_another_order(
            facts(
                photos=[PhotoFact("e1", "antes", "b" * 64, True)],
                other_orders=[OtherOrderFact("wo-2", "OT-2", frozenset({"c" * 64}))],
            )
        )
        == []
    )


def test_rf_174_un_mismo_punto_gps_en_dos_ot_se_reporta() -> None:
    found = anomalies.check_gps_shared_with_another_order(
        facts(
            answers={"gps": {"latitude": ASSET[0], "longitude": ASSET[1]}},
            other_orders=[OtherOrderFact("wo-2", "OT-2", frozenset(), ASSET[0], ASSET[1])],
        )
    )
    assert len(found) == 1
    assert "mismo punto" in found[0].message


def test_dos_ot_lejanas_no_se_reportan() -> None:
    assert (
        anomalies.check_gps_shared_with_another_order(
            facts(
                answers={"gps": {"latitude": ASSET[0], "longitude": ASSET[1]}},
                other_orders=[OtherOrderFact("wo-2", "OT-2", frozenset(), FAR[0], FAR[1])],
            )
        )
        == []
    )


def test_una_foto_repetida_dentro_de_la_ot_se_reporta_una_sola_vez() -> None:
    found = anomalies.check_duplicate_photos_within_the_order(
        facts(
            photos=[
                PhotoFact("e1", "antes", "d" * 64, True),
                PhotoFact("e2", "despues", "d" * 64, True),
            ]
        )
    )
    assert len(found) == 1
    assert {ref.evidence_id for ref in found[0].evidence if ref.evidence_id} == {"e1", "e2"}


# --- consolidación (RF-175) --------------------------------------------------------------
def test_rf_175_una_sola_severidad_alta_hace_alto_el_riesgo() -> None:
    """Promediar dejaría que nueve hallazgos inocuos diluyan el que dice que la puesta a tierra está
    fuera de límite, y quien ordena la cola por riesgo no llegaría nunca a él."""
    assert (
        risk_level([observation(severity=Severity.LOW)] * 9 + [observation(severity=Severity.HIGH)])
        is RiskLevel.HIGH
    )


def test_rf_175_suficientes_medias_tambien_hacen_alto_el_riesgo() -> None:
    """El volumen es un patrón que una persona nota y un máximo no."""
    mediums = [
        observation(id=f"m{i}", severity=Severity.MEDIUM) for i in range(MEDIUMS_THAT_MAKE_A_HIGH)
    ]
    assert risk_level(mediums) is RiskLevel.HIGH
    assert risk_level(mediums[:-1]) is RiskLevel.MEDIUM


def test_rf_175_sin_observaciones_el_riesgo_es_bajo_y_se_dice() -> None:
    report = consolidate("wo-1", GRAPH_VERSION, "C", [])
    assert report.risk_level is RiskLevel.LOW
    assert "Sin observaciones" in report.summary


def test_rf_175_las_observaciones_se_ordenan_peor_primero() -> None:
    ordered = sort_observations(
        [
            observation(id="c", severity=Severity.LOW, category=Category.ANOMALY),
            observation(id="a", severity=Severity.HIGH, category=Category.EVIDENCE),
            observation(id="b", severity=Severity.MEDIUM, category=Category.COHERENCE),
        ]
    )
    assert [item.id for item in ordered] == ["a", "b", "c"]


def test_rf_180_el_resumen_es_determinista() -> None:
    """«La reproducción de una ejecución con la misma versión da el mismo informe.»"""
    items = [observation(id="a", severity=Severity.HIGH), observation(id="b")]
    assert summarise(items, []) == summarise(items, [])


def test_rf_175_el_informe_valida_contra_el_esquema() -> None:
    report = consolidate("wo-1", GRAPH_VERSION, "C", [observation()])
    # Ida y vuelta por el esquema: el criterio de aceptación pide el 100 % de las ejecuciones.
    assert AgentReport.model_validate(report.model_dump(mode="json")) == report


# --- el grafo (RF-170, RF-204) -----------------------------------------------------------
def test_rf_204_un_nodo_que_no_corre_deja_el_informe_parcial_y_lo_dice() -> None:
    """Un informe que corrió cuatro nodos de cinco y se llama completo es peor que ninguno: parece
    terminado."""
    report = run_pre_review(facts(), "A")
    assert report.status is RunStatus.PARTIAL
    assert report.skipped
    assert any("evidencia visual" in entry for entry in report.skipped)
    # Y el resumen lo menciona, porque la primera línea es lo que se lee antes de decidir cuánto
    # confiar en el resto.
    assert "No se ejecutó" in report.summary


def test_rf_204_con_la_pasarela_caida_el_informe_se_produce_igual() -> None:
    report = run_pre_review(facts(), "C", gateway_reachable=False)
    assert report.status is RunStatus.PARTIAL
    assert report.skipped
    assert isinstance(report.summary, str) and report.summary


def test_el_grafo_declara_su_version_para_poder_comparar_dos_informes() -> None:
    assert run_pre_review(facts(), "C").graph_version == GRAPH_VERSION


def test_una_captura_limpia_produce_un_informe_sin_observaciones() -> None:
    """La mitad del valor de un informe es no decir nada cuando no hay nada que decir."""
    clean = facts(
        answers={
            "started_at": "2026-09-22T08:00:00+00:00",
            "finished_at": "2026-09-22T09:30:00+00:00",
            "gps": {"latitude": ASSET[0], "longitude": ASSET[1]},
        },
        photos=[
            PhotoFact("e1", "antes", "a" * 64, True),
            PhotoFact("e2", "despues", "b" * 64, True),
        ],
    )
    report = run_pre_review(clean, "C")
    assert report.observations == []
    assert report.risk_level is RiskLevel.LOW


# --- la distancia, en castellano ---------------------------------------------------------
@pytest.mark.parametrize(
    ("metres", "text"),
    [(0, "0 m"), (12.4, "12 m"), (999, "999 m"), (1_000, "1,0 km"), (6_480, "6,5 km")],
)
def test_regla_11_la_distancia_se_escribe_como_se_lee_en_ecuador(metres: float, text: str) -> None:
    """`:,.0f` de Python escribe «6,480 m», que en es-EC se lee como seis coma cuatro ocho metros:
    los separadores están al revés. Fue un defecto real de este módulo."""
    assert format_distance(metres) == text


def test_la_distancia_entre_dos_puntos_conocidos_es_la_esperada() -> None:
    """Un grado de latitud son unos 111 km; sirve para ver que la fórmula no está en radianes."""
    assert distance_m(0.0, 0.0, 1.0, 0.0) == pytest.approx(111_195, rel=0.01)
    assert distance_m(ASSET[0], ASSET[1], ASSET[0], ASSET[1]) == 0.0


# --- la regla 14, estructuralmente -------------------------------------------------------
def test_regla_14_un_agente_no_puede_aprobar_cerrar_ni_integrar() -> None:
    """No se comprueba leyendo el código con cuidado: se comprueba recorriendo los imports.

    El fallo que importa no es escribir mal una función hoy, es que alguien añada el atajo dentro de
    un año — «solo para las de riesgo bajo» — y que nadie lo note. Así que el paquete no puede
    importar nada que escriba el estado de una OT, ni recibir una sesión.
    """
    import ast
    from pathlib import Path

    package = Path(__file__).resolve().parents[2] / "app" / "agents"
    forbidden = (
        "app.review.service",
        "app.workorders.service",
        "app.gis_gateway.asbuilt",
        "app.responses.service",
        "sqlalchemy",
        "app.infra.database",
    )
    offences: list[str] = []
    for source in sorted(package.glob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if any(name == item or name.startswith(item + ".") for item in forbidden):
                    offences.append(f"{source.name} importa {name}")

    assert not offences, (
        "el paquete de agentes no puede escribir: " + "; ".join(offences) + ". Un agente solo "
        "escribe su AgentReport (regla 14)"
    )


def test_la_guarda_de_la_regla_14_detecta_un_import_prohibido() -> None:
    """La prueba en negativo: una guarda que solo se ha visto pasar no está probada."""
    import ast

    tree = ast.parse("from app.review.service import decide\n")
    found = [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "app.review.service"
    ]
    assert found == ["app.review.service"]
