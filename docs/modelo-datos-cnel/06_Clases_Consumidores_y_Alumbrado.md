# 06 · Clases: Consumidores, Cargas y Alumbrado/Semaforización

[⬅ Volver al índice](00_Indice_y_Conceptos.md) · [Dominios](01_Dominios.md) · [Relaciones](02_Relaciones.md) · [03](03_Clases_Redes_y_Soporte.md) · [04](04_Clases_Proteccion_y_Potencia.md) · [05](05_Clases_Generacion_Subestaciones_Fuentes.md)

El extremo de carga ("Sink") de la red: puntos de carga, conexiones de consumidor y sus atributos comerciales, luminarias y semáforos.

**Clases en este archivo:** [`PuntoCarga`](#puntocarga) · [`CONEXIONCONSUMIDOR`](#conexionconsumidor) · [`ATRIBUTOSCONSUMIDOR`](#atributosconsumidor) · [`Luminaria`](#luminaria) · [`UNIDADLUMINARIA`](#unidadluminaria) · [`Semaforo`](#semaforo)

**Leyenda de categoría de campo:** ✅ **CORE** = obligatorio según el manual `MN-TEC-OPE-100` · 🔌 **Conectividad** = usado por el motor de red geométrica / trazado eléctrico (ver [00 · Conceptos](00_Indice_y_Conceptos.md#conectividad-eléctrica-y-trazado-source--sink)) · 🔧 **Sistema** = auditoría/metadatos técnicos común a casi todas las clases (usuario y fecha de registro, IDs internos, geometría, ubicación administrativa) · ▫️ **Otro** = resto de atributos propios de la clase — **no es "innecesario", solo no está confirmado como obligatorio por el manual**; revisar según el caso de uso.

---

## `PuntoCarga` — Punto de Carga
<a id="puntocarga"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple Junction) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Junction** (punto de conexión) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 58 total — ✅ 19 core · 🔌 3 conectividad · 🔧 13 sistema · ▫️ 23 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object Id | OID | 4 | No | 🔧 Sistema |  |
| `ANCILLARYROLE` | ANCILLARYROLE | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ENABLED` | Enabled | Small Integer | 2 | Yes | ✅ CORE | true |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 20/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Inform Alim | Integer | 4 | Yes | ▫️ Otro |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | PMD |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 01/03/2019 |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | null |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Milagro |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ✅ CORE | A |
| `SUBTIPO` | Subtipo | Integer | 4 | Yes | ✅ CORE | Medidor Bajo Voltaje |
| `ESTRUCTURASOPORTEOBJECTID` | Estructura Soporte OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURANIVELOBJECTID` | Estructura Nivel OID | Integer | 4 | Yes | ▫️ Otro |  |
| `PUESTOTRANSFDISTOBJECTID` | Puesto Transformador Distribucion OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURASUBTERRANEAOBJECTID` | EstrucSubterrOID | Integer | 4 | Yes | ▫️ Otro |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `RUTALECTURA` | Ruta Lectura | String | 12 | Yes | ▫️ Otro |  |
| `SECUENCIALECTURA` | Secuencia Lectura | String | 255 | Yes | ▫️ Otro |  |
| `COORD_X` | Coord X | Double | 8 | Yes | ▫️ Otro |  |
| `COORD_Y` | Coord Y | Double | 8 | Yes | ▫️ Otro |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | ✅ CORE | c://alimentador4/OID1225.jpg |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PUESTOTRANSFDISTGLOBALID` | PUESTOTRANSFDISTGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURANIVELGLOBALID` | ESTRUCTURANIVELGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURASUBTERRANEAGLOBALID` | ESTRUCTURASUBTERRANEAGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURASOPORTEGLOBALID` | EstructuraSoporteGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador 2 | String | 10 | Yes | ▫️ Otro |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `NUMEROCLIENTES` | Número de Clientes | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRATO` | Estrato | String | 20 | Yes | ▫️ Otro |  |
| `CONSUMOPROMEDIOANUAL` | Consumo Promedio Anual | Double | 8 | Yes | ▫️ Otro |  |
| `FUENTEENERGIA` | Fuente de Energía | String | 20 | Yes | ✅ CORE | Convencional |
| `POTENCIAACUMULADA` | POTENCIAACUMULADA | Double | 8 | Yes | ▫️ Otro |  |
| `TOTALIZADOR` | TOTALIZADOR | String | 2 | Yes | ✅ CORE | No |
| `TRAMOGLOBALID` | TRAMOGLOBALID_ | GUID | 38 | Yes | ▫️ Otro |  |
| `REVISADO` | REVISADO | Integer | 4 | Yes | ▫️ Otro |  |
| `CODIGOCLIENTE` | Codigo Cliente | String | 150 | Yes | ✅ CORE | 1299642 |
| `MEDIDOR` | Medidor | String | 250 | Yes | ✅ CORE | 56432 |
| `PREPAGO` | Prepago | String | 1 | Yes | ✅ CORE | No |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | O/T 2361 |

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
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `SUBTIPO` | 6 | — |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `FUENTEENERGIA` |  | [FuenteEnergia](01_Dominios.md#fuenteenergia) |
| `TOTALIZADOR` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PREPAGO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Medidor Alto Voltaje (Subtipo=9)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FUENTEENERGIA` |  | [FuenteEnergia](01_Dominios.md#fuenteenergia) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PREPAGO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `TOTALIZADOR` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Medidor Bajo Voltaje (Subtipo=8)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FUENTEENERGIA` |  | [FuenteEnergia](01_Dominios.md#fuenteenergia) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PREPAGO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `TOTALIZADOR` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Medidor Medio Voltaje (Subtipo=6) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FUENTEENERGIA` |  | [FuenteEnergia](01_Dominios.md#fuenteenergia) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PREPAGO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TOTALIZADOR` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G237ESTRUCTURANI | ESTRUCTURANIVELGLOBALID | No | Yes |
| G237ESTRUCTURASO | ESTRUCTURASOPORTEGLOBALID | No | Yes |
| G237ESTRUCTURASU | ESTRUCTURASUBTERRANEAGLOBALID | No | Yes |
| G237MIGUID | MIGUID | No | Yes |
| G237PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |
| I237ALIMENTADOR | ALIMENTADOR | No | Yes |
| I237ALIMENTADOR2 | ALIMENTADOR2ID | No | Yes |
| I237ALIMENTADORI | ALIMENTADORID | No | Yes |

</details>

### Relaciones donde participa (8)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [EstrucNivel_PuntoCarga](02_Relaciones.md#estrucnivelpuntocarga) | Destino | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | One To Many |
| [EstrucSop_PuntoCarga](02_Relaciones.md#estrucsoppuntocarga) | Destino | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | One To Many |
| [PuestoTransDist_PuntoCarga](02_Relaciones.md#puestotransdistpuntocarga) | Destino | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | One To Many |
| [PuntoCarga_ConexConsumidor](02_Relaciones.md#puntocargaconexconsumidor) | Origen | [`CONEXIONCONSUMIDOR`](#conexionconsumidor) | One To Many |
| [PuntoCarga_Generador](02_Relaciones.md#puntocargagenerador) | Origen | [`Generador`](05_Clases_Generacion_Subestaciones_Fuentes.md#generador) | One To One |
| [PuntoCarga_GeneradorDist](02_Relaciones.md#puntocargageneradordist) | Origen | [`GeneradorDistribuido`](05_Clases_Generacion_Subestaciones_Fuentes.md#generadordistribuido) | One To One |
| [PuntoCarga_MotorInduccion](02_Relaciones.md#puntocargamotorinduccion) | Origen | [`MOTORINDUCCION`](05_Clases_Generacion_Subestaciones_Fuentes.md#motorinduccion) | One To Many |
| [PuntoCarga_MotorSincrono](02_Relaciones.md#puntocargamotorsincrono) | Origen | [`MOTORSINCRONO`](05_Clases_Generacion_Subestaciones_Fuentes.md#motorsincrono) | One To Many |

---

## `CONEXIONCONSUMIDOR` — Conexión Consumidor
<a id="conexionconsumidor"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 45 total — ✅ 16 core · 🔌 0 conectividad · 🔧 13 sistema · ▫️ 16 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | 🔧 Sistema |  |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PUNTOCARGAOBJECTID` | Punto Carga OId | Integer | 4 | Yes | ▫️ Otro |  |
| `CODIGOCLIENTE` | Codigo | String | 8 | Yes | ✅ CORE | 1299642 |
| `PROYECTOCONSTRUCCION` | PROYECTOCONSTRUCCION | String | 32 | Yes | 🔧 Sistema |  |
| `FECHACONSTRUCCION` | FECHACONSTRUCCION | Date | 8 | Yes | 🔧 Sistema |  |
| `POS_T_HOR` | POS_T_HOR | Integer | 4 | Yes | ▫️ Otro |  |
| `POS_T_VER` | POS_T_VER | Integer | 4 | Yes | ▫️ Otro |  |
| `MIPCRGCOD` | MIPCRGCOD | String | 20 | Yes | ▫️ Otro |  |
| `MIPCRG_OID` | MIPCRG_OID | String | 20 | Yes | ▫️ Otro |  |
| `CLIPRVCODP` | CLIPRVCOD | String | 2 | Yes | ▫️ Otro |  |
| `CLICANCODP` | CLICANCODP | String | 2 | Yes | ▫️ Otro |  |
| `NOVEDADES` | Novedades | Small Integer | 2 | Yes | ✅ CORE | Sin novedad |
| `CODRUT` | Agencia_Ruta | String | 9 | Yes | ▫️ Otro |  |
| `MDENUMFAB` | N. Serie Medidor | String | 50 | Yes | ✅ CORE | 12356 |
| `MDENUMEMP` | SR del Medidor | String | 50 | Yes | ✅ CORE | SR-45311 |
| `MEDMAR` | Codigo Medidor | String | 3 | Yes | ✅ CORE | Sanxing Electric |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PUNTOCARGAGLOBALID` | PUNTOCARGAGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `CODIGOUNICO` | Código Único | String | 10 | Yes | ✅ CORE | 1201299642 |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACION` | F Modificacion | Date | 8 | Yes | ▫️ Otro |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROYECTOMODIFICACION` | Proyecto Mod | String | 32 | Yes | 🔧 Sistema |  |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Milagro |
| `PARROQUIA` | Parroquia | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `EXISTENOVEDAD` | Existe Novedad | Small Integer | 2 | Yes | ▫️ Otro |  |
| `ESTADO` | Estado | Small Integer | 2 | Yes | ▫️ Otro |  |
| `MIESTADO` | MIESTADO | String | 20 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `SECUENCIAFASE` | Secuencia Fase BV | String | 3 | Yes | ✅ CORE | a |
| `TIPOMEDIDOR` | TIPOMEDIDOR | String | 30 | Yes | ✅ CORE | Electromecánico-Directa-Socket |
| `PREPAGO` | PREPAGO | String | 2 | Yes | ✅ CORE | No |
| `CODIGOESTRUCTURA` | CODIGOESTRUCTURA | String | 10 | Yes | ✅ CORE | 1E100_1AC |
| `CLIRLSCOD` | CLIRLSCOD | String | 20 | Yes | ▫️ Otro |  |
| `CLISLCCOD` | CLISLCCOD | String | 20 | Yes | ▫️ Otro |  |
| `CLISECINM` | CLISECINM | String | 50 | Yes | ▫️ Otro |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | O/T 2361 |
| `CIRCUITOS` | Circuitos | String | 3 | Yes | ✅ CORE | F12 |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `POS_T_HOR` | 1 | — |
| `POS_T_VER` | 1 | — |
| `NOVEDADES` | 0 | [Novedades](01_Dominios.md#novedades) |
| `MEDMAR` |  | [Marca](01_Dominios.md#marca) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `EXISTENOVEDAD` | 2 | [ExisteNovedad](01_Dominios.md#existenovedad) |
| `ESTADO` | 1 | [Estado](01_Dominios.md#estado) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `TIPOMEDIDOR` |  | [TipoMedidorCIS](01_Dominios.md#tipomedidorcis) |
| `PREPAGO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `CODIGOESTRUCTURA` |  | [UP_MEDIDORES](01_Dominios.md#upmedidores) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G200CODIGOUNICO | CODIGOUNICO | No | Yes |
| G200MIGUID | MIGUID | No | Yes |
| G200PUNTOCARGAGL | PUNTOCARGAGLOBALID | No | Yes |
| I200CODIGOCLIENT | CODIGOCLIENTE | No | Yes |
| I200PUNTOCARGAOB | PUNTOCARGAOBJECTID | No | Yes |

</details>

### Relaciones donde participa (2)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [AtribConsumidor_ConexConsumidor](02_Relaciones.md#atribconsumidorconexconsumidor) | Destino | [`ATRIBUTOSCONSUMIDOR`](#atributosconsumidor) | One To One |
| [PuntoCarga_ConexConsumidor](02_Relaciones.md#puntocargaconexconsumidor) | Destino | [`PuntoCarga`](#puntocarga) | One To Many |

---

## `ATRIBUTOSCONSUMIDOR`
<a id="atributosconsumidor"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 48 total — ✅ 8 core · 🔌 0 conectividad · 🔧 3 sistema · ▫️ 37 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object ID | OID | 4 | No | 🔧 Sistema |  |
| `CODIGOCLIENTE` | Codigo Cliente | String | 8 | No | ✅ CORE | 1299642 |
| `CLITOTDEU` | Valor Deuda | Double | 8 | Yes | ✅ CORE | $ 2,351 |
| `CLIFECULTP` | Fecha Ultimo Pago | Date | 8 | Yes | ✅ CORE | 12/12/2018 |
| `CLIULTCONM` | Ultimo Consumo Mes (Kwh) | Integer | 4 | Yes | ▫️ Otro |  |
| `CLIULTCONP` | Consumo Diario Promedio (Kwh) | Double | 8 | Yes | ▫️ Otro |  |
| `CLIFECINS` | Fecha Instalacion | Date | 8 | Yes | ▫️ Otro |  |
| `EDCCOD` | Estado del Servicio | String | 1 | Yes | ▫️ Otro |  |
| `CDAFAS` | Numero de Fases | Small Integer | 2 | Yes | ▫️ Otro |  |
| `CDACON` | Numero de Conductores | Small Integer | 2 | Yes | ▫️ Otro |  |
| `USOCOD` | Codigo Uso Energia | String | 2 | Yes | ▫️ Otro |  |
| `CLINOMABR` | Nombre Cliente | String | 125 | Yes | ✅ CORE | Juan Piguave |
| `CALDES` | Calle | String | 255 | Yes | ▫️ Otro |  |
| `CLIPRVCOD` | Provincia | String | 2 | Yes | ▫️ Otro |  |
| `CLICANCOD` | Canton | String | 4 | Yes | ▫️ Otro |  |
| `CLIPARCOD` | Parroquia | String | 6 | Yes | ▫️ Otro |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `CLIFECULT` | Fecha Ult.Lectura | Date | 8 | Yes | ▫️ Otro |  |
| `TIPOMEDIDOR` | Tipo Medidor | String | 30 | Yes | ▫️ Otro |  |
| `EMAIL` | Email | String | 255 | Yes | ▫️ Otro |  |
| `POTENCIAACTIVA` | Potencia Activa | Double | 8 | Yes | ▫️ Otro |  |
| `POTENCIAREACTIVA` | Potencia Reactiva | Double | 8 | Yes | ▫️ Otro |  |
| `CATEGORIA` | Categoría | String | 4 | Yes | ▫️ Otro |  |
| `IDCCEDRUC` | RUC Cliente | String | 20 | Yes | ✅ CORE | 09235732001 |
| `NUMMEDIDOR` | Numero de Medidor | String | 20 | Yes | ✅ CORE | 24631 |
| `MDMCOD` | Codigo Marca Medidor | String | 20 | Yes | ▫️ Otro |  |
| `NIVTENSION` | Nivel Tension | String | 10 | Yes | ▫️ Otro |  |
| `PAQUETE` | Paquete | String | 20 | Yes | ▫️ Otro |  |
| `TELEFONO` | Teléfono | String | 30 | Yes | ▫️ Otro |  |
| `CRITICIDAD` | Criticidad | String | 1 | Yes | ▫️ Otro |  |
| `DISCAPACIDAD` | Discapacidad | String | 1 | Yes | ▫️ Otro |  |
| `CELULAR` | Celular | String | 30 | Yes | ▫️ Otro |  |
| `ES_BDH` | Es DBH | String | 1 | Yes | ▫️ Otro |  |
| `TASABASURA` | Tasa de Basura | Double | 8 | Yes | ▫️ Otro |  |
| `AGENCIA` | Agencia | String | 14 | Yes | ▫️ Otro |  |
| `CONSUMOPROMEDIO` | Consumo Promedio | Double | 8 | Yes | ▫️ Otro |  |
| `ESTADOEXTENDIDO` | Estado Extendido | String | 2 | Yes | ▫️ Otro |  |
| `FECHAPRIMERAINSTALACION` | Fec. Primera Inst. | Date | 8 | Yes | ▫️ Otro |  |
| `FACTORMULT` | Tiene Fact.Mult. | String | 50 | Yes | ▫️ Otro |  |
| `TIPOTARIFA` | Tipo Tarifa | String | 10 | Yes | ▫️ Otro |  |
| `ESTADO` | Estado | String | 1 | Yes | ▫️ Otro |  |
| `CUENTACONTRATO` | Cuenta Contrato | String | 50 | Yes | ✅ CORE | 20000135320 |
| `CLISLCCOD` | CLISLCCOD | String | 20 | Yes | ▫️ Otro |  |
| `CLISECINM` | CLISECINM | String | 20 | Yes | ▫️ Otro |  |
| `CLIRLSCOD` | CLIRLSCOD | String | 20 | Yes | ▫️ Otro |  |
| `CODIGOUNICO` | Código Único | String | 20 | Yes | ✅ CORE | 1200456731 |
| `CODIGOEMPRESA` | Empresa | String | 10 | Yes | 🔧 Sistema |  |
| `CLINUMPOS` | CLINUMPOS | String | 16 | Yes | ▫️ Otro |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `EDCCOD` |  | [EstCliente](01_Dominios.md#estcliente) |
| `USOCOD` |  | [Usocod Energia](01_Dominios.md#usocod-energia) |
| `CLIPRVCOD` |  | [Provincias](01_Dominios.md#provincias) |
| `CLICANCOD` |  | [Cantones](01_Dominios.md#cantones) |
| `CLIPARCOD` |  | [Parroquias](01_Dominios.md#parroquias) |
| `TIPOMEDIDOR` |  | [TipoMedidorCIS](01_Dominios.md#tipomedidorcis) |
| `CATEGORIA` |  | [Categoria](01_Dominios.md#categoria) |
| `TIPOTARIFA` |  | [TipoTarifaCIS](01_Dominios.md#tipotarifacis) |
| `CODIGOEMPRESA` |  | [Empresas](01_Dominios.md#empresas) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G199CODIGOUNICO | CODIGOUNICO | No | Yes |
| I199CODIGOCLIENT | CODIGOCLIENTE | No | Yes |

</details>

### Relaciones donde participa (1)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [AtribConsumidor_ConexConsumidor](02_Relaciones.md#atribconsumidorconexconsumidor) | Origen | [`CONEXIONCONSUMIDOR`](#conexionconsumidor) | One To One |

---

## `Luminaria`
<a id="luminaria"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple Junction) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Junction** (punto de conexión) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 53 total — ✅ 23 core · 🔌 3 conectividad · 🔧 14 sistema · ▫️ 13 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 24/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | PMD |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 01/04/2019 |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | MEER |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Milagro |
| `PARROQUIA` | Parroquia | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `CODIGOELEMENTO` | Codigo Luminaria | Integer | 4 | Yes | ✅ CORE | 76538 |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ✅ CORE | LDPM100ACC |
| `ESTRUCTURASOPORTEOBJECTID` | ESTRUCTURA SOPORTEOBJECT OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `ANCILLARYROLE` | ANCILLARYROLE | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ENABLED` | ENABLED | Small Integer | 2 | Yes | ✅ CORE | True |
| `ALIMENTADORID` | ALIMENTADORID | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORID2` | ALIMENTADOR2ID | String | 10 | Yes | ▫️ Otro |  |
| `PUESTOTRANSFDISTOBJECTID` | PUESTOTRANSFDISTOBJECTID | Integer | 4 | Yes | ▫️ Otro |  |
| `FASECONEXION` | FASECONEXION | Integer | 4 | Yes | ✅ CORE | A |
| `ALIMENTADORINFO` | ALIMENTADORINFO | Integer | 4 | Yes | ▫️ Otro |  |
| `ELECTRICTRACEWEIGHT` | ELECTRICTRACEWEIGHT | Integer | 4 | Yes | 🔌 Conectividad |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `SECTORLUMINARIAOBJECTID` | SECTORLUMINARIAOBJECTID | Integer | 4 | Yes | ▫️ Otro |  |
| `HORASFUNC1` | HORASFUNC1 | Small Integer | 2 | Yes | ✅ CORE | 12 |
| `HORASFUNC2` | HORASFUNC2 | Small Integer | 2 | Yes | ✅ CORE | 0 |
| `DIASFUNCMES` | DIASFUNCMES | Small Integer | 2 | Yes | ✅ CORE | 100 |
| `SUBTIPO` | Subtipo | Integer | 4 | Yes | ✅ CORE | Mercurio Cerrado |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PUESTOTRANSFDISTGLOBALID` | PUESTOTRANSFDISTGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `ESTRUCTURASOPORTEGLOBALID` | ESTRUCTURASOPORTEGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador2 | String | 10 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | Comentarios | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `BAJOMEDICION` | Bajo Medición | Small Integer | 2 | Yes | ✅ CORE | Si |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `CLASIFICACION_AP` | CLASIFICACION_AP | String | 20 | Yes | ✅ CORE | Alumbrado Intervenido |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `PROPIEDAD` | PROPIEDAD | String | 20 | Yes | ✅ CORE | Distribuidora |
| `FUENTEENERGIA` | FUENTEENERGIA | String | 20 | Yes | ✅ CORE | Convencional |
| `CIRCUITOS` | Circuitos | String | 3 | Yes | ▫️ Otro |  |
| `SECUENCIAFASE` | Fase de Bajo Voltaje | String | 3 | Yes | ✅ CORE | F12 |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | OT-5420 |
| `POTENCIA` | POTENCIA | Double | 8 | Yes | ▫️ Otro |  |

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
| `SUBTIPO` | 1 | — |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `BAJOMEDICION` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CLASIFICACION_AP` |  | [Lum_Clasificacion_AP](01_Dominios.md#lumclasificacionap) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROPIEDAD` |  | [Lum_Propiedad](01_Dominios.md#lumpropiedad) |
| `FUENTEENERGIA` |  | [FuenteEnergia](01_Dominios.md#fuenteenergia) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |

**Inducción (SUBTIPO=9)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `BAJOMEDICION` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CLASIFICACION_AP` |  | [Lum_Clasificacion_AP](01_Dominios.md#lumclasificacionap) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_AP_INDUCCION](01_Dominios.md#upapinduccion) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FUENTEENERGIA` |  | [FuenteEnergia](01_Dominios.md#fuenteenergia) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` |  | [Lum_Propiedad](01_Dominios.md#lumpropiedad) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**LED (SUBTIPO=5)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `BAJOMEDICION` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CLASIFICACION_AP` |  | [Lum_Clasificacion_AP](01_Dominios.md#lumclasificacionap) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_AP_LUMIN_LED](01_Dominios.md#upapluminled) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FUENTEENERGIA` |  | [FuenteEnergia](01_Dominios.md#fuenteenergia) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` |  | [Lum_Propiedad](01_Dominios.md#lumpropiedad) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Mercurio Abierta (SUBTIPO=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `BAJOMEDICION` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CLASIFICACION_AP` |  | [Lum_Clasificacion_AP](01_Dominios.md#lumclasificacionap) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_AP_LUMIN_HG_ABIERTA](01_Dominios.md#upapluminhgabierta) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FUENTEENERGIA` |  | [FuenteEnergia](01_Dominios.md#fuenteenergia) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` |  | [Lum_Propiedad](01_Dominios.md#lumpropiedad) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Mercurio Cerrada (SUBTIPO=1) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `BAJOMEDICION` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CLASIFICACION_AP` |  | [Lum_Clasificacion_AP](01_Dominios.md#lumclasificacionap) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_AP_LUMIN_HG_CERRADA](01_Dominios.md#upapluminhgcerrada) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FUENTEENERGIA` |  | [FuenteEnergia](01_Dominios.md#fuenteenergia) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` |  | [Lum_Propiedad](01_Dominios.md#lumpropiedad) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Metal Halide (SUBTIPO=11)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `BAJOMEDICION` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CLASIFICACION_AP` |  | [Lum_Clasificacion_AP](01_Dominios.md#lumclasificacionap) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_AP_LUMIN_MH](01_Dominios.md#upapluminmh) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FUENTEENERGIA` |  | [FuenteEnergia](01_Dominios.md#fuenteenergia) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` |  | [Lum_Propiedad](01_Dominios.md#lumpropiedad) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Proyector LED (SUBTIPO=12)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `BAJOMEDICION` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CLASIFICACION_AP` |  | [Lum_Clasificacion_AP](01_Dominios.md#lumclasificacionap) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_AP_PROYECTOR_LED](01_Dominios.md#upapproyectorled) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FUENTEENERGIA` |  | [FuenteEnergia](01_Dominios.md#fuenteenergia) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` |  | [Lum_Propiedad](01_Dominios.md#lumpropiedad) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Proyector Mercurio (SUBTIPO=7)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `BAJOMEDICION` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CLASIFICACION_AP` |  | [Lum_Clasificacion_AP](01_Dominios.md#lumclasificacionap) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_AP_PROYECTOR_HG](01_Dominios.md#upapproyectorhg) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FUENTEENERGIA` |  | [FuenteEnergia](01_Dominios.md#fuenteenergia) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` |  | [Lum_Propiedad](01_Dominios.md#lumpropiedad) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Proyector Metal Halide (SUBTIPO=10)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `BAJOMEDICION` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CLASIFICACION_AP` |  | [Lum_Clasificacion_AP](01_Dominios.md#lumclasificacionap) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_AP_PROYECTOR_MH](01_Dominios.md#upapproyectormh) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FUENTEENERGIA` |  | [FuenteEnergia](01_Dominios.md#fuenteenergia) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` |  | [Lum_Propiedad](01_Dominios.md#lumpropiedad) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Proyector Sodio (SUBTIPO=6)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `BAJOMEDICION` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CLASIFICACION_AP` |  | [Lum_Clasificacion_AP](01_Dominios.md#lumclasificacionap) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_AP_PROYECTOR_NA](01_Dominios.md#upapproyectorna) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FUENTEENERGIA` |  | [FuenteEnergia](01_Dominios.md#fuenteenergia) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` |  | [Lum_Propiedad](01_Dominios.md#lumpropiedad) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Sodio Abierta (SUBTIPO=3)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `BAJOMEDICION` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CLASIFICACION_AP` |  | [Lum_Clasificacion_AP](01_Dominios.md#lumclasificacionap) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_AP_LUMIN_NA_CERRADA](01_Dominios.md#upapluminnacerrada) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FUENTEENERGIA` |  | [FuenteEnergia](01_Dominios.md#fuenteenergia) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` |  | [Lum_Propiedad](01_Dominios.md#lumpropiedad) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Sodio Cerrada (SUBTIPO=4)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `BAJOMEDICION` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CLASIFICACION_AP` |  | [Lum_Clasificacion_AP](01_Dominios.md#lumclasificacionap) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_AP_LUMIN_NA_CERRADA](01_Dominios.md#upapluminnacerrada) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `FUENTEENERGIA` |  | [FuenteEnergia](01_Dominios.md#fuenteenergia) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` |  | [Lum_Propiedad](01_Dominios.md#lumpropiedad) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G225CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G225ESTRUCTURASO | ESTRUCTURASOPORTEGLOBALID | No | Yes |
| G225MIGUID | MIGUID | No | Yes |
| G225PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |
| G225PUESTOTRANSF | PUESTOTRANSFDISTGLOBALID | No | Yes |
| I225ALIMENTADOR | ALIMENTADOR | No | Yes |
| I225ALIMENTADORI | ALIMENTADORID | No | Yes |
| I225ALIMENTADORI_1 | ALIMENTADORID2 | No | Yes |

</details>

### Relaciones donde participa (4)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_Luminaria](02_Relaciones.md#catestrucluminaria) | Destino | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | One To Many |
| [EstrucSop_Luminaria](02_Relaciones.md#estrucsopluminaria) | Destino | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | One To Many |
| [Luminaria_UnidadLuminaria](02_Relaciones.md#luminariaunidadluminaria) | Origen | [`UNIDADLUMINARIA`](#unidadluminaria) | One To One |
| [PuestoTransDist_Luminaria](02_Relaciones.md#puestotransdistluminaria) | Destino | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | One To Many |

---

## `UNIDADLUMINARIA` — Unidad Luminaria
<a id="unidadluminaria"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 26 total — ✅ 0 core · 🔌 0 conectividad · 🔧 19 sistema · ▫️ 7 otros |

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
| `MARCA` | Marca | String | 5 | Yes | ▫️ Otro |  |
| `CODIGOUNIDAD` | Codigo Unidad | String | 20 | Yes | ▫️ Otro |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `LUMINARIAGLOBALID` | LUMINARIAGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | 🔧 Sistema |  |
| `ESTADO` | Estado | Small Integer | 2 | Yes | ▫️ Otro |  |
| `MIESTADO` | MIESTADO | String | 20 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `EXISTENOVEDAD` | Existe Novedad | Small Integer | 2 | Yes | ▫️ Otro |  |
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
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `ESTADO` |  | [Estado](01_Dominios.md#estado) |
| `EXISTENOVEDAD` |  | [ExisteNovedad](01_Dominios.md#existenovedad) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G209LUMINARIAGLO | LUMINARIAGLOBALID | No | Yes |
| G209MIGUID | MIGUID | No | Yes |

</details>

### Relaciones donde participa (1)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [Luminaria_UnidadLuminaria](02_Relaciones.md#luminariaunidadluminaria) | Destino | [`Luminaria`](#luminaria) | One To One |

---

## `Semaforo`
<a id="semaforo"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple Junction) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Junction** (punto de conexión) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 48 total — ✅ 17 core · 🔌 4 conectividad · 🔧 15 sistema · ▫️ 12 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 24/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | PMD |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 01/04/2019 |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | AFD |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Milagro |
| `PARROQUIA` | PARROQUIA | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `CODIGOELEMENTO` | Codigo Semaforo | Integer | 4 | Yes | ▫️ Otro |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ✅ CORE | SCPV28M4 |
| `ESTRUCTURASOPORTEOBJECTID` | ESTRUCTURA SOPORTEOBJECT OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `ANCILLARYROLE` | ANCILLARYROLE | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ENABLED` | ENABLED | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | ALIMENTADORID | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORID2` | ALIMENTADOR2ID | String | 10 | Yes | ▫️ Otro |  |
| `PUESTOTRANSFDISTOBJECTID` | PUESTOTRANSFDISTOBJECTID | Integer | 4 | Yes | ▫️ Otro |  |
| `FASECONEXION` | FASECONEXION | Integer | 4 | Yes | ✅ CORE | A |
| `ALIMENTADORINFO` | ALIMENTADORINFO | Integer | 4 | Yes | ▫️ Otro |  |
| `ELECTRICTRACEWEIGHT` | ELECTRICTRACEWEIGHT | Integer | 4 | Yes | 🔌 Conectividad |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `HORASFUNC1` | HORASFUNC1 | Small Integer | 2 | Yes | ✅ CORE | 24 |
| `HORASFUNC2` | HORASFUNC2 | Small Integer | 2 | Yes | ✅ CORE | 0 |
| `DIASFUNCMES` | DIASFUNCMES | Small Integer | 2 | Yes | ✅ CORE | 100 |
| `SUBTIPO` | Subtipo | Integer | 4 | Yes | ✅ CORE | Vehicular |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `ESTRUCTURASOPORTEGLOBALID` | ESTRUCTURASOPORTEGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `PUESTOTRANSFDISTGLOBALID` | PUESTOTRANSFDISTGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `SECTORSEMAFOROOBJECTID` | SECTORSEMAFOROOBJECTID | Integer | 4 | Yes | ▫️ Otro |  |
| `PARENTCIRCUITSOURCEGUID` | PARENTCIRCUITSOURCEGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `GLOBALID` | GlobalID | Global ID | 38 | No | 🔧 Sistema |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `TEXTOETIQUETA` | TEXTOETIQUETA | String | 255 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador 2 | String | 10 | Yes | ▫️ Otro |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `CIRCUITOS` | Circuitos | String | 3 | Yes | ✅ CORE | F12 |
| `SECUENCIAFASE` | Fase de Bajo Voltaje | String | 3 | Yes | ✅ CORE | c |
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
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |

**Acustico (SUBTIPO=3)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_CS_A](01_Dominios.md#upcsa) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 1 | — |

**Camara (SUBTIPO=4)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_CS_C](01_Dominios.md#upcsc) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Camara de Vigilancia (SUBTIPO=5)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Peatonal (SUBTIPO=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_CS_P](01_Dominios.md#upcsp) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 1 | — |

**Vehicular (SUBTIPO=1) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_CS_V](01_Dominios.md#upcsv) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBTIPO` | 1 | — |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G239CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G239ESTRUCTURASO | ESTRUCTURASOPORTEGLOBALID | No | Yes |
| G239MIGUID | MIGUID | No | Yes |
| G239PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |

</details>

### Relaciones donde participa (4)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_Semaforo](02_Relaciones.md#catestrucsemaforo) | Destino | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | One To Many |
| [EstrucSop_Semaforo](02_Relaciones.md#estrucsopsemaforo) | Destino | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | One To Many |
| [PuestoTransDist_Semaforo](02_Relaciones.md#puestotransdistsemaforo) | Destino | [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion) | One To Many |
| [Semaforo_ServicioCAlles](02_Relaciones.md#semaforoserviciocalles) | Origen | [`SERVICIOCALLES`](03_Clases_Redes_y_Soporte.md#serviciocalles) | One To Many |

---
