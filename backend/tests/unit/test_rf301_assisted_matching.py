"""Coincidencia asistida: propone bindings y no los decide (RF-301, RF-302).

El criterio de aceptación de I2 dice que un administrador funcional produce un perfil
operativo partiendo del export de metadatos de otra Unidad de Negocio, **sin escribir
código**. Hasta ahora existía el motor que usa el perfil y el validador que lo revisa; lo
que faltaba era la forma de llegar a él sin escribir un YAML a mano.

La propiedad central de esta suite no es "acierta", es **"no acierta calladamente"**. Un
importador que elige mal la clase produce un perfil que funciona —los formularios se
generan, la sincronización corre— y manda los datos de campo a la clase equivocada. Eso no
se nota en semanas. Así que cada caso de abajo prueba una forma de equivocarse:

* una clase con la geometría incorrecta queda descartada, no penalizada;
* un campo de conectividad de la red geométrica no es candidato ni siquiera si el nombre
  encaja, y tampoco se acepta como anulación manual (ADR-001);
* una columna de auditoría no es candidata a clave de negocio, que es lo que `OBJECTID`
  parecería si nadie lo impidiera;
* dos clases que puntúan casi igual se reportan como ambiguas y **no** se preseleccionan.

Ningún nombre real aparece aquí: los casos sintéticos usan nombres inventados, y el caso de
ida y vuelta deriva los nombres del perfil activo (RF-305).
"""

from __future__ import annotations

import pytest

from app.model_profile.amd import load_asset_model
from app.model_profile.matching import (
    AMBIGUITY_MARGIN,
    DocumentError,
    build_profile_document,
    default_decisions,
    distinctive_attribute_keys,
    fold,
    normalise_geometry,
    propose_asset_against,
    propose_profile,
    propose_value_map,
    render_profile_yaml,
    tokens_of,
    validate_document,
)
from app.model_profile.metadata import (
    DomainType,
    FieldCategory,
    GisDomain,
    GisField,
    GisLayerMetadata,
    GisMetadata,
    GisRelationship,
)
from app.model_profile.profile import ProfileHeader, load_profile
from app.model_profile.resolver import NEVER_WRITE_FIELDS


def _header(profile_id: str = "importado") -> ProfileHeader:
    return ProfileHeader(id=profile_id, provider="arcpy-agent", spatial_reference=32717)


# --- ida y vuelta: el perfil vigente se reconstruye desde sus propios metadatos -------
@pytest.mark.parametrize("profile_id", ["cnel-gye", "alt-synthetic"])
def test_rf_301_la_propuesta_reconstruye_el_perfil_de_origen(profile_id: str) -> None:
    """El caso más fuerte que se puede montar sin una geodatabase real.

    Se generan los metadatos que el agente habría exportado de un perfil conocido y se
    comprueba que la propuesta vuelve a ese mismo perfil. Corre con los dos perfiles, que
    son deliberadamente distintos —uno en español y otro en inglés—, de modo que lo que se
    verifica es el mecanismo y no un diccionario afinado a un cliente.
    """
    from tests.conftest import build_metadata

    metadata = build_metadata(profile_id)
    expected = load_profile(profile_id)
    proposal = propose_profile(metadata)

    for asset in proposal.assets:
        binding = expected.bindings[asset.asset_type_key]
        assert asset.best is not None, f"no se propuso clase para '{asset.asset_type_key}'"
        assert asset.best.layer == binding.layer
        assert not asset.ambiguous

    document = build_profile_document(metadata, default_decisions(proposal, _header(profile_id)))
    assert validate_document(document) == []


