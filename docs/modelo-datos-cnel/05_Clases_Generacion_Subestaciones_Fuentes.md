# 05 · Clases: Generación, Subestaciones y Fuentes de Circuito

[⬅ Volver al índice](00_Indice_y_Conceptos.md) · [Dominios](01_Dominios.md) · [Relaciones](02_Relaciones.md) · [03](03_Clases_Redes_y_Soporte.md) · [04](04_Clases_Proteccion_y_Potencia.md) · [06](06_Clases_Consumidores_y_Alumbrado.md)

Generación (convencional y distribuida), motores, subestaciones y la tabla `CIRCUITOFUENTE` que define los parámetros eléctricos de cabecera de cada alimentador — pieza clave del trazado eléctrico (ver [00_Indice_y_Conceptos.md](00_Indice_y_Conceptos.md#conectividad-eléctrica-y-trazado-source--sink)).

**Clases en este archivo:** [`Generador`](#generador) · [`GeneradorDistribuido`](#generadordistribuido) · [`MOTORINDUCCION`](#motorinduccion) · [`MOTORSINCRONO`](#motorsincrono) · [`Subestacion`](#subestacion) · [`CIRCUITOFUENTE`](#circuitofuente) · [`DATOSOPERADORA`](#datosoperadora)

**Leyenda de categoría de campo:** ✅ **CORE** = obligatorio según el manual `MN-TEC-OPE-100` · 🔌 **Conectividad** = usado por el motor de red geométrica / trazado eléctrico (ver [00 · Conceptos](00_Indice_y_Conceptos.md#conectividad-eléctrica-y-trazado-source--sink)) · 🔧 **Sistema** = auditoría/metadatos técnicos común a casi todas las clases (usuario y fecha de registro, IDs internos, geometría, ubicación administrativa) · ▫️ **Otro** = resto de atributos propios de la clase — **no es "innecesario", solo no está confirmado como obligatorio por el manual**; revisar según el caso de uso.

---

## `Generador`
<a id="generador"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple) |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 53 total — ✅ 0 core · 🔌 4 conectividad · 🔧 25 sistema · ▫️ 24 otros |

> ℹ️ Esta clase no tiene una tabla de "Campos obligatorios" dedicada en el manual `MN-TEC-OPE-100`. La columna **Categoría** solo distingue campos de 🔌 *conectividad* / 🔧 *sistema* (comunes a casi todas las clases) de ▫️ *otros* (atributos propios de la clase, no confirmados como obligatorios por el manual pero potencialmente relevantes según el contexto de uso).

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | 🔧 Sistema |  |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | 🔧 Sistema |  |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | 🔧 Sistema |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | 🔧 Sistema |  |
| `PROVINCIA` | Provincia | String | 2 | Yes | 🔧 Sistema |  |
| `CANTON` | Canton | String | 4 | Yes | 🔧 Sistema |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | 🔧 Sistema |  |
| `CODIGOELEMENTO` | Codigo Luminaria | Integer | 4 | Yes | ▫️ Otro |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `ANCILLARYROLE` | ANCILLARYROLE | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ENABLED` | ENABLED | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | ALIMENTADORID | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORID2` | ALIMENTADOR2ID | String | 10 | Yes | ▫️ Otro |  |
| `FASECONEXION` | FASECONEXION | Integer | 4 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | ALIMENTADORINFO | Integer | 4 | Yes | ▫️ Otro |  |
| `ELECTRICTRACEWEIGHT` | ELECTRICTRACEWEIGHT | Integer | 4 | Yes | 🔌 Conectividad |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `SUBTIPO` | Subtipo | Integer | 4 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Small Integer | 2 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador2 | String | 10 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | Comentarios | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `CONEXIONCONFIGURACION` | Configuración Conexión | String | 50 | Yes | ▫️ Otro |  |
| `REACTANCIATIERRA` | React.Tierra | Integer | 4 | Yes | ▫️ Otro |  |
| `RESISTENCIATIERRA` | Resist.Tierra | Integer | 4 | Yes | ▫️ Otro |  |
| `SECUENCIAREACTANCIAPOSITIVA` | React.Seq.Posit. | Double | 8 | Yes | ▫️ Otro |  |
| `SECUENCIARESISTENCIAPOSITIVA` | Resit.Seq.Positiv. | Double | 8 | Yes | ▫️ Otro |  |
| `FACTORPOTENCIA` | Factor Potencia | Double | 8 | Yes | ▫️ Otro |  |
| `REACTANCIASUBTRANSITORIA` | Rect. Subtransitoria | Double | 8 | Yes | ▫️ Otro |  |
| `REACTANCIATRANSITORIA` | React. Transitoria | Double | 8 | Yes | ▫️ Otro |  |
| `REACTANCIASECUENCIAZERO` | React.Seq. Cero | Double | 8 | Yes | ▫️ Otro |  |
| `RESISTENCIASECUENCIAZERO` | Resist. Seq. Cero | Double | 8 | Yes | ▫️ Otro |  |
| `KW` | Potencia Activa | Integer | 4 | Yes | ▫️ Otro |  |
| `VOLTAJENOMINAL` | VOLTAJENOMINAL | String | 50 | Yes | ▫️ Otro |  |
| `PUNTOCARGAGLOBALID` | Punto Carga Global Id | GUID | 38 | Yes | ▫️ Otro |  |
| `POTENCIANOMINAL` | Potencia (Kva) | String | 50 | Yes | ▫️ Otro |  |
| `GENERACIONMAXREACTIVO` | Gener.Max.Reactivos | Integer | 4 | Yes | ▫️ Otro |  |
| `SHAPE` | SHAPE | Geometry | 0 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | — |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `SUBTIPO` | 1 | — |
| `CONEXIONCONFIGURACION` |  | [Generador ConexiónConfiguración](01_Dominios.md#generador-conexionconfiguracion) |
| `VOLTAJENOMINAL` |  | [Generador VoltajeNominal](01_Dominios.md#generador-voltajenominal) |
| `POTENCIANOMINAL` |  | [Potencia Nominal Transformador Distribucion](01_Dominios.md#potencia-nominal-transformador-distribucion) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G251MIGUID | MIGUID | No | Yes |
| G251PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |
| G251PUNTOCARGAGL | PUNTOCARGAGLOBALID | No | Yes |

</details>

### Relaciones donde participa (1)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [PuntoCarga_Generador](02_Relaciones.md#puntocargagenerador) | Destino | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | One To One |

---

## `GeneradorDistribuido` — Generador Distribuido
<a id="generadordistribuido"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple) |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 80 total — ✅ 0 core · 🔌 4 conectividad · 🔧 25 sistema · ▫️ 51 otros |

> ℹ️ Esta clase no tiene una tabla de "Campos obligatorios" dedicada en el manual `MN-TEC-OPE-100`. La columna **Categoría** solo distingue campos de 🔌 *conectividad* / 🔧 *sistema* (comunes a casi todas las clases) de ▫️ *otros* (atributos propios de la clase, no confirmados como obligatorios por el manual pero potencialmente relevantes según el contexto de uso).

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | 🔧 Sistema |  |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | 🔧 Sistema |  |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | 🔧 Sistema |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | 🔧 Sistema |  |
| `PROVINCIA` | Provincia | String | 2 | Yes | 🔧 Sistema |  |
| `CANTON` | Canton | String | 4 | Yes | 🔧 Sistema |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | 🔧 Sistema |  |
| `CODIGOELEMENTO` | Codigo Luminaria | Integer | 4 | Yes | ▫️ Otro |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ▫️ Otro |  |
| `ESTRUCTURASOPORTEOBJECTID` | ESTRUCTURA SOPORTEOBJECT OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `ANCILLARYROLE` | ANCILLARYROLE | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ENABLED` | ENABLED | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | ALIMENTADORID | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORID2` | ALIMENTADOR2ID | String | 10 | Yes | ▫️ Otro |  |
| `FASECONEXION` | Fase | Integer | 4 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | ALIMENTADORINFO | Integer | 4 | Yes | ▫️ Otro |  |
| `ELECTRICTRACEWEIGHT` | ELECTRICTRACEWEIGHT | Integer | 4 | Yes | 🔌 Conectividad |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `SUBTIPO` | Subtipo | Integer | 4 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Small Integer | 2 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `ESTRUCTURASOPORTEGLOBALID` | Estructura Soporte GUID | GUID | 38 | Yes | ▫️ Otro |  |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador2 | String | 10 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | Comentarios | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `RATEDKVA` | RATEDKVA | Integer | 4 | Yes | ▫️ Otro |  |
| `PROPIEDAD` | PROPIEDAD | String | 50 | Yes | ▫️ Otro |  |
| `CONEXIONTIERRA` | CONEXIONTIERRA | String | 50 | Yes | ▫️ Otro |  |
| `NOMBRE` | NOMBRE | String | 50 | Yes | ▫️ Otro |  |
| `CODIGOCLIENTE` | CODIGOCLIENTE | String | 50 | Yes | ▫️ Otro |  |
| `CODIGOUNICO` | CODIGOUNICO | String | 50 | Yes | ▫️ Otro |  |
| `TIPO` | Tipo | Small Integer | 2 | Yes | ▫️ Otro |  |
| `FASE` | FASE | String | 50 | Yes | ▫️ Otro |  |
| `SUBTERRANEO` | Subterraneo | Small Integer | 2 | Yes | ▫️ Otro |  |
| `ATERRADO` | Aterrado | Small Integer | 2 | Yes | ▫️ Otro |  |
| `CONTRIBUCION` | Contribución | Double | 8 | Yes | ▫️ Otro |  |
| `EFICIENCIA` | Eficiencia | Double | 8 | Yes | ▫️ Otro |  |
| `FACTORPOTENCIA` | Factor Potencia | Double | 8 | Yes | ▫️ Otro |  |
| `POTENCIANOMINAL` | Potencia Nominal | String | 50 | Yes | ▫️ Otro |  |
| `VOLTAJENOMINAL` | Voltaje (Kv) | Double | 8 | Yes | ▫️ Otro |  |
| `TIPOREGULADOR` | Tipo Regulador | Small Integer | 2 | Yes | ▫️ Otro |  |
| `TIPOCONTRATO` | Tipo Contrato | String | 50 | Yes | ▫️ Otro |  |
| `MAXFP` | Max FP | Double | 8 | Yes | ▫️ Otro |  |
| `MAXP` | Max P | Double | 8 | Yes | ▫️ Otro |  |
| `MAXQ` | Max Q | Double | 8 | Yes | ▫️ Otro |  |
| `MINFP` | Min FP | Double | 8 | Yes | ▫️ Otro |  |
| `MINP` | Min P | Double | 8 | Yes | ▫️ Otro |  |
| `MINQ` | Min Q | Double | 8 | Yes | ▫️ Otro |  |
| `CONECTADOMEDIA` | Conectado a media | Small Integer | 2 | Yes | ▫️ Otro |  |
| `CONECTADOBAJA` | Conectado a Baja | Small Integer | 2 | Yes | ▫️ Otro |  |
| `SECUENCIARESISTPOS` | Resist.Seq.Posit. | Double | 8 | Yes | ▫️ Otro |  |
| `SECUENCIAREACTPOS` | React.Seq.Posit. | Double | 8 | Yes | ▫️ Otro |  |
| `RESISTSECUENCIAZERO` | Resist.Seq.Cero | Double | 8 | Yes | ▫️ Otro |  |
| `REACTSECUENCIAZERO` | React.Seq.Cero | Double | 8 | Yes | ▫️ Otro |  |
| `RESISTTIERRA` | Resist.Tierra(ohm) | Double | 8 | Yes | ▫️ Otro |  |
| `REACTTIERRA` | REACTTIERRA | Double | 8 | Yes | ▫️ Otro |  |
| `CONFIGURACIONCONEXION` | Conf.Conexión | String | 50 | Yes | ▫️ Otro |  |
| `RESISTTRANSITORIA` | Resist.Transitoria | Double | 8 | Yes | ▫️ Otro |  |
| `REACTTRANSITORIA` | React.Transitoria | Double | 8 | Yes | ▫️ Otro |  |
| `RESISTSUBTRANSITORIA` | Resist.Subtransitoria | Double | 8 | Yes | ▫️ Otro |  |
| `REACTSUBTRANSITORIA` | React.Subtransitoria | Double | 8 | Yes | ▫️ Otro |  |
| `NUMEROPOSTES` | Nro.Postes | Small Integer | 2 | Yes | ▫️ Otro |  |
| `SECUENCIARESISTNEG` | Resist.Seq.Neg. | Double | 8 | Yes | ▫️ Otro |  |
| `SECUENCIAREACTNEG` | React. Seq. Neg. | Double | 8 | Yes | ▫️ Otro |  |
| `PUNTOCARGAGLOBALID` | Punto Carga Global Id | GUID | 38 | Yes | ▫️ Otro |  |
| `SHAPE` | SHAPE | Geometry | 0 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `SUBTIPO` | 0 | — |
| `PROPIEDAD` |  | [Propietario](01_Dominios.md#propietario) |
| `TIPO` |  | [TipoGeneradorDist](01_Dominios.md#tipogeneradordist) |
| `SUBTERRANEO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `ATERRADO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `POTENCIANOMINAL` |  | [Potencia Nominal Transformador Distribucion](01_Dominios.md#potencia-nominal-transformador-distribucion) |
| `TIPOREGULADOR` |  | [TipoReguladorGenerador](01_Dominios.md#tiporeguladorgenerador) |
| `TIPOCONTRATO` |  | [TipoContratoGenerador](01_Dominios.md#tipocontratogenerador) |
| `CONECTADOMEDIA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CONECTADOBAJA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CONFIGURACIONCONEXION` |  | [Generador ConexiónConfiguración](01_Dominios.md#generador-conexionconfiguracion) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Almacenamiento (SUBTIPO=7)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ATERRADO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONECTADOBAJA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CONECTADOMEDIA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POTENCIANOMINAL` |  | [Potencia Nominal Transformador Distribucion](01_Dominios.md#potencia-nominal-transformador-distribucion) |
| `PROPIEDAD` |  | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTERRANEO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `TIPO` |  | [TipoGeneradorDist](01_Dominios.md#tipogeneradordist) |
| `TIPOCONTRATO` |  | [TipoContratoGenerador](01_Dominios.md#tipocontratogenerador) |
| `TIPOREGULADOR` |  | [TipoReguladorGenerador](01_Dominios.md#tiporeguladorgenerador) |

**Biomasa (SUBTIPO=4)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ATERRADO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONECTADOBAJA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CONECTADOMEDIA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POTENCIANOMINAL` |  | [Potencia Nominal Transformador Distribucion](01_Dominios.md#potencia-nominal-transformador-distribucion) |
| `PROPIEDAD` |  | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTERRANEO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `TIPO` |  | [TipoGeneradorDist](01_Dominios.md#tipogeneradordist) |
| `TIPOCONTRATO` |  | [TipoContratoGenerador](01_Dominios.md#tipocontratogenerador) |
| `TIPOREGULADOR` |  | [TipoReguladorGenerador](01_Dominios.md#tiporeguladorgenerador) |

**Eólico (SUBTIPO=3)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ATERRADO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONECTADOBAJA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CONECTADOMEDIA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POTENCIANOMINAL` |  | [Potencia Nominal Transformador Distribucion](01_Dominios.md#potencia-nominal-transformador-distribucion) |
| `PROPIEDAD` |  | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTERRANEO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `TIPO` |  | [TipoGeneradorDist](01_Dominios.md#tipogeneradordist) |
| `TIPOCONTRATO` |  | [TipoContratoGenerador](01_Dominios.md#tipocontratogenerador) |
| `TIPOREGULADOR` |  | [TipoReguladorGenerador](01_Dominios.md#tiporeguladorgenerador) |

**Fotovoltaico (SUBTIPO=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ATERRADO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONECTADOBAJA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CONECTADOMEDIA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POTENCIANOMINAL` |  | [Potencia Nominal Transformador Distribucion](01_Dominios.md#potencia-nominal-transformador-distribucion) |
| `PROPIEDAD` |  | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTERRANEO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `TIPO` |  | [TipoGeneradorDist](01_Dominios.md#tipogeneradordist) |
| `TIPOCONTRATO` |  | [TipoContratoGenerador](01_Dominios.md#tipocontratogenerador) |
| `TIPOREGULADOR` |  | [TipoReguladorGenerador](01_Dominios.md#tiporeguladorgenerador) |

**Fuel Cells (SUBTIPO=6)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ATERRADO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONECTADOBAJA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CONECTADOMEDIA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POTENCIANOMINAL` |  | [Potencia Nominal Transformador Distribucion](01_Dominios.md#potencia-nominal-transformador-distribucion) |
| `PROPIEDAD` |  | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTERRANEO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `TIPO` |  | [TipoGeneradorDist](01_Dominios.md#tipogeneradordist) |
| `TIPOCONTRATO` |  | [TipoContratoGenerador](01_Dominios.md#tipocontratogenerador) |
| `TIPOREGULADOR` |  | [TipoReguladorGenerador](01_Dominios.md#tiporeguladorgenerador) |

**Geotérmico (SUBTIPO=5)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ATERRADO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONECTADOBAJA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CONECTADOMEDIA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POTENCIANOMINAL` |  | [Potencia Nominal Transformador Distribucion](01_Dominios.md#potencia-nominal-transformador-distribucion) |
| `PROPIEDAD` |  | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTERRANEO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `TIPO` |  | [TipoGeneradorDist](01_Dominios.md#tipogeneradordist) |
| `TIPOCONTRATO` |  | [TipoContratoGenerador](01_Dominios.md#tipocontratogenerador) |
| `TIPOREGULADOR` |  | [TipoReguladorGenerador](01_Dominios.md#tiporeguladorgenerador) |

**Hidraúlico (SUBTIPO=0) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ATERRADO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONECTADOBAJA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CONECTADOMEDIA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POTENCIANOMINAL` |  | [Potencia Nominal Transformador Distribucion](01_Dominios.md#potencia-nominal-transformador-distribucion) |
| `PROPIEDAD` |  | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTERRANEO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `TIPO` |  | [TipoGeneradorDist](01_Dominios.md#tipogeneradordist) |
| `TIPOCONTRATO` |  | [TipoContratoGenerador](01_Dominios.md#tipocontratogenerador) |
| `TIPOREGULADOR` |  | [TipoReguladorGenerador](01_Dominios.md#tiporeguladorgenerador) |

**Térmico (SUBTIPO=1)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ATERRADO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONECTADOBAJA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CONECTADOMEDIA` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POTENCIANOMINAL` |  | [Potencia Nominal Transformador Distribucion](01_Dominios.md#potencia-nominal-transformador-distribucion) |
| `PROPIEDAD` |  | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTERRANEO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `TIPO` |  | [TipoGeneradorDist](01_Dominios.md#tipogeneradordist) |
| `TIPOCONTRATO` |  | [TipoContratoGenerador](01_Dominios.md#tipocontratogenerador) |
| `TIPOREGULADOR` |  | [TipoReguladorGenerador](01_Dominios.md#tiporeguladorgenerador) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G252ESTRUCTURASO | ESTRUCTURASOPORTEGLOBALID | No | Yes |
| G252MIGUID | MIGUID | No | Yes |
| G252PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |
| G252PUNTOCARGAGL | PUNTOCARGAGLOBALID | No | Yes |

</details>

### Relaciones donde participa (1)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [PuntoCarga_GeneradorDist](02_Relaciones.md#puntocargageneradordist) | Destino | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | One To One |

---

## `MOTORINDUCCION` — Motor Sincrono
<a id="motorinduccion"></a>

> ⚠️ **Inconsistencia observada en el esquema fuente**: el alias registrado para `MOTORINDUCCION` en la geodatabase es literalmente *"Motor Sincrono"* (idéntico al alias de la clase `MOTORSINCRONO`). No es un error de esta documentación — así está definido en `Modelo_Datos.htm`. Al programar contra esta tabla, usar siempre el `field_name`/nombre técnico (`MOTORINDUCCION`) y no el alias para distinguir ambas clases.

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 47 total — ✅ 0 core · 🔌 0 conectividad · 🔧 19 sistema · ▫️ 28 otros |

> ℹ️ Esta clase no tiene una tabla de "Campos obligatorios" dedicada en el manual `MN-TEC-OPE-100`. La columna **Categoría** solo distingue campos de 🔌 *conectividad* / 🔧 *sistema* (comunes a casi todas las clases) de ▫️ *otros* (atributos propios de la clase, no confirmados como obligatorios por el manual pero potencialmente relevantes según el contexto de uso).

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | 🔧 Sistema |  |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | 🔧 Sistema |  |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | F Activacion | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | Proyecto Mod | String | 32 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACION` | F Modificacion | Date | 8 | Yes | ▫️ Otro |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | 🔧 Sistema |  |
| `PROVINCIA` | Provincia | String | 2 | Yes | 🔧 Sistema |  |
| `CANTON` | Canton | String | 4 | Yes | 🔧 Sistema |  |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ▫️ Otro |  |
| `POTENCIANOMINAL` | Potencia (kva) | String | 255 | Yes | ▫️ Otro |  |
| `PUESTOTRANSFDISTOBJECTID` | Puesto Transformador Distribucion OID | Integer | 4 | Yes | ▫️ Otro |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ▫️ Otro |  |
| `ESTADO` | Estado | Small Integer | 2 | Yes | ▫️ Otro |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PUESTOTRANSFDISTGLOBALID` | PUESTOTRANSFDISTGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | 🔧 Sistema |  |
| `MIESTADO` | MIESTADO | String | 20 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `EXISTENOVEDAD` | Existe Novedad | Small Integer | 2 | Yes | ▫️ Otro |  |
| `REACTANCIATIERRA` | React.Tierra | Double | 8 | Yes | ▫️ Otro |  |
| `RESISTENCIATIERRA` | Resist.Tierra | Double | 8 | Yes | ▫️ Otro |  |
| `EFICIENCIA` | Eficiencia | Double | 8 | Yes | ▫️ Otro |  |
| `MULTIPLICADORROTORBLOQUEADO` | Mult.Rotor Bloq. | Double | 8 | Yes | ▫️ Otro |  |
| `FACTORPOTENCIAROTORBLOQUEADO` | Factor Pot.Rotor Bloq. | Double | 8 | Yes | ▫️ Otro |  |
| `LIMITEARRANQUEMOTOR` | Limite arranq. Motor | Double | 8 | Yes | ▫️ Otro |  |
| `CANTIDADLIMITEARRANQUEMOTOR` | Cant.Limite arranq. Motor | Double | 8 | Yes | ▫️ Otro |  |
| `RANGOROTORNEMABLOQUEADO` | Rango Rotor NEMA Bloq. | Double | 8 | Yes | ▫️ Otro |  |
| `VOLTAJENOMINAL` | Voltaje Nominal | Small Integer | 2 | Yes | ▫️ Otro |  |
| `FASEDESIGNACION` | Fase Designación | Small Integer | 2 | Yes | ▫️ Otro |  |
| `HPNOMINAL` | HP Nominal | Double | 8 | Yes | ▫️ Otro |  |
| `PUNTOCARGAGLOBALID` | PuntoCargaGlobalID | GUID | 38 | Yes | ▫️ Otro |  |
| `RECATANCIARRANQUESUAVE` | React.Arranq.Suave | Double | 8 | Yes | ▫️ Otro |  |
| `RESISTENCIAARRANQUESUAVE` | React.Arranq.Suave | Double | 8 | Yes | ▫️ Otro |  |
| `TAPARRANQUESUAVE` | Tap Arranq. Suave | Double | 8 | Yes | ▫️ Otro |  |
| `DEVANADOARRANQUESUAVE` | Devan. Arranq. Suave | Double | 8 | Yes | ▫️ Otro |  |
| `RESISTENCIAARMAZON` | Resist. Armazon | Double | 8 | Yes | ▫️ Otro |  |
| `CONFIGURACIONCONEXION` | Configuración Conexión | String | 50 | Yes | ▫️ Otro |  |
| `FACTORPOTENCIA` | Factor Potencia | Double | 8 | Yes | ▫️ Otro |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `FASECONEXION` |  | [Fase Conexion](01_Dominios.md#fase-conexion) |
| `POTENCIANOMINAL` |  | [Potencia Nominal Transformador Distribucion](01_Dominios.md#potencia-nominal-transformador-distribucion) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_TODOS](01_Dominios.md#uptrftodos) |
| `ESTADO` |  | [Estado](01_Dominios.md#estado) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `EXISTENOVEDAD` |  | [ExisteNovedad](01_Dominios.md#existenovedad) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G218MIGUID | MIGUID | No | Yes |
| G218PUESTOTRANSF | PUESTOTRANSFDISTGLOBALID | No | Yes |
| G218PUNTOCARGAGL | PUNTOCARGAGLOBALID | No | Yes |

</details>

### Relaciones donde participa (1)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [PuntoCarga_MotorInduccion](02_Relaciones.md#puntocargamotorinduccion) | Destino | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | One To Many |

---

## `MOTORSINCRONO` — Motor Sincrono
<a id="motorsincrono"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 43 total — ✅ 0 core · 🔌 0 conectividad · 🔧 19 sistema · ▫️ 24 otros |

> ℹ️ Esta clase no tiene una tabla de "Campos obligatorios" dedicada en el manual `MN-TEC-OPE-100`. La columna **Categoría** solo distingue campos de 🔌 *conectividad* / 🔧 *sistema* (comunes a casi todas las clases) de ▫️ *otros* (atributos propios de la clase, no confirmados como obligatorios por el manual pero potencialmente relevantes según el contexto de uso).

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | 🔧 Sistema |  |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | 🔧 Sistema |  |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | F Activacion | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | Proyecto Mod | String | 32 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACION` | F Modificacion | Date | 8 | Yes | ▫️ Otro |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | 🔧 Sistema |  |
| `PROVINCIA` | Provincia | String | 2 | Yes | 🔧 Sistema |  |
| `CANTON` | Canton | String | 4 | Yes | 🔧 Sistema |  |
| `MODELO` | Modelo | String | 20 | Yes | ▫️ Otro |  |
| `NUMEROSERIE` | No Serie | String | 20 | Yes | ▫️ Otro |  |
| `MARCA` | Marca | String | 5 | Yes | ▫️ Otro |  |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ▫️ Otro |  |
| `CODIGOUNIDAD` | Codigo Unidad | String | 20 | Yes | ▫️ Otro |  |
| `POTENCIANOMINAL` | Potencia (kva) | String | 255 | Yes | ▫️ Otro |  |
| `TENSIONLADOALTA` | Tension AT | Integer | 4 | Yes | ▫️ Otro |  |
| `PUESTOTRANSFDISTOBJECTID` | Puesto Transformador Distribucion OID | Integer | 4 | Yes | ▫️ Otro |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ▫️ Otro |  |
| `ESTADO` | Estado | Small Integer | 2 | Yes | ▫️ Otro |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PUESTOTRANSFDISTGLOBALID` | PUESTOTRANSFDISTGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | 🔧 Sistema |  |
| `MIESTADO` | MIESTADO | String | 20 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `EXISTENOVEDAD` | Existe Novedad | Small Integer | 2 | Yes | ▫️ Otro |  |
| `RESISTENCIAARMAZON` | Resist. Armazon | Double | 8 | Yes | ▫️ Otro |  |
| `CONFIGURACIONCONEXION` | Configuración Conexión | String | 50 | Yes | ▫️ Otro |  |
| `EJERECTSINCRONADIRECTA` | Eje React. Sinc.Directa | Double | 8 | Yes | ▫️ Otro |  |
| `EJERECTSINCRONACUADRATURA` | Eje React. Sinc.Cuadratura | Double | 8 | Yes | ▫️ Otro |  |
| `COEF10SATURACION` | Coef.10 Saturación | Double | 8 | Yes | ▫️ Otro |  |
| `COEF12SATURACION` | Coef.12 Saturación | Double | 8 | Yes | ▫️ Otro |  |
| `PUNTOCARGAGLOBALID` | PuntoCargaGlobalId | GUID | 38 | Yes | ▫️ Otro |  |
| `REACTANCIASUBTRANSITORIA` | React.Subtransitoria | Double | 8 | Yes | ▫️ Otro |  |
| `REACTANCIATRANSITORIA` | React.Transitoria | Double | 8 | Yes | ▫️ Otro |  |
| `REACTANCIASEQCERO` | React.Seq.Cero | Double | 8 | Yes | ▫️ Otro |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `MARCA` |  | [Marcas](01_Dominios.md#marcas) |
| `FASECONEXION` |  | [Fase Conexion](01_Dominios.md#fase-conexion) |
| `POTENCIANOMINAL` |  | [Potencia Nominal Transformador Distribucion](01_Dominios.md#potencia-nominal-transformador-distribucion) |
| `TENSIONLADOALTA` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_TODOS](01_Dominios.md#uptrftodos) |
| `ESTADO` |  | [Estado](01_Dominios.md#estado) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `EXISTENOVEDAD` |  | [ExisteNovedad](01_Dominios.md#existenovedad) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G217MIGUID | MIGUID | No | Yes |
| G217PUESTOTRANSF | PUESTOTRANSFDISTGLOBALID | No | Yes |
| G217PUNTOCARGAGL | PUNTOCARGAGLOBALID | No | Yes |

</details>

### Relaciones donde participa (1)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [PuntoCarga_MotorSincrono](02_Relaciones.md#puntocargamotorsincrono) | Destino | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | One To Many |

---

## `Subestacion`
<a id="subestacion"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple) |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 34 total — ✅ 0 core · 🔌 0 conectividad · 🔧 25 sistema · ▫️ 9 otros |

> ℹ️ Esta clase no tiene una tabla de "Campos obligatorios" dedicada en el manual `MN-TEC-OPE-100`. La columna **Categoría** solo distingue campos de 🔌 *conectividad* / 🔧 *sistema* (comunes a casi todas las clases) de ▫️ *otros* (atributos propios de la clase, no confirmados como obligatorios por el manual pero potencialmente relevantes según el contexto de uso).

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object Id | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | 🔧 Sistema |  |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | 🔧 Sistema |  |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | 🔧 Sistema |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | 🔧 Sistema |  |
| `PROVINCIA` | Provincia | String | 2 | Yes | 🔧 Sistema |  |
| `CANTON` | Canton | String | 4 | Yes | 🔧 Sistema |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | 🔧 Sistema |  |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `DIRECCION` | DIRECCION | String | 50 | Yes | ▫️ Otro |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `ALTURA` | ALTURA | Integer | 4 | Yes | ▫️ Otro |  |
| `VPRIMARIO` | VPRIMARIO | Integer | 4 | Yes | ▫️ Otro |  |
| `VSECUNDARIO` | VSECUNDARIO | Integer | 4 | Yes | ▫️ Otro |  |
| `TELEFONO` | TELEFONO | String | 15 | Yes | ▫️ Otro |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `COMENTARIOS` | Comentarios | String | 255 | Yes | 🔧 Sistema |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `NUMEROSUBESTACION` | Numero Subestacion | String | 6 | Yes | ▫️ Otro |  |
| `NOMBRE` | Nombre Subestacion | String | 30 | Yes | ▫️ Otro |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `SUBTIPO` | 2 | — |
| `CODIGOESTRUCTURA` |  | [Tipo Subestacion](01_Dominios.md#tipo-subestacion) |
| `VPRIMARIO` |  | [Voltaje AT](01_Dominios.md#voltaje-at) |
| `VSECUNDARIO` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `NUMEROSUBESTACION` |  | [Numero Estacion](01_Dominios.md#numero-estacion) ⚠️ |
| `NOMBRE` |  | [Subestacion](01_Dominios.md#subestacion) ⚠️ |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Subestacion Exterior (Subtipo=2) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [Tipo Subestacion](01_Dominios.md#tipo-subestacion) |
| `NOMBRE` |  | [Subestacion](01_Dominios.md#subestacion) ⚠️ |
| `NUMEROSUBESTACION` |  | [Numero Estacion](01_Dominios.md#numero-estacion) ⚠️ |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 2 | — |
| `VPRIMARIO` |  | [Voltaje AT](01_Dominios.md#voltaje-at) |
| `VSECUNDARIO` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Subestacion Interior (Subtipo=1)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [Tipo Subestacion](01_Dominios.md#tipo-subestacion) |
| `NOMBRE` |  | [Subestacion](01_Dominios.md#subestacion) ⚠️ |
| `NUMEROSUBESTACION` |  | [Numero Estacion](01_Dominios.md#numero-estacion) ⚠️ |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `VPRIMARIO` |  | [Voltaje AT](01_Dominios.md#voltaje-at) |
| `VSECUNDARIO` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Subestacion Otros (Subtipo=3)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [Tipo Subestacion](01_Dominios.md#tipo-subestacion) |
| `NOMBRE` |  | [Subestacion](01_Dominios.md#subestacion) ⚠️ |
| `NUMEROSUBESTACION` |  | [Numero Estacion](01_Dominios.md#numero-estacion) ⚠️ |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 2 | — |
| `VPRIMARIO` |  | [Voltaje AT](01_Dominios.md#voltaje-at) |
| `VSECUNDARIO` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G250MIGUID | MIGUID | No | Yes |

</details>

### Relaciones donde participa (1)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [Subestacion_PuestoTransfPot](02_Relaciones.md#subestacionpuestotransfpot) | Origen | [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) | One To Many |

---

## `CIRCUITOFUENTE` — Alimentador Cabecera
<a id="circuitofuente"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 40 total — ✅ 11 core · 🔌 0 conectividad · 🔧 7 sistema · ▫️ 22 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object ID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S. A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 20/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `SUBTIPO` | Subtipo | Integer | 4 | Yes | ✅ CORE | Voltaje |
| `CODIGOALIMENTADOR` | Codigo Alimentador | String | 10 | Yes | ✅ CORE | S/E Milagro Norte - Simón Bolívar |
| `FUENTEALIMENTADORAINFO` | Fuente Alim Info | Integer | 4 | Yes | ▫️ Otro |  |
| `PUESTOPROTDINAMOBJECTID` | Puesto Protec Dina OID | Integer | 4 | Yes | ▫️ Otro |  |
| `CONFIGURACIONCONEXION` | Configuracion Conexion | String | 5 | Yes | ✅ CORE | Radial |
| `CAPACIDADEMERGENCIAKW` | Capacidad Emergencia KW | Integer | 4 | Yes | ▫️ Otro |  |
| `REACTANCIATIERRA` | X Tierra | Double | 8 | Yes | ▫️ Otro |  |
| `RESISTENCIATIERRA` | R Tierra | Double | 8 | Yes | ▫️ Otro |  |
| `CAPACIDADMAXIMAKW` | Capacidad Max | Integer | 4 | Yes | ▫️ Otro |  |
| `MAXKVAR` | KVAR Maxima | Integer | 4 | Yes | ▫️ Otro |  |
| `MINKVAR` | KVAR Minima | Integer | 4 | Yes | ▫️ Otro |  |
| `MAXREACTANCIASEQUENCIAPOSITIVA` | MAX REACTANCIA SEQUENCIAPOSITIVA | Double | 8 | Yes | ▫️ Otro |  |
| `MINREACTANCIASEQUENCIAPOSITIVA` | MIN REACTANCIA SEQUENCIAPOSITIVA | Double | 8 | Yes | ▫️ Otro |  |
| `MAXRESISTENCIASEQUENCIAPOSITIV` | Rsec+max | Double | 8 | Yes | ▫️ Otro |  |
| `MINRESISTENCIASEQUENCIAPOSITIV` | Rsec+min | Double | 8 | Yes | ▫️ Otro |  |
| `MAXREACTANCIASEQUENCIACERO` | MAX REACTANCIA SEQUENCIA CERO | Double | 8 | Yes | ▫️ Otro |  |
| `MINREACTANCIASEQUENCIACERO` | MIN REACTANCIA SEQUENCIA CERO | Double | 8 | Yes | ▫️ Otro |  |
| `MAXRESISTENCIASEQUENCIACERO` | MAX RESISTENCIA SEQUENCIA CERO | Double | 8 | Yes | ▫️ Otro |  |
| `MINRESISTENCIASEQUENCIACERO` | MIN RESISTENCIA SEQUENCIA CERO | Double | 8 | Yes | ▫️ Otro |  |
| `TENSIONNOMINAL` | Tension Nom | Integer | 4 | Yes | ✅ CORE | 13.8KV |
| `TENSIONOPERACION` | Tension Oper | Integer | 4 | Yes | ✅ CORE | 13.8KV |
| `ANGULOVOLTAJE` | Angulo Voltaje | Double | 8 | Yes | ▫️ Otro |  |
| `FACTORPOTENCIADEMMAX` | Factor Pot Dmax | Double | 8 | Yes | ▫️ Otro |  |
| `FACTORDECARGA` | Factor Carga | Double | 8 | Yes | ▫️ Otro |  |
| `FACTORDEPERDIDA` | Factor Perdida | Double | 8 | Yes | ▫️ Otro |  |
| `DEMANDAMAXIMA` | Dem Max | Integer | 4 | Yes | ▫️ Otro |  |
| `TIPOALIMENTADOR` | Tipo Alimentador | String | 2 | Yes | ✅ CORE | Rural |
| `ZONAINFLUENCIA` | Zona de Influencia | String | 100 | Yes | ✅ CORE | Simón Bolívar, Lorenzo de Garaicoa |
| `NOMBREALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ✅ CORE | S/E Milagro Norte - Simón Bolívar |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PUESTOPROTDINAMGLOBALID` | PUESTOPROTDINAMGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `IDSUBESTACION` | Nombre Subestacion | String | 6 | Yes | ✅ CORE | S/E Milagro Norte |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `SUBTIPO` | 3 | — |
| `CODIGOALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CONFIGURACIONCONEXION` |  | [Configuracion de Alimentador](01_Dominios.md#configuracion-de-alimentador) |
| `TENSIONNOMINAL` |  | [Tension de Circuito Fuente](01_Dominios.md#tension-de-circuito-fuente) |
| `TENSIONOPERACION` |  | [Tension de Circuito Fuente](01_Dominios.md#tension-de-circuito-fuente) |
| `TIPOALIMENTADOR` |  | [Tipo Alimentador](01_Dominios.md#tipo-alimentador) |
| `NOMBREALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `IDSUBESTACION` |  | [Subestacion](01_Dominios.md#subestacion) ⚠️ |
| `CODIGOEMPRESA` |  | [Empresas](01_Dominios.md#empresas) |

**kW (Subtipo=1)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CONFIGURACIONCONEXION` |  | [Configuracion de Alimentador](01_Dominios.md#configuracion-de-alimentador) |
| `IDSUBESTACION` |  | [Subestacion](01_Dominios.md#subestacion) ⚠️ |
| `NOMBREALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `SUBTIPO` | 1 | — |
| `TENSIONNOMINAL` |  | [Tension de Circuito Fuente](01_Dominios.md#tension-de-circuito-fuente) |
| `TENSIONOPERACION` |  | [Tension de Circuito Fuente](01_Dominios.md#tension-de-circuito-fuente) |
| `TIPOALIMENTADOR` |  | [Tipo Alimentador](01_Dominios.md#tipo-alimentador) |

**Swing (Subtipo=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CONFIGURACIONCONEXION` |  | [Configuracion de Alimentador](01_Dominios.md#configuracion-de-alimentador) |
| `IDSUBESTACION` |  | [Subestacion](01_Dominios.md#subestacion) ⚠️ |
| `NOMBREALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `SUBTIPO` | 2 | — |
| `TENSIONNOMINAL` |  | [Tension de Circuito Fuente](01_Dominios.md#tension-de-circuito-fuente) |
| `TENSIONOPERACION` |  | [Tension de Circuito Fuente](01_Dominios.md#tension-de-circuito-fuente) |
| `TIPOALIMENTADOR` |  | [Tipo Alimentador](01_Dominios.md#tipo-alimentador) |

**Voltaje (Subtipo=3) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CONFIGURACIONCONEXION` |  | [Configuracion de Alimentador](01_Dominios.md#configuracion-de-alimentador) |
| `IDSUBESTACION` |  | [Subestacion](01_Dominios.md#subestacion) ⚠️ |
| `NOMBREALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `SUBTIPO` | 3 | — |
| `TENSIONNOMINAL` |  | [Tension de Circuito Fuente](01_Dominios.md#tension-de-circuito-fuente) |
| `TENSIONOPERACION` |  | [Tension de Circuito Fuente](01_Dominios.md#tension-de-circuito-fuente) |
| `TIPOALIMENTADOR` |  | [Tipo Alimentador](01_Dominios.md#tipo-alimentador) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G216PUESTOPROTDI | PUESTOPROTDINAMOBJECTID | No | Yes |
| G216PUESTOPROTDI_1 | PUESTOPROTDINAMGLOBALID | No | Yes |

</details>

### Relaciones donde participa (1)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [PuestoProtDinam_CircuitoFuente](02_Relaciones.md#puestoprotdinamcircuitofuente) | Destino | [`PuestoProteccionDinamico`](04_Clases_Proteccion_y_Potencia.md#puestoprotecciondinamico) | One To One |

---

## `DATOSOPERADORA`
<a id="datosoperadora"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 13 total — ✅ 0 core · 🔌 0 conectividad · 🔧 3 sistema · ▫️ 10 otros |

> ℹ️ Esta clase no tiene una tabla de "Campos obligatorios" dedicada en el manual `MN-TEC-OPE-100`. La columna **Categoría** solo distingue campos de 🔌 *conectividad* / 🔧 *sistema* (comunes a casi todas las clases) de ▫️ *otros* (atributos propios de la clase, no confirmados como obligatorios por el manual pero potencialmente relevantes según el contexto de uso).

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `CODIGOOPERADORA` | OPERADORA | String | 50 | Yes | ▫️ Otro |  |
| `NOMBRE` | NOMBRE | String | 50 | Yes | ▫️ Otro |  |
| `RUC` | RUC | String | 50 | Yes | ▫️ Otro |  |
| `DIRECCION1` | DIRECCION | String | 50 | Yes | ▫️ Otro |  |
| `TELEFONO1` | TELEFONO | String | 50 | Yes | ▫️ Otro |  |
| `TELEFONO2` | TELEFONO2 | String | 50 | Yes | ▫️ Otro |  |
| `CORREO1` | CORREO1 | String | 50 | Yes | ▫️ Otro |  |
| `CORREO2` | CORREO2 | String | 50 | Yes | ▫️ Otro |  |
| `PERSONACONTACTO` | PERSONACONTACTO | String | 50 | Yes | ▫️ Otro |  |
| `CODIGOEMPRESA` | EMPRESA | String | 50 | Yes | 🔧 Sistema |  |
| `OBSERVACION` | OBSERVACION | String | 100 | Yes | ▫️ Otro |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOEMPRESA` |  | [Empresas](01_Dominios.md#empresas) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G221CODIGOOPERAD | CODIGOOPERADORA | No | Yes |

</details>

### Relaciones donde participa (1)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [DATOSOPERADOR_OPERADORA](02_Relaciones.md#datosoperadoroperadora) | Origen | [`OPERADORAENPOSTE`](03_Clases_Redes_y_Soporte.md#operadoraenposte) | One To Many |

---
