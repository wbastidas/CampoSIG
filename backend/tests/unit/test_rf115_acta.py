"""El acta de la OT, como documento (RF-115).

Lo que se prueba es lo que el papel podría mentir. Un acta es lo que una cuadrilla entrega a un
cliente y lo que queda archivado, así que cada caso de abajo corresponde a algo que el documento
diría mal si nadie lo hubiera decidido:

* un valor propuesto por un modelo impreso como si lo hubiera escrito una persona (regla 8);
* un límite normativo sin verificar presentado como cita del texto oficial (ADR-007);
* una fotografía cuyo hash no cuadra, omitida en silencio;
* un hueco bajo un pie de firma, que se lee como una firma mal escaneada;
* un acta de una OT sin aprobar que no dice que es un borrador;
* un campo nuevo del formulario que no aparece, porque el acta llevaba una lista escrita a mano.

Ningún nombre real del modelo de datos aparece aquí, y el documento se compone del formulario,
que es dato (regla 3).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest

from app.reports.acta import (
    Acta,
    ActaDecision,
    ActaFinding,
    ActaPhoto,
    ActaRow,
    ActaSection,
    ActaSignature,
    ai_note,
    display_value,
    esc,
    render_html,
    render_pdf,
    sections_from_form,
    signatures_from_form,
)

ISSUED_AT = datetime(2026, 9, 22, 15, 30, tzinfo=UTC)


def acta(**overrides: object) -> Acta:
    defaults: dict[str, object] = {
        "verification_code": "Zm9vYmFyMTIzNDU2",
        "verification_url": "https://sigec.example/verificar/Zm9vYmFyMTIzNDU2",
        "issued_by": "keycloak|supervisor.1",
        "issued_at": ISSUED_AT,
        "business_unit": "GYE",
        "work_order_code": "OT-2026-000123",
        "work_order_state": "aprobada",
        "work_type": "mantenimiento",
        "form_code": "F-MT-01",
        "form_version": "1.0.0",
        "form_title": "Mantenimiento preventivo",
    }
    defaults.update(overrides)
    return Acta(**defaults)  # type: ignore[arg-type]


# --- valores que vienen de JSONB -------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "—"),
        ("", "—"),
        ("hormigón", "hormigón"),
        (12, "12"),
        (3.5, "3.5"),
        (True, "Sí"),
        (False, "No"),
        ([], "—"),
        (["a", "b"], "a, b"),
        ({"min": 1, "max": 9}, "min: 1; max: 9"),
        ([{"uc": "E1", "cantidad": 2}], "uc: E1; cantidad: 2"),
    ],
)
def test_rf_115_un_valor_de_jsonb_se_imprime_legible(value: object, expected: str) -> None:
    """La misma lección que costó la pantalla de revisión, pero aquí se firma y se archiva.

    `str()` sobre una fila de tabla repetible o un rango produce un repr de Python, y quien lee
    el acta cree que se le mostró la respuesta.
    """
    assert display_value(value) == expected


# --- la procedencia de un valor de IA --------------------------------------------------
def test_regla_8_un_valor_propuesto_por_un_modelo_se_imprime_como_tal() -> None:
    note = ai_note(
        {
            "origin": "voz",
            "model_name": "qwen2.5-1.5b",
            "model_version": "q4_k_m",
            "confidence": 0.82,
            "confirmed_by": "tecnico.7",
            "accepted_unchanged": True,
        }
    )
    assert "dictado" in note
    assert "qwen2.5-1.5b q4_k_m" in note
    assert "82%" in note
    assert "aceptado sin cambios por tecnico.7" in note


def test_regla_8_un_valor_de_ia_sin_confirmar_lo_dice() -> None:
    """Sin esto, un valor que nadie miró se lee igual que uno confirmado."""
    note = ai_note({"origin": "vision", "model_name": "d-fine-n", "confidence": 0.4})
    assert "sin confirmación humana" in note


def test_regla_8_una_confianza_ausente_no_se_inventa() -> None:
    note = ai_note({"origin": "voz", "confidence": None})
    assert "sin confianza" in note
    assert "0%" not in note


# --- las secciones salen del formulario, no de una lista escrita a mano ----------------
FORM_SCHEMA = {
    "properties": {
        "final_state": {"type": "string", "title": "Estado final"},
        "measured_ohms": {"type": "number", "title": "Resistencia medida"},
        "found": {"type": "string", "title": "Encontrado"},
        "crew_leader_signature": {
            "type": "string",
            "format": "uri",
            "title": "Firma del jefe de cuadrilla",
            "x-signature": "jefe_cuadrilla",
        },
        "customer_signature": {
            "type": "string",
            "format": "uri",
            "title": "Firma del cliente",
            "x-signature": "cliente",
        },
    }
}

FORM_UI = {
    "ui:groups": [
        {"block": "B13", "title": "Mediciones", "fields": ["measured_ohms"]},
        {"block": "B10", "title": "Resumen", "fields": ["found"]},
        {
            "block": "B12",
            "title": "Cierre",
            "fields": ["final_state", "crew_leader_signature", "customer_signature"],
        },
    ]
}


def test_rf_115_las_secciones_y_su_orden_son_los_del_formulario() -> None:
    """El acta reproduce los bloques del formulario en su orden.

    El fallo que esto impide: una lista de campos escrita en el código deja de mencionar el
    campo que un administrador funcional añade mañana, y el acta sigue pareciendo completa.
    """
    sections = sections_from_form(
        FORM_SCHEMA,
        FORM_UI,
        {"measured_ohms": 18.4, "found": "poste inclinado", "final_state": "resuelto"},
    )
    assert [s.title for s in sections] == ["Mediciones", "Resumen", "Cierre"]
    assert sections[0].rows[0].label == "Resistencia medida"
    assert sections[0].rows[0].value == "18.4"


def test_rf_115_las_firmas_no_se_imprimen_como_filas_con_una_uri() -> None:
    sections = sections_from_form(FORM_SCHEMA, FORM_UI, {"final_state": "resuelto"})
    cierre = next(s for s in sections if s.title == "Cierre")
    assert [row.label for row in cierre.rows] == ["Estado final"]


def test_rf_115_un_campo_sin_responder_sale_con_raya_y_no_se_omite() -> None:
    """Omitirlo haría que el acta pareciera más completa de lo que está."""
    sections = sections_from_form(FORM_SCHEMA, FORM_UI, {})
    assert all(row.value == "—" for section in sections for row in section.rows)


def test_rf_115_el_valor_de_ia_lleva_su_procedencia_pegada_a_la_fila() -> None:
    sections = sections_from_form(
        FORM_SCHEMA,
        FORM_UI,
        {"found": "poste inclinado"},
        [
            {
                "field_key": "found",
                "origin": "voz",
                "model_name": "qwen2.5-1.5b",
                "model_version": "q4_k_m",
                "confidence": 0.9,
                "confirmed_by": "tecnico.7",
                "accepted_unchanged": False,
                "is_ai": True,
            }
        ],
    )
    row = next(r for s in sections for r in s.rows if r.label == "Encontrado")
    assert row.ai_note is not None and "dictado" in row.ai_note
    # Y un campo que la persona escribió no lleva nota: decirlo de todos significaría nada.
    other = next(r for s in sections for r in s.rows if r.label == "Resistencia medida")
    assert other.ai_note is None


# --- firmas -----------------------------------------------------------------------------
def test_rf_115_una_firma_declarada_y_no_capturada_sale_como_sin_firma() -> None:
    signatures = signatures_from_form(FORM_SCHEMA, {})
    assert {s.role for s in signatures} == {"jefe_cuadrilla", "cliente"}
    assert all(not s.present for s in signatures)

    html = render_html(acta(signatures=signatures))
    assert html.count("Sin firma") == 2


def test_rf_115_una_firma_capturada_se_incrusta() -> None:
    def loader(key: str) -> tuple[bytes, str] | None:
        return (b"\x89PNG\r\n\x1a\n", "image/png") if key == "s3://firmas/jefe.png" else None

    signatures = signatures_from_form(
        FORM_SCHEMA, {"crew_leader_signature": "s3://firmas/jefe.png"}, loader
    )
    jefe = next(s for s in signatures if s.role == "jefe_cuadrilla")
    cliente = next(s for s in signatures if s.role == "cliente")
    assert (
        jefe.present
        and jefe.data_uri is not None
        and jefe.data_uri.startswith("data:image/png;base64,")
    )
    assert not cliente.present


# --- fotografías -------------------------------------------------------------------------
def test_rf_115_una_foto_cuyo_hash_no_cuadra_se_imprime_diciendolo() -> None:
    """Dejarla fuera haría que el acta pareciera más ordenada que la evidencia."""
    sospechosa = ActaPhoto(
        stage="despues",
        kind="foto",
        storage_hash="a" * 64,
        integrity_verified=False,
        data_uri="data:image/png;base64,AA==",
    )
    assert "el hash no coincide" in sospechosa.caption
    html = render_html(acta(photos=[sospechosa]))
    assert "photo--suspect" in html
    assert "el hash no coincide" in html


def test_rf_115_una_foto_que_no_se_pudo_cargar_deja_constancia_con_su_hash() -> None:
    ausente = ActaPhoto(stage="antes", kind="foto", storage_hash="b" * 64, integrity_verified=True)
    html = render_html(acta(photos=[ausente]))
    assert "Imagen no disponible" in html
    assert "bbbbbbbbbbbbbbbb" in html


def test_rf_115_sin_evidencia_el_acta_lo_dice() -> None:
    assert "no registra evidencia fotográfica" in render_html(acta())


# --- hallazgos normativos -----------------------------------------------------------------
def test_adr_007_un_limite_sin_verificar_no_se_cita_como_texto_oficial() -> None:
    """Una cifra que nadie leyó en la resolución, con una referencia de aspecto oficial debajo,
    es peor que no tener la regla."""
    sin_verificar = ActaFinding(
        message="Resistencia de puesta a tierra por encima del límite",
        outcome="incumple",
        severity="high",
        citation="ARCERNNR 002/20 Art. 7",
        limit_verified=False,
    )
    html = render_html(acta(findings=[sin_verificar]))
    assert "límite sin verificar" in html
    assert "provisional" in html
    assert "ARCERNNR 002/20" not in html


def test_adr_007_un_limite_verificado_si_se_cita() -> None:
    verificado = ActaFinding(
        message="Reposición dentro del plazo",
        outcome="cumple",
        severity="low",
        citation="ARCERNNR 002/20 Art. 7",
    )
    assert "ARCERNNR 002/20 Art. 7" in render_html(acta(findings=[verificado]))


# --- borrador ------------------------------------------------------------------------------
def test_rf_115_un_acta_de_una_ot_sin_aprobar_se_imprime_como_borrador() -> None:
    borrador = acta(work_order_state="en_revision")
    assert borrador.is_draft
    html = render_html(borrador)
    assert "BORRADOR" in html


def test_rf_115_un_acta_de_una_ot_aprobada_no_dice_borrador() -> None:
    assert "BORRADOR" not in render_html(acta())


def test_rf_115_los_avisos_del_formulario_se_imprimen() -> None:
    """Un acta salida de un formulario incompleto debe decirlo en su propia cara."""
    html = render_html(acta(warnings=["el bloque 'B07' no existe y se omitió"]))
    assert "B07" in html


# --- escapado ------------------------------------------------------------------------------
def test_rf_115_una_observacion_con_marcado_no_se_convierte_en_marcado() -> None:
    """Un técnico dicta lo que dicta, y una etiqueta del GIS puede traer cualquier cosa."""
    peligro = '<script>alert(1)</script> & "comillas"'
    assert esc(peligro) == ("&lt;script&gt;alert(1)&lt;/script&gt; &amp; &quot;comillas&quot;")
    html = render_html(
        acta(
            sections=[
                ActaSection(code="B10", title="Resumen", rows=[ActaRow("Encontrado", peligro)])
            ]
        )
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_rf_115_tambien_se_escapa_el_titulo_de_una_seccion() -> None:
    html = render_html(
        acta(sections=[ActaSection(code="B1", title="<b>Bloque</b>", rows=[ActaRow("a", "b")])])
    )
    assert "<b>Bloque</b>" not in html


# --- el QR y la huella ----------------------------------------------------------------------
def test_rf_115_el_qr_apunta_a_la_url_de_verificacion_y_es_svg() -> None:
    html = render_html(acta())
    assert "<svg" in html
    assert "https://sigec.example/verificar/Zm9vYmFyMTIzNDU2" in html


def test_rf_115_la_huella_es_la_de_los_bytes_entregados() -> None:
    """Lo único que la verificación puede afirmar, y lo único que afirma."""
    document = acta(
        sections=[ActaSection(code="B10", title="Resumen", rows=[ActaRow("Encontrado", "ok")])],
        decisions=[ActaDecision("aprobada", "supervisor.1", None, "2026-09-22T15:00")],
        signatures=[ActaSignature(role="cliente", data_uri=None)],
    )
    pdf, digest = render_pdf(document)

    assert pdf.startswith(b"%PDF-")
    assert digest == hashlib.sha256(pdf).hexdigest()
    assert len(digest) == 64


def test_rf_115_cada_render_trae_su_propia_huella_y_ninguna_se_supone_igual_a_otra() -> None:
    """El supuesto que hay que dejar fijado, porque el primer diseño se apoyaba en él.

    Volver a renderizar **no** garantiza los mismos bytes. La salida de WeasyPrint sí es estable
    byte a byte para una página trivial —que es lo que muestra una comprobación rápida, y de ahí
    salió el error— pero en cuanto se incrustan subconjuntos de fuentes reales deja de estarlo, y
    depende de qué fuentes use el documento. Ni «siempre estable» ni «nunca» es cierto, así que el
    diseño no puede depender de ninguna de las dos.

    De ahí la regla: el registro guarda la huella de los bytes que se entregaron, y la
    verificación compara el archivo que alguien tiene contra esa huella. Nunca se vuelve a
    renderizar para comprobar. Este test no afirma una igualdad ni una desigualdad —sería frágil
    en ambos sentidos—: afirma que cada render responde por sus propios bytes.
    """
    document = acta(
        sections=[ActaSection(code="B10", title="Resumen", rows=[ActaRow("Encontrado", "ok")])],
        findings=[ActaFinding("hallazgo", "cumple", "low", "ARCERNNR 002/20")],
    )
    for _ in range(2):
        pdf, digest = render_pdf(document)
        assert pdf.startswith(b"%PDF-")
        assert digest == hashlib.sha256(pdf).hexdigest()
