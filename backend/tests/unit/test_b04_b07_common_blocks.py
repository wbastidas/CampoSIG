"""Los dos bloques comunes que el SRS declaraba y no existían: B04 Seguridad y B07 Materiales.

El SRS 4.2 dice que B1 a B12 están «en todos los formularios». Faltaban dos, y cada uno dejaba una
declaración sin efecto:

* **B04.** Seis formularios declaraban `requires_ats: true`. La bandera llegaba al teléfono como
  `x-requires-ats` y **nada la miraba**, porque no había campo donde anotar qué ATS se firmó. Una OT
  «que exige ATS» se podía cerrar sin nombrar ninguno. El test que más importa aquí es el que habría
  encontrado eso: un formulario que exige ATS y no incluye B04 tiene que avisar.
* **B07.** El catálogo `material` existía —`source: integracion`, vacío «hasta el primer envío del
  ERP»— y **ningún formulario** donde anotar el consumo, salvo una tabla propia dentro del bloque de
  luminarias. Ahora hay un solo lugar, que es lo que el conector del ERP puede leer sin desviarse.

Corre bajo los dos perfiles: un bloque común que solo funcionara con un modelo de datos fallaría
aquí, que es la alerta temprana de ADR-004.
"""

from __future__ import annotations

import pytest

from app.forms.catalog import get_definition, load_blocks, load_definitions
from app.forms.composer import SAFETY_REFERENCE, FormComposer
from app.forms.rules import missing_requirements
from app.model_profile.profile import load_profile
from app.model_profile.resolver import ModelResolver
from tests.conftest import ALL_PROFILE_IDS, build_metadata

#: Los formularios del piloto que exigen ATS. Leído del catálogo y no escrito a mano, para que el
#: test siga al dato: si mañana un formulario más lo exige, este test lo cubre sin editarlo.
ATS_FORMS = sorted(
    code for code, definition in load_definitions().items() if definition.form.requires_ats
)


@pytest.fixture(params=ALL_PROFILE_IDS)
def any_composer(request: pytest.FixtureRequest) -> FormComposer:
    profile_id = request.param
    return FormComposer(ModelResolver(load_profile(profile_id)), build_metadata(profile_id))


@pytest.fixture
def composer() -> FormComposer:
    return FormComposer(ModelResolver(load_profile("cnel-gye")), build_metadata("cnel-gye"))


class TestTheBlocksExist:
    def test_los_dos_bloques_comunes_estan_en_la_biblioteca(self) -> None:
        blocks = load_blocks()
        assert "B04" in blocks
        assert "B07" in blocks

    def test_b04_lleva_la_referencia_del_ats_el_permiso_y_el_epp(self) -> None:
        fields = load_blocks()["B04"].fields
        assert set(fields) == {"ats_reference", "work_permit_reference", "ppe_confirmed"}

    def test_b07_distingue_instalado_de_retirado(self) -> None:
        """Un cambio de luminaria instala una y retira otra: el ERP necesita los dos movimientos."""
        items = load_blocks()["B07"].fields["materials"]["items"]["properties"]
        assert "installed_quantity" in items
        assert "removed_quantity" in items
        assert items["removed_state"]["enum"] == ["reutilizable", "chatarra", "no_aplica"]

    def test_b07_es_condicional_porque_no_toda_ot_consume_material(self) -> None:
        assert load_blocks()["B07"].block.required is False

    def test_el_material_sale_del_catalogo_y_no_de_una_lista_en_el_bloque(self) -> None:
        items = load_blocks()["B07"].fields["materials"]["items"]["properties"]
        assert items["material_code"]["x-catalog-ref"] == "material"


