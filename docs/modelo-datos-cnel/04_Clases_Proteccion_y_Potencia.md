# 04 · Clases: Protección, Maniobra, Transformación y Compensación

[⬅ Volver al índice](00_Indice_y_Conceptos.md) · [Dominios](01_Dominios.md) · [Relaciones](02_Relaciones.md) · [03](03_Clases_Redes_y_Soporte.md) · [05](05_Clases_Generacion_Subestaciones_Fuentes.md) · [06](06_Clases_Consumidores_y_Alumbrado.md)

Equipos de protección y maniobra (reconectadores/seccionadores/fusibles), transformadores de distribución y potencia, reguladores de tensión y bancos de capacitores — cada uno con su par Puesto (ubicación física, único) + Unidad (atributos constructivos, relacionada, 1-a-N por fase).

**Clases en este archivo:** [`PuestoProteccionDinamico`](#puestoprotecciondinamico) · [`UNIDADPROTECCIONDINAMICO`](#unidadprotecciondinamico) · [`PuestoSeccionador`](#puestoseccionador) · [`PuestoSeccionadorFusible`](#puestoseccionadorfusible) · [`UNIDADFUSIBLE`](#unidadfusible) · [`PuestoProteccionBajaTension`](#puestoproteccionbajatension) · [`UNIDADPROTECCIONBAJATENSION`](#unidadproteccionbajatension) · [`Pararrayos`](#pararrayos) · [`PuestoTransfDistribucion`](#puestotransfdistribucion) · [`UNIDADTRANSFDISTRIBUCION`](#unidadtransfdistribucion) · [`PuestoTransfPotencia`](#puestotransfpotencia) · [`UNIDADTRANSFPOTENCIA`](#unidadtransfpotencia) · [`PuestoReguladorTension`](#puestoreguladortension) · [`UNIDADREGULADORTENSION`](#unidadreguladortension) · [`PuestoCorrectorFactorPotencia`](#puestocorrectorfactorpotencia) · [`UNIDADCAPACITOR`](#unidadcapacitor)

**Leyenda de categoría de campo:** ✅ **CORE** = obligatorio según el manual `MN-TEC-OPE-100` · 🔌 **Conectividad** = usado por el motor de red geométrica / trazado eléctrico (ver [00 · Conceptos](00_Indice_y_Conceptos.md#conectividad-eléctrica-y-trazado-source--sink)) · 🔧 **Sistema** = auditoría/metadatos técnicos común a casi todas las clases (usuario y fecha de registro, IDs internos, geometría, ubicación administrativa) · ▫️ **Otro** = resto de atributos propios de la clase — **no es "innecesario", solo no está confirmado como obligatorio por el manual**; revisar según el caso de uso.

---

## `PuestoProteccionDinamico` — Puesto Proteccion Dinamico
<a id="puestoprotecciondinamico"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple Junction) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Junction** (punto de conexión) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 70 total — ✅ 27 core · 🔌 4 conectividad · 🔧 14 sistema · ▫️ 25 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `ANCILLARYROLE` | ANCILLARY ROLE | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ENABLED` | ENABLED | Small Integer | 2 | Yes | ✅ CORE | True |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S. A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 20/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | Alim1 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Inform Alim | Integer | 4 | Yes | ▫️ Otro |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | Ferum 2019 |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 01/03/2019 |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | AFD |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Milagro |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | ✅ CORE | Reconectador |
| `CODIGOPUESTO` | Codigo Puesto | String | 20 | Yes | ✅ CORE | 34567 |
| `TEXTOETIQUETA` | Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ✅ CORE | ABC |
| `VOLTAJE` | Voltaje | Integer | 4 | Yes | ✅ CORE | 13.8KV |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `POSICIONNORMAL_A` | Posicion Normal A | Integer | 4 | Yes | ✅ CORE | Cerrado |
| `POSICIONNORMAL_B` | Posicion Normal B | Integer | 4 | Yes | ✅ CORE | Cerrado |
| `POSICIONNORMAL_C` | Posicion Normal C | Integer | 4 | Yes | ✅ CORE | Cerrado |
| `POSICIONACTUAL_A` | Posicion Actual A | Integer | 4 | Yes | ✅ CORE | Cerrado |
| `POSICIONACTUAL_B` | Posicion Actual B | Integer | 4 | Yes | ✅ CORE | Cerrado |
| `POSICIONACTUAL_C` | Posicion Actual C | Integer | 4 | Yes | ✅ CORE | Cerrado |
| `INTERRUPTORBYPASS` | Interruptor By Pass | String | 1 | Yes | ▫️ Otro |  |
| `INDICADORPOSICIONINTERRUPTOR` | Posis Interr | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURASOPORTEOBJECTID` | Estructura Soporte OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURANIVELOBJECTID` | Estructura Nivel OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `KVLN` | KVLN | Double | 8 | Yes | ▫️ Otro |  |
| `CORRIENTE` | Corriente | Double | 8 | Yes | ✅ CORE | 600A |
| `CAIDA_TENSION_ACUM` | Caida de Tension Acumulada | Double | 8 | Yes | ▫️ Otro |  |
| `CORRIENTE_3F_CIRCUITO` | Corriente TriFas.Cortocircuito | Double | 8 | Yes | ▫️ Otro |  |
| `DEMANDA` | Demanda | Double | 8 | Yes | ▫️ Otro |  |
| `POSICION` | Posición | Small Integer | 2 | Yes | ▫️ Otro |  |
| `PROTECCION` | Protección | String | 1 | Yes | ▫️ Otro |  |
| `CAPACIDADEQUIPO` | Capacidad Equipo | Double | 8 | Yes | ▫️ Otro |  |
| `CORRIENTE_1F_CIRCUITO` | Corriente MonoFas.Cortocircuito | Double | 8 | Yes | ▫️ Otro |  |
| `POTENCIA_ACUMULADA` | Potencia Acumulada | Double | 8 | Yes | ▫️ Otro |  |
| `INDICE_FALLAS` | Indice de Fallas | Double | 8 | Yes | ▫️ Otro |  |
| `CLIENTES_ACUMULADOS` | Clientes Acumulados | Double | 8 | Yes | ▫️ Otro |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ✅ CORE | 3R600_125T |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `ESTRUCTURANIVELGLOBALID` | EstructuraNivelGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURASOPORTEGLOBALID` | EstructuraSoporteGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `CIRCUITSOURCEGUID` | CircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `SUBSOURCE` | SubSource | Small Integer | 2 | Yes | ✅ CORE | Si |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `CORRIENTEMAXCORTOCIRCUITO` | Corriente max. Corto C. | Integer | 4 | Yes | ✅ CORE | 12.5KA |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador 2 | String | 10 | Yes | ▫️ Otro |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `FACILITYID` | FACILITYID | String | 10 | Yes | ▫️ Otro |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `CODIGOADMS` | CODIGOADMS | String | 100 | Yes | ▫️ Otro |  |
| `TIPOUSO` | TIPOUSO | String | 30 | Yes | ✅ CORE | Cabecera Alimentador |
| `CONTROL` | CONTROL | String | 30 | Yes | ✅ CORE | Tele comandado |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | OT-3455 |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ANCILLARYROLE` | 0 | [AncillaryRoleDomain](01_Dominios.md#ancillaryroledomain) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `SUBTIPO` | 1 | — |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `VOLTAJE` |  | [Voltaje AT/MT](01_Dominios.md#voltaje-atmt) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `INTERRUPTORBYPASS` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `INDICADORPOSICIONINTERRUPTOR` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `PROTECCION` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `TIPOUSO` |  | [P_TipoUso](01_Dominios.md#ptipouso) |
| `CONTROL` |  | [P_Control](01_Dominios.md#pcontrol) |

**Celdas de Interconexión (Subtipo=6)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ANCILLARYROLE` | 0 | [AncillaryRoleDomain](01_Dominios.md#ancillaryroledomain) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PPD_CELDA_INT](01_Dominios.md#upppdceldaint) |
| `CONTROL` |  | [P_Control](01_Dominios.md#pcontrol) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `INDICADORPOSICIONINTERRUPTOR` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `INTERRUPTORBYPASS` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROTECCION` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 1 | — |
| `TIPOUSO` |  | [P_TipoUso](01_Dominios.md#ptipouso) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje AT/MT](01_Dominios.md#voltaje-atmt) |

**Celdas de Protección (Subtipo=7)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ANCILLARYROLE` | 0 | [AncillaryRoleDomain](01_Dominios.md#ancillaryroledomain) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PPD_CELDA_PROT](01_Dominios.md#upppdceldaprot) |
| `CONTROL` |  | [P_Control](01_Dominios.md#pcontrol) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `INDICADORPOSICIONINTERRUPTOR` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `INTERRUPTORBYPASS` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROTECCION` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 1 | — |
| `TIPOUSO` |  | [P_TipoUso](01_Dominios.md#ptipouso) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje AT/MT](01_Dominios.md#voltaje-atmt) |

**Celdas de Seccionamiento (Subtipo=5)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ANCILLARYROLE` | 0 | [AncillaryRoleDomain](01_Dominios.md#ancillaryroledomain) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PPD_CELDA_SEC](01_Dominios.md#upppdceldasec) |
| `CONTROL` |  | [P_Control](01_Dominios.md#pcontrol) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `INDICADORPOSICIONINTERRUPTOR` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `INTERRUPTORBYPASS` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROTECCION` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 1 | — |
| `TIPOUSO` |  | [P_TipoUso](01_Dominios.md#ptipouso) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje AT/MT](01_Dominios.md#voltaje-atmt) |

**Controladores-MV (Subtipo=9)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ANCILLARYROLE` | 0 | [AncillaryRoleDomain](01_Dominios.md#ancillaryroledomain) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONTROL` |  | [P_Control](01_Dominios.md#pcontrol) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `INDICADORPOSICIONINTERRUPTOR` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `INTERRUPTORBYPASS` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROTECCION` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 1 | — |
| `TIPOUSO` |  | [P_TipoUso](01_Dominios.md#ptipouso) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje AT/MT](01_Dominios.md#voltaje-atmt) |

**Disyuntor (Subtipo=1) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ANCILLARYROLE` | 0 | [AncillaryRoleDomain](01_Dominios.md#ancillaryroledomain) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONTROL` |  | [P_Control](01_Dominios.md#pcontrol) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Trifasica](01_Dominios.md#fase-conexion-trifasica) |
| `INDICADORPOSICIONINTERRUPTOR` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `INTERRUPTORBYPASS` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROTECCION` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 1 | — |
| `TIPOUSO` |  | [P_TipoUso](01_Dominios.md#ptipouso) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje AT/MT](01_Dominios.md#voltaje-atmt) |

**Interruptor (Subtipo=3)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ANCILLARYROLE` | 0 | [AncillaryRoleDomain](01_Dominios.md#ancillaryroledomain) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PPD_INTERRUPTOR](01_Dominios.md#upppdinterruptor) |
| `CONTROL` |  | [P_Control](01_Dominios.md#pcontrol) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `INDICADORPOSICIONINTERRUPTOR` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `INTERRUPTORBYPASS` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROTECCION` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 4 | — |
| `TIPOUSO` |  | [P_TipoUso](01_Dominios.md#ptipouso) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje AT/MT](01_Dominios.md#voltaje-atmt) |

**Interruptores Subterraneos (Subtipo=8)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ANCILLARYROLE` | 0 | [AncillaryRoleDomain](01_Dominios.md#ancillaryroledomain) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PPD_INTERRUPTORES_SUB](01_Dominios.md#upppdinterruptoressub) |
| `CONTROL` |  | [P_Control](01_Dominios.md#pcontrol) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `INDICADORPOSICIONINTERRUPTOR` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `INTERRUPTORBYPASS` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROTECCION` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 1 | — |
| `TIPOUSO` |  | [P_TipoUso](01_Dominios.md#ptipouso) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje AT/MT](01_Dominios.md#voltaje-atmt) |

**Reconectador (Subtipo=4)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ANCILLARYROLE` | 0 | [AncillaryRoleDomain](01_Dominios.md#ancillaryroledomain) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PPD_RECONECTADOR](01_Dominios.md#upppdreconectador) |
| `CONTROL` |  | [P_Control](01_Dominios.md#pcontrol) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `INDICADORPOSICIONINTERRUPTOR` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `INTERRUPTORBYPASS` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROTECCION` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 1 | — |
| `TIPOUSO` |  | [P_TipoUso](01_Dominios.md#ptipouso) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje AT/MT](01_Dominios.md#voltaje-atmt) |

**Seccionalizador (Subtipo=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ANCILLARYROLE` | 0 | [AncillaryRoleDomain](01_Dominios.md#ancillaryroledomain) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CONTROL` |  | [P_Control](01_Dominios.md#pcontrol) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `INDICADORPOSICIONINTERRUPTOR` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `INTERRUPTORBYPASS` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROTECCION` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 4 | — |
| `TIPOUSO` |  | [P_TipoUso](01_Dominios.md#ptipouso) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje AT/MT](01_Dominios.md#voltaje-atmt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G236CIRCUITSOURC | CIRCUITSOURCEGUID | No | Yes |
| G236ESTRUCTURANI | ESTRUCTURANIVELGLOBALID | No | Yes |
| G236ESTRUCTURASO | ESTRUCTURASOPORTEGLOBALID | No | Yes |
| G236MIGUID | MIGUID | No | Yes |
| G236PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |

</details>

### Relaciones donde participa (4)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [EstrucNivel_PuestoProtDin](02_Relaciones.md#estrucnivelpuestoprotdin) | Destino | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | One To Many |
| [EstrucSop_PuestoProtDinam](02_Relaciones.md#estrucsoppuestoprotdinam) | Destino | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | One To Many |
| [PuestoProtDinam_CircuitoFuente](02_Relaciones.md#puestoprotdinamcircuitofuente) | Origen | [`CIRCUITOFUENTE`](05_Clases_Generacion_Subestaciones_Fuentes.md#circuitofuente) | One To One |
| [PuestoProtDinam_UnidadProtDinam](02_Relaciones.md#puestoprotdinamunidadprotdinam) | Origen | [`UNIDADPROTECCIONDINAMICO`](#unidadprotecciondinamico) | One To Many |

---

## `UNIDADPROTECCIONDINAMICO` — Proteccion Dinamica
<a id="unidadprotecciondinamico"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 31 total — ✅ 12 core · 🔌 0 conectividad · 🔧 12 sistema · ▫️ 7 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object ID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S. A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 20/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | 🔧 Sistema |  |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | F Activacion | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | Proyecto Mod | String | 32 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACION` | F Modificacion | Date | 8 | Yes | ▫️ Otro |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Milagro |
| `MODELO` | MODELO | String | 20 | Yes | ▫️ Otro |  |
| `NUMEROSERIE` | Serie | String | 20 | Yes | ✅ CORE | S-234567 |
| `MARCA` | Marca | String | 5 | Yes | ✅ CORE | ABB |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ✅ CORE | ABC |
| `CODIGOUNIDAD` | Codigo Unidad | String | 20 | Yes | ✅ CORE | 34567 |
| `PUESTOPROTDINAMOBJECTID` | Puesto Protec Dinam OID | Integer | 4 | Yes | ▫️ Otro |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ✅ CORE | 3R600_125T |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PUESTOPROTDINAMGLOBALID` | PuestoProtDinamGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `ESTADO` | Estado | Small Integer | 2 | Yes | ▫️ Otro |  |
| `MIESTADO` | MIESTADO | String | 20 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `EXISTENOVEDAD` | Existe Novedad | Small Integer | 2 | Yes | ▫️ Otro |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | OT-3455 |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `MARCA` |  | [Marcas](01_Dominios.md#marcas) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `CODIGOESTRUCTURA` |  | [UP_PPD_TODOS](01_Dominios.md#upppdtodos) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `ESTADO` |  | [Estado](01_Dominios.md#estado) |
| `EXISTENOVEDAD` |  | [ExisteNovedad](01_Dominios.md#existenovedad) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G212CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G212MIGUID | MIGUID | No | Yes |
| G212PUESTOPROTDI | PUESTOPROTDINAMOBJECTID | No | Yes |
| G212PUESTOPROTDI_1 | PUESTOPROTDINAMGLOBALID | No | Yes |

</details>

### Relaciones donde participa (2)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_UnidadProtecDinamico](02_Relaciones.md#catestrucunidadprotecdinamico) | Destino | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | One To Many |
| [PuestoProtDinam_UnidadProtDinam](02_Relaciones.md#puestoprotdinamunidadprotdinam) | Destino | [`PuestoProteccionDinamico`](#puestoprotecciondinamico) | One To Many |

---

## `PuestoSeccionador` — Seccionador Cuchilla
<a id="puestoseccionador"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple Junction) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Junction** (punto de conexión) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 64 total — ✅ 25 core · 🔌 3 conectividad · 🔧 14 sistema · ▫️ 22 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECT ID | OID | 4 | No | 🔧 Sistema |  |
| `ANCILLARYROLE` | ANCILLARYROLE | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ENABLED` | Enabled | Small Integer | 2 | Yes | ✅ CORE | True |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 24/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | Alim1 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Inform Alim | Integer | 4 | Yes | ▫️ Otro |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | Ferum 2019 |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 01/04/2019 |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | MEER |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Milagro |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | ✅ CORE | Unipolar con Dispositivo Rompe Arco |
| `CODIGOPUESTO` | Codigo Puesto | String | 20 | Yes | ✅ CORE | 65667 |
| `TEXTOETIQUETA` | Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ✅ CORE | A |
| `VOLTAJE` | Voltaje | Integer | 4 | Yes | ✅ CORE | 7.96KV |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ✅ CORE | 1S100T |
| `POSICIONNORMAL_A` | Posicion Normal A | Integer | 4 | Yes | ✅ CORE | Cerrado |
| `POSICIONNORMAL_B` | Posicion Normal B | Integer | 4 | Yes | ✅ CORE | Abierto |
| `POSICIONNORMAL_C` | Posicion Normal C | Integer | 4 | Yes | ✅ CORE | Abierto |
| `POSICIONACTUAL_A` | Posicion Actual A | Integer | 4 | Yes | ✅ CORE | Cerrado |
| `POSICIONACTUAL_B` | Posicion Actual B | Integer | 4 | Yes | ✅ CORE | Abierto |
| `POSICIONACTUAL_C` | Posicion Actual C | Integer | 4 | Yes | ✅ CORE | Abierto |
| `ESTRUCTURASOPORTEOBJECTID` | Estructura Soporte OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURANIVELOBJECTID` | Estructura Nivel OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURASUBTERRANEAOBJECTID` | Estructura Subterranea OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `KVLN` | KVLN | Double | 8 | Yes | ▫️ Otro |  |
| `CORRIENTE` | Corriente | Double | 8 | Yes | ✅ CORE | 300A |
| `CAIDA_TENSION_ACUM` | Caida de Tension Acumulada | Double | 8 | Yes | ▫️ Otro |  |
| `CORRIENTE_3F_CIRCUITO` | Corriente TriFas.Cortocircuito | Double | 8 | Yes | ▫️ Otro |  |
| `DEMANDA` | Demanda | Double | 8 | Yes | ▫️ Otro |  |
| `POSICION` | Posición | Small Integer | 2 | Yes | ▫️ Otro |  |
| `CORRIENTE_1F_CIRCUITO` | Corriente MonoFas.Cortocircuito | Double | 8 | Yes | ▫️ Otro |  |
| `POTENCIA_ACUMULADA` | Potencia Acumulada | Double | 8 | Yes | ▫️ Otro |  |
| `INDICE_FALLAS` | Indice de Fallas | Double | 8 | Yes | ▫️ Otro |  |
| `CLIENTES_ACUMULADOS` | Clientes Acumulados | Double | 8 | Yes | ▫️ Otro |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `ESTRUCTURANIVELGLOBALID` | EstructuraNivelGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURASUBTERRANEAGLOBALID` | ESTRUCTURASUBTERRANEAGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURASOPORTEGLOBALID` | EstructuraSoporteGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador 2 | String | 10 | Yes | ▫️ Otro |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `CORRIENTEMAXCORTOCIRCUITO` | Corriente max. Corto C. | Integer | 4 | Yes | ✅ CORE | 12.5KA |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `CODIGOADMS` | CODIGOADMS | String | 100 | Yes | ▫️ Otro |  |
| `TIPOUSO` | TIPOUSO | String | 30 | Yes | ✅ CORE | Secc. Fusib. de Línea |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | OT-3442 |

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
| `SUBTIPO` | 3 | — |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `TIPOUSO` |  | [PS_TipoUso](01_Dominios.md#pstipouso) |

**Tripolar (Subtipo=3) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PSC_TRIPOL](01_Dominios.md#uppsctripol) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` | 7 | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 4 | — |
| `TIPOUSO` |  | [PS_TipoUso](01_Dominios.md#pstipouso) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Tripolar con Dispositivo Rompe Arco (Subtipo=4)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PSC_TRIPOL_ROMPE](01_Dominios.md#uppsctripolrompe) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` | 7 | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 7 | — |
| `TIPOUSO` |  | [PS_TipoUso](01_Dominios.md#pstipouso) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Unipolar (Subtipo=1)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PSC_UNIPOL](01_Dominios.md#uppscunipol) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` | 7 | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TIPOUSO` |  | [PS_TipoUso](01_Dominios.md#pstipouso) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Unipolar con Dispositivo Rompe Arco (Subtipo=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PSC_UNIPOL_ROMPE](01_Dominios.md#uppscunipolrompe) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` | 7 | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 2 | — |
| `TIPOUSO` |  | [PS_TipoUso](01_Dominios.md#pstipouso) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G227CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G227ESTRUCTURANI | ESTRUCTURANIVELGLOBALID | No | Yes |
| G227ESTRUCTURASO | ESTRUCTURASOPORTEGLOBALID | No | Yes |
| G227ESTRUCTURASU | ESTRUCTURASUBTERRANEAGLOBALID | No | Yes |
| G227MIGUID | MIGUID | No | Yes |
| G227PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |

</details>

### Relaciones donde participa (3)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_PuestoSecc](02_Relaciones.md#catestrucpuestosecc) | Destino | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | One To Many |
| [EstrucNivel_PuestoSecc](02_Relaciones.md#estrucnivelpuestosecc) | Destino | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | One To Many |
| [EstrucSop_PuestoSecc](02_Relaciones.md#estrucsoppuestosecc) | Destino | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | One To Many |

---

## `PuestoSeccionadorFusible` — Seccionador Fusible
<a id="puestoseccionadorfusible"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple Junction) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Junction** (punto de conexión) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 68 total — ✅ 26 core · 🔌 3 conectividad · 🔧 14 sistema · ▫️ 25 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object ID | OID | 4 | No | 🔧 Sistema |  |
| `ANCILLARYROLE` | ANCILLARYROLE | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ENABLED` | ENABLED | Small Integer | 2 | Yes | ✅ CORE | True |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 20/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | Alim1 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Inform Alim | Integer | 4 | Yes | ▫️ Otro |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | Ferum 2019 |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 01/03/2019 |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | AFD |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Milagro |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | ✅ CORE | Unipolar Abierto |
| `CODIGOPUESTO` | Codigo Puesto | String | 20 | Yes | ✅ CORE | 45667 |
| `TEXTOETIQUETA` | Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ✅ CORE | A |
| `VOLTAJE` | Voltaje | Integer | 4 | Yes | ✅ CORE | 7.96KV |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ✅ CORE | 1S100T |
| `TRAMODISTRIBUCIONOBJECTID` | Tramo Distribucion OID | Integer | 4 | Yes | ▫️ Otro |  |
| `POSICIONNORMAL_A` | Posicion Normal A | Integer | 4 | Yes | ✅ CORE | Cerrado |
| `POSICIONNORMAL_B` | Posicion Normal B | Integer | 4 | Yes | ✅ CORE | Abierto |
| `POSICIONNORMAL_C` | Posicion Normal C | Integer | 4 | Yes | ✅ CORE | Abierto |
| `POSICIONACTUAL_A` | Posicion Actual A | Integer | 4 | Yes | ✅ CORE | Cerrado |
| `POSICIONACTUAL_B` | Posicion Actual B | Integer | 4 | Yes | ✅ CORE | Abierto |
| `POSICIONACTUAL_C` | Posicion Actual C | Integer | 4 | Yes | ✅ CORE | Abierto |
| `ESTRUCTURASOPORTEOBJECTID` | Estructura Soporte OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURASUBTERRANEAOBJECTID` | Estrucutra Subterranea OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURANIVELOBJECTID` | Estructura Nivel OID | Integer | 4 | Yes | ▫️ Otro |  |
| `PUESTOTRANSFDISTOBJECTID` | Puesto Transf Dist OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `KVLN` | KVLN | Double | 8 | Yes | ▫️ Otro |  |
| `CORRIENTE` | Corriente | Double | 8 | Yes | ✅ CORE | 100A |
| `CAIDA_TENSION_ACUM` | Caida de Tension Acumulada | Double | 8 | Yes | ▫️ Otro |  |
| `CORRIENTE_3F_CIRCUITO` | Corriente TriFas.Cortocircuito | Double | 8 | Yes | ▫️ Otro |  |
| `DEMANDA` | Demanada | Double | 8 | Yes | ▫️ Otro |  |
| `POSICION` | Posición | Small Integer | 2 | Yes | ▫️ Otro |  |
| `CORRIENTE_1F_CIRCUITO` | Corriente MonoFas.Cortocircuito | Double | 8 | Yes | ▫️ Otro |  |
| `POTENCIA_ACUMULADA` | Potencia Acumulada | Double | 8 | Yes | ▫️ Otro |  |
| `INDICE_FALLAS` | Indice de Fallas | Double | 8 | Yes | ▫️ Otro |  |
| `CLIENTES_ACUMULADOS` | Clientes Acumulados | Double | 8 | Yes | ▫️ Otro |  |
| `TIPO` | Tipo | Small Integer | 2 | Yes | ✅ CORE | Secc.Fusib. de Trafo |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PUESTOTRANSFDISTGLOBALID` | PuestoTransfDistGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURANIVELGLOBALID` | EstructuraNivelGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURASUBTERRANEAGLOBALID` | ESTRUCTURASUBTERRANEAGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURASOPORTEGLOBALID` | EstructuraSoporteGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `CORRIENTEMAXCORTOCIRCUITO` | Corriente max. Corto C. | Integer | 4 | Yes | ✅ CORE | 4KA |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador 2 | String | 10 | Yes | ▫️ Otro |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TIRAFUSIBLE` | TiraFusible | String | 50 | Yes | ✅ CORE | 2H |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `CODIGOADMS` | CODIGOADMS | String | 100 | Yes | ▫️ Otro |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | OT-3456 |

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
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `TIPO` |  | [TipoSecciFusible](01_Dominios.md#tiposeccifusible) |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ALIMENTADOR2` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Unipolar Abierto (Subtipo=1) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PSF_UNIPOL_ABIERTO](01_Dominios.md#uppsfunipolabierto) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TIPO` |  | [TipoSecciFusible](01_Dominios.md#tiposeccifusible) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Unipolar Abierto con Dispositivo Rompe Arco (Subtipo=3)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PSF_UNIPOL_ABIERTO_ROMPE](01_Dominios.md#uppsfunipolabiertorompe) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 2 | — |
| `TIPO` |  | [TipoSecciFusible](01_Dominios.md#tiposeccifusible) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Unipolar Cerrado (Subtipo=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PSF_UNIPOL_CERRADO](01_Dominios.md#uppsfunipolcerrado) |
| `CORRIENTE` |  | [Corriente Nominal](01_Dominios.md#corriente-nominal) |
| `CORRIENTEMAXCORTOCIRCUITO` |  | [Corriente Corto Circuito](01_Dominios.md#corriente-corto-circuito) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 2 | — |
| `TIPO` |  | [TipoSecciFusible](01_Dominios.md#tiposeccifusible) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G233CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G233ESTRUCTURANI | ESTRUCTURANIVELGLOBALID | No | Yes |
| G233ESTRUCTURASO | ESTRUCTURASOPORTEGLOBALID | No | Yes |
| G233ESTRUCTURASU | ESTRUCTURASUBTERRANEAGLOBALID | No | Yes |
| G233MIGUID | MIGUID | No | Yes |
| G233PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |
| G233PUESTOTRANSF | PUESTOTRANSFDISTGLOBALID | No | Yes |
| I233ALIMENTADOR2 | ALIMENTADOR2ID | No | Yes |
| I233ALIMENTADORI | ALIMENTADORID | No | Yes |

</details>

### Relaciones donde participa (5)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_PuestoSeccFus](02_Relaciones.md#catestrucpuestoseccfus) | Destino | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | One To Many |
| [EstrucNivel_PuestoSeccFus](02_Relaciones.md#estrucnivelpuestoseccfus) | Destino | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | One To Many |
| [EstrucSop_PuestoSeccFus](02_Relaciones.md#estrucsoppuestoseccfus) | Destino | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | One To Many |
| [PuestoSeccFusible_UnidadFusible](02_Relaciones.md#puestoseccfusibleunidadfusible) | Origen | [`UNIDADFUSIBLE`](#unidadfusible) | One To Many |
| [PuestoTransDist_PuestoSeccFus](02_Relaciones.md#puestotransdistpuestoseccfus) | Destino | [`PuestoTransfDistribucion`](#puestotransfdistribucion) | One To Many |

---

## `UNIDADFUSIBLE` — Fusible
<a id="unidadfusible"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 28 total — ✅ 9 core · 🔌 0 conectividad · 🔧 12 sistema · ▫️ 7 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 20/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | 🔧 Sistema |  |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | F Activacion | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | Proyecto Mod | String | 32 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACION` | F Modificacion | Date | 8 | Yes | ▫️ Otro |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Milagro |
| `MARCA` | Marca | String | 5 | Yes | ▫️ Otro |  |
| `CODIGOUNIDAD` | Codigo Unidad | String | 20 | Yes | ▫️ Otro |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `CAPACIDAD` | Capacidad | String | 10 | Yes | ✅ CORE | 2H |
| `PUESTOSECFUSIBLEGLOBALID` | PUESTOSECFUSIBLEGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `ESTADO` | Estado | String | 2 | Yes | ▫️ Otro |  |
| `MIESTADO` | MIESTADO | String | 2 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `EXISTENOVEDAD` | Existe Novedad | Small Integer | 2 | Yes | ▫️ Otro |  |
| `FASECONEXION` | Fase Conexión | Integer | 4 | Yes | ✅ CORE | A |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | OT-3456 |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `MARCA` |  | [Marcas](01_Dominios.md#marcas) |
| `CAPACIDAD` |  | [Capacidad Fusible](01_Dominios.md#capacidad-fusible) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `ESTADO` |  | [Estado](01_Dominios.md#estado) |
| `EXISTENOVEDAD` |  | [ExisteNovedad](01_Dominios.md#existenovedad) |
| `FASECONEXION` |  | [Fase Conexion Monofasica](01_Dominios.md#fase-conexion-monofasica) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G208MIGUID | MIGUID | No | Yes |
| G208PUESTOSECFUS | PUESTOSECFUSIBLEGLOBALID | No | Yes |

</details>

### Relaciones donde participa (1)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [PuestoSeccFusible_UnidadFusible](02_Relaciones.md#puestoseccfusibleunidadfusible) | Destino | [`PuestoSeccionadorFusible`](#puestoseccionadorfusible) | One To Many |

---

## `PuestoProteccionBajaTension` — Puesto Proteccion BT
<a id="puestoproteccionbajatension"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple Junction) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Junction** (punto de conexión) |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 56 total — ✅ 0 core · 🔌 4 conectividad · 🔧 25 sistema · ▫️ 27 otros |

> ℹ️ Esta clase no tiene una tabla de "Campos obligatorios" dedicada en el manual `MN-TEC-OPE-100`. La columna **Categoría** solo distingue campos de 🔌 *conectividad* / 🔧 *sistema* (comunes a casi todas las clases) de ▫️ *otros* (atributos propios de la clase, no confirmados como obligatorios por el manual pero potencialmente relevantes según el contexto de uso).

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECTID | OID | 4 | No | 🔧 Sistema |  |
| `ANCILLARYROLE` | ANCILLARYROLE | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ENABLED` | Enabled | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | 🔧 Sistema |  |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | Alim1 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Infomr Alim | Integer | 4 | Yes | ▫️ Otro |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | 🔧 Sistema |  |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | 🔧 Sistema |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | 🔧 Sistema |  |
| `PROVINCIA` | Provincia | String | 2 | Yes | 🔧 Sistema |  |
| `CANTON` | Canton | String | 4 | Yes | 🔧 Sistema |  |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `CODIGOPUESTO` | Codigo Puesto | String | 20 | Yes | ▫️ Otro |  |
| `TEXTOETIQUETA` | Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ▫️ Otro |  |
| `VOLTAJE` | Voltaje | Integer | 4 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | Comentarios | String | 255 | Yes | 🔧 Sistema |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ▫️ Otro |  |
| `POSICIONNORMAL_A` | Posicion Normal A | Integer | 4 | Yes | ▫️ Otro |  |
| `POSICIONNORMAL_B` | Posicion Normal B | Integer | 4 | Yes | ▫️ Otro |  |
| `POSICIONNORMAL_C` | Posicion Normal C | Integer | 4 | Yes | ▫️ Otro |  |
| `POSICIONACTUAL_A` | Posicion Actual A | Integer | 4 | Yes | ▫️ Otro |  |
| `POSICIONACTUAL_B` | Posicion Actual B | Integer | 4 | Yes | ▫️ Otro |  |
| `POSICIONACTUAL_C` | Posicion Actual C | Integer | 4 | Yes | ▫️ Otro |  |
| `PUESTOTRANSFDISTOBJECTID` | Puesto Trans Dist OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURASOPORTEOBJECTID` | Estructura Soporte OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURANIVELOBJECTID` | Estructura Nivel OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURASUBTERRANEAOBJECTID` | Estructura Subterranea OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | 🔧 Sistema |  |
| `POSICION` | Posición | Small Integer | 2 | Yes | ▫️ Otro |  |
| `CAPACIDADBREAKER` | Capacida Breaker | Double | 8 | Yes | ▫️ Otro |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PUESTOTRANSFDISTGLOBALID` | PuestoTransfDistGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURANIVELGLOBALID` | EstructuraNivelGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURASUBTERRANEAGLOBALID` | ESTRUCTURASUBTERRANEAGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURASOPORTEGLOBALID` | EstructuraSoporteGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador 2 | String | 10 | Yes | ▫️ Otro |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `CODIGOADMS` | CODIGOADMS | String | 100 | Yes | ▫️ Otro |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | 🔧 Sistema |  |

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
| `SUBTIPO` | 2 | — |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Conector Tipo Estanco (Subtipo=4)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PPBT_ESTANCO](01_Dominios.md#upppbtestanco) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 2 | — |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Interruptor Termomagnetico (Subtipo=1)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PPBT_IT](01_Dominios.md#upppbtit) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Seccionador NH (Subtipo=3)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PPBT_NH](01_Dominios.md#upppbtnh) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 2 | — |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Seccionamiento NH (Subtipo=2) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PPBT_NH](01_Dominios.md#upppbtnh) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POSICIONACTUAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONACTUAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_A` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_B` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `POSICIONNORMAL_C` | 1 | [Posicion Abertura](01_Dominios.md#posicion-abertura) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 2 | — |
| `VOLTAJE` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G226CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G226ESTRUCTURANI | ESTRUCTURANIVELGLOBALID | No | Yes |
| G226ESTRUCTURASO | ESTRUCTURASOPORTEGLOBALID | No | Yes |
| G226ESTRUCTURASU | ESTRUCTURASUBTERRANEAGLOBALID | No | Yes |
| G226MIGUID | MIGUID | No | Yes |
| G226PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |
| G226PUESTOTRANSF | PUESTOTRANSFDISTGLOBALID | No | Yes |

</details>

### Relaciones donde participa (5)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_PuestoProtBT](02_Relaciones.md#catestrucpuestoprotbt) | Destino | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | One To Many |
| [EstrucNivel_PuestoProtBT](02_Relaciones.md#estrucnivelpuestoprotbt) | Destino | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | One To Many |
| [EstrucSop_PuestoProtBT](02_Relaciones.md#estrucsoppuestoprotbt) | Destino | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | One To Many |
| [PuestoProtBT_UnidadProtBT](02_Relaciones.md#puestoprotbtunidadprotbt) | Origen | [`UNIDADPROTECCIONBAJATENSION`](#unidadproteccionbajatension) | One To Many |
| [PuestoTransDist_PuestoProtBT](02_Relaciones.md#puestotransdistpuestoprotbt) | Destino | [`PuestoTransfDistribucion`](#puestotransfdistribucion) | One To Many |

---

## `UNIDADPROTECCIONBAJATENSION`
<a id="unidadproteccionbajatension"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 28 total — ✅ 0 core · 🔌 0 conectividad · 🔧 19 sistema · ▫️ 9 otros |

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
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `PUESTOPROTECCIONBTGLOBALID` | PUESTOSECFUSIBLEGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `EXISTENOVEDAD` | Existe Novedad | Small Integer | 2 | Yes | ▫️ Otro |  |
| `CAPACIDAD` | Capacidad | String | 10 | Yes | ▫️ Otro |  |
| `ESTADO` | Estado | String | 2 | Yes | ▫️ Otro |  |
| `MIESTADO` | MIESTADO | String | 2 | Yes | ▫️ Otro |  |
| `FASECONEXION` | Fase Conexión | Integer | 4 | Yes | ▫️ Otro |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOEMPRESA` | EERCS | — |
| `PROVINCIA` | 01 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` |  | [Cantones](01_Dominios.md#cantones) |
| `MARCA` |  | [Marca](01_Dominios.md#marca) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `EXISTENOVEDAD` |  | [ExisteNovedad](01_Dominios.md#existenovedad) |
| `CAPACIDAD` |  | [Capacidad PBT](01_Dominios.md#capacidad-pbt) |
| `FASECONEXION` |  | [Fase Conexion Monofasica](01_Dominios.md#fase-conexion-monofasica) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G211PUESTOPROTEC | PUESTOPROTECCIONBTGLOBALID | No | Yes |

</details>

### Relaciones donde participa (1)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [PuestoProtBT_UnidadProtBT](02_Relaciones.md#puestoprotbtunidadprotbt) | Destino | [`PuestoProteccionBajaTension`](#puestoproteccionbajatension) | One To Many |

---

## `Pararrayos` — Pararrayo
<a id="pararrayos"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple) |
| **Tabla de campos obligatorios en el manual** | No hay tabla dedicada en el manual para esta clase (ver nota) |
| **Campos** | 27 total — ✅ 0 core · 🔌 0 conectividad · 🔧 24 sistema · ▫️ 3 otros |

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
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | 🔧 Sistema |  |
| `PROVINCIA` | Provincia | String | 2 | Yes | 🔧 Sistema |  |
| `CANTON` | Canton | String | 4 | Yes | 🔧 Sistema |  |
| `PARROQUIA` | PARROQUIA | String | 6 | Yes | 🔧 Sistema |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | 🔧 Sistema |  |
| `SUBTIPO` | Subtipo | Integer | 4 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `TEXTOETIQUETA` | Texto Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `HIPERVINCULO` | Hipervinculo | String | 255 | Yes | 🔧 Sistema |  |
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
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `CODIGOESTRUCTURA` |  | [Estructura Pararrayo](01_Dominios.md#estructura-pararrayo) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `SUBTIPO` | 2 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |

**Descargador (SUBTIPO=2) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [Estructura Pararrayo](01_Dominios.md#estructura-pararrayo) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |

**Puesta a Tierra (SUBTIPO=1)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PUESTA_TIERRA](01_Dominios.md#uppuestatierra) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G249CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G249MIGUID | MIGUID | No | Yes |
| I249ALIMENTADOR | ALIMENTADOR | No | Yes |
| I249HIPERVINCULO | HIPERVINCULO | No | Yes |

</details>

### Relaciones donde participa (1)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_Pararrayos](02_Relaciones.md#catestrucpararrayos) | Destino | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | One To Many |

---

## `PuestoTransfDistribucion` — Puesto TransfDistribucion
<a id="puestotransfdistribucion"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple Junction) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Junction** (punto de conexión) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 68 total — ✅ 26 core · 🔌 4 conectividad · 🔧 14 sistema · ▫️ 24 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object Id | OID | 4 | No | 🔧 Sistema |  |
| `ANCILLARYROLE` | ANCILLARYROLE | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ENABLED` | Enabled | Small Integer | 2 | Yes | ✅ CORE | True |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 24/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Inform Alim | Integer | 4 | Yes | ▫️ Otro |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | PMD |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 01/04/2019 |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | Propio |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Milagro |
| `SUBTIPO` | Subtipo | Integer | 4 | Yes | ✅ CORE | Transformador Monofásico en Poste |
| `CODIGOPUESTO` | Codigo Puesto | String | 20 | Yes | ▫️ Otro |  |
| `TEXTOETIQUETA` | Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `FASECONEXION` | Fase Conexión | Integer | 4 | Yes | ✅ CORE | C |
| `VOLTAJE` | Voltaje | Integer | 4 | Yes | ✅ CORE | 7.96KV |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `RESISTENCIATIERRA` | Resistencia Tierra | Double | 8 | Yes | ▫️ Otro |  |
| `PROTECCIONLADOALTA` | Proteccion AT | String | 5 | Yes | ▫️ Otro |  |
| `POTENCIAKVA` | Potencia (kva) | Double | 8 | Yes | ✅ CORE | 15 |
| `CONFIGURACIONLADOBAJA` | Configuración BT | String | 2 | Yes | ✅ CORE | Línea Monofásica |
| `PROTECCIONLADOBAJA` | Proteccion BT | String | 20 | Yes | ▫️ Otro |  |
| `ESTRUCTURASOPORTEOBJECTID` | Estructura Soporte OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURANIVELOBJECTID` | Estructura Nivel OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURASUBTERRANEAOBJECTID` | Estructura Subterranea OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `TRAFO` | No.Transf. | String | 50 | Yes | ✅ CORE | 45678 |
| `PARROQUIA` | Parroquia | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `PROPIEDAD` | Propiedad | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `MEDIDO` | MEDIDO | Small Integer | 2 | Yes | ✅ CORE | Si |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ✅ CORE | 1A15T |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `ESTRUCTURANIVELGLOBALID` | EstructuraNivelGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURASUBTERRANEAGLOBALID` | ESTRUCTURASUBTERRANEAGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURASOPORTEGLOBALID` | EstructuraSoporteGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador 2 | String | 10 | Yes | ▫️ Otro |  |
| `VOLTAJESECUNDARIO` | Voltaje Secundario | Integer | 4 | Yes | ✅ CORE | 240V |
| `CONFIGURACIONLADOMEDIA` | Conf. Lado Media | String | 2 | Yes | ▫️ Otro |  |
| `CIRCUITSOURCEGUID` | CircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `SUBSOURCE` | Subsource | Small Integer | 2 | Yes | ✅ CORE | Si |
| `TIPO` | Tipo | Small Integer | 2 | Yes | ✅ CORE | Distribución |
| `CARGABILIDAD` | Cargabilidad(%) | Double | 8 | Yes | ▫️ Otro |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `FACILITYID` | FACILITYID | String | 10 | Yes | ▫️ Otro |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `CODIGOADMS` | CODIGOADMS | String | 100 | Yes | ▫️ Otro |  |
| `TOTALLUMINARIAS` | TOTALLUMINARIAS | Integer | 4 | Yes | ▫️ Otro |  |
| `SUMAPOTENCIALUMINARIAS` | SUMAPOTENCIALUMINARIAS | Double | 8 | Yes | ▫️ Otro |  |
| `TOTALCLIENTES` | TOTALCLIENTES | Integer | 4 | Yes | ▫️ Otro |  |
| `SUMACONSUMO` | SUMACONSUMO | Double | 8 | Yes | ▫️ Otro |  |
| `TIPORED` | TIPORED | String | 20 | Yes | ✅ CORE | Preensamblado |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | OT-9834 |
| `CIRCUITOS` | Circuitos | String | 3 | Yes | ✅ CORE | F12 |
| `SECUENCIAFASE` | Fase de Bajo Voltaje | String | 3 | Yes | ✅ CORE | c |

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
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `SUBSOURCE` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `TIPO` | 1 | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |

**Banco de 2 Transformadores en Cabina (Subtipo=10)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_BANCO_2_CABINA](01_Dominios.md#uptrfbanco2cabina) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 4 | — |
| `TIPO` |  | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Banco de 2 Transformadores en Poste (Subtipo=9)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_BANCO_2_POSTE](01_Dominios.md#uptrfbanco2poste) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 4 | — |
| `TIPO` |  | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Banco de 3 Transformadores en Cabina (Subtipo=12)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_BANCO_3_CABINA](01_Dominios.md#uptrfbanco3cabina) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 4 | — |
| `TIPO` |  | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Banco de 3 Transformadores en Poste (Subtipo=11)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_BANCO_3_POSTE](01_Dominios.md#uptrfbanco3poste) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 4 | — |
| `TIPO` |  | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Padmounted Bifásico en Cabina (Subtipo=16)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_2F_PAD_EXT](01_Dominios.md#uptrf2fpadext) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBSOURCE` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `TIPO` | 1 | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Padmounted Bifásico Exterior (Subtipo=15)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_2F_PAD_EXT](01_Dominios.md#uptrf2fpadext) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBSOURCE` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `TIPO` | 1 | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Padmounted Monofásico en Cabina (Subtipo=4)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_1F_PAD_EXT](01_Dominios.md#uptrf1fpadext) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 4 | — |
| `TIPO` |  | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Padmounted Monofásico Exterior (Subtipo=3)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_1F_PAD_EXT](01_Dominios.md#uptrf1fpadext) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 4 | — |
| `TIPO` |  | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Padmounted Trifásico en Cabina (Subtipo=8)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_3F_PAD_EXT](01_Dominios.md#uptrf3fpadext) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 4 | — |
| `TIPO` |  | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Padmounted Trifásico Exterior (Subtipo=7)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_3F_PAD_EXT](01_Dominios.md#uptrf3fpadext) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 4 | — |
| `TIPO` |  | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Transformador Bifásico en Cabina (Subtipo=14)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_2F_CABINA](01_Dominios.md#uptrf2fcabina) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBSOURCE` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 1 | — |
| `TIPO` |  | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Transformador Bifásico en Poste (Subtipo=13)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_2F_POSTE](01_Dominios.md#uptrf2fposte) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBSOURCE` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 1 | — |
| `TIPO` |  | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Transformador Monofásico en Cabina (Subtipo=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_1F_CABINA](01_Dominios.md#uptrf1fcabina) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 4 | — |
| `TIPO` |  | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Transformador Monofásico en Poste (Subtipo=1) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_1F_POSTE](01_Dominios.md#uptrf1fposte) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Fase Conexion Monofasica](01_Dominios.md#fase-conexion-monofasica) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `POTENCIAKVA` | 25 | — |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 1 | — |
| `TIPO` |  | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Transformador Trifásico en Cabina (Subtipo=6)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_3F_CABINA](01_Dominios.md#uptrf3fcabina) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 4 | — |
| `TIPO` |  | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

**Transformador Trifásico en Poste (Subtipo=5)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_3F_POSTE](01_Dominios.md#uptrf3fposte) |
| `CONFIGURACIONLADOBAJA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONLADOMEDIA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `MEDIDO` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` | CNELGYE | [Propietario](01_Dominios.md#propietario) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROTECCIONLADOBAJA` |  | [Proteccion Puesto Baja Tension](01_Dominios.md#proteccion-puesto-baja-tension) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `SUBTIPO` | 4 | — |
| `TIPO` |  | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `TIPORED` |  | [PT_TipoRed](01_Dominios.md#pttipored) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G223ESTRUCTURASO | ESTRUCTURASOPORTEGLOBALID | No | Yes |
| G223MIGUID | MIGUID | No | Yes |
| I223ALIMENTADOR | ALIMENTADOR | No | Yes |
| I223ALIMENTADOR2 | ALIMENTADOR2ID | No | Yes |
| I223ALIMENTADORI | ALIMENTADORID | No | Yes |

</details>

### Relaciones donde participa (10)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [EstrucNivel_PuestoTransDist](02_Relaciones.md#estrucnivelpuestotransdist) | Destino | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | One To Many |
| [EstrucSop_PuestoTransDist](02_Relaciones.md#estrucsoppuestotransdist) | Destino | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | One To Many |
| [PuestoTransDist_Luminaria](02_Relaciones.md#puestotransdistluminaria) | Origen | [`Luminaria`](06_Clases_Consumidores_y_Alumbrado.md#luminaria) | One To Many |
| [PuestoTransDist_PuestoProtBT](02_Relaciones.md#puestotransdistpuestoprotbt) | Origen | [`PuestoProteccionBajaTension`](#puestoproteccionbajatension) | One To Many |
| [PuestoTransDist_PuestoSeccFus](02_Relaciones.md#puestotransdistpuestoseccfus) | Origen | [`PuestoSeccionadorFusible`](#puestoseccionadorfusible) | One To Many |
| [PuestoTransDist_PuntoCarga](02_Relaciones.md#puestotransdistpuntocarga) | Origen | [`PuntoCarga`](06_Clases_Consumidores_y_Alumbrado.md#puntocarga) | One To Many |
| [PuestoTransDist_Semaforo](02_Relaciones.md#puestotransdistsemaforo) | Origen | [`Semaforo`](06_Clases_Consumidores_y_Alumbrado.md#semaforo) | One To Many |
| [PuestoTransDist_TramoBTA](02_Relaciones.md#puestotransdisttramobta) | Origen | [`TramoBajaTensionAereo`](03_Clases_Redes_y_Soporte.md#tramobajatensionaereo) | One To Many |
| [PuestoTransDist_TramoBTS](02_Relaciones.md#puestotransdisttramobts) | Origen | [`TramoBajaTensionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramobajatensionsubterraneo) | One To Many |
| [PuestoTransDist_UnidadTransDist](02_Relaciones.md#puestotransdistunidadtransdist) | Origen | [`UNIDADTRANSFDISTRIBUCION`](#unidadtransfdistribucion) | One To Many |

---

## `UNIDADTRANSFDISTRIBUCION` — Transformador
<a id="unidadtransfdistribucion"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 47 total — ✅ 26 core · 🔌 0 conectividad · 🔧 10 sistema · ▫️ 11 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object ID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 24/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | PMD |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | F Activacion | Date | 8 | Yes | ✅ CORE | 01/04/2019 |
| `PROYECTOMODIFICACION` | Proyecto Mod | String | 32 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACION` | F Modificacion | Date | 8 | Yes | ▫️ Otro |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Milagro |
| `MODELO` | Modelo | String | 20 | Yes | ▫️ Otro |  |
| `NUMEROSERIE` | No Serie | String | 20 | Yes | ✅ CORE | SE234622 |
| `MARCA` | Marca | String | 5 | Yes | ✅ CORE | Ecuatran |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ✅ CORE | C |
| `CODIGOUNIDAD` | Codigo Unidad | String | 20 | Yes | ✅ CORE | 45678 |
| `POTENCIANOMINAL` | Potencia (kva) | String | 255 | Yes | ✅ CORE | 15KVA |
| `TENSIONLADOALTA` | Tension AT | Integer | 4 | Yes | ✅ CORE | 7.96KV |
| `PUESTOTRANSFDISTOBJECTID` | Puesto Transformador Distribucion OID | Integer | 4 | Yes | ▫️ Otro |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ✅ CORE | 1A15T |
| `CODIGUNI` | CODIGUNI | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTADO` | Estado | Small Integer | 2 | Yes | ▫️ Otro |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PUESTOTRANSFDISTGLOBALID` | PUESTOTRANSFDISTGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `TAPNEUTRAL` | Tap Neutral | Small Integer | 2 | Yes | ✅ CORE | 3 |
| `TAPNORMAL` | Tap Normal | Small Integer | 2 | Yes | ✅ CORE | 3 |
| `NUMEROTAPS` | Tap Numero | Small Integer | 2 | Yes | ✅ CORE | 5 |
| `TAPPORCENTAJE` | Tap Porcentaje | Small Integer | 2 | Yes | ✅ CORE | 2.5 |
| `PARROQUIA` | Parroquia | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `MIESTADO` | MIESTADO | String | 20 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `EXISTENOVEDAD` | Existe Novedad | Small Integer | 2 | Yes | ▫️ Otro |  |
| `TIPOTAP` | Tipo TAP | String | 3 | Yes | ✅ CORE | 2arriba/2abajo |
| `MITRFCOD` | MITRFCOD | String | 20 | Yes | ▫️ Otro |  |
| `MITRF_OID` | MITRF_OID | String | 20 | Yes | ▫️ Otro |  |
| `PCB` | PCB | String | 10 | Yes | ✅ CORE | No |
| `PROPIEDAD` | Propiedad | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `TIPO` | Tipo Trafo | Small Integer | 2 | Yes | ▫️ Otro |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | OT-9834 |
| `CIRCUITOS` | Circuitos | String | 3 | Yes | ✅ CORE | F12 |
| `SECUENCIAFASE` | Fase de Bajo Voltaje | String | 3 | Yes | ✅ CORE | c |
| `VOLTAJESECUNDARIO` | Voltaje Secundario BT | Integer | 4 | Yes | ✅ CORE | 240V |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `MARCA` |  | [Marcas](01_Dominios.md#marcas) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `POTENCIANOMINAL` |  | [Potencia Nominal Transformador Distribucion](01_Dominios.md#potencia-nominal-transformador-distribucion) |
| `TENSIONLADOALTA` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_TODOS](01_Dominios.md#uptrftodos) |
| `ESTADO` |  | [Estado](01_Dominios.md#estado) |
| `TAPNEUTRAL` | 3 | [Tap Neutral](01_Dominios.md#tap-neutral) |
| `TAPNORMAL` | 3 | [Tap Normal](01_Dominios.md#tap-normal) |
| `NUMEROTAPS` | 5 | [Taps Numero](01_Dominios.md#taps-numero) |
| `TAPPORCENTAJE` | 25 | [Tap Porcentaje](01_Dominios.md#tap-porcentaje) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `EXISTENOVEDAD` |  | [ExisteNovedad](01_Dominios.md#existenovedad) |
| `TIPOTAP` | 22 | [Tipo de Tap Transformador Unidad](01_Dominios.md#tipo-de-tap-transformador-unidad) |
| `PCB` |  | [PCB](01_Dominios.md#pcb) |
| `PROPIEDAD` |  | [Propietario](01_Dominios.md#propietario) |
| `TIPO` |  | [TipoTrafo](01_Dominios.md#tipotrafo) |
| `CIRCUITOS` |  | [Circuito BV](01_Dominios.md#circuito-bv) |
| `SECUENCIAFASE` |  | [Secuencia Fase BV](01_Dominios.md#secuencia-fase-bv) |
| `VOLTAJESECUNDARIO` |  | [Voltaje BT](01_Dominios.md#voltaje-bt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G214CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G214MIGUID | MIGUID | No | Yes |
| G214PUESTOTRANSF | PUESTOTRANSFDISTGLOBALID | No | Yes |

</details>

### Relaciones donde participa (2)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_UnidadTransDistribucion](02_Relaciones.md#catestrucunidadtransdistribucion) | Destino | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | One To Many |
| [PuestoTransDist_UnidadTransDist](02_Relaciones.md#puestotransdistunidadtransdist) | Destino | [`PuestoTransfDistribucion`](#puestotransfdistribucion) | One To Many |

---

## `PuestoTransfPotencia` — Puesto Transfo Potencia
<a id="puestotransfpotencia"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple Junction) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Junction** (punto de conexión) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 60 total — ✅ 16 core · 🔌 5 conectividad · 🔧 15 sistema · ▫️ 24 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object Id | OID | 4 | No | 🔧 Sistema |  |
| `ANCILLARYROLE` | ANCILLARYROLE | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ENABLED` | Enabled | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 24/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | PMD |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 01/04/2019 |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | AFD |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Milagro |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | ✅ CORE | Transformador con 2 devanados |
| `CODIGOPUESTO` | Codigo Puesto | String | 20 | Yes | ▫️ Otro |  |
| `TEXTOETIQUETA` | Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ✅ CORE | ABC |
| `VOLTAJE` | Voltaje | Integer | 4 | Yes | ✅ CORE | 69KV |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `CODIGOESTRUCTURA` | CODIGOESTRUCTURA | String | 10 | Yes | ▫️ Otro |  |
| `RESISTENCIATIERRA` | R Tierra | Double | 8 | Yes | ▫️ Otro |  |
| `POTENCIAKVA` | Potencia KVA | Double | 8 | Yes | ✅ CORE | 16000 |
| `ESTRUCTURANIVELOBJECTID` | Estructura Nivel OID | Integer | 4 | Yes | ▫️ Otro |  |
| `SUBESTACIONOBJECTID` | Subestacion OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `PARROQUIA` | PARROQUIA | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PROTECCIONLADOSUBTRA` | PROTECCIONLADOSUBTRA | String | 5 | Yes | ▫️ Otro |  |
| `CONFIGURACIONLADOMEDIA` | Configuracion MT | String | 2 | Yes | ✅ CORE | Estrella |
| `PROTECCIONLADOMEDIA` | Proteccion MT | String | 20 | Yes | ▫️ Otro |  |
| `COLOR` | Color | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURASUBTERRANEAOBJECTID` | Estrctura Subterranea OID | Integer | 4 | Yes | ▫️ Otro |  |
| `TRAFO` | No. Transf. | Integer | 4 | Yes | ▫️ Otro |  |
| `PROPIEDAD` | Propiedad | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `MEDIDO` | Medido | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURASUBTERRANEAGLOBALID` | Estrcutura Subterranea GUID | GUID | 38 | Yes | ▫️ Otro |  |
| `ALIMENTADORID` | Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Inform Alim | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `ESTRUCTURANIVELGLOBALID` | Estructura Nivel Guid | GUID | 38 | Yes | ▫️ Otro |  |
| `SUBESTACIONGLOBALID` | Subestación Guid | GUID | 38 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre ALimentador 2 | String | 10 | Yes | ▫️ Otro |  |
| `VOLTAJESECUNDARIO` | Voltaje Secundario | Integer | 4 | Yes | ✅ CORE | 13.8KV |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `CIRCUITSOURCEGUID` | CircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `SUBSOURCE` | Subsource | Small Integer | 2 | Yes | ▫️ Otro |  |
| `TIPO` | Tipo Uso Tramo | Small Integer | 2 | Yes | ▫️ Otro |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `FACILITYID` | FACILITYID | String | 10 | Yes | ▫️ Otro |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `CODIGOADMS` | CODIGOADMS | String | 100 | Yes | ▫️ Otro |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | 🔧 Sistema |  |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `CODIGOEMPRESA` |  | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` |  | [Provincias](01_Dominios.md#provincias) |
| `CANTON` |  | [Cantones](01_Dominios.md#cantones) |
| `SUBTIPO` | 1 | — |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `VOLTAJE` |  | [Voltaje AT](01_Dominios.md#voltaje-at) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROPIEDAD` |  | [Propietario](01_Dominios.md#propietario) |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `VOLTAJESECUNDARIO` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |
| `SUBSOURCE` | 0 | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `TIPO` |  | [TipoTrafoPotencia](01_Dominios.md#tipotrafopotencia) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Autotransformador con 2 devanados (SUBTIPO=2)**

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
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `TIPO` |  | [TipoTrafoPotencia](01_Dominios.md#tipotrafopotencia) |
| `VOLTAJE` |  | [Voltaje AT](01_Dominios.md#voltaje-at) |
| `VOLTAJESECUNDARIO` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Autransformador con 3 devanados (SUBTIPO=4)**

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
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `TIPO` |  | [TipoTrafoPotencia](01_Dominios.md#tipotrafopotencia) |
| `VOLTAJE` |  | [Voltaje AT](01_Dominios.md#voltaje-at) |
| `VOLTAJESECUNDARIO` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Transformador con 2 devanados (SUBTIPO=1) [Default]**

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
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `TIPO` |  | [TipoTrafoPotencia](01_Dominios.md#tipotrafopotencia) |
| `VOLTAJE` |  | [Voltaje AT](01_Dominios.md#voltaje-at) |
| `VOLTAJESECUNDARIO` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Transformador con 3 devanados (SUBTIPO=3)**

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
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBSOURCE` |  | [Indicador Si-No (entero)](01_Dominios.md#indicador-si-no-entero) |
| `TIPO` |  | [TipoTrafoPotencia](01_Dominios.md#tipotrafopotencia) |
| `VOLTAJE` |  | [Voltaje AT](01_Dominios.md#voltaje-at) |
| `VOLTAJESECUNDARIO` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G238CIRCUITSOURC | CIRCUITSOURCEGUID | No | Yes |
| G238CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G238ESTRUCTURANI | ESTRUCTURANIVELGLOBALID | No | Yes |
| G238ESTRUCTURASU | ESTRUCTURASUBTERRANEAGLOBALID | No | Yes |
| G238MIGUID | MIGUID | No | Yes |
| G238PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |
| G238SUBESTACIONG | SUBESTACIONGLOBALID | No | Yes |
| G238SUBESTACIONO | SUBESTACIONOBJECTID | No | Yes |

</details>

### Relaciones donde participa (5)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [EstrucNivel_PuestoTransPot](02_Relaciones.md#estrucnivelpuestotranspot) | Destino | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | One To Many |
| [PuestoTransPot_TramoSTA](02_Relaciones.md#puestotranspottramosta) | Origen | [`TramoSubtransmisionAereo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionaereo) | One To Many |
| [PuestoTransPot_TramoSTS](02_Relaciones.md#puestotranspottramosts) | Origen | [`TramoSubtransmisionSubterraneo`](03_Clases_Redes_y_Soporte.md#tramosubtransmisionsubterraneo) | One To Many |
| [PuestoTransPot_UnidadTransPot](02_Relaciones.md#puestotranspotunidadtranspot) | Origen | [`UNIDADTRANSFPOTENCIA`](#unidadtransfpotencia) | One To Many |
| [Subestacion_PuestoTransfPot](02_Relaciones.md#subestacionpuestotransfpot) | Destino | [`Subestacion`](05_Clases_Generacion_Subestaciones_Fuentes.md#subestacion) | One To Many |

---

## `UNIDADTRANSFPOTENCIA` — Transformador Potencia
<a id="unidadtransfpotencia"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 37 total — ✅ 13 core · 🔌 0 conectividad · 🔧 12 sistema · ▫️ 12 otros |

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
| `FECHAACTIVACION` | F Activacion | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | Proyecto Mod | String | 32 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACION` | F Modificacion | Date | 8 | Yes | ▫️ Otro |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Milagro |
| `MODELO` | Modelo | String | 20 | Yes | ▫️ Otro |  |
| `NUMEROSERIE` | No Serie | String | 20 | Yes | ✅ CORE | AC-347321 |
| `MARCA` | Marca | String | 5 | Yes | ✅ CORE | ABB |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ✅ CORE | ABC |
| `CODIGOUNIDAD` | Codigo Unidad | String | 20 | Yes | ▫️ Otro |  |
| `POTENCIANOMINAL` | Potencia (kva) | String | 255 | Yes | ✅ CORE | 16.000KVA |
| `TENSIONLADOALTA` | Tension AT | Integer | 4 | Yes | ✅ CORE | 69KV |
| `PUESTOTRANSFPOTOBJECTID` | Puesto Transformador Potencia OID | Integer | 4 | Yes | ▫️ Otro |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ▫️ Otro |  |
| `ESTADO` | Estado | Small Integer | 2 | Yes | ▫️ Otro |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PUESTOTRANSFPOTGLOBALID` | Puesto Transf. Potencia Guid | GUID | 38 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `MIESTADO` | MIESTADO | String | 20 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `EXISTENOVEDAD` | Existe Novedad | Small Integer | 2 | Yes | ▫️ Otro |  |
| `MITRFCOD` | MITRFCOD | String | 20 | Yes | ▫️ Otro |  |
| `MITRF_OID` | MITRF_OID | String | 20 | Yes | ▫️ Otro |  |
| `CODIGUNI` | CODIGUNI | Integer | 4 | Yes | ▫️ Otro |  |
| `POTENCIAFORZADA` | POTENCIAFORZADA | String | 50 | Yes | ✅ CORE | 20.000KVA |
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
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `POTENCIANOMINAL` |  | [Potencia Nominal Transformador Potencia Unidad](01_Dominios.md#potencia-nominal-transformador-potencia-unidad) |
| `TENSIONLADOALTA` |  | [Voltaje AT](01_Dominios.md#voltaje-at) |
| `CODIGOESTRUCTURA` |  | [UP_TRF_TODOS](01_Dominios.md#uptrftodos) |
| `ESTADO` |  | [Estado](01_Dominios.md#estado) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `EXISTENOVEDAD` |  | [ExisteNovedad](01_Dominios.md#existenovedad) |
| `POTENCIAFORZADA` |  | [Potencia Nominal Transformador Potencia Unidad](01_Dominios.md#potencia-nominal-transformador-potencia-unidad) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G215CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G215MIGUID | MIGUID | No | Yes |
| G215PUESTOTRANSF | PUESTOTRANSFPOTGLOBALID | No | Yes |

</details>

### Relaciones donde participa (2)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_UnidadTransPotencia](02_Relaciones.md#catestrucunidadtranspotencia) | Destino | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | One To Many |
| [PuestoTransPot_UnidadTransPot](02_Relaciones.md#puestotranspotunidadtranspot) | Destino | [`PuestoTransfPotencia`](#puestotransfpotencia) | One To Many |

---

## `PuestoReguladorTension` — Regulador Tension
<a id="puestoreguladortension"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple Junction) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Junction** (punto de conexión) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 51 total — ✅ 19 core · 🔌 3 conectividad · 🔧 14 sistema · ▫️ 15 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object ID | OID | 4 | No | 🔧 Sistema |  |
| `ANCILLARYROLE` | ANCILLARYROLE | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ENABLED` | ENABLED | Small Integer | 2 | Yes | ✅ CORE | true |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 20/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | Alim1 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Inform Alim | Integer | 4 | Yes | ▫️ Otro |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | PMD |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 01/03/2019 |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | AFD |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Milagro |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | ✅ CORE | Regulador Tensión Trifásico |
| `CODIGOPUESTO` | Codigo Puesto | String | 20 | Yes | ✅ CORE | 18/05/2058 |
| `TEXTOETIQUETA` | Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ✅ CORE | ABC |
| `VOLTAJE` | Voltaje | Integer | 4 | Yes | ✅ CORE | 13.8KV |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `CODIGOESTRUCTURA` | CODIGOESTRUCTURA | String | 10 | Yes | ✅ CORE | C3RM300T |
| `RESISTENCIATIERRA` | Resistencia Tierra | Double | 8 | Yes | ▫️ Otro |  |
| `PROTECCIONLADOALTA` | Proteccion AT | String | 5 | Yes | ▫️ Otro |  |
| `POTENCIAKVA` | Potencia KVA | Double | 8 | Yes | ▫️ Otro |  |
| `INTERRUPTORBYPASS` | Interruptor By Pass | String | 5 | Yes | ▫️ Otro |  |
| `ESTRUCTURASOPORTEOBJECTID` | Estructura Soporte OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURANIVELOBJECTID` | Estructura Nivel OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `PARROQUIA` | PARROQUIA | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `ESTRUCTURANIVELGLOBALID` | EstructuraNivelGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURASOPORTEGLOBALID` | EstructuraSoporteGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre Alimentador | String | 10 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `CONFIGURACIONENTRADA` | Configuración Entrada | String | 5 | Yes | ✅ CORE | Estrella |
| `CONFIGURACIONSALIDA` | Configuración Salida | String | 5 | Yes | ✅ CORE | Estrella |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador 2 | String | 10 | Yes | ▫️ Otro |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `CODIGOADMS` | CODIGOADMS | String | 100 | Yes | ▫️ Otro |  |
| `CONTROL` | CONTROL | String | 30 | Yes | ✅ CORE | Manual |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | OT-3457 |

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
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `INTERRUPTORBYPASS` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `CONFIGURACIONENTRADA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONSALIDA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `CONTROL` |  | [P_Control](01_Dominios.md#pcontrol) |

**Regulador Tension Bifasico (Subtipo=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PR_2F](01_Dominios.md#uppr2f) |
| `CONFIGURACIONENTRADA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONSALIDA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONTROL` |  | [P_Control](01_Dominios.md#pcontrol) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `INTERRUPTORBYPASS` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Regulador Tension Monofasico (Subtipo=1) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PR_1F](01_Dominios.md#uppr1f) |
| `CONFIGURACIONENTRADA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONSALIDA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONTROL` |  | [P_Control](01_Dominios.md#pcontrol) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `INTERRUPTORBYPASS` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Regulador Tension Trifasico (Subtipo=3)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PR_3F](01_Dominios.md#uppr3f) |
| `CONFIGURACIONENTRADA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONFIGURACIONSALIDA` |  | [Config Lado Baja Banco Transf](01_Dominios.md#config-lado-baja-banco-transf) |
| `CONTROL` |  | [P_Control](01_Dominios.md#pcontrol) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `INTERRUPTORBYPASS` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROTECCIONLADOALTA` | S | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G231CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G231ESTRUCTURANI | ESTRUCTURANIVELGLOBALID | No | Yes |
| G231ESTRUCTURASO | ESTRUCTURASOPORTEGLOBALID | No | Yes |
| G231MIGUID | MIGUID | No | Yes |
| G231PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |

</details>

### Relaciones donde participa (3)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [EstrucNivel_PuestoRegTens](02_Relaciones.md#estrucnivelpuestoregtens) | Destino | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | One To Many |
| [EstrucSop_PuestoRegTens](02_Relaciones.md#estrucsoppuestoregtens) | Destino | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | One To Many |
| [PuestoRegTens_UnidadRegTens](02_Relaciones.md#puestoregtensunidadregtens) | Origen | [`UNIDADREGULADORTENSION`](#unidadreguladortension) | One To Many |

---

## `UNIDADREGULADORTENSION` — Regulador de Tension
<a id="unidadreguladortension"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 38 total — ✅ 17 core · 🔌 0 conectividad · 🔧 11 sistema · ▫️ 10 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object ID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 20/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | 🔧 Sistema |  |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | F Activacion | Date | 8 | Yes | ✅ CORE | 01/03/2019 |
| `PROYECTOMODIFICACION` | Proyecto Mod | String | 32 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACION` | F Modificacion | Date | 8 | Yes | ▫️ Otro |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Milagro |
| `MODELO` | MODELO | String | 20 | Yes | ▫️ Otro |  |
| `NUMEROSERIE` | Serie | String | 20 | Yes | ▫️ Otro |  |
| `MARCA` | Marca | String | 5 | Yes | ✅ CORE | ABB |
| `FASECONEXION` | F Conexion | Integer | 4 | Yes | ✅ CORE | A |
| `CODIGOUNIDAD` | Codigo Unidad | String | 20 | Yes | ▫️ Otro |  |
| `PUESTOREGTENSOBJECTID` | Reg Tension OID | Integer | 4 | Yes | ▫️ Otro |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ✅ CORE | C1RM100T |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PUESTOREGTENSGLOBALID` | PuestoRegTensGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | ✅ CORE | Roberto Astudillo |
| `ESTADO` | Estado | Small Integer | 2 | Yes | ▫️ Otro |  |
| `MIESTADO` | MIESTADO | String | 20 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `EXISTENOVEDAD` | Existe Novedad | Small Integer | 2 | Yes | ▫️ Otro |  |
| `TAPNORMAL` | Tap Normal | Small Integer | 2 | Yes | ✅ CORE | 16 |
| `TAPNEUTRAL` | Tap Neutral | Small Integer | 2 | Yes | ✅ CORE | 16 |
| `NUMEROTAPS` | Tap Numero | Small Integer | 2 | Yes | ✅ CORE | 32 |
| `TAPPORCENTAJE` | Tap Porcentaje | Small Integer | 2 | Yes | ✅ CORE | 0.625 |
| `TIPOTAP` | Tipo Tap | String | 3 | Yes | ✅ CORE | 16 arriba/16 abajo |
| `CODIGOADMS` | CODIGOADMS | String | 100 | Yes | ▫️ Otro |  |
| `POTENCIANOMINAL` | Potencia (Kva) | String | 50 | Yes | ✅ CORE | 100 |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | OT-3732 |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `MARCA` |  | [Marcas](01_Dominios.md#marcas) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `CODIGOESTRUCTURA` |  | [UP_PR_TODOS](01_Dominios.md#upprtodos) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `ESTADO` |  | [Estado](01_Dominios.md#estado) |
| `EXISTENOVEDAD` |  | [ExisteNovedad](01_Dominios.md#existenovedad) |
| `TAPNORMAL` |  | [Tap Normal](01_Dominios.md#tap-normal) |
| `TAPNEUTRAL` |  | [Tap Neutral](01_Dominios.md#tap-neutral) |
| `NUMEROTAPS` |  | [Taps Numero](01_Dominios.md#taps-numero) |
| `TAPPORCENTAJE` |  | [Tap Porcentaje](01_Dominios.md#tap-porcentaje) |
| `TIPOTAP` |  | [Tipo de Tap Transformador Unidad](01_Dominios.md#tipo-de-tap-transformador-unidad) |
| `POTENCIANOMINAL` |  | [Capacidad Regulador Tension Unidad](01_Dominios.md#capacidad-regulador-tension-unidad) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G213CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G213MIGUID | MIGUID | No | Yes |
| G213PUESTOREGTEN | PUESTOREGTENSOBJECTID | No | Yes |
| G213PUESTOREGTEN_1 | PUESTOREGTENSGLOBALID | No | Yes |

</details>

### Relaciones donde participa (2)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_UnidadReguladorTension](02_Relaciones.md#catestrucunidadreguladortension) | Destino | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | One To Many |
| [PuestoRegTens_UnidadRegTens](02_Relaciones.md#puestoregtensunidadregtens) | Destino | [`PuestoReguladorTension`](#puestoreguladortension) | One To Many |

---

## `PuestoCorrectorFactorPotencia` — Capacitor
<a id="puestocorrectorfactorpotencia"></a>

| | |
|---|---|
| **Tipo de dataset** | FeatureClass |
| **Geometría** | Point (Simple Junction) |
| **Red geométrica `Electrico_RedGeom`** | Participa como **Junction** (punto de conexión) |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 48 total — ✅ 18 core · 🔌 3 conectividad · 🔧 14 sistema · ▫️ 13 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | OBJECT ID | OID | 4 | No | 🔧 Sistema |  |
| `ANCILLARYROLE` | ANCILLARYROLE | Small Integer | 2 | Yes | 🔌 Conectividad |  |
| `ENABLED` | Enabled | Small Integer | 2 | Yes | ✅ CORE | true |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 20/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `ELECTRICTRACEWEIGHT` | Electric Trace Weight | Integer | 4 | Yes | 🔌 Conectividad |  |
| `ALIMENTADORID` | Alim 1 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADOR2ID` | Alim2 | String | 10 | Yes | ▫️ Otro |  |
| `ALIMENTADORINFO` | Inform Alim | Integer | 4 | Yes | ▫️ Otro |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | ✅ CORE | PMD |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | FECHAENERGIZACION | Date | 8 | Yes | ✅ CORE | 01/03/2019 |
| `PROYECTOMODIFICACION` | FINANCIAMIENTO | String | 32 | Yes | ✅ CORE | Propio |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Naranjito |
| `SUBTIPO` | SUBTIPO | Integer | 4 | Yes | ✅ CORE | Capacitor Fijo |
| `CODIGOPUESTO` | Codigo del Puesto | String | 20 | Yes | ✅ CORE | 76538 |
| `TEXTOETIQUETA` | Etiqueta | String | 255 | Yes | 🔧 Sistema |  |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ✅ CORE | ABC |
| `VOLTAJE` | Voltaje | Integer | 4 | Yes | ✅ CORE | 13.8KV |
| `HIPERVINCULO` | HIPERVINCULO | String | 255 | Yes | 🔧 Sistema |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ✅ CORE | C3C300T |
| `CONFIGURACIONCONEXION` | Configuracion Conexion | String | 3 | Yes | ✅ CORE | Estrella |
| `ESTRUCTURASOPORTEOBJECTID` | ESTRUCTURA SOPORTE OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURANIVELOBJECTID` | ESTRUCTURA NIVEL OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ESTRUCTURASUBTERRANEAOBJECTID` | ESTRUCTURA SUBTERRANEA OID | Integer | 4 | Yes | ▫️ Otro |  |
| `ROTACIONSIMBOLO` | ROTACIONSIMBOLO | Double | 8 | Yes | ▫️ Otro |  |
| `POTENCIAKVA` | Potencia KVAr | Double | 8 | Yes | ✅ CORE | 600 |
| `PARROQUIA` | Parroquia | String | 6 | Yes | ✅ CORE | Naranjito |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `ESTRUCTURANIVELGLOBALID` | EstructuraNivelGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURASUBTERRANEAGLOBALID` | ESTRUCTURASUBTERRANEAGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `ESTRUCTURASOPORTEGLOBALID` | EstructuraSoporteGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `PARENTCIRCUITSOURCEGUID` | ParentCircuitSourceGUID | GUID | 38 | Yes | 🔌 Conectividad |  |
| `ALIMENTADOR` | Nombre alimentador | String | 10 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `ALIMENTADOR2` | Nombre Alimentador2 | String | 10 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | Comentarios | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `SHAPE` | Shape | Geometry | 0 | Yes | 🔧 Sistema |  |
| `MISUBTIPO` | MISUBTIPO | Integer | 4 | Yes | 🔧 Sistema |  |
| `TRANSFERENCIAACTIVO` | TRANSFERENCIAACTIVO | String | 2 | Yes | 🔧 Sistema |  |
| `CODIGOADMS` | CODIGOADMS | String | 100 | Yes | ▫️ Otro |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | OT-1237 |

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
| `CONFIGURACIONCONEXION` |  | [Configuracion Conexion](01_Dominios.md#configuracion-conexion) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `TRANSFERENCIAACTIVO` |  | [Indicador Si-No](01_Dominios.md#indicador-si-no) |

**Capacitor Automatico (Subtipo=2)**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PC_Automatico](01_Dominios.md#uppcautomatico) |
| `CONFIGURACIONCONEXION` |  | [Configuracion Conexion](01_Dominios.md#configuracion-conexion) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

**Capacitor Fijo (Subtipo=1) [Default]**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `ALIMENTADOR` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADOR2ID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `ALIMENTADORID` |  | [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `CODIGOESTRUCTURA` |  | [UP_PC_Fijo](01_Dominios.md#uppcfijo) |
| `CONFIGURACIONCONEXION` |  | [Configuracion Conexion](01_Dominios.md#configuracion-conexion) |
| `ENABLED` | 1 | [EnabledDomain](01_Dominios.md#enableddomain) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `SUBTIPO` | 1 | — |
| `VOLTAJE` |  | [Voltaje MT](01_Dominios.md#voltaje-mt) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| FDO_SHAPE | SHAPE | No | Yes |
| G232CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G232ESTRUCTURANI | ESTRUCTURANIVELGLOBALID | No | Yes |
| G232ESTRUCTURASO | ESTRUCTURASOPORTEGLOBALID | No | Yes |
| G232ESTRUCTURASU | ESTRUCTURASUBTERRANEAGLOBALID | No | Yes |
| G232MIGUID | MIGUID | No | Yes |
| G232PARENTCIRCUI | PARENTCIRCUITSOURCEGUID | No | Yes |

</details>

### Relaciones donde participa (3)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [EstrucNivel_PuestoCorrFacPot](02_Relaciones.md#estrucnivelpuestocorrfacpot) | Destino | [`EstructuraANivel`](03_Clases_Redes_y_Soporte.md#estructuraanivel) | One To Many |
| [EstrucSop_PuestoCorrFacPot](02_Relaciones.md#estrucsoppuestocorrfacpot) | Destino | [`EstructuraSoporte`](03_Clases_Redes_y_Soporte.md#estructurasoporte) | One To Many |
| [PuestoCorrFacPot_UnidadCapacitor](02_Relaciones.md#puestocorrfacpotunidadcapacitor) | Origen | [`UNIDADCAPACITOR`](#unidadcapacitor) | One To Many |

---

## `UNIDADCAPACITOR` — Capacitor
<a id="unidadcapacitor"></a>

| | |
|---|---|
| **Tipo de dataset** | Table |
| **Naturaleza** | Tabla no espacial |
| **Tabla de campos obligatorios en el manual** | Sí — ver columna *Categoría* abajo |
| **Campos** | 33 total — ✅ 12 core · 🔌 0 conectividad · 🔧 12 sistema · ▫️ 9 otros |

### Campos

| Campo (`field_name`) | Alias | Tipo | Long. | Nulo | Categoría | Ejemplo (manual) |
|---|---|---|---|---|---|---|
| `OBJECTID` | Object ID | OID | 4 | No | 🔧 Sistema |  |
| `USUARIOREGISTRO` | Usu Cre | String | 50 | Yes | ✅ CORE | Empresa S.A |
| `FECHAREGISTRO` | F Cre Sis | Date | 8 | Yes | ✅ CORE | 20/02/2019 |
| `FECHAMODIFICACIONREGISTRO` | F Mod Sis | Date | 8 | Yes | 🔧 Sistema |  |
| `USUARIOMODIFICACIONREGISTRO` | Usu Mod | String | 50 | Yes | 🔧 Sistema |  |
| `PROYECTOCONSTRUCCION` | Proyecto Const | String | 32 | Yes | 🔧 Sistema |  |
| `FECHACONSTRUCCION` | F Construccion | Date | 8 | Yes | 🔧 Sistema |  |
| `FECHAACTIVACION` | F Activacion | Date | 8 | Yes | 🔧 Sistema |  |
| `PROYECTOMODIFICACION` | Proyecto Mod | String | 32 | Yes | 🔧 Sistema |  |
| `FECHAMODIFICACION` | F Modificacion | Date | 8 | Yes | ▫️ Otro |  |
| `CODIGOEMPRESA` | Codigo Empresa | String | 10 | Yes | ✅ CORE | CNEL EP MLG |
| `PROVINCIA` | Provincia | String | 2 | Yes | ✅ CORE | Guayas |
| `CANTON` | Canton | String | 4 | Yes | ✅ CORE | Naranjito |
| `MODELO` | MODELO | String | 20 | Yes | ▫️ Otro |  |
| `NUMEROSERIE` | Serie | String | 20 | Yes | ✅ CORE | S-6732fgd |
| `MARCA` | Marca | String | 5 | Yes | ✅ CORE | Schneider |
| `FASECONEXION` | Fase Conexion | Integer | 4 | Yes | ✅ CORE | B |
| `CODIGOUNIDAD` | Codigo Unidad | String | 20 | Yes | ▫️ Otro |  |
| `CODIGOESTRUCTURA` | Codigo Estructura | String | 10 | Yes | ✅ CORE | C1C100T |
| `PUESTOCORRFACPOTOBJECTID` | PUESTOCORRFACPOT OID | Integer | 4 | Yes | ▫️ Otro |  |
| `GLOBALID` | GLOBALID | Global ID | 38 | No | 🔧 Sistema |  |
| `PUESTOCORRFACPOTGLOBALID` | PuestoCorrFacPotGLOBALID | GUID | 38 | Yes | ▫️ Otro |  |
| `COMENTARIOS` | COMENTARIOS | String | 255 | Yes | 🔧 Sistema |  |
| `OBSERVACIONES` | Observaciones | String | 255 | Yes | 🔧 Sistema |  |
| `PARROQUIA` | Parroquia | String | 6 | Yes | ✅ CORE | Naranjito |
| `ESTADO` | Estado | Small Integer | 2 | Yes | ▫️ Otro |  |
| `MIESTADO` | MIESTADO | String | 20 | Yes | ▫️ Otro |  |
| `MIGUID` | MIGUID | GUID | 38 | Yes | 🔧 Sistema |  |
| `MIOID` | MIOID | Integer | 4 | Yes | 🔧 Sistema |  |
| `EXISTENOVEDAD` | Existe Novedad | Small Integer | 2 | Yes | ▫️ Otro |  |
| `POTENCIANOMINAL` | Potencia Nominal | Integer | 4 | Yes | ✅ CORE | 100 |
| `CODIGOADMS` | CODIGOADMS | String | 100 | Yes | ▫️ Otro |  |
| `ORDENTRABAJO` | Orden de trabajo | String | 50 | Yes | ✅ CORE | OT-1237 |

### Subtipos y dominios asignados

Cada subtipo puede asignar un **valor por defecto** y/o un **dominio de validación** distinto al mismo campo. La fila `ObjectClass` son los valores/dominios que aplican **a nivel de clase** (antes de considerar el subtipo específico del registro, campo `SUBTIPO`).

**ObjectClass**

| Campo | Valor por defecto | Dominio |
|---|---|---|
| `CODIGOEMPRESA` | CNELGYE | [Empresas](01_Dominios.md#empresas) |
| `PROVINCIA` | 09 | [Provincias](01_Dominios.md#provincias) |
| `CANTON` | 0901 | [Cantones](01_Dominios.md#cantones) |
| `MARCA` |  | [Marcas](01_Dominios.md#marcas) |
| `FASECONEXION` |  | [Phase Designation](01_Dominios.md#phase-designation) |
| `CODIGOESTRUCTURA` |  | [UP_PC_TODOS](01_Dominios.md#uppctodos) |
| `PARROQUIA` |  | [Parroquias](01_Dominios.md#parroquias) |
| `ESTADO` |  | [Estado](01_Dominios.md#estado) |
| `EXISTENOVEDAD` |  | [ExisteNovedad](01_Dominios.md#existenovedad) |
| `POTENCIANOMINAL` |  | [kVAR Capacitor Unidad](01_Dominios.md#kvar-capacitor-unidad) |

<details><summary>Índices definidos en el esquema</summary>

| Índice | Campos | Único | Ascendente |
|---|---|---|---|
| FDO_GLOBALID | GLOBALID | No | Yes |
| FDO_OBJECTID | OBJECTID | Yes | Yes |
| G210CODIGOESTRUC | CODIGOESTRUCTURA | No | Yes |
| G210MIGUID | MIGUID | No | Yes |
| G210PUESTOCORRFA | PUESTOCORRFACPOTOBJECTID | No | Yes |
| G210PUESTOCORRFA_1 | PUESTOCORRFACPOTGLOBALID | No | Yes |

</details>

### Relaciones donde participa (2)

| Relación | Rol | Contraparte | Cardinalidad |
|---|---|---|---|
| [CatEstruc_UnidadCapacitor](02_Relaciones.md#catestrucunidadcapacitor) | Destino | [`CATALOGOESTRUCTURA`](03_Clases_Redes_y_Soporte.md#catalogoestructura) | One To Many |
| [PuestoCorrFacPot_UnidadCapacitor](02_Relaciones.md#puestocorrfacpotunidadcapacitor) | Destino | [`PuestoCorrectorFactorPotencia`](#puestocorrectorfactorpotencia) | One To Many |

---