@pytest.mark.parametrize("profile_id", ["cnel-gye", "alt-synthetic"])
def test_rf_301_el_documento_propuesto_resuelve_igual_que_el_original(profile_id: str) -> None:
    """Y el perfil reconstruido resuelve los mismos nombres reales que el de origen.

    Reconstruir los bindings no basta: lo que la plataforma usa es el resolver, así que la
    prueba es que el resolver construido sobre el documento propuesto conteste lo mismo.
    """
    from app.model_profile.profile import DataModelProfile
    from app.model_profile.resolver import ModelResolver
    from tests.conftest import build_metadata

    metadata = build_metadata(profile_id)
    original = ModelResolver(load_profile(profile_id))
    proposal = propose_profile(metadata)
    imported = ModelResolver(
        DataModelProfile.model_validate(
            build_profile_document(metadata, default_decisions(proposal, _header(profile_id)))
        )
    )

    for asset_key in load_asset_model().asset_type_keys:
        assert imported.binding(asset_key).layer == original.binding(asset_key).layer
        for attribute in original.asset_type(asset_key).attributes:
            expected = original.binding(asset_key).attributes.get(attribute.key)
            got = imported.binding(asset_key).attributes.get(attribute.key)
            if expected is None:
                continue
            if got is None:
                # Legítimo, y es la propiedad que importa: lo que la propuesta no resuelve
                # sola queda sin decidir y aparece en la lista de huecos, en vez de
                # resolverse a cara o cruz. Lo que no se admite es que falte en silencio.
                assert any(asset_key in gap and attribute.key in gap for gap in proposal.gaps), (
                    f"'{asset_key}.{attribute.key}' se perdió sin quedar reportado"
                )
                continue
            assert got.field == expected.field


# --- casos sintéticos: cada uno es una forma de equivocarse ---------------------------
def _point_layer(name: str, extra: list[GisField] | None = None) -> GisLayerMetadata:
    return GisLayerMetadata(
        name=name,
        geometry_type="Point",
        fields=[
            GisField(
                name="CODIGO_ACT",
                alias="Código",
                type="String",
                nullable=False,
                category=FieldCategory.CORE,
            ),
            GisField(
                name="MAT_TIPO",
                alias="Material",
                type="String",
                domain="DomMaterial",
                category=FieldCategory.CORE,
            ),
            GisField(name="ALTURA_M", alias="Altura", type="Double", category=FieldCategory.OTHER),
            GisField(
                name="ALIM_COD",
                alias="Alimentador",
                type="String",
                domain="DomAlim",
                category=FieldCategory.CORE,
            ),
            GisField(
                name="F_INSTAL",
                alias="Fecha de instalación",
                type="Date",
                category=FieldCategory.OTHER,
            ),
            *(extra or []),
        ],
    )


_MATERIAL_DOMAIN = GisDomain(
    name="DomMaterial",
    domain_type=DomainType.CODED_VALUE,
    # Display names in Ecuadorian Spanish, which is the only thing the matcher has to go on:
    # the codes themselves say nothing.
    coded_values={
        "1": "Hormigón armado",
        "2": "Madera",
        "3": "Acero galvanizado",
        "9": "Otro material",
    },
)

_FEEDER_DOMAIN = GisDomain(
    name="DomAlim",
    domain_type=DomainType.CODED_VALUE,
    coded_values={"A01": "Alimentador uno"},
    volatile_by_business_unit=True,
)


def _snapshot(layers: list[GisLayerMetadata], **kwargs: object) -> GisMetadata:
    return GisMetadata(
        profile_id="sintetico",
        domains=[_MATERIAL_DOMAIN, _FEEDER_DOMAIN],
        layers=layers,
        **kwargs,  # type: ignore[arg-type]
    )


def test_rf_301_una_clase_con_geometria_incorrecta_queda_descartada() -> None:
    """Descartada, no penalizada. Un activo puntual no vive en una polilínea.

    El nombre de la clase de abajo es el mejor que podría tener para `support_structure`;
    la geometría es la que no puede ser. Si la puntuación fuera una suma ponderada sin
    descalificaciones, un nombre perfecto compensaría la geometría y la propuesta sería
    imposible de aplicar.
    """
    metadata = _snapshot(
        [
            GisLayerMetadata(
                name="PosteSoporteTendido",
                geometry_type="Polyline",
                fields=_point_layer("x").fields,
            )
        ]
    )
    proposal = propose_profile(metadata)
    assert proposal.asset("support_structure").best is None
    assert any("support_structure" in gap for gap in proposal.gaps)