class TestTheAtsDeclarationNowMeansSomething:
    @pytest.mark.parametrize("code", ATS_FORMS)
    def test_todo_formulario_que_exige_ats_incluye_b04(self, code: str) -> None:
        assert "B04" in get_definition(code).form.blocks

    @pytest.mark.parametrize("code", ATS_FORMS)
    def test_la_referencia_del_ats_es_obligatoria_en_el_esquema(
        self, code: str, any_composer: FormComposer
    ) -> None:
        composed = any_composer.compose(code)
        assert SAFETY_REFERENCE in composed.schema["required"]

    @pytest.mark.parametrize("code", ATS_FORMS)
    def test_ningun_formulario_que_exige_ats_avisa_de_que_le_falta_donde_anotarlo(
        self, code: str, any_composer: FormComposer
    ) -> None:
        composed = any_composer.compose(code)
        assert not any("B04" in warning for warning in composed.warnings)

    def test_un_formulario_que_exige_ats_sin_b04_avisa(self, composer: FormComposer) -> None:
        """El test que habría encontrado el hueco, y el que impide que vuelva.

        Se comprueba quitando el bloque de un formulario que sí lo exige: una mala configuración que
        nadie notaría es exactamente el estado en que estaban los seis.
        """
        definitions = load_definitions()
        definition = definitions[ATS_FORMS[0]]
        definition.form.blocks = [code for code in definition.form.blocks if code != "B04"]

        composed = composer.compose(definition.code)

        assert any("B04" in warning for warning in composed.warnings)
        assert SAFETY_REFERENCE not in composed.schema.get("required", [])

    def test_un_formulario_que_no_exige_ats_no_obliga_a_la_referencia(
        self, composer: FormComposer
    ) -> None:
        """Y es una decisión: el registro de una interrupción no es una visita a campo."""
        without = [
            code
            for code, definition in load_definitions().items()
            if not definition.form.requires_ats
        ]
        assert without, "el catálogo debería tener al menos un formulario sin ATS"
        for code in without:
            composed = composer.compose(code)
            assert SAFETY_REFERENCE not in composed.schema.get("required", [])


class TestTheB04Rule:
    """Un permiso de trabajo sin su ATS no se puede cerrar.

    La regla usa el operador «está contestado», que hasta ahora ninguna de las tres
    implementaciones tenía: escrita con un operador desconocido habría sido otra declaración que no
    hace nada, que es justo el defecto que este bloque viene a cerrar.
    """

    def rules(self) -> list[dict[str, object]]:
        return [rule.model_dump(exclude_none=True) for rule in load_blocks()["B04"].rules]

    def test_con_permiso_y_sin_ats_la_regla_exige_el_ats(self) -> None:
        missing = missing_requirements(self.rules(), {"work_permit_reference": "PT-2026-77"})
        assert [item.field for item in missing] == ["ats_reference"]

    def test_con_permiso_y_con_ats_no_exige_nada(self) -> None:
        answers = {"work_permit_reference": "PT-2026-77", "ats_reference": "ATS-2026-0001"}
        assert missing_requirements(self.rules(), answers) == []

    def test_sin_permiso_la_regla_calla(self) -> None:
        assert missing_requirements(self.rules(), {}) == []

    def test_un_permiso_en_blanco_no_dispara_la_regla(self) -> None:
        """Un campo con espacios se ve vacío en la pantalla: exigir por él sería inexplicable."""
        assert missing_requirements(self.rules(), {"work_permit_reference": "   "}) == []


class TestMaterialsHaveOnePlace:
    def test_el_bloque_de_luminarias_ya_no_lleva_su_propia_tabla(self) -> None:
        """Dos tablas obligarían al conector del ERP a leer en dos sitios, y una se desviaría."""
        assert "replaced_items" not in load_blocks()["AP01"].fields

    def test_los_formularios_que_consumen_material_llevan_b07(self) -> None:
        for code in ("F-AP-01", "F-OP-01", "F-IC-03"):
            assert "B07" in get_definition(code).form.blocks, code

    def test_una_inspeccion_no_lleva_materiales(self) -> None:
        """No consume nada, y un bloque de más es una pantalla de más con guantes puestos."""
        assert "B07" not in get_definition("F-MT-01").form.blocks

    @pytest.mark.parametrize("code", ["F-AP-01", "F-OP-01", "F-IC-03"])
    def test_la_tabla_de_materiales_llega_al_formulario_compuesto(
        self, code: str, any_composer: FormComposer
    ) -> None:
        composed = any_composer.compose(code)
        assert "materials" in composed.schema["properties"]

    @pytest.mark.parametrize("code", ["F-AP-01", "F-OP-01", "F-IC-03"])
    def test_los_materiales_no_son_obligatorios(
        self, code: str, any_composer: FormComposer
    ) -> None:
        """B07 es condicional: exigirlos convertiría toda inspección en una liquidación."""
        composed = any_composer.compose(code)
        assert "materials" not in composed.schema.get("required", [])
