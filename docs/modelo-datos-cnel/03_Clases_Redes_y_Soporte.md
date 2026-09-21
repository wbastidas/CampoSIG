# 03 · Clases: Redes Eléctricas y Estructuras de Soporte

[⬅ Volver al índice](00_Indice_y_Conceptos.md) · [Dominios](01_Dominios.md) · [Relaciones](02_Relaciones.md) · [04](04_Clases_Proteccion_y_Potencia.md) · [05](05_Clases_Generacion_Subestaciones_Fuentes.md) · [06](06_Clases_Consumidores_y_Alumbrado.md)

Tramos de línea (MT/BT/Subtransmisión, aéreo/subterráneo), la clase `Barra`, y toda la infraestructura física de soporte: postes, estructuras, tensores, catálogo homologado de estructuras y puntos misceláneos/de apertura de la red.

**Clases en este archivo:** [`Barra`](#barra) · [`TramoDistribucionAereo`](#tramodistribucionaereo) · [`TramoDistribucionSubterraneo`](#tramodistribucionsubterraneo) · [`TramoBajaTensionAereo`](#tramobajatensionaereo) · [`TramoBajaTensionSubterraneo`](#tramobajatensionsubterraneo) · [`TramoSubtransmisionAereo`](#tramosubtransmisionaereo) · [`TramoSubtransmisionSubterraneo`](#tramosubtransmisionsubterraneo) · [`EstructuraSoporte`](#estructurasoporte) · [`ESTRUCTURAENPOSTE`](#estructuraenposte) · [`INSTITUCIONENPOSTE`](#institucionenposte) · [`OPERADORAENPOSTE`](#operadoraenposte) · [`Tensor`](#tensor) · [`CATALOGOESTRUCTURA`](#catalogoestructura) · [`EstructuraANivel`](#estructuraanivel) · [`SERVICIOCALLES`](#serviciocalles) · [`PuntoMiscelaneo`](#puntomiscelaneo) · [`PuntoApertura`](#puntoapertura) · [`Electrico_RedGeom_Junctions`](#electricoredgeomjunctions)

**Leyenda de categoría de campo:** ✅ **CORE** = obligatorio según el manual `MN-TEC-OPE-100` · 🔌 **Conectividad** = usado por el motor de red geométrica / trazado eléctrico (ver [00 · Conceptos](00_Indice_y_Conceptos.md#conectividad-eléctrica-y-trazado-source--sink)) · 🔧 **Sistema** = auditoría/metadatos técnicos común a casi todas las clases (usuario y fecha de registro, IDs internos, geometría, ubicación administrativa) · ▫️ **Otro** = resto de atributos propios de la clase — **no es "innecesario", solo no está confirmado como obligatorio por el manual**; revisar según el caso de uso.

---

## `Barra`
<a id="barra"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Polyline (Complex Edge) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Edge** (línea/tramo) |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 41 total — ✅ 0 core · 🔌 3 conectividad · 🔧 25 sistema · ▫️ 13 otros |

> ℹ️ Esta clase no tiene una tabla de "Campos obligatorios" dedicada en el manual `MN-TEC-OPE-100`. La columna **Categoría** solo distingue campos de 🔌 *conectividad* / 🔧 *sistema* (comunes a casi todas las clases) de ▫️ *otros* (atributos propios de la clase, no confirmados como obligatorios por el manual pero potencialmente relevantes según el contexto de uso).

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object ID | OID | 4 | No | 🔧 Sistema |  |
| `ENABLED` | Enabled | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | 🔧 Sistema |  |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | Alim1 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Inform Alim | Integer | 4 | Yes | ▫️ Otro |  |
| `FDRMGRNONTRACEABLE` | FdrMgrNonTraceable | Integer | 4 | Yes | ▫️ Otro |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | 🔧 Sistema |  |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | 🔧 Sistema |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | 🔧 Sistema |  |
| `SUBTIPO` | Subtipo | Integer | 4 | Yes | 🔧 Sistema |  |
| `FASECONEXION` | Fase | Integer | 4 | Yes | ▫️ Otro |  |
| `VOLTAJE` | VOLTAJE | Integer | 4 | Yes | ▫️ Otro |  |
| `CODIGOBARRA` | Codigo Barra | Integer | 4 | Yes | ▫️ Otro |  |
| `FORMABARRA` | Forma Barra | String | 10 | Yes | ▫️ Otro |  |
| `ESQUEMABARRA` | Esquema Barra | String | 10 | Yes | ▫️ Otro |  |
| `CAPACIDADTERMICA` | Capacidad Termica | Integer | 4 | Yes | ▫️ Otro |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `ENERGIZADO` | ENERGIZADO | Small Integer | 2 | Yes | ▫️ Otro |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador2 | String | 10 | Yes | ▫️ Otro |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `PROVINCIA` | Provincia | String | 2 | Yes | 🔧 Sistema |  |
| `CANTON` | Canton | String | 4 | Yes | 🔧 Sistema |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `COMENTARIOS` | Comentarios | String | 255 | Yes | 🔧 Sistema |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | 🔧 Sistema |  |
| `SHAPE_Length` | SHAPE_Length | Double | 8 | Yes | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `SUBTIPO` | 2 | — |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Barra Baja Tension (Subtipo=1)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` | 7 | [Fase Conexion Trifasica](01_Dominios.md#fase-conexion-trifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Barra Media Tension (Subtipo=2) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` | 7 | [Fase Conexion Trifasica](01_Dominios.md#fase-conexion-trifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 2 | — |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Barra Subtransmision (Subtipo=3)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` | 7 | [Fase Conexion Trifasica](01_Dominios.md#fase-conexion-trifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 3 | — |
| `VOLTAJE` |  | [Voltaje AT](01_Dominios.md#voltaje-at) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G230MIGUID | MIGUID | No | Yes |
| G230PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |

</details>

---

## `TramoDistribucionAereo` — Tramo MT Aereo
<a id="tramodistribucionaereo"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Polyline (Complex Edge) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Edge** (línea/tramo) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 45 total — ✅ 20 core · 🔌 2 conectividad · 🔧 15 sistema · ▫️ 8 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object ID | OID | 4 | No | 🔧 Sistema |  |
| `ENABLED` | Enabled | Small Integer | 2 | Yes | ✅ CORE | True |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 24/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | Alim1 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Inform Alim | Integer | 4 | Yes | ▫️ Otro |  |
| `FDRMGRNONTRACEABLE` | FdrMgrNonTraceable | Integer | 4 | Yes | ✅ CORE | Yes |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | PMD |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | Propio |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | ✅ CORE | Tramo MTA Monofásico |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ✅ CORE | C |
| `VOLTAJE` | VOLTAJE | Integer | 4 | Yes | ✅ CORE | 7,96KV |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `CODIGOCONDUCTORFASE` | Codigo Conductor Fase | String | 10 | Yes | ✅ CORE | ACSR#1/0 |
| `CODIGOCONDUCTORNEUTRO` | Codigo Conductor Neutro | String | 10 | Yes | ✅ CORE | Null |
| `CONFIGURACIONCONDUCTORES` | Configuracion Conductores | String | 5 | Yes | ✅ CORE | 1F1C |
| `SECUENCIAFASE` | SECUENCIAFASE | String | 3 | Yes | ✅ CORE | C |
| `LONGITUDSISTEMA` | Longitud del Sistema | Double | 8 | Yes | ▫️ Otro |  |
| `ENERGIZADO` | ENERGIZADO | Small Integer | 2 | Yes | ▫️ Otro |  |
| `RAMAL` | Ramal | String | 10 | Yes | ✅ CORE | Ramal Primario |
| `LONGITUDCAMPO` | Longitud en Campo | Double | 8 | Yes | ▫️ Otro |  |
| `PROVINCIA` | PROVINCIA | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | CANTON | String | 4 | Yes | ✅ CORE | Milagro |
| `PARROQUIA` | PARROQUIA | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 01/04/2019 |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `HIPERVINCULO` | Hipervinculo | String | 255 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador 2 | String | 10 | Yes | ▫️ Otro |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | O/T 3471 |
| `SHAPE_Length` | SHAPE_Length | Double | 8 | Yes | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `SUBTIPO` | 3 | — |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Bajante MTA Bifasica (Subtipo=5)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOCONDUCTORFASE` |  | [UP_TMA_BAJANTE](01_Dominios.md#uptmabajante) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TMA_BAJANTE](01_Dominios.md#uptmabajante) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Bifasica](01_Dominios.md#fase-conexion-bifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `SECUENCIAFASE` |  | [Secuencia Fase](01_Dominios.md#secuencia-fase) |
| `SUBTIPO` | 5 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Bajante MTA Monofasica (Subtipo=4)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOCONDUCTORFASE` |  | [UP_TMA_BAJANTE](01_Dominios.md#uptmabajante) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TMA_BAJANTE](01_Dominios.md#uptmabajante) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Monofasica](01_Dominios.md#fase-conexion-monofasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `SECUENCIAFASE` |  | [Secuencia Fase](01_Dominios.md#secuencia-fase) |
| `SUBTIPO` | 4 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Bajante MTA Trifasica (Subtipo=6)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOCONDUCTORFASE` |  | [UP_TMA_BAJANTE](01_Dominios.md#uptmabajante) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TMA_BAJANTE](01_Dominios.md#uptmabajante) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` | 7 | [Fase Conexion Trifasica](01_Dominios.md#fase-conexion-trifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `SECUENCIAFASE` |  | [Secuencia Fase](01_Dominios.md#secuencia-fase) |
| `SUBTIPO` | 6 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Tramo MTA Bifasico (Subtipo=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOCONDUCTORFASE` |  | [UP_TMA_TRAMO](01_Dominios.md#uptmatramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TMA_TRAMO](01_Dominios.md#uptmatramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Bifasica](01_Dominios.md#fase-conexion-bifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `SECUENCIAFASE` |  | [Secuencia Fase](01_Dominios.md#secuencia-fase) |
| `SUBTIPO` | 2 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Tramo MTA Monofasico (Subtipo=1)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOCONDUCTORFASE` |  | [UP_TMA_TRAMO](01_Dominios.md#uptmatramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TMA_TRAMO](01_Dominios.md#uptmatramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Monofasica](01_Dominios.md#fase-conexion-monofasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `SECUENCIAFASE` |  | [Secuencia Fase](01_Dominios.md#secuencia-fase) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Tramo MTA Trifasico (Subtipo=3) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOCONDUCTORFASE` |  | [UP_TMA_TRAMO](01_Dominios.md#uptmatramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TMA_TRAMO](01_Dominios.md#uptmatramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` | 7 | [Fase Conexion Trifasica](01_Dominios.md#fase-conexion-trifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `SECUENCIAFASE` |  | [Secuencia Fase](01_Dominios.md#secuencia-fase) |
| `SUBTIPO` | 3 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G229CODIGOCONDUC | CODIGOCONDUCTORFASE | No | Yes |
| G229CODIGOCONDUC_1 | CODIGOCONDUCTORNEUTRO | No | Yes |
| G229MIGUID | MIGUID | No | Yes |
| G229PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |
| I229ALIMENTADOR | ALIMENTADOR | No | Yes |
| I229ALIMENTADORI | ALIMENTADORID | No | Yes |
| I229HIPERVINCULO | HIPERVINCULO | No | Yes |

</details>

### Relaciones donde participa (2)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_TramoDistAereoFase](02_Relaciones.md#catestructramodistaereofase) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |
| [CatEstruc_TramoDistAereoNeutro](02_Relaciones.md#catestructramodistaereoneutro) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |

---

## `TramoDistribucionSubterraneo` — Tramo MT Subterraneo
<a id="tramodistribucionsubterraneo"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Polyline (Complex Edge) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Edge** (línea/tramo) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 46 total — ✅ 20 core · 🔌 2 conectividad · 🔧 15 sistema · ▫️ 9 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object ID | OID | 4 | No | 🔧 Sistema |  |
| `ENABLED` | Enabled | Small Integer | 2 | Yes | ✅ CORE | True |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 24/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | Alim1 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Inform Alim | Integer | 4 | Yes | ▫️ Otro |  |
| `FDRMGRNONTRACEABLE` | FdrMgrNonTraceable | Integer | 4 | Yes | ✅ CORE | Yes |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | PMD |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | CAF |
| `CODIGOEMPRESA` | CodigoEmpresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | ✅ CORE | Tramo MTS Monofásico |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ✅ CORE | B |
| `VOLTAJE` | VOLTAJE | Integer | 4 | Yes | ✅ CORE | 7,96KV |
| `LONGITUDSISTEMA` | Longitud del Sistema | Double | 8 | Yes | ▫️ Otro |  |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `CODIGOCONDUCTORFASE` | Codigo Conductor Fase | String | 10 | Yes | ✅ CORE | 15kV.Cu.1/0 |
| `CODIGOCONDUCTORNEUTRO` | Codigo Conductor Neutro | String | 10 | Yes | ✅ CORE | Null |
| `CONFIGURACIONCONDUCTORES` | Configuracion Conductores | String | 5 | Yes | ✅ CORE | 1F1C |
| `CANTIDADCONDUCTORES` | Cantidad Conductores | Integer | 4 | Yes | ▫️ Otro |  |
| `SECUENCIAFASE` | SECUENCIAFASE | String | 3 | Yes | ✅ CORE | B |
| `INDICADORDOBLETERNA` | Doble Terna | String | 1 | Yes | ▫️ Otro |  |
| `RAMAL` | Ramal | String | 10 | Yes | ✅ CORE | Ramal Primario |
| `LONGITUDCAMPO` | Longitud en Campo | Double | 8 | Yes | ▫️ Otro |  |
| `PROVINCIA` | PROVINCIA | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | CANTON | String | 4 | Yes | ✅ CORE | Milagro |
| `PARROQUIA` | PARROQUIA | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 01/04/2019 |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `HIPERVINCULO` | Hipervinculo | String | 255 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador 2 | String | 10 | Yes | ▫️ Otro |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | O/T 3474 |
| `SHAPE_Length` | SHAPE_Length | Double | 8 | Yes | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `SUBTIPO` | 3 | — |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `CODIGOCONDUCTORFASE` |  | [Catalogo Conductores](01_Dominios.md#catalogo-conductores) |
| `CODIGOCONDUCTORNEUTRO` |  | [Catalogo Conductores](01_Dominios.md#catalogo-conductores) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `INDICADORDOBLETERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Bajante MTS Bifasica (Subtipo=5)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOCONDUCTORFASE` |  | [UP_TMS_TRAMO](01_Dominios.md#uptmstramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TMS_TRAMO](01_Dominios.md#uptmstramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Bifasica](01_Dominios.md#fase-conexion-bifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `INDICADORDOBLETERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `SECUENCIAFASE` |  | [Secuencia Fase](01_Dominios.md#secuencia-fase) |
| `SUBTIPO` | 5 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Bajante MTS Monofasica (Subtipo=4)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOCONDUCTORFASE` |  | [UP_TMS_TRAMO](01_Dominios.md#uptmstramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TMS_TRAMO](01_Dominios.md#uptmstramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Monofasica](01_Dominios.md#fase-conexion-monofasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `INDICADORDOBLETERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `SECUENCIAFASE` |  | [Secuencia Fase](01_Dominios.md#secuencia-fase) |
| `SUBTIPO` | 4 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Bajante MTS Trifasica (Subtipo=6)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOCONDUCTORFASE` |  | [UP_TMS_TRAMO](01_Dominios.md#uptmstramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TMS_TRAMO](01_Dominios.md#uptmstramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` | 7 | [Fase Conexion Trifasica](01_Dominios.md#fase-conexion-trifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `INDICADORDOBLETERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `SECUENCIAFASE` |  | [Secuencia Fase](01_Dominios.md#secuencia-fase) |
| `SUBTIPO` | 6 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Tramo MTS Bifasico (Subtipo=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOCONDUCTORFASE` |  | [UP_TMS_TRAMO](01_Dominios.md#uptmstramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TMS_TRAMO](01_Dominios.md#uptmstramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Bifasica](01_Dominios.md#fase-conexion-bifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `INDICADORDOBLETERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `SECUENCIAFASE` |  | [Secuencia Fase](01_Dominios.md#secuencia-fase) |
| `SUBTIPO` | 2 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Tramo MTS Monofasico (Subtipo=1)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOCONDUCTORFASE` |  | [UP_TMS_TRAMO](01_Dominios.md#uptmstramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TMS_TRAMO](01_Dominios.md#uptmstramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Monofasica](01_Dominios.md#fase-conexion-monofasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `INDICADORDOBLETERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `SECUENCIAFASE` |  | [Secuencia Fase](01_Dominios.md#secuencia-fase) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Tramo MTS Trifasico (Subtipo=3) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOCONDUCTORFASE` |  | [UP_TMS_TRAMO](01_Dominios.md#uptmstramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TMS_TRAMO](01_Dominios.md#uptmstramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` | 7 | [Fase Conexion Trifasica](01_Dominios.md#fase-conexion-trifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `INDICADORDOBLETERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `SECUENCIAFASE` |  | [Secuencia Fase](01_Dominios.md#secuencia-fase) |
| `SUBTIPO` | 3 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G235CODIGOCONDUC | CODIGOCONDUCTORFASE | No | Yes |
| G235CODIGOCONDUC_1 | CODIGOCONDUCTORNEUTRO | No | Yes |
| G235MIGUID | MIGUID | No | Yes |
| G235PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |
| I235ALIMENTADOR | ALIMENTADOR | No | Yes |
| I235ALIMENTADOR2 | ALIMENTADOR2ID | No | Yes |
| I235ALIMENTADORI | ALIMENTADORID | No | Yes |
| I235HIPERVINCULO | HIPERVINCULO | No | Yes |

</details>

### Relaciones donde participa (2)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_TramoDistSubterrFase](02_Relaciones.md#catestructramodistsubterrfase) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |
| [CatEstruc_TramoDistSubterrNeutro](02_Relaciones.md#catestructramodistsubterrneutro) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |

---

## `TramoBajaTensionAereo` — Tramo BT Aereo
<a id="tramobajatensionaereo"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Polyline (Complex Edge) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Edge** (línea/tramo) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 48 total — ✅ 21 core · 🔌 2 conectividad · 🔧 15 sistema · ▫️ 10 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object Id | OID | 4 | No | 🔧 Sistema |  |
| `ENABLED` | Enabled | Small Integer | 2 | Yes | ✅ CORE | True |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 01/03/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | Alim1 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Inform Alim | Integer | 4 | Yes | ▫️ Otro |  |
| `FDRMGRNONTRACEABLE` | FdrMgrNonTraceable | Integer | 4 | Yes | ✅ CORE | Yes |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | FERUM 2019 |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | Propio |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | ✅ CORE | Tramo BTA Monofásico |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ✅ CORE | B |
| `VOLTAJE` | VOLTAJE | Integer | 4 | Yes | ✅ CORE | 240V |
| `LONGITUDSISTEMA` | Longitud Sistema | Double | 8 | Yes | ▫️ Otro |  |
| `CODIGOCONDUCTORFASE` | Codigo Conductor Fase | String | 10 | Yes | ✅ CORE | PRE.Al.2x50(50) |
| `CODIGOCONDUCTORNEUTRO` | Codigo Conductor Neutro | String | 10 | Yes | ✅ CORE | Null |
| `CONFIGURACIONCONDUCTORES` | Configuracion Conductores | String | 5 | Yes | ✅ CORE | 1F3C |
| `SECUENCIAFASE` | Circuitos | String | 3 | Yes | ✅ CORE | F12 |
| `PUESTOTRANSFDISTOBJECTID` | Puesto Transformador Distribucion OID | Integer | 4 | Yes | ▫️ Otro |  |
| `LONGITUDCAMPO` | Longitud en Campo | Double | 8 | Yes | ▫️ Otro |  |
| `PROVINCIA` | PROVINCIA | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | CANTON | String | 4 | Yes | ✅ CORE | Milagro |
| `PARROQUIA` | PARROQUIA | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 01/04/2019 |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PUESTOTRANSFDISTGLOBALID` | PUESTOTRANSFDISTGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `HILOPILOTO` | Código Conductor Piloto | String | 10 | Yes | ✅ CORE | null |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `HIPERVINCULO` | Hipervinculo | String | 255 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre ALimentador 2 | String | 10 | Yes | ▫️ Otro |  |
| `TIPOUSOTRAMO` | Tipo Uso Tramo | Small Integer | 2 | Yes | ✅ CORE | Distribución |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `CIRCUITOS` | Circuitos | String | 3 | Yes | ▫️ Otro |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | O/T 3478 |
| `SHAPE_Length` | SHAPE_Length | Double | 8 | Yes | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `SUBTIPO` | 7 | — |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `CONFIGURACIONCONDUCTORES` | 23 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `HILOPILOTO` |  | [UP_TBA_TRAMO](01_Dominios.md#uptbatramo) |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |

**Acometida BTA Bifasica (Subtipo=8)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBA_ACOMETIDA](01_Dominios.md#uptbaacometida) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBA_ACOMETIDA](01_Dominios.md#uptbaacometida) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Bifasica](01_Dominios.md#fase-conexion-bifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBA_ACOMETIDA](01_Dominios.md#uptbaacometida) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 8 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Acometida BTA Monofasica (Subtipo=7) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBA_ACOMETIDA](01_Dominios.md#uptbaacometida) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBA_ACOMETIDA](01_Dominios.md#uptbaacometida) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Monofasica](01_Dominios.md#fase-conexion-monofasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBA_ACOMETIDA](01_Dominios.md#uptbaacometida) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 7 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Acometida BTA Trifasica (Subtipo=9)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBA_ACOMETIDA](01_Dominios.md#uptbaacometida) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBA_ACOMETIDA](01_Dominios.md#uptbaacometida) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Trifasica](01_Dominios.md#fase-conexion-trifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBA_ACOMETIDA](01_Dominios.md#uptbaacometida) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 9 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Bajante BTA Bifasica (Subtipo=5)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBA_BAJANTE](01_Dominios.md#uptbabajante) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBA_BAJANTE](01_Dominios.md#uptbabajante) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Bifasica](01_Dominios.md#fase-conexion-bifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBA_BAJANTE](01_Dominios.md#uptbabajante) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 5 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Bajante BTA Monofasica (Subtipo=4)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBA_BAJANTE](01_Dominios.md#uptbabajante) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBA_BAJANTE](01_Dominios.md#uptbabajante) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Monofasica](01_Dominios.md#fase-conexion-monofasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBA_BAJANTE](01_Dominios.md#uptbabajante) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 4 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Bajante BTA Trifasica (Subtipo=6)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBA_BAJANTE](01_Dominios.md#uptbabajante) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBA_BAJANTE](01_Dominios.md#uptbabajante) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Trifasica](01_Dominios.md#fase-conexion-trifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBA_BAJANTE](01_Dominios.md#uptbabajante) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 6 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Tramo BTA Bifasico (Subtipo=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBA_TRAMO](01_Dominios.md#uptbatramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBA_TRAMO](01_Dominios.md#uptbatramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Bifasica](01_Dominios.md#fase-conexion-bifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBA_TRAMO](01_Dominios.md#uptbatramo) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 2 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Tramo BTA Monofasico (Subtipo=1)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBA_TRAMO](01_Dominios.md#uptbatramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBA_TRAMO](01_Dominios.md#uptbatramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Monofasica](01_Dominios.md#fase-conexion-monofasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBA_TRAMO](01_Dominios.md#uptbatramo) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 1 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Tramo BTA Trifasico (Subtipo=3)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBA_TRAMO](01_Dominios.md#uptbatramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBA_TRAMO](01_Dominios.md#uptbatramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Trifasica](01_Dominios.md#fase-conexion-trifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBA_TRAMO](01_Dominios.md#uptbatramo) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 3 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G234CODIGOCONDUC | CODIGOCONDUCTORFASE | No | Yes |
| G234CODIGOCONDUC_1 | CODIGOCONDUCTORNEUTRO | No | Yes |
| G234MIGUID | MIGUID | No | Yes |
| G234PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |
| G234PUESTOTRANSF | PUESTOTRANSFDISTGLOBALID | No | Yes |
| I234ALIMENTADOR | ALIMENTADOR | No | Yes |
| I234ALIMENTADOR2 | ALIMENTADOR2ID | No | Yes |
| I234ALIMENTADORI | ALIMENTADORID | No | Yes |
| I234HIPERVINCULO | HIPERVINCULO | No | Yes |

</details>

### Relaciones donde participa (3)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_TramoBTAFase](02_Relaciones.md#catestructramobtafase) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |
| [CatEstruc_TramoBTANeutro](02_Relaciones.md#catestructramobtaneutro) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |
| [PuestoTransDist_TramoBTA](02_Relaciones.md#puestotransdisttramobta) | Destino | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | One To Many |

---

## `TramoBajaTensionSubterraneo` — Tramo BT Subterraneo
<a id="tramobajatensionsubterraneo"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Polyline (Complex Edge) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Edge** (línea/tramo) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 51 total — ✅ 21 core · 🔌 2 conectividad · 🔧 15 sistema · ▫️ 13 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object Id | OID | 4 | No | 🔧 Sistema |  |
| `ENABLED` | Enabled | Small Integer | 2 | Yes | ✅ CORE | True |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 01/03/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | Alim1 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Inform Alim | Integer | 4 | Yes | ▫️ Otro |  |
| `FDRMGRNONTRACEABLE` | FdrMgrNonTraceable | Integer | 4 | Yes | ✅ CORE | Yes |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | FERUM 2019 |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | Propio |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | ✅ CORE | Acometida BTS Monofásica |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ✅ CORE | A |
| `VOLTAJE` | VOLTAJE | Integer | 4 | Yes | ✅ CORE | 240V |
| `LONGITUDSISTEMA` | Longitud Sistema | Double | 8 | Yes | ▫️ Otro |  |
| `CODIGOCONDUCTORFASE` | Codigo Conductor Fase | String | 10 | Yes | ✅ CORE | CON.Al.3x6 |
| `CODIGOCONDUCTORNEUTRO` | Codigo Conductor Neutro | String | 10 | Yes | ✅ CORE | Null |
| `CONFIGURACIONCONDUCTORES` | Configuracion Conductores | String | 5 | Yes | ✅ CORE | 1F3C |
| `CANTIDADCONDUCTORES` | Cantidad Conductores | Integer | 4 | Yes | ▫️ Otro |  |
| `SECUENCIAFASE` | Circuitos | String | 3 | Yes | ✅ CORE | F12 |
| `INDICADORTERNA` | INDICADORTERNA | String | 1 | Yes | ▫️ Otro |  |
| `PUESTOTRANSFDISTOBJECTID` | Puesto Transformador Distribucion OID | Integer | 4 | Yes | ▫️ Otro |  |
| `NOMBRECIRCUITO` | Circuito | String | 7 | Yes | ▫️ Otro |  |
| `LONGITUDCAMPO` | Longitud en Campo | Double | 8 | Yes | ▫️ Otro |  |
| `PROVINCIA` | PROVINCIA | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | CANTON | String | 4 | Yes | ✅ CORE | Milagro |
| `PARROQUIA` | PARROQUIA | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 01/04/2019 |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PUESTOTRANSFDISTGLOBALID` | PUESTOTRANSFDISTGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `HILOPILOTO` | Código Conductor Piloto | String | 10 | Yes | ✅ CORE | null |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `HIPERVINCULO` | Hipervinculo | String | 255 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador 2 | String | 10 | Yes | ▫️ Otro |  |
| `TIPOUSOTRAMO` | Tipo Uso Tramo | Small Integer | 2 | Yes | ✅ CORE | Distribución |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `CIRCUITOS` | Circuitos | String | 3 | Yes | ▫️ Otro |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | O/T 3178 |
| `SHAPE_Length` | SHAPE_Length | Double | 8 | Yes | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `SUBTIPO` | 1 | — |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `CONFIGURACIONCONDUCTORES` | 23 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `INDICADORTERNA` |  | [IndicadorTerna](01_Dominios.md#indicadorterna) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `HILOPILOTO` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |

**Acometida BTS Bifasica (Subtipo=8)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBS_ACOMETIDA](01_Dominios.md#uptbsacometida) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBS_ACOMETIDA](01_Dominios.md#uptbsacometida) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Bifasica](01_Dominios.md#fase-conexion-bifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBS_ACOMETIDA](01_Dominios.md#uptbsacometida) |
| `INDICADORTERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 8 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Acometida BTS Monofasica (Subtipo=7)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBS_ACOMETIDA](01_Dominios.md#uptbsacometida) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBS_ACOMETIDA](01_Dominios.md#uptbsacometida) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Monofasica](01_Dominios.md#fase-conexion-monofasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBS_ACOMETIDA](01_Dominios.md#uptbsacometida) |
| `INDICADORTERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 7 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Acometida BTS Trifasica (Subtipo=9)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBS_ACOMETIDA](01_Dominios.md#uptbsacometida) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBS_ACOMETIDA](01_Dominios.md#uptbsacometida) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` | 7 | [Fase Conexion Trifasica](01_Dominios.md#fase-conexion-trifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBS_ACOMETIDA](01_Dominios.md#uptbsacometida) |
| `INDICADORTERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 9 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Bajante BTS Bifasica (Subtipo=5)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Bifasica](01_Dominios.md#fase-conexion-bifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `INDICADORTERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 5 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Bajante BTS Monofasica (Subtipo=4)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Monofasica](01_Dominios.md#fase-conexion-monofasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `INDICADORTERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 4 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Bajante BTS Trifasica (Subtipo=6)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` | 7 | [Fase Conexion Trifasica](01_Dominios.md#fase-conexion-trifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `INDICADORTERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 6 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Tramo BTS Bifasico (Subtipo=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Bifasica](01_Dominios.md#fase-conexion-bifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `INDICADORTERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 2 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Tramo BTS Monofasico (Subtipo=1) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Monofasica](01_Dominios.md#fase-conexion-monofasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `INDICADORTERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 1 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Tramo BTS Trifasico (Subtipo=3)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOCONDUCTORFASE` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | [Configuracion de Conductores](01_Dominios.md#configuracion-de-conductores) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` | 7 | [Fase Conexion Trifasica](01_Dominios.md#fase-conexion-trifasica) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `HILOPILOTO` |  | [UP_TBS_TRAMO](01_Dominios.md#uptbstramo) |
| `INDICADORTERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 3 | — |
| `TIPOUSOTRAMO` |  | [Tipo Tramo Baja](01_Dominios.md#tipo-tramo-baja) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G228CODIGOCONDUC | CODIGOCONDUCTORFASE | No | Yes |
| G228CODIGOCONDUC_1 | CODIGOCONDUCTORNEUTRO | No | Yes |
| G228MIGUID | MIGUID | No | Yes |
| G228PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |
| G228PUESTOTRANSF | PUESTOTRANSFDISTGLOBALID | No | Yes |
| I228ALIMENTADOR | ALIMENTADOR | No | Yes |
| I228HIPERVINCULO | HIPERVINCULO | No | Yes |

</details>

### Relaciones donde participa (3)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_TramoBTSFase](02_Relaciones.md#catestructramobtsfase) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |
| [CatEstruc_TramoBTSNeutro](02_Relaciones.md#catestructramobtsneutro) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |
| [PuestoTransDist_TramoBTS](02_Relaciones.md#puestotransdisttramobts) | Destino | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | One To Many |

---

## `TramoSubtransmisionAereo` — Tramo Subtransmicion Aereo
<a id="tramosubtransmisionaereo"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Polyline (Complex Edge) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Edge** (línea/tramo) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 46 total — ✅ 22 core · 🔌 2 conectividad · 🔧 13 sistema · ▫️ 9 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `ENABLED` | Enabled | Small Integer | 2 | Yes | ✅ CORE | True |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 24/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | Alim1 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Inform Alim | Integer | 4 | Yes | ▫️ Otro |  |
| `FDRMGRNONTRACEABLE` | FdrMgrNonTraceable | Integer | 4 | Yes | ✅ CORE | Yes |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | PMD |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | Propio |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | ✅ CORE | Tramo STA Trifásico |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ✅ CORE | ABC |
| `VOLTAJE` | VOLTAJE | Integer | 4 | Yes | ✅ CORE | 69 kV |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | ✅ CORE | S/E M. MARIDUEÑA-S/E NARANJITO |
| `CODIGOCONDUCTORFASE` | Codigo Conductor Fase | String | 10 | Yes | ✅ CORE | ACSR.477 |
| `CODIGOCONDUCTORNEUTRO` | Codigo Conductor Neutro | String | 10 | Yes | ✅ CORE | Null |
| `CONFIGURACIONCONDUCTORES` | Configuracion Conductores | String | 5 | Yes | ✅ CORE | 3F3C |
| `SECUENCIAFASE` | SECUENCIAFASE | String | 3 | Yes | ✅ CORE | ABC |
| `LONGITUDSISTEMA` | Longitud del Sistema | Double | 8 | Yes | ▫️ Otro |  |
| `ENERGIZADO` | ENERGIZADO | Small Integer | 2 | Yes | ▫️ Otro |  |
| `RAMAL` | Ramal | String | 10 | Yes | ✅ CORE | Troncal |
| `LONGITUDCAMPO` | Longitud en Campo | Double | 8 | Yes | ▫️ Otro |  |
| `PROVINCIA` | PROVINCIA | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | CANTON | String | 4 | Yes | ✅ CORE | Milagro |
| `PARROQUIA` | PARROQUIA | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 01/04/2019 |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PARENTCIRCUITSOURCEGUID` | PARENTCIRCUITSOURCEGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `PUESTOTRANSFPOTGLOBALID` | Puesto Transf. Potencia Guid | GUID | 38 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | ✅ CORE | PARTICULAR |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `HIPERVINCULO` | Hipervinculo | String | 255 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador 2 | String | 10 | Yes | ▫️ Otro |  |
| `SHAPE` | SHAPE | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | O/T 5471 |
| `SHAPE_Length` | SHAPE_Length | Double | 8 | Yes | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `SUBTIPO` | 1 | — |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `VOLTAJE` |  | [Voltaje AT/MT](01_Dominios.md#voltaje-atmt) |
| `CONFIGURACIONCONDUCTORES` | 34 | — |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Bajante STA Trifásica (SUBTIPO=1) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOCONDUCTORFASE` |  | [UP_TS_TRAMO](01_Dominios.md#uptstramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TS_TRAMO](01_Dominios.md#uptstramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | — |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `VOLTAJE` |  | [Voltaje AT/MT](01_Dominios.md#voltaje-atmt) |

**Tramo STA Trifásico (SUBTIPO=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOCONDUCTORFASE` |  | [UP_TS_TRAMO](01_Dominios.md#uptstramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TS_TRAMO](01_Dominios.md#uptstramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | — |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `VOLTAJE` |  | [Voltaje AT/MT](01_Dominios.md#voltaje-atmt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G240CODIGOCONDUC | CODIGOCONDUCTORNEUTRO | No | Yes |
| G240CODIGOCONDUC_1 | CODIGOCONDUCTORFASE | No | Yes |
| G240MIGUID | MIGUID | No | Yes |
| G240PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |
| G240PUESTOTRANSF | PUESTOTRANSFPOTGLOBALID | No | Yes |

</details>

### Relaciones donde participa (3)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_TramoSubtAereoFase](02_Relaciones.md#catestructramosubtaereofase) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |
| [CatEstruc_TramoSubtAereoNeutro](02_Relaciones.md#catestructramosubtaereoneutro) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |
| [PuestoTransPot_TramoSTA](02_Relaciones.md#puestotranspottramosta) | Destino | [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) | One To Many |

---

## `TramoSubtransmisionSubterraneo` — Tramo Subtransmision Subterraneo
<a id="tramosubtransmisionsubterraneo"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Polyline (Complex Edge) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Edge** (línea/tramo) |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 49 total — ✅ 0 core · 🔌 3 conectividad · 🔧 26 sistema · ▫️ 20 otros |

> ℹ️ Esta clase no tiene una tabla de "Campos obligatorios" dedicada en el manual `MN-TEC-OPE-100`. La columna **Categoría** solo distingue campos de 🔌 *conectividad* / 🔧 *sistema* (comunes a casi todas las clases) de ▫️ *otros* (atributos propios de la clase, no confirmados como obligatorios por el manual pero potencialmente relevantes según el contexto de uso).

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `ENABLED` | Enabled | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | 🔧 Sistema |  |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | Alim1 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Inform Alim | Integer | 4 | Yes | ▫️ Otro |  |
| `FDRMGRNONTRACEABLE` | FdrMgrNonTraceable | Integer | 4 | Yes | ▫️ Otro |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | 🔧 Sistema |  |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | 🔧 Sistema |  |
| `CODIGOEMPRESA` | CodigoEmpresa | String | 10 | Yes | 🔧 Sistema |  |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ▫️ Otro |  |
| `VOLTAJE` | VOLTAJE | Integer | 4 | Yes | ▫️ Otro |  |
| `LONGITUDSISTEMA` | Longitud del Sistema | Double | 8 | Yes | ▫️ Otro |  |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `CODIGOCONDUCTORFASE` | Codigo Conductor Fase | String | 10 | Yes | ▫️ Otro |  |
| `CODIGOCONDUCTORNEUTRO` | Codigo Conductor Neutro | String | 10 | Yes | ▫️ Otro |  |
| `CONFIGURACIONCONDUCTORES` | Configuracion Conductores | String | 5 | Yes | ▫️ Otro |  |
| `CANTIDADCONDUCTORES` | Cantidad Conductores | Integer | 4 | Yes | ▫️ Otro |  |
| `SECUENCIAFASE` | SECUENCIAFASE | String | 3 | Yes | ▫️ Otro |  |
| `POSICIONESTRUCSUBTERRANEA` | Pos Subterranea | Integer | 4 | Yes | ▫️ Otro |  |
| `INDICADORDOBLETERNA` | Doble Terna | String | 1 | Yes | ▫️ Otro |  |
| `ENERGIZADO` | ENERGIZADO | Small Integer | 2 | Yes | ▫️ Otro |  |
| `RAMAL` | Ramal | String | 10 | Yes | ▫️ Otro |  |
| `LONGITUDCAMPO` | Longitud en Campo | Double | 8 | Yes | ▫️ Otro |  |
| `PROVINCIA` | PROVINCIA | String | 2 | Yes | 🔧 Sistema |  |
| `CANTON` | CANTON | String | 4 | Yes | 🔧 Sistema |  |
| `PARROQUIA` | PARROQUIA | String | 6 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PARENTCIRCUITSOURCEGUID` | PARENTCIRCUITSOURCEGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `PUESTOTRANSFPOTGLOBALID` | Puesto Trnsf. Potencia Guid | GUID | 38 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `HIPERVINCULO` | Hipervinculo | String | 255 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador 2 | String | 10 | Yes | ▫️ Otro |  |
| `SHAPE` | SHAPE | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | 🔧 Sistema |  |
| `SHAPE_Length` | SHAPE_Length | Double | 8 | Yes | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `SUBTIPO` | 1 | — |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `VOLTAJE` |  | [Voltaje AT/MT](01_Dominios.md#voltaje-atmt) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `CONFIGURACIONCONDUCTORES` | 34 | — |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `INDICADORDOBLETERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Bajante STS Trifásico (SUBTIPO=1) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOCONDUCTORFASE` |  | [UP_TS_TRAMO](01_Dominios.md#uptstramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TS_TRAMO](01_Dominios.md#uptstramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | — |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `INDICADORDOBLETERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `VOLTAJE` |  | [Voltaje AT/MT](01_Dominios.md#voltaje-atmt) |

**Tramo STS Trifásico (SUBTIPO=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTIDADCONDUCTORES` | 1 | [Cantidad de Cables](01_Dominios.md#cantidad-de-cables) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOCONDUCTORFASE` |  | [UP_TS_TRAMO](01_Dominios.md#uptstramo) |
| `CODIGOCONDUCTORNEUTRO` |  | [UP_TS_TRAMO](01_Dominios.md#uptstramo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONFIGURACIONCONDUCTORES` | 34 | — |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FDRMGRNONTRACEABLE` | 0 | [FdrMgrNonTraceable](01_Dominios.md#fdrmgrnontraceable) |
| `INDICADORDOBLETERNA` | N | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `LONGITUDCAMPO` |  | [Measured Length](01_Dominios.md#measured-length) |
| `LONGITUDSISTEMA` |  | [Measured Length](01_Dominios.md#measured-length) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `RAMAL` |  | [DominioRamal](01_Dominios.md#dominioramal) |
| `VOLTAJE` |  | [Voltaje AT/MT](01_Dominios.md#voltaje-atmt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G241CODIGOCONDUC | CODIGOCONDUCTORNEUTRO | No | Yes |
| G241CODIGOCONDUC_1 | CODIGOCONDUCTORFASE | No | Yes |
| G241MIGUID | MIGUID | No | Yes |
| G241PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |
| G241PUESTOTRANSF | PUESTOTRANSFPOTGLOBALID | No | Yes |

</details>

### Relaciones donde participa (3)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_TramoSubtSubterraneoFase](02_Relaciones.md#catestructramosubtsubterraneofase) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |
| [CatEstruc_TramoSubtSubterraneoNeutro](02_Relaciones.md#catestructramosubtsubterraneoneutro) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |
| [PuestoTransPot_TramoSTS](02_Relaciones.md#puestotranspottramosts) | Destino | [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) | One To Many |

---

## `EstructuraSoporte` — Poste
<a id="estructurasoporte"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 35 total — ✅ 18 core · 🔌 0 conectividad · 🔧 13 sistema · ▫️ 4 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 05/03/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | FERUM 2019 |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 02/04/2019 |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | CAF |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Naranjal |
| `PARROQUIA` | Parroquia | String | 6 | Yes | ✅ CORE | Naranjal |
| `SUBTIPO` | Subtipo | Integer | 4 | Yes | ✅ CORE | Poste Hormigón |
| `PROPIEDAD` | Propiedad | String | 10 | Yes | ✅ CORE | CNELEP-MILAGRO |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | ✅ CORE | c://Alimentador1/73124.jpg |
| `TIPOCIMIENTO` | Cimiento | String | 15 | Yes | ✅ CORE | Canastilla de Hormigón |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ✅ CORE | PHC11_500 |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `COORD_X` | Coord_X | Double | 8 | Yes | ▫️ Otro |  |
| `COORD_Y` | Coord_Y | Double | 8 | Yes | ▫️ Otro |  |
| `ALIMENTADOR` | Alimentador | String | 10 | Yes | ✅ CORE | S/E DMLA016 (PTO.INCA - VILLANUEVA I) |
| `TIPOUSOPOSTE` | Tipo Uso Poste | Small Integer | 2 | Yes | ✅ CORE | Media Baja |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `ESTRUCTURAENPOSTE` | ESTRUCTURAENPOSTE | String | 200 | Yes | ▫️ Otro |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `CODIGOELEMENTO` | CODIGOELEMENTO | String | 16 | Yes | ✅ CORE | 73124 |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | O/T 6512 |

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
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `TIPOCIMIENTO` |  | [Tipo de Cimiento de Poste](01_Dominios.md#tipo-de-cimiento-de-poste) |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `TIPOUSOPOSTE` |  | [Tipo Poste](01_Dominios.md#tipo-poste) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Poste Hormigon (Subtipo=1)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PO_HORMIGON](01_Dominios.md#uppohormigon) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 2 | — |
| `TIPOCIMIENTO` |  | [Tipo de Cimiento de Poste](01_Dominios.md#tipo-de-cimiento-de-poste) |
| `TIPOUSOPOSTE` |  | [Tipo Poste](01_Dominios.md#tipo-poste) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Poste Madera (Subtipo=2) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PO_MADERA](01_Dominios.md#uppomadera) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 3 | — |
| `TIPOCIMIENTO` |  | [Tipo de Cimiento de Poste](01_Dominios.md#tipo-de-cimiento-de-poste) |
| `TIPOUSOPOSTE` |  | [Tipo Poste](01_Dominios.md#tipo-poste) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Poste Metalico (Subtipo=4)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PO_METALICO](01_Dominios.md#uppometalico) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 5 | — |
| `TIPOCIMIENTO` |  | [Tipo de Cimiento de Poste](01_Dominios.md#tipo-de-cimiento-de-poste) |
| `TIPOUSOPOSTE` |  | [Tipo Poste](01_Dominios.md#tipo-poste) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Poste Plastico (Subtipo=3)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PO_PLASTICO](01_Dominios.md#uppoplastico) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 4 | — |
| `TIPOCIMIENTO` |  | [Tipo de Cimiento de Poste](01_Dominios.md#tipo-de-cimiento-de-poste) |
| `TIPOUSOPOSTE` |  | [Tipo Poste](01_Dominios.md#tipo-poste) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Poste Semaforización (Subtipo=5)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PO_SEMAFORO](01_Dominios.md#upposemaforo) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 2 | — |
| `TIPOCIMIENTO` |  | [Tipo de Cimiento de Poste](01_Dominios.md#tipo-de-cimiento-de-poste) |
| `TIPOUSOPOSTE` |  | [Tipo Poste](01_Dominios.md#tipo-poste) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Torre (Subtipo=6)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TORRE](01_Dominios.md#uptorre) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 2 | — |
| `TIPOCIMIENTO` |  | [Tipo de Cimiento de Poste](01_Dominios.md#tipo-de-cimiento-de-poste) |
| `TIPOUSOPOSTE` |  | [Tipo Poste](01_Dominios.md#tipo-poste) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G246CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G246MIGUID | MIGUID | No | Yes |
| I246ALIMENTADOR | ALIMENTADOR | No | Yes |

</details>

### Relaciones donde participa (14)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [EstrucSop_EstrucEnPoste](02_Relaciones.md#estrucsopestrucenposte) | Origen | [`ESTRUCTURAENPOSTE`](#estructuraenposte) | One To Many |
| [EstrucSop_InstEnPoste](02_Relaciones.md#estrucsopinstenposte) | Origen | [`INSTITUCIONENPOSTE`](#institucionenposte) | One To Many |
| [EstrucSop_Luminaria](02_Relaciones.md#estrucsopluminaria) | Origen | [`Luminaria`](06_Clases_Consumidores_y_Alumbrado.md#luminaria) | One To Many |
| [EstrucSop_PuestoCorrFacPot](02_Relaciones.md#estrucsoppuestocorrfacpot) | Origen | [`PuestoCorrectorFactorPotencia`](04_Clases_Proteccion_y_Potencia.md#puestocorrectorfactorpotencia) | One To Many |
| [EstrucSop_PuestoProtBT](02_Relaciones.md#estrucsoppuestoprotbt) | Origen | [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension) | One To Many |
| [EstrucSop_PuestoProtDinam](02_Relaciones.md#estrucsoppuestoprotdinam) | Origen | [`PuestoProteccionDinamico`](04_Clases_Proteccion_y_Potencia.md#puestoprotecciondinamico) | One To Many |
| [EstrucSop_PuestoRegTens](02_Relaciones.md#estrucsoppuestoregtens) | Origen | [`PuestoReguladorTension`](04_Clases_Proteccion_y_Potencia.md#puestoreguladortension) | One To Many |
| [EstrucSop_PuestoSecc](02_Relaciones.md#estrucsoppuestosecc) | Origen | [`PuestoSeccionador`](04_Clases_Proteccion_y_Potencia.md#puestoseccionador) | One To Many |
| [EstrucSop_PuestoSeccFus](02_Relaciones.md#estrucsoppuestoseccfus) | Origen | [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible) | One To Many |
| [EstrucSop_PuestoTransDist](02_Relaciones.md#estrucsoppuestotransdist) | Origen | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | One To Many |
| [EstrucSop_PuntoCarga](02_Relaciones.md#estrucsoppuntocarga) | Origen | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | One To Many |
| [EstrucSop_Semaforo](02_Relaciones.md#estrucsopsemaforo) | Origen | [`Semaforo`](06_Clases_Consumidores_y_Alumbrado.md#semaforo) | One To Many |
| [EstrucSop_Tensor](02_Relaciones.md#estrucsoptensor) | Origen | [`Tensor`](#tensor) | One To Many |
| [POSTE_OPERADORAPOSTE](02_Relaciones.md#posteoperadoraposte) | Origen | [`OPERADORAENPOSTE`](#operadoraenposte) | One To Many |

---

## `ESTRUCTURAENPOSTE` — Estructura en Poste
<a id="estructuraenposte"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 29 total — ✅ 13 core · 🔌 0 conectividad · 🔧 10 sistema · ▫️ 6 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 05/03/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | FERUM 2019 |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | F Activacion | Date | 8 | Yes | ✅ CORE | 02/04/2019 |
| `PROYECTOMODIFICACION` | Proyecto Mod | String | 32 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACION` | F Modificacion | Date | 8 | Yes | ▫️ Otro |  |
| `CODIGOEMPRESA` | Codigo de Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Naranjal |
| `PARROQUIA` | PARROQUIA | String | 6 | Yes | ✅ CORE | Naranjal |
| `CODIGOESTRUCTURA` | Estructura | String | 10 | Yes | ✅ CORE | 1CPT |
| `ESTRUCTURASOPORTEOBJECTID` | Estructura Soporte OID | Integer | 4 | Yes | ▫️ Otro |  |
| `CANTIDAD` | Cantidad | Integer | 4 | Yes | ✅ CORE | 1 |
| `MIPOSCOD` | MIPOSCOD | Double | 8 | Yes | ▫️ Otro |  |
| `MIPOS_OID` | MIPOS_OID | String | 20 | Yes | ▫️ Otro |  |
| `ESTADO` | Estado | Small Integer | 2 | Yes | ✅ CORE | Buen Estado |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `ESTRUCTURASOPORTEGLOBALID` | ESTRUCTURASOPORTEGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `MIESTADO` | MIESTADO | String | 20 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `EXISTENOVEDAD` | Existe Novedad | Small Integer | 2 | Yes | ✅ CORE | No |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | O/T 6515 |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `CODIGOESTRUCTURA` |  | [UP_ES_TODOS](01_Dominios.md#upestodos) |
| `CANTIDAD` | 1 | — |
| `ESTADO` |  | [Estado](01_Dominios.md#estado) |
| `EXISTENOVEDAD` |  | [ExisteNovedad](01_Dominios.md#existenovedad) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G202CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G202ESTRUCTURASO | ESTRUCTURASOPORTEGLOBALID | No | Yes |
| G202MIGUID | MIGUID | No | Yes |

</details>

### Relaciones donde participa (2)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_EstrucPoste](02_Relaciones.md#catestrucestrucposte) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |
| [EstrucSop_EstrucEnPoste](02_Relaciones.md#estrucsopestrucenposte) | Destino | [`EstructuraSoporte`](#estructurasoporte) | One To Many |

---

## `INSTITUCIONENPOSTE` — Institucion en Poste
<a id="institucionenposte"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 28 total — ✅ 11 core · 🔌 0 conectividad · 🔧 10 sistema · ▫️ 7 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre Sis | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 06/03/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | FERUM 2019 |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | F Activacion | Date | 8 | Yes | ✅ CORE | 02/04/2019 |
| `PROYECTOMODIFICACION` | Proyecto Mod | String | 32 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACION` | F Modificacion | Date | 8 | Yes | ▫️ Otro |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Naranjal |
| `PARROQUIA` | PARROQUIA | String | 6 | Yes | ✅ CORE | Naranjal |
| `FACTURABLE` | Facturable | String | 5 | Yes | ✅ CORE | Si |
| `ESTRUCTURASOPORTEOBJECTID` | Estructura Soporte OID | Integer | 4 | Yes | ▫️ Otro |  |
| `INSTITUCION` | Institucion | Small Integer | 2 | Yes | ✅ CORE | Conecel S.A. |
| `MIPOSCOD` | MIPOSCOD | Double | 8 | Yes | ▫️ Otro |  |
| `MIPOS_OID` | MIPOS_OID | String | 20 | Yes | ▫️ Otro |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `ESTRUCTURASOPORTEGLOBALID` | ESTRUCTURASOPORTEGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `ESTADO` | Estado | Small Integer | 2 | Yes | ✅ CORE | Buen Estado |
| `MIESTADO` | MIESTADO | String | 20 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `EXISTENOVEDAD` | Existe Novedad | Small Integer | 2 | Yes | ▫️ Otro |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `FACTURABLE` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `INSTITUCION` | 3 | [Instituciones](01_Dominios.md#instituciones) |
| `ESTADO` |  | [Estado](01_Dominios.md#estado) |
| `EXISTENOVEDAD` |  | [ExisteNovedad](01_Dominios.md#existenovedad) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G203ESTRUCTURASO | ESTRUCTURASOPORTEOBJECTID | No | Yes |
| G203ESTRUCTURASO_1 | ESTRUCTURASOPORTEGLOBALID | No | Yes |
| G203MIGUID | MIGUID | No | Yes |

</details>

### Relaciones donde participa (1)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [EstrucSop_InstEnPoste](02_Relaciones.md#estrucsopinstenposte) | Destino | [`EstructuraSoporte`](#estructurasoporte) | One To Many |

---

## `OPERADORAENPOSTE`
<a id="operadoraenposte"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 23 total — ✅ 0 core · 🔌 0 conectividad · 🔧 8 sistema · ▫️ 15 otros |

> ℹ️ Esta clase no tiene una tabla de "Campos obligatorios" dedicada en el manual `MN-TEC-OPE-100`. La columna **Categoría** solo distingue campos de 🔌 *conectividad* / 🔧 *sistema* (comunes a casi todas las clases) de ▫️ *otros* (atributos propios de la clase, no confirmados como obligatorios por el manual pero potencialmente relevantes según el contexto de uso).

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `OPERADORA` | OPERADORA | String | 50 | Yes | ▫️ Otro |  |
| `PROYECTOCONSTRUCCION` | PROYECTO CONSTRUCCION | String | 50 | Yes | 🔧 Sistema |  |
| `CONTRATO` | CONTRATO | String | 50 | Yes | ▫️ Otro |  |
| `FECHAINICIOCONTRATO` | FECHA INICIO CONTRATO | Date | 8 | Yes | ▫️ Otro |  |
| `FECHAFINCONTRATO` | FECHA FIN CONTRATO | Date | 8 | Yes | ▫️ Otro |  |
| `FECHAINGRESO` | FECHA INGRESO | Date | 8 | Yes | ▫️ Otro |  |
| `FECHAMODIFICACION` | FECHA MODIFICACION | Date | 8 | Yes | ▫️ Otro |  |
| `USUARIOCREACION` | USUARIO CREACION | String | 50 | Yes | ▫️ Otro |  |
| `USUARIOMODIFICACION` | USUARIO MODIFICACION | String | 50 | Yes | ▫️ Otro |  |
| `CODIGOEMPRESA` | EMPRESA | String | 50 | Yes | 🔧 Sistema |  |
| `CANTIDADTOTALTRAMOS` | CANT TOTAL TRAMOS | Small Integer | 2 | Yes | ▫️ Otro |  |
| `CANTIDADTOTALEQUIPOS` | CANT TOTAL EQUIPOS | Small Integer | 2 | Yes | ▫️ Otro |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 200 | Yes | 🔧 Sistema |  |
| `ESPACIOENPOSTE` | ESPACIO POSTE | Small Integer | 2 | Yes | ▫️ Otro |  |
| `NUMEROPOSTE` | NUMERO POSTE | String | 50 | Yes | ▫️ Otro |  |
| `POSTEGLOBALID` | POSTEGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ZONA` | ZONA | Small Integer | 2 | Yes | ▫️ Otro |  |
| `PROVINCIA` | PROVINCIA | String | 50 | Yes | 🔧 Sistema |  |
| `CANTON` | CANTON | String | 50 | Yes | 🔧 Sistema |  |
| `PARROQUIA` | PARROQUIA | String | 50 | Yes | 🔧 Sistema |  |
| `OBSERVACION` | OBSERVACION | String | 100 | Yes | ▫️ Otro |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `OPERADORA` |  | [Dom_Arrendatarios](01_Dominios.md#domarrendatarios) |
| `CODIGOEMPRESA` |  | [Empresas](01_Dominios.md#empresas) |
| `ZONA` |  | [ZONA](01_Dominios.md#zona) |
| `PROVINCIA` |  | [Provincias](01_Dominios.md#provincias) |
| `CANTON` |  | [Cantones](01_Dominios.md#cantones) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G220OPERADORA | OPERADORA | No | Yes |
| G220POSTEGLOBALI | POSTEGLOBALID | No | Yes |

</details>

### Relaciones donde participa (2)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [DATOSOPERADOR_OPERADORA](02_Relaciones.md#datosoperadoroperadora) | Destino | [`DATOSOPERADORA`](05_Clases_Generacion_Subestaciones_Fuentes.md#datosoperadora) | One To Many |
| [POSTE_OPERADORAPOSTE](02_Relaciones.md#posteoperadoraposte) | Destino | [`EstructuraSoporte`](#estructurasoporte) | One To Many |

---

## `Tensor`
<a id="tensor"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 30 total — ✅ 12 core · 🔌 0 conectividad · 🔧 14 sistema · ▫️ 4 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object Id | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 05/03/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | FERUM 2019 |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | CAF |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ✅ CORE | TTST |
| `ESTRUCTURASOPORTEOBJECTID` | Estructura Soporte OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 02/04/2019 |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | ✅ CORE | Tensor a tierra en MT |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `ESTRUCTURASOPORTEGLOBALID` | ESTRUCTURASOPORTEGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `HIPERVINCULO` | Hipervinculo | String | 255 | Yes | 🔧 Sistema |  |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Naranjal |
| `PARROQUIA` | Parroquia | String | 6 | Yes | ✅ CORE | Naranjal |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR` | ALIMENTADOR | String | 10 | Yes | ▫️ Otro |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | O/T 6513 |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `SUBTIPO` | 1 | — |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |

**Tensor a farol en BT (Subtipo=3)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TF_BT](01_Dominios.md#uptfbt) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Tensor a farol en MT (Subtipo=4)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TF_MT](01_Dominios.md#uptfmt) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Tensor a Tierra Doble (Subtipo=7)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TT_DOBLE](01_Dominios.md#upttdoble) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Tensor a tierra en BT (Subtipo=1) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TT_BT](01_Dominios.md#upttbt) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Tensor a tierra en MT (Subtipo=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TT_MT](01_Dominios.md#upttmt) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Tensor de Empuje BT (Subtipo=10)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TE_BT](01_Dominios.md#uptebt) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Tensor de Empuje MT (Subtipo=11)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TE_MT](01_Dominios.md#uptemt) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Tensor Farol Doble (Subtipo=8)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TF_DOBLE](01_Dominios.md#uptfdoble) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Tensor Poste a Poste Doble (Subtipo=9)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TP_DOBLE](01_Dominios.md#uptpdoble) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Tensor Poste a Poste en BT (Subtipo=5)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TP_BT](01_Dominios.md#uptpbt) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Tensor Poste a Poste en MT (Subtipo=6)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TP_MT](01_Dominios.md#uptpmt) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Tensor Subtransmisión (Subtipo=12)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TE_ST](01_Dominios.md#uptest) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G247CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G247ESTRUCTURASO | ESTRUCTURASOPORTEGLOBALID | No | Yes |
| G247MIGUID | MIGUID | No | Yes |
| I247ALIMENTADOR | ALIMENTADOR | No | Yes |

</details>

### Relaciones donde participa (2)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_Tensor](02_Relaciones.md#catestructensor) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |
| [EstrucSop_Tensor](02_Relaciones.md#estrucsoptensor) | Destino | [`EstructuraSoporte`](#estructurasoporte) | One To Many |

---

## `CATALOGOESTRUCTURA` — Catalogo Estructura
<a id="catalogoestructura"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 21 total — ✅ 0 core · 🔌 0 conectividad · 🔧 7 sistema · ▫️ 14 otros |

> ℹ️ Esta clase no tiene una tabla de "Campos obligatorios" dedicada en el manual `MN-TEC-OPE-100`. La columna **Categoría** solo distingue campos de 🔌 *conectividad* / 🔧 *sistema* (comunes a casi todas las clases) de ▫️ *otros* (atributos propios de la clase, no confirmados como obligatorios por el manual pero potencialmente relevantes según el contexto de uso).

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object ID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | 🔧 Sistema |  |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `VIDAUTIL` | VIDA UTIL | Small Integer | 2 | Yes | ▫️ Otro |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ▫️ Otro |  |
| `POTENCIA` | POTENCIA | Double | 8 | Yes | ▫️ Otro |  |
| `TIPO` | TIPO | String | 15 | Yes | ▫️ Otro |  |
| `POTENCIA2` | POTENCIA2 | Double | 8 | Yes | ▫️ Otro |  |
| `PERDIDA_PORCENTAJE` | Porcentaje_Perdidas | Double | 8 | Yes | ▫️ Otro |  |
| `DOBLENIVEL` | DOBLENIVEL | String | 2 | Yes | ▫️ Otro |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 120 | Yes | 🔧 Sistema |  |
| `DESCRIPCIONLARGA` | DESCRIPCIONLARGA | String | 255 | Yes | ▫️ Otro |  |
| `DESCRIPCIONCORTA` | DESCRIPCIONCORTA | String | 60 | Yes | ▫️ Otro |  |
| `DESC_NEMOT` | DESC_NEMOT | String | 64 | Yes | ▫️ Otro |  |
| `PERDIDA_PORCENTAJE2` | Porcentaje Perdidas 2 | Double | 8 | Yes | ▫️ Otro |  |
| `CODIGO_SISDAT` | Código SISDAT | String | 30 | Yes | ▫️ Otro |  |
| `PERDIDAS` | Perdidas (W) | Double | 8 | Yes | ▫️ Otro |  |
| `PERDIDAS2` | Perdidas 2 (W) | Double | 8 | Yes | ▫️ Otro |  |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G201CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |

</details>

### Relaciones donde participa (28)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_EstrucNivel](02_Relaciones.md#catestrucestrucnivel) | Origen | [`EstructuraANivel`](#estructuraanivel) | One To Many |
| [CatEstruc_EstrucPoste](02_Relaciones.md#catestrucestrucposte) | Origen | [`ESTRUCTURAENPOSTE`](#estructuraenposte) | One To Many |
| [CatEstruc_Luminaria](02_Relaciones.md#catestrucluminaria) | Origen | [`Luminaria`](06_Clases_Consumidores_y_Alumbrado.md#luminaria) | One To Many |
| [CatEstruc_Pararrayos](02_Relaciones.md#catestrucpararrayos) | Origen | [`Pararrayos`](04_Clases_Proteccion_y_Potencia.md#pararrayos) | One To Many |
| [CatEstruc_PuestoProtBT](02_Relaciones.md#catestrucpuestoprotbt) | Origen | [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension) | One To Many |
| [CatEstruc_PuestoSecc](02_Relaciones.md#catestrucpuestosecc) | Origen | [`PuestoSeccionador`](04_Clases_Proteccion_y_Potencia.md#puestoseccionador) | One To Many |
| [CatEstruc_PuestoSeccFus](02_Relaciones.md#catestrucpuestoseccfus) | Origen | [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible) | One To Many |
| [CatEstruc_PuntoApertura](02_Relaciones.md#catestrucpuntoapertura) | Origen | [`PuntoApertura`](#puntoapertura) | One To Many |
| [CatEstruc_PuntoMiscelaneo](02_Relaciones.md#catestrucpuntomiscelaneo) | Origen | [`PuntoMiscelaneo`](#puntomiscelaneo) | One To Many |
| [CatEstruc_Semaforo](02_Relaciones.md#catestrucsemaforo) | Origen | [`Semaforo`](06_Clases_Consumidores_y_Alumbrado.md#semaforo) | One To Many |
| [CatEstruc_Tensor](02_Relaciones.md#catestructensor) | Origen | [`Tensor`](#tensor) | One To Many |
| [CatEstruc_TramoBTAFase](02_Relaciones.md#catestructramobtafase) | Origen | [`TramoBajaTensionAereo`](#tramobajatensionaereo) | One To Many |
| [CatEstruc_TramoBTANeutro](02_Relaciones.md#catestructramobtaneutro) | Origen | [`TramoBajaTensionAereo`](#tramobajatensionaereo) | One To Many |
| [CatEstruc_TramoBTSFase](02_Relaciones.md#catestructramobtsfase) | Origen | [`TramoBajaTensionSubterraneo`](#tramobajatensionsubterraneo) | One To Many |
| [CatEstruc_TramoBTSNeutro](02_Relaciones.md#catestructramobtsneutro) | Origen | [`TramoBajaTensionSubterraneo`](#tramobajatensionsubterraneo) | One To Many |
| [CatEstruc_TramoDistAereoFase](02_Relaciones.md#catestructramodistaereofase) | Origen | [`TramoDistribucionAereo`](#tramodistribucionaereo) | One To Many |
| [CatEstruc_TramoDistAereoNeutro](02_Relaciones.md#catestructramodistaereoneutro) | Origen | [`TramoDistribucionAereo`](#tramodistribucionaereo) | One To Many |
| [CatEstruc_TramoDistSubterrFase](02_Relaciones.md#catestructramodistsubterrfase) | Origen | [`TramoDistribucionSubterraneo`](#tramodistribucionsubterraneo) | One To Many |
| [CatEstruc_TramoDistSubterrNeutro](02_Relaciones.md#catestructramodistsubterrneutro) | Origen | [`TramoDistribucionSubterraneo`](#tramodistribucionsubterraneo) | One To Many |
| [CatEstruc_TramoSubtAereoFase](02_Relaciones.md#catestructramosubtaereofase) | Origen | [`TramoSubtransmisionAereo`](#tramosubtransmisionaereo) | One To Many |
| [CatEstruc_TramoSubtAereoNeutro](02_Relaciones.md#catestructramosubtaereoneutro) | Origen | [`TramoSubtransmisionAereo`](#tramosubtransmisionaereo) | One To Many |
| [CatEstruc_TramoSubtSubterraneoFase](02_Relaciones.md#catestructramosubtsubterraneofase) | Origen | [`TramoSubtransmisionSubterraneo`](#tramosubtransmisionsubterraneo) | One To Many |
| [CatEstruc_TramoSubtSubterraneoNeutro](02_Relaciones.md#catestructramosubtsubterraneoneutro) | Origen | [`TramoSubtransmisionSubterraneo`](#tramosubtransmisionsubterraneo) | One To Many |
| [CatEstruc_UnidadCapacitor](02_Relaciones.md#catestrucunidadcapacitor) | Origen | [`UNIDADCAPACITOR`](04_Clases_Proteccion_y_Potencia.md#unidadcapacitor) | One To Many |
| [CatEstruc_UnidadProtecDinamico](02_Relaciones.md#catestrucunidadprotecdinamico) | Origen | [`UNIDADPROTECCIONDINAMICO`](04_Clases_Proteccion_y_Potencia.md#unidadprotecciondinamico) | One To Many |
| [CatEstruc_UnidadReguladorTension](02_Relaciones.md#catestrucunidadreguladortension) | Origen | [`UNIDADREGULADORTENSION`](04_Clases_Proteccion_y_Potencia.md#unidadreguladortension) | One To Many |
| [CatEstruc_UnidadTransDistribucion](02_Relaciones.md#catestrucunidadtransdistribucion) | Origen | [`UNIDADTRANSFDISTRIBUCION`](04_Clases_Proteccion_y_Potencia.md#unidadtransfdistribucion) | One To Many |
| [CatEstruc_UnidadTransPotencia](02_Relaciones.md#catestrucunidadtranspotencia) | Origen | [`UNIDADTRANSFPOTENCIA`](04_Clases_Proteccion_y_Potencia.md#unidadtransfpotencia) | One To Many |

---

## `EstructuraANivel` — Estructura a Nivel
<a id="estructuraanivel"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple) |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 34 total — ✅ 0 core · 🔌 1 conectividad · 🔧 25 sistema · ▫️ 8 otros |

> ℹ️ Esta clase no tiene una tabla de "Campos obligatorios" dedicada en el manual `MN-TEC-OPE-100`. La columna **Categoría** solo distingue campos de 🔌 *conectividad* / 🔧 *sistema* (comunes a casi todas las clases) de ▫️ *otros* (atributos propios de la clase, no confirmados como obligatorios por el manual pero potencialmente relevantes según el contexto de uso).

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | 🔧 Sistema |  |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto de Const | String | 32 | Yes | 🔧 Sistema |  |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | 🔧 Sistema |  |
| `CODIGOEMPRESA` | Codigo de Empresa | String | 10 | Yes | 🔧 Sistema |  |
| `CODIGOELEMENTO` | Codigo Elemento | Integer | 4 | Yes | ▫️ Otro |  |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `PROPIEDAD` | Propiedad | String | 10 | Yes | ▫️ Otro |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `MATERIAL` | MATERIAL | String | 10 | Yes | ▫️ Otro |  |
| `NOMBRE` | NOMBRE | String | 30 | Yes | ▫️ Otro |  |
| `MARCA` | MARCA | String | 3 | Yes | ▫️ Otro |  |
| `CODIGOESTRUCTURA` | ESTRUCTURA | String | 10 | Yes | ▫️ Otro |  |
| `ENABLED` | Enabled | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | 🔧 Sistema |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `PROVINCIA` | Provincia | String | 2 | Yes | 🔧 Sistema |  |
| `CANTON` | Canton | String | 4 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR` | ALIMENTADOR | String | 10 | Yes | ▫️ Otro |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `SUBTIPO` | 5 | — |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `MATERIAL` |  | [Tipo Material](01_Dominios.md#tipo-material) |
| `MARCA` |  | [Marcas](01_Dominios.md#marcas) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` |  | [Provincias](01_Dominios.md#provincias) |
| `CANTON` |  | [Cantones](01_Dominios.md#cantones) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |

**Armario (Subtipo=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CANTON` |  | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `MARCA` |  | [Marcas](01_Dominios.md#marcas) |
| `MATERIAL` | B | [Surface Structure - Pad Material](01_Dominios.md#surface-structure---pad-material) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` |  | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 2 | — |

**Cabina (Subtipo=5) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CANTON` |  | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `MARCA` |  | [Marcas](01_Dominios.md#marcas) |
| `MATERIAL` |  | [Tipo Material](01_Dominios.md#tipo-material) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` |  | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 5 | — |

**Caja Tronal (Subtipo=1)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CANTON` |  | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `MARCA` |  | [Marcas](01_Dominios.md#marcas) |
| `MATERIAL` |  | [Tipo Material](01_Dominios.md#tipo-material) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` |  | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 5 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Tablero (Subtipo=3)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CANTON` |  | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `MARCA` |  | [Marcas](01_Dominios.md#marcas) |
| `MATERIAL` | C | [Surface Structure - Pad Material](01_Dominios.md#surface-structure---pad-material) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROVINCIA` |  | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 3 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G245CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G245MIGUID | MIGUID | No | Yes |

</details>

### Relaciones donde participa (11)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_EstrucNivel](02_Relaciones.md#catestrucestrucnivel) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |
| [EstrucNivel_PuestoCorrFacPot](02_Relaciones.md#estrucnivelpuestocorrfacpot) | Origen | [`PuestoCorrectorFactorPotencia`](04_Clases_Proteccion_y_Potencia.md#puestocorrectorfactorpotencia) | One To Many |
| [EstrucNivel_PuestoProtBT](02_Relaciones.md#estrucnivelpuestoprotbt) | Origen | [`PuestoProteccionBajaTension`](04_Clases_Proteccion_y_Potencia.md#puestoproteccionbajatension) | One To Many |
| [EstrucNivel_PuestoProtDin](02_Relaciones.md#estrucnivelpuestoprotdin) | Origen | [`PuestoProteccionDinamico`](04_Clases_Proteccion_y_Potencia.md#puestoprotecciondinamico) | One To Many |
| [EstrucNivel_PuestoRegTens](02_Relaciones.md#estrucnivelpuestoregtens) | Origen | [`PuestoReguladorTension`](04_Clases_Proteccion_y_Potencia.md#puestoreguladortension) | One To Many |
| [EstrucNivel_PuestoSecc](02_Relaciones.md#estrucnivelpuestosecc) | Origen | [`PuestoSeccionador`](04_Clases_Proteccion_y_Potencia.md#puestoseccionador) | One To Many |
| [EstrucNivel_PuestoSeccFus](02_Relaciones.md#estrucnivelpuestoseccfus) | Origen | [`PuestoSeccionadorFusible`](04_Clases_Proteccion_y_Potencia.md#puestoseccionadorfusible) | One To Many |
| [EstrucNivel_PuestoTransDist](02_Relaciones.md#estrucnivelpuestotransdist) | Origen | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | One To Many |
| [EstrucNivel_PuestoTransPot](02_Relaciones.md#estrucnivelpuestotranspot) | Origen | [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia) | One To Many |
| [EstrucNivel_PuntoAper](02_Relaciones.md#estrucnivelpuntoaper) | Origen | [`PuntoApertura`](#puntoapertura) | One To Many |
| [EstrucNivel_PuntoCarga](02_Relaciones.md#estrucnivelpuntocarga) | Origen | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | One To Many |

---

## `SERVICIOCALLES` — Calles
<a id="serviciocalles"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 26 total — ✅ 0 core · 🔌 0 conectividad · 🔧 18 sistema · ▫️ 8 otros |

> ℹ️ Esta clase no tiene una tabla de "Campos obligatorios" dedicada en el manual `MN-TEC-OPE-100`. La columna **Categoría** solo distingue campos de 🔌 *conectividad* / 🔧 *sistema* (comunes a casi todas las clases) de ▫️ *otros* (atributos propios de la clase, no confirmados como obligatorios por el manual pero potencialmente relevantes según el contexto de uso).

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `PUNTOSEMAFORIZACIONGUID` | PUNTOSEMAFORIZACIONGUID | GUID | 38 | Yes | ▫️ Otro |  |
| `PUNTOSEMAFORIZACION` | PUNTOSEMAFORIZACION | Integer | 4 | Yes | ▫️ Otro |  |
| `INTERSECCIONCALLES` | INTERSECCIONCALLES | String | 50 | Yes | ▫️ Otro |  |
| `CALLEPRINCIPAL` | CALLEPRINCIPAL | String | 50 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACION` | F Modificacion | Date | 8 | Yes | ▫️ Otro |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | Proyecto Mod | String | 32 | Yes | 🔧 Sistema |  |
| `PROVINCIA` | Provincia | String | 2 | Yes | 🔧 Sistema |  |
| `CANTON` | Canton | String | 4 | Yes | 🔧 Sistema |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | 🔧 Sistema |  |
| `ESTADO` | Estado | Small Integer | 2 | Yes | ▫️ Otro |  |
| `MIESTADO` | MIESTADO | String | 20 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `EXISTENOVEDAD` | Existe Novedad | Small Integer | 2 | Yes | ▫️ Otro |  |
| `GLOBALID` | GlobalID | Global ID | 38 | No | 🔧 Sistema |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` |  | [Provincias](01_Dominios.md#provincias) |
| `CANTON` |  | [Cantones](01_Dominios.md#cantones) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `ESTADO` |  | [Estado](01_Dominios.md#estado) |
| `EXISTENOVEDAD` |  | [ExisteNovedad](01_Dominios.md#existenovedad) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G219MIGUID | MIGUID | No | Yes |
| G219PUNTOSEMAFOR | PUNTOSEMAFORIZACIONGUID | No | Yes |

</details>

### Relaciones donde participa (1)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [Semaforo_ServicioCAlles](02_Relaciones.md#semaforoserviciocalles) | Destino | [`Semaforo`](06_Clases_Consumidores_y_Alumbrado.md#semaforo) | One To Many |

---

## `PuntoMiscelaneo` — Puntos Miscelaneos
<a id="puntomiscelaneo"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple) |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 29 total — ✅ 0 core · 🔌 0 conectividad · 🔧 25 sistema · ▫️ 4 otros |

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
| `CANTIDAD` | CANTIDAD | Integer | 4 | Yes | ▫️ Otro |  |
| `CODIGOESTRUCTURA` | CODIGOESTRUCTURA | String | 10 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR` | ALIMENTADOR | String | 10 | Yes | ▫️ Otro |  |
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
| `SUBTIPO` | 4 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |

**Amortiguador (Subtipo=9)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 4 | — |

**Barraje Subterraneo (Subtipo=14)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PM_BARRAJE](01_Dominios.md#uppmbarraje) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 4 | — |

**Caja Control para Alumbrado (Subtipo=10)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [Estructura Alumbrado Publ](01_Dominios.md#estructura-alumbrado-publ) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 4 | — |

**Caja Distribución Acometidas (Subtipo=11)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 4 | — |

**Control de Semaforización (Subtipo=12)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 4 | — |

**Empalme Subterraneo (Subtipo=4) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 4 | — |

**Fin de Linea BT (Subtipo=5)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 5 | — |

**Fin de Linea MT (Subtipo=6)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 4 | — |

**Puente Aereo BT (Subtipo=7)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 4 | — |

**Puente Aereo MT (Subtipo=8)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 4 | — |

**Punta Terminal (Subtipo=1)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` | P201061 | [Estructura Punta Terminal](01_Dominios.md#estructura-punta-terminal) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |

**Tablero de Medidores (Subtipo=13)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 4 | — |

**Tablero Subterraneo (Subtipo=16)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 4 | — |

**Transici​​on Subterranea ​ (Subtipo=15)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 4 | — |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G248CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G248MIGUID | MIGUID | No | Yes |
| I248ALIMENTADOR | ALIMENTADOR | No | Yes |

</details>

### Relaciones donde participa (1)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_PuntoMiscelaneo](02_Relaciones.md#catestrucpuntomiscelaneo) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |

---

## `PuntoApertura` — Punto Apertura
<a id="puntoapertura"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple Junction) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Junction** (punto de conexión) |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 54 total — ✅ 0 core · 🔌 4 conectividad · 🔧 25 sistema · ▫️ 25 otros |

> ℹ️ Esta clase no tiene una tabla de "Campos obligatorios" dedicada en el manual `MN-TEC-OPE-100`. La columna **Categoría** solo distingue campos de 🔌 *conectividad* / 🔧 *sistema* (comunes a casi todas las clases) de ▫️ *otros* (atributos propios de la clase, no confirmados como obligatorios por el manual pero potencialmente relevantes según el contexto de uso).

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object Id | OID | 4 | No | 🔧 Sistema |  |
| `ANCILLARYROLE` | ANCILLARYROLE | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ENABLED` | Enabled | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | 🔧 Sistema |  |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | Alim1 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Inform Alim | Integer | 4 | Yes | ▫️ Otro |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | 🔧 Sistema |  |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | 🔧 Sistema |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | 🔧 Sistema |  |
| `PROVINCIA` | Provincia | String | 2 | Yes | 🔧 Sistema |  |
| `CANTON` | Canton | String | 4 | Yes | 🔧 Sistema |  |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TEXTOETIQUETA` | Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ▫️ Otro |  |
| `VOLTAJE` | Voltaje | Integer | 4 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ▫️ Otro |  |
| `POSICIONNORMAL_A` | Posicion Normal A | Integer | 4 | Yes | ▫️ Otro |  |
| `POSICIONNORMAL_B` | Posicion Normal B | Integer | 4 | Yes | ▫️ Otro |  |
| `POSICIONNORMAL_C` | Posicion Normal C | Integer | 4 | Yes | ▫️ Otro |  |
| `POSICIONACTUAL_A` | Posicion Actual A | Integer | 4 | Yes | ▫️ Otro |  |
| `POSICIONACTUAL_B` | Posicion Actual B | Integer | 4 | Yes | ▫️ Otro |  |
| `POSICIONACTUAL_C` | Posicion Actual C | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURANIVELOBJECTID` | Estructura NIVEL OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURASUBTERRANEAOBJECTID` | Estructura Sub OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `PARROQUIA` | PARROQUIA | String | 6 | Yes | 🔧 Sistema |  |
| `POSICION` | POSICION | Small Integer | 2 | Yes | ▫️ Otro |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `ESTRUCTURANIVELGLOBALID` | EstructuraNivelGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURASUBTERRANEAGLOBALID` | ESTRUCTURASUBTERRANEAGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador 2 | String | 10 | Yes | ▫️ Otro |  |
| `CAPACIDADFUSIBLE` | Capacidad Fusible | String | 50 | Yes | ▫️ Otro |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `CODIGOADMS` | CODIGOADMS | String | 100 | Yes | ▫️ Otro |  |
| `CODIGOPUESTO` | Codigo Puesto | String | 20 | Yes | ▫️ Otro |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | 🔧 Sistema |  |
| `CORRIENTE` | CORRIENTE | Double | 8 | Yes | ▫️ Otro |  |
| `CORRIENTEMAXCORTOCIRCUITO` | CORRIENTEMAXCORTOCIRCUITO | Integer | 4 | Yes | ▫️ Otro |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `SUBTIPO` | 1 | — |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `POSICIONNORMAL_A` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_A` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CAPACIDADFUSIBLE` |  | [UP_PA_CAPACIDAD_FUSIBLE](01_Dominios.md#uppacapacidadfusible) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |

**Codo Bajo Carga (Subtipo=1) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PA_TIPO_CODO](01_Dominios.md#uppatipocodo) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Codo PortaFusible (Subtipo=4)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CAPACIDADFUSIBLE` |  | [UP_PA_CAPACIDAD_FUSIBLE](01_Dominios.md#uppacapacidadfusible) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PA_PORTAFUSIBLE](01_Dominios.md#uppaportafusible) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Premoldeado T (Subtipo=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PA_TIPO_T](01_Dominios.md#uppatipot) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 2 | — |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Puente (Subtipo=3)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PA_PORTAFUSIBLE](01_Dominios.md#uppaportafusible) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 0 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G224CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G224ESTRUCTURANI | ESTRUCTURANIVELGLOBALID | No | Yes |
| G224ESTRUCTURASU | ESTRUCTURASUBTERRANEAGLOBALID | No | Yes |
| G224MIGUID | MIGUID | No | Yes |
| G224PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |

</details>

### Relaciones donde participa (2)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_PuntoApertura](02_Relaciones.md#catestrucpuntoapertura) | Destino | [`CATALOGOESTRUCTURA`](#catalogoestructura) | One To Many |
| [EstrucNivel_PuntoAper](02_Relaciones.md#estrucnivelpuntoaper) | Destino | [`EstructuraANivel`](#estructuraanivel) | One To Many |

---

## `Electrico_RedGeom_Junctions`
<a id="electricoredgeomjunctions"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple Junction) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Junction** (punto de conexión) |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 4 total — ✅ 0 core · 🔌 1 conectividad · 🔧 3 sistema · ▫️ 0 otros |

> ℹ️ Esta clase no tiene una tabla de "Campos obligatorios" dedicada en el manual `MN-TEC-OPE-100`. La columna **Categoría** solo distingue campos de 🔌 *conectividad* / 🔧 *sistema* (comunes a casi todas las clases) de ▫️ *otros* (atributos propios de la clase, no confirmados como obligatorios por el manual pero potencialmente relevantes según el contexto de uso).

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `ENABLED` | ENABLED | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `SHAPE` | SHAPE | Geometry | 0 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |

</details>

---