def test_rf_301_un_campo_de_conectividad_nunca_es_candidato() -> None:
    """ADR-001, en el importador.

    Se le da al campo de conectividad un alias que encaja perfectamente con el atributo
    canónico. La única razón por la que no gana es su categoría, que es exactamente la
    razón por la que tiene que no ganar.
    """
    connectivity = sorted(NEVER_WRITE_FIELDS)[0]
    metadata = _snapshot(
        [
            _point_layer(
                "PosteSoporte",
                extra=[
                    GisField(
                        name=connectivity,
                        alias="Código",
                        type="String",
                        category=FieldCategory.CONNECTIVITY,
                    )
                ],
            )
        ]
    )
    proposal = propose_profile(metadata)
    code = next(
        a for a in proposal.asset("support_structure").attributes if a.attribute_key == "code"
    )
    assert connectivity not in [c.field for c in code.candidates]
    # Y se dice por qué, porque "¿por qué no aparece este campo?" se pregunta una vez por
    # instalación y merece respuesta en la pantalla, no en el código.
    assert any(connectivity in reason for reason in code.refused)


def test_rf_301_un_campo_de_conectividad_tampoco_se_acepta_como_anulacion_manual() -> None:
    """La propuesta no lo ofrece; el constructor del documento tampoco lo acepta.

    Dos compuertas y no una: la primera es una recomendación, y una recomendación se puede
    ignorar desde una pantalla o desde un cliente escrito a mano.
    """
    connectivity = sorted(NEVER_WRITE_FIELDS)[0]
    metadata = _snapshot(
        [
            _point_layer(
                "PosteSoporte",
                extra=[
                    GisField(name=connectivity, type="String", category=FieldCategory.CONNECTIVITY)
                ],
            )
        ]
    )
    decisions = default_decisions(propose_profile(metadata), _header())
    decisions.assets["support_structure"].attributes["code"] = connectivity

    with pytest.raises(DocumentError, match="conectividad"):
        build_profile_document(metadata, decisions)


def test_rf_301_una_columna_de_auditoria_no_es_clave_de_negocio() -> None:
    """`OBJECTID` es un candidato excelente a `code` si nadie lo impide."""
    metadata = _snapshot(
        [
            _point_layer(
                "PosteSoporte",
                extra=[GisField(name="OBJECTID", alias="Id", type="Integer", nullable=False)],
            )
        ]
    )
    proposal = propose_profile(metadata)
    code = next(
        a for a in proposal.asset("support_structure").attributes if a.attribute_key == "code"
    )
    assert "OBJECTID" not in [c.field for c in code.candidates]
    assert code.best is not None and code.best.field == "CODIGO_ACT"


def test_rf_301_dos_clases_parecidas_se_reportan_ambiguas_y_no_se_preseleccionan() -> None:
    """El caso que de verdad ocurre: aéreo y subterráneo, o urbano y rural.

    Preseleccionar una de las dos y llamarlo valor por defecto es cómo un binding
    equivocado lo acepta alguien pasando pantallas.
    """
    metadata = _snapshot([_point_layer("PosteSoporteA"), _point_layer("PosteSoporteB")])
    asset = propose_profile(metadata).asset("support_structure")

    assert asset.ambiguous
    assert abs(asset.candidates[0].score - asset.candidates[1].score) < AMBIGUITY_MARGIN
    assert "support_structure" not in default_decisions(propose_profile(metadata), _header()).assets


def test_rf_301_sin_ninguna_clase_parecida_no_se_propone_nada() -> None:
    """Y se dice que no se propuso nada, en vez de elegir lo menos malo."""
    metadata = _snapshot(
        [
            GisLayerMetadata(
                name="ZonaAdministrativa",
                geometry_type="Polygon",
                fields=[GisField(name="NOMBRE", type="String")],
            )
        ]
    )
    proposal = propose_profile(metadata)
    assert all(asset.best is None for asset in proposal.assets)
    assert len(proposal.gaps) == len(load_asset_model().asset_types)


def test_rf_301_la_estructura_sola_no_identifica_un_tipo_sin_atributos_propios() -> None:
    """Tener código y alimentador no dice de qué clase se trata.

    Es la regla que costó descubrir escribiendo esta suite: con un solo snapshot de una
    clase puntual, cinco de los seis tipos canónicos recibían candidato, porque coincidir en
    los dos atributos más genéricos del vocabulario bastaba para pasar el piso de
    puntuación. `service_point` no tiene ningún atributo propio, así que solo se puede
    identificar por el nombre de la clase — y decirlo es más útil que adivinarlo.
    """
    metadata = _snapshot([_point_layer("PosteSoporte")])
    proposal = propose_profile(metadata)

    assert proposal.asset("support_structure").best is not None
    assert proposal.asset("service_point").best is None
    assert "code" not in distinctive_attribute_keys(load_asset_model())
    assert "material" in distinctive_attribute_keys(load_asset_model())


def test_rf_302_los_huecos_se_enumeran_en_castellano_por_tipo_de_activo() -> None:
    """RF-302: el diagnóstico es lo que hace verificable el "configurar, no programar"."""
    metadata = _snapshot([_point_layer("PosteSoporte")])
    proposal = propose_profile(metadata)

    # Cinco de los seis tipos canónicos no tienen clase en este snapshot.
    assert sum(1 for asset in proposal.assets if asset.best is None) == 5
    assert all(isinstance(gap, str) and gap for gap in proposal.gaps)
    assert proposal.unclaimed_layer_count == 0


# --- dominios y mapas de valores -----------------------------------------------------
def test_rf_301_el_mapa_de_valores_sale_de_los_nombres_visibles_del_dominio() -> None:
    """Los códigos no dicen nada; las etiquetas sí, y el vocabulario canónico las conoce."""
    amd = load_asset_model()
    attribute = amd.asset_type("support_structure").attribute("material")
    assert attribute is not None

    from app.voice.lexicon import load_spoken_vocabulary

    proposal = propose_value_map(
        attribute, _MATERIAL_DOMAIN, amd, load_spoken_vocabulary().enum_synonyms
    )

    assert proposal.mapping["concrete"] == "1"
    assert proposal.mapping["wood"] == "2"
    assert proposal.mapping["steel"] == "3"
    assert proposal.mapping["other"] == "9"
    # El dominio sintético no tiene fibra de vidrio, y eso se reporta en vez de inventarse.
    assert proposal.unmapped == ["fiberglass"]


def test_rf_301_un_dominio_de_rango_no_produce_mapa_de_valores() -> None:
    """Un rango no tiene códigos que mapear, y decir que los tiene sería mentir."""
    amd = load_asset_model()
    attribute = amd.asset_type("support_structure").attribute("material")
    assert attribute is not None

    proposal = propose_value_map(
        attribute,
        GisDomain(name="Rango", domain_type=DomainType.RANGE, range_min=1, range_max=9),
        amd,
        {},
    )
    assert proposal.mapping == {}
    assert set(proposal.unmapped) == set(amd.enums["material.support"])


def test_rf_304_la_volatilidad_del_dominio_viaja_al_binding() -> None:
    """Un catálogo que cambia por unidad no se puede empaquetar como constante."""
    metadata = _snapshot([_point_layer("PosteSoporte")])
    document = build_profile_document(
        metadata, default_decisions(propose_profile(metadata), _header())
    )
    bindings = document["bindings"]
    assert isinstance(bindings, dict)
    feeder = bindings["support_structure"]["attributes"]["feeder_code"]
    assert feeder["domain"] == "DomAlim"
    assert feeder["volatile_by_business_unit"] is True


def test_rf_345_el_documento_propuesto_nunca_habilita_escritura_directa() -> None:
    """La escritura directa es una decisión con firma del equipo GIS, no un valor por defecto."""
    metadata = _snapshot([_point_layer("PosteSoporte")])
    document = build_profile_document(
        metadata, default_decisions(propose_profile(metadata), _header())
    )
    bindings = document["bindings"]
    assert isinstance(bindings, dict)
    assert all(binding["write_path"] == "staging_only" for binding in bindings.values())
    assert set(document["never_write_fields"]) == NEVER_WRITE_FIELDS


def test_rf_301_las_unidades_relacionadas_se_proponen_con_nombre_canonico() -> None:
    """El nombre del bloque repetible no puede salir del nombre real de la clase (RF-305)."""
    transformer = GisLayerMetadata(
        name="PuestoTrafo",
        geometry_type="Point",
        fields=[
            GisField(name="COD_TRAFO", alias="Código", type="String", nullable=False),
            GisField(name="KVA_NOM", alias="Potencia", type="Double"),
        ],
    )
    metadata = _snapshot(
        [transformer],
        relationships=[
            GisRelationship(
                name="RelTrafoUnidad",
                origin_layer="PuestoTrafo",
                destination_layer="UnidadTrafo",
                cardinality="One To Many",
            )
        ],
    )
    asset = propose_profile(metadata).asset("distribution_transformer")
    assert [r.as_ for r in asset.related] == ["units"]
    assert asset.related[0].target_layer == "UnidadTrafo"


# --- anulaciones y reevaluación -------------------------------------------------------
def test_rf_301_reevaluar_contra_otra_clase_recalcula_los_atributos() -> None:
    """Cuando alguien rechaza la clase líder, los atributos en pantalla son de la rechazada."""
    chosen = GisLayerMetadata(
        name="PosteRural",
        geometry_type="Point",
        fields=[GisField(name="NUM_POSTE", alias="Número", type="String", nullable=False)],
    )
    metadata = _snapshot([_point_layer("PosteSoporte"), chosen])

    asset = propose_asset_against(metadata, "support_structure", "PosteRural")
    code = next(a for a in asset.attributes if a.attribute_key == "code")
    assert code.best is not None and code.best.field == "NUM_POSTE"


def test_rf_301_elegir_una_clase_con_geometria_incorrecta_se_permite_pero_puntua_cero() -> None:
    """Un administrador puede saber algo que el snapshot no dice; no se le silencia el aviso."""
    metadata = _snapshot(
        [
            GisLayerMetadata(
                name="TramoRed",
                geometry_type="Polyline",
                fields=[GisField(name="CODIGO", alias="Código", type="String")],
            )
        ]
    )
    asset = propose_asset_against(metadata, "support_structure", "TramoRed")
    assert asset.candidates[0].score == 0.0
    reasons = [e for e in asset.candidates[0].evidence if e.signal == "geometría"]
    assert reasons and "point" in reasons[0].detail


def test_rf_301_un_campo_inexistente_en_la_clase_se_rechaza_al_armar_el_documento() -> None:
    metadata = _snapshot([_point_layer("PosteSoporte")])
    decisions = default_decisions(propose_profile(metadata), _header())
    decisions.assets["support_structure"].attributes["code"] = "NO_EXISTE"

    with pytest.raises(DocumentError, match="NO_EXISTE"):
        build_profile_document(metadata, decisions)


def test_rf_301_una_clase_inexistente_se_rechaza_al_armar_el_documento() -> None:
    metadata = _snapshot([_point_layer("PosteSoporte")])
    decisions = default_decisions(propose_profile(metadata), _header())
    decisions.assets["support_structure"].layer = "OtraClase"

    with pytest.raises(DocumentError, match="OtraClase"):
        build_profile_document(metadata, decisions)


# --- utilidades de plegado -------------------------------------------------------------
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("EstructuraDeSoporte", ["estructura", "de", "soporte"]),
        ("TIPO_MAT", ["tipo", "mat"]),
        ("ALTURA_M", ["altura", "m"]),
        ("códigoActivo", ["codigo", "activo"]),
        ("XFMR3F", ["xfmr3f"]),
    ],
)
def test_los_nombres_se_parten_por_las_tres_convenciones_que_conviven(
    name: str, expected: list[str]
) -> None:
    """CamelCase, SNAKE_CASE y la carrera en mayúsculas del límite de diez caracteres."""
    assert tokens_of(name) == expected


@pytest.mark.parametrize(
    ("declared", "expected"),
    [
        ("Point", "point"),
        ("esriGeometryPolyline", "polyline"),
        ("Polygon", "polygon"),
        ("Multipoint", "multipoint"),
        (None, None),
        ("Table", None),
    ],
)
def test_la_geometria_se_normaliza_desde_cualquier_grafia(
    declared: str | None, expected: str | None
) -> None:
    assert normalise_geometry(declared) == expected


def test_el_plegado_quita_acentos_mayusculas_y_separadores() -> None:
    assert fold("Código_Activo") == fold("CODIGOACTIVO") == "codigoactivo"


# --- exportación -----------------------------------------------------------------------
def test_rf_301_el_yaml_exportado_se_vuelve_a_cargar_como_perfil() -> None:
    """Lo que se descarga para versionar en profiles/ tiene que ser un perfil de verdad."""
    import yaml

    from app.model_profile.profile import DataModelProfile

    metadata = _snapshot([_point_layer("PosteSoporte")])
    document = build_profile_document(
        metadata, default_decisions(propose_profile(metadata), _header("importado"))
    )
    rendered = render_profile_yaml(document)

    assert rendered.startswith("#")
    reloaded = DataModelProfile.model_validate(yaml.safe_load(rendered))
    assert reloaded.id == "importado"
    assert reloaded.bindings["support_structure"].layer == "PosteSoporte"
