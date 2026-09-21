# 01 · Catálogo de Dominios

[⬅ Volver al índice](00_Indice_y_Conceptos.md) · [Clases: Redes y Soporte](03_Clases_Redes_y_Soporte.md) · [Clases: Protección y Potencia](04_Clases_Proteccion_y_Potencia.md) · [Clases: Generación/Subestaciones](05_Clases_Generacion_Subestaciones_Fuentes.md) · [Clases: Consumidores/Alumbrado](06_Clases_Consumidores_y_Alumbrado.md) · [Relaciones](02_Relaciones.md)

> **Fuente:** `Modelo_Datos.htm` (reporte ArcGIS Diagrammer, geodatabase GYE, corte 2025-05-12), cruzado con `MN-TEC-OPE-100` (Manual de ingreso de información ArcGIS, CNEL EP, v01, 2021-02).

Este archivo cataloga los **196 dominios** (196: 194 de valor codificado + 2 de rango) definidos en la geodatabase. Cada dominio se usa como referencia de validación de campos en los archivos de clases (03 a 06); allí cada campo con dominio asignado enlaza aquí.

## Cómo usar este catálogo

Los dominios se agrupan en 4 categorías según su naturaleza. Esto importa porque **no todos son iguales de confiables para hardcodear en un query o programa**:

| Categoría | Significado | ¿Se puede hardcodear la lista de valores? |
|---|---|---|
| 🟥 **Variable por Unidad de Negocio (UN)** | Códigos de alimentador y subestación — **cada Unidad de Negocio de CNEL EP (y cada distribuidora del país) tiene su propio conjunto**, ya que el modelo de datos es nacional pero la red física es local. | **No.** Consultar siempre el dominio vigente en la Geodatabase de la UN correspondiente (o vía servicio/API), nunca fijar una lista estática en código. |
| 🟧 **Catálogo nacional extenso** | Dominios de alcance nacional (aplican a todas las UN) pero con muchos miembros (>40): catálogos homologados MERNNR de unidades de propiedad (estructuras, transformadores, etc.), división política (provincias/cantones/parroquias). | Con precaución — son estables pero extensos y pueden actualizarse; preferible consultarlos desde la geodatabase en vez de mantener una copia embebida. |
| 🟩 **Catálogo pequeño fijo** | Listas cortas y estables (fases, tipos, sí/no, banderas de estado, listado de empresas eléctricas del país, etc.) | Sí — se listan completos abajo. |
| 🟦 **Dominio de rango** | Define un mínimo y máximo numérico válido, no una lista. | Sí — el rango se documenta completo. |

---

**Resumen:** 🟥 3 variables por UN · 🟧 55 catálogos nacionales extensos · 🟩 136 catálogos pequeños fijos · 🟦 2 de rango.

## 🟥 Dominios variables por Unidad de Negocio
<a id="🟥-dominios-variables-por-unidad-de-negocio"></a>

> ⚠️ **Importante para cualquier query o programa**: los tres dominios siguientes contienen los códigos de **alimentadores** y **subestaciones** de la Unidad de Negocio Guayaquil (GYE), que es la geodatabase de origen de este export. Otra Unidad de Negocio de CNEL EP (Manabí, Milagro, Los Ríos, etc.) o cualquier otra distribuidora del país que use este mismo modelo de datos nacional **tendrá una lista de miembros completamente distinta** en estos mismos dominios, porque referencian su propia red física. **No copiar estas listas como constantes en código reutilizable entre Unidades de Negocio** — consultarlas siempre desde la geodatabase activa (p. ej. `arcpy.da.ListDomains`, o la tabla de dominios de la BD si es enterprise geodatabase).

### Codigo Alimentador
<a id="codigo-alimentador"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros (en este export, UN=GYE):** 246
- **Merge policy:** Default Value · **Split policy:** Duplicate

Muestra ilustrativa (primeros 8 de 246 — **no exhaustivo, no usar como lista fija**):

| Nombre (Name) | Valor (Value / código guardado) |
|---|---|
| S/E BELO HORIZONTE - PORTAL AL SOL | `04BH070T11` |
| S/E LOTES CON SERVICIO ALEGRIA - COLINAS AL SOL | `04LA380T11` |
| S/E LOTES CON SERVICIO ALEGRIA - EXPOGRANOS | `04LA380T12` |
| S/E MUCHO LOTE - GERANIOS | `04ML390T12` |
| S/E MUCHO LOTE - MAGISTERIO | `04ML390T11` |
| S/E ORQUIDEAS - LIMONCOCHA | `04OR240T22` |
| S/E SAMANES - ALBORNOR | `04SM320T24` |
| S/E SAMANES - LOS ALAMOS | `04SM320T22` |

### Numero Estacion
<a id="numero-estacion"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros (en este export, UN=GYE):** 118
- **Merge policy:** Default Value · **Split policy:** Duplicate

Muestra ilustrativa (primeros 8 de 118 — **no exhaustivo, no usar como lista fija**):

| Nombre (Name) | Valor (Value / código guardado) |
|---|---|
| S/E ALBORADA 1 | `04A101` |
| S/E ALBORADA 2 | `04A202` |
| S/E AMERICA | `04AM03` |
| S/E ASTILLERO | `04AS04` |
| S/E ATARAZANA | `04AT05` |
| S/E AYACUCHO | `04AY06` |
| S/E BELO HORIZONTE | `04BH07` |
| S/E BIEN PUBLICO | `04BP08` |

### Subestacion
<a id="subestacion"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros (en este export, UN=GYE):** 139
- **Merge policy:** Default Value · **Split policy:** Default Value

Muestra ilustrativa (primeros 8 de 139 — **no exhaustivo, no usar como lista fija**):

| Nombre (Name) | Valor (Value / código guardado) |
|---|---|
| S/E ALBORADA 1 | `04A101` |
| S/E ALBORADA 2 | `04A202` |
| S/E AMERICA | `04AM03` |
| S/E ASTILLERO | `04AS04` |
| S/E ATARAZANA | `04AT05` |
| S/E AYACUCHO | `04AY06` |
| S/E BELO HORIZONTE | `04BH07` |
| S/E BIEN PUBLICO | `04BP08` |

---

## 🟧 Catálogos nacionales extensos (>40 miembros)

Dominios de alcance nacional (no cambian por Unidad de Negocio) pero con muchos miembros — en su mayoría catálogos homologados de **Unidades de Propiedad (UP)** por tipo de estructura (Catálogo de Estructuras MERNNR, ver manual cap. 3) o división política del Ecuador. Se muestra una muestra; el listado completo está en la geodatabase / `Modelo_Datos.htm` original.

| Dominio | Tipo | Tipo de campo | Nº de miembros |
|---|---|---|---|
| [UP_TRF_TODOS](#uptrftodos) | Coded Value | String | 1853 |
| [Parroquias](#parroquias) | Coded Value | String | 1410 |
| [UP_ES_TODOS](#upestodos) | Coded Value | String | 646 |
| [UP_TRF_3F_CABINA](#uptrf3fcabina) | Coded Value | String | 358 |
| [Catalogo Conductores](#catalogo-conductores) | Coded Value | String | 333 |
| [UP_PPD_TODOS](#upppdtodos) | Coded Value | String | 300 |
| [UP_TRF_BANCO_2_CABINA](#uptrfbanco2cabina) | Coded Value | String | 270 |
| [UP_TBS_ACOMETIDA](#uptbsacometida) | Coded Value | String | 258 |
| [UP_TBS_TRAMO](#uptbstramo) | Coded Value | String | 257 |
| [UP_TRF_BANCO_2_POSTE](#uptrfbanco2poste) | Coded Value | String | 256 |
| [UP_TMA_BAJANTE](#uptmabajante) | Coded Value | String | 254 |
| [UP_TBA_BAJANTE](#uptbabajante) | Coded Value | String | 251 |
| [UP_TBA_TRAMO](#uptbatramo) | Coded Value | String | 248 |
| [UP_TBA_ACOMETIDA](#uptbaacometida) | Coded Value | String | 232 |
| [UP_PO_HORMIGON](#uppohormigon) | Coded Value | String | 228 |
| [Cantones](#cantones) | Coded Value | String | 224 |
| [Dom_Arrendatarios](#domarrendatarios) | Coded Value | String | 210 |
| [Instituciones](#instituciones) | Coded Value | Small Integer | 209 |
| [UP_TRF_BANCO_3_CABINA](#uptrfbanco3cabina) | Coded Value | String | 209 |
| [UP_AP_LUMIN_LED](#upapluminled) | Coded Value | String | 192 |
| [UP_TRF_3F_PAD_EXT](#uptrf3fpadext) | Coded Value | String | 172 |
| [UP_TMA_TRAMO](#uptmatramo) | Coded Value | String | 167 |
| [UP_TRF_3F_POSTE](#uptrf3fposte) | Coded Value | String | 159 |
| [UP_PPD_INTERRUPTOR](#upppdinterruptor) | Coded Value | String | 152 |
| [UP_PR_TODOS](#upprtodos) | Coded Value | String | 146 |
| [UP_PC_TODOS](#uppctodos) | Coded Value | String | 144 |
| [Marcas](#marcas) | Coded Value | String | 143 |
| [UP_AP_LUMIN_NA_CERRADA](#upapluminnacerrada) | Coded Value | String | 139 |
| [Marca](#marca) | Coded Value | String | 135 |
| [UP_TRF_1F_POSTE](#uptrf1fposte) | Coded Value | String | 129 |
| [Categoria](#categoria) | Coded Value | String | 127 |
| [UP_TMS_TRAMO](#uptmstramo) | Coded Value | String | 125 |
| [UP_PPD_RECONECTADOR](#upppdreconectador) | Coded Value | String | 120 |
| [Usocod Energia](#usocod-energia) | Coded Value | String | 117 |
| [UP_TRF_BANCO_3_POSTE](#uptrfbanco3poste) | Coded Value | String | 97 |
| [UP_TRF_1F_CABINA](#uptrf1fcabina) | Coded Value | String | 91 |
| [Capacidad Fusible](#capacidad-fusible) | Coded Value | String | 86 |
| [TipoTarifaCIS](#tipotarifacis) | Coded Value | String | 84 |
| [Potencia Nominal Transformador Distribucion](#potencia-nominal-transformador-distribucion) | Coded Value | String | 82 |
| [UP_PR_1F](#uppr1f) | Coded Value | String | 82 |
| [UP_PA_CAPACIDAD_FUSIBLE](#uppacapacidadfusible) | Coded Value | String | 80 |
| [UP_PC_Fijo](#uppcfijo) | Coded Value | String | 76 |
| [UP_PC_Automatico](#uppcautomatico) | Coded Value | String | 68 |
| [UP_MEDIDORES](#upmedidores) | Coded Value | String | 65 |
| [UP_PR_3F](#uppr3f) | Coded Value | String | 64 |
| [UP_AP_LUMIN_HG_CERRADA](#upapluminhgcerrada) | Coded Value | String | 61 |
| [UP_AP_PROYECTOR_HG](#upapproyectorhg) | Coded Value | String | 61 |
| [UP_TS_TRAMO](#uptstramo) | Coded Value | String | 56 |
| [UP_PM_BARRAJE](#uppmbarraje) | Coded Value | String | 49 |
| [UP_AP_PROYECTOR_NA](#upapproyectorna) | Coded Value | String | 47 |
| [UP_TRF_2F_POSTE](#uptrf2fposte) | Coded Value | String | 46 |
| [UP_PSC_UNIPOL](#uppscunipol) | Coded Value | String | 45 |
| [UP_PO_METALICO](#uppometalico) | Coded Value | String | 43 |
| [UP_PSC_UNIPOL_ROMPE](#uppscunipolrompe) | Coded Value | String | 43 |
| [UP_AP_PROYECTOR_LED](#upapproyectorled) | Coded Value | String | 42 |

### UP_TRF_TODOS
<a id="uptrftodos"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 1853

Muestra (primeros 10 de 1853):

| Nombre | Valor |
|---|---|
| 1C1R | `TRR0264` |
| 1C1.5R | `TRR0299` |
| 1C3R | `TRR0001` |
| 1C5R | `TRR0002` |
| 1C7.5R | `TRR0257` |
| 1C10R | `TRR0003` |
| 1C15R | `TRR0004` |
| 1C20R | `TRR0266` |
| 1C25R | `TRR0005` |
| 1C30R | `TRR0211` |

### Parroquias
<a id="parroquias"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 1410

Muestra (primeros 10 de 1410):

| Nombre | Valor |
|---|---|
| BELLAVISTA | `010101` |
| CAÑARIBAMBA | `010102` |
| EL BATÁN | `010103` |
| EL SAGRARIO | `010104` |
| EL VECINO | `010105` |
| GIL RAMÍREZ DÁVALOS | `010106` |
| HUAYNACÁPAC | `010107` |
| MACHÁNGARA | `010108` |
| MONAY | `010109` |
| SAN BLAS | `010110` |

### UP_ES_TODOS
<a id="upestodos"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 646

Muestra (primeros 10 de 646):

| Nombre | Valor |
|---|---|
| 1PP1 | `ESE0008` |
| 1PD1 | `ESE0009` |
| 1PA1 | `ESE0010` |
| 1PR1 | `ESE0007` |
| 1PP2 | `ESD0037` |
| 1PA2 | `ESD0040` |
| 1PD2 | `ESD0038` |
| 1PR2 | `ESD0039` |
| 1PP3 | `ESD0027` |
| 1PA3 | `ESD0029` |

### UP_TRF_3F_CABINA
<a id="uptrf3fcabina"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 358

Muestra (primeros 10 de 358):

| Nombre | Valor |
|---|---|
| 3O5R | `TRR0343` |
| 3O15R | `TRR0076` |
| 3O20R | `TRR0332` |
| 3O25R | `TRR0333` |
| 3O30R | `TRR0077` |
| 3O37.5R | `TRR0428` |
| 3O45R | `TRR0078` |
| 3O50R | `TRR0079` |
| 3O60R | `TRR0080` |
| 3O75R | `TRR0081` |

### Catalogo Conductores
<a id="catalogo-conductores"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 333

Muestra (primeros 10 de 333):

| Nombre | Valor |
|---|---|
| Des.Cu.8 | `COO0184` |
| Des.Cu.6 | `COO0011` |
| Des.Cu.4 | `COO0012` |
| Des.Cu.2 | `COO0013` |
| Des.Cu.1/0 | `COO0014` |
| Des.Cu.2/0 | `COO0015` |
| Des.Cu.3/0 | `COO0016` |
| Des.Cu.4/0 | `COO0185` |
| Des.Cu.250 | `COO0274` |
| Des.Cu.350 | `COO0275` |

### UP_PPD_TODOS
<a id="upppdtodos"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 300

Muestra (primeros 10 de 300):

| Nombre | Valor |
|---|---|
| 1R400_95R | `SPR0017` |
| 1R400_125R | `SPR0018` |
| 1R600_95R | `SPR0019` |
| 1R600_125R | `SPR0020` |
| 3R400_75R | `SPR0109` |
| 3R400_95R | `SPR0059` |
| 3R400_125R | `SPR0060` |
| 3R400_150R | `SPR0074` |
| 3R560_75R | `SPR0077` |
| 3R560_95R | `SPR0078` |

### UP_TRF_BANCO_2_CABINA
<a id="uptrfbanco2cabina"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 270

Muestra (primeros 10 de 270):

| Nombre | Valor |
|---|---|
| 3V15R | `TRR0306` |
| 3V20R | `TRR0122` |
| 3V25R | `TRR0123` |
| 3V28R | `TRR0443` |
| 3V30R | `TRR0124` |
| 3V35R | `TRR0125` |
| 3V40R | `TRR0126` |
| 3V47.5R | `TRR0127` |
| 3V50R | `TRR0128` |
| 3V52.5R | `TRR0129` |

### UP_TBS_ACOMETIDA
<a id="uptbsacometida"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 258

Muestra (primeros 10 de 258):

| Nombre | Valor |
|---|---|
| Des.Cu.8 | `COO0184` |
| Des.Cu.6 | `COO0011` |
| Des.Cu.4 | `COO0012` |
| Des.Cu.2 | `COO0013` |
| Des.Cu.1/0 | `COO0014` |
| Des.Cu.2/0 | `COO0015` |
| Des.Cu.3/0 | `COO0016` |
| Des.Cu.4/0 | `COO0185` |
| Des.Cu.250 | `COO0274` |
| Des.Cu.350 | `COO0275` |

### UP_TBS_TRAMO
<a id="uptbstramo"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 257

Muestra (primeros 10 de 257):

| Nombre | Valor |
|---|---|
| Des.Cu.8 | `COO0184` |
| Des.Cu.6 | `COO0011` |
| Des.Cu.4 | `COO0012` |
| Des.Cu.2 | `COO0013` |
| Des.Cu.1/0 | `COO0014` |
| Des.Cu.2/0 | `COO0015` |
| Des.Cu.3/0 | `COO0016` |
| Des.Cu.4/0 | `COO0185` |
| Des.Cu.250 | `COO0274` |
| Des.Cu.350 | `COO0275` |

### UP_TRF_BANCO_2_POSTE
<a id="uptrfbanco2poste"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 256

Muestra (primeros 10 de 256):

| Nombre | Valor |
|---|---|
| 3B6R | `TRR0278` |
| 3B8R | `TRR0279` |
| 3B10R | `TRR0280` |
| 3B13R | `TRR0281` |
| 3B15R | `TRR0254` |
| 3B17.5R | `TRR0282` |
| 3B20R | `TRR0085` |
| 3B25R | `TRR0086` |
| 3B28R | `TRR0442` |
| 3B30R | `TRR0087` |

### UP_TMA_BAJANTE
<a id="uptmabajante"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 254

Muestra (primeros 10 de 254):

| Nombre | Valor |
|---|---|
| AAAC5005.6 | `COO0017` |
| AAAC5005.4 | `COO0018` |
| AAAC5005.2 | `COO0019` |
| AAAC5005.1/0 | `COO0020` |
| AAAC5005.2/0 | `COO0021` |
| AAAC5005.3/0 | `COO0022` |
| AAAC5005.4/0 | `COO0248` |
| AAAC5005.266.8 | `COO0238` |
| AAAC5005.281.4 | `COO0266` |
| AAAC5005.312.8 | `COO0239` |

### UP_TBA_BAJANTE
<a id="uptbabajante"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 251

Muestra (primeros 10 de 251):

| Nombre | Valor |
|---|---|
| Des.Cu.8 | `COO0184` |
| Des.Cu.6 | `COO0011` |
| Des.Cu.4 | `COO0012` |
| Des.Cu.2 | `COO0013` |
| Des.Cu.1/0 | `COO0014` |
| Des.Cu.2/0 | `COO0015` |
| Des.Cu.3/0 | `COO0016` |
| Des.Cu.4/0 | `COO0185` |
| Des.Cu.250 | `COO0274` |
| Des.Cu.350 | `COO0275` |

### UP_TBA_TRAMO
<a id="uptbatramo"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 248

Muestra (primeros 10 de 248):

| Nombre | Valor |
|---|---|
| Des.Cu.8 | `COO0184` |
| Des.Cu.6 | `COO0011` |
| Des.Cu.4 | `COO0012` |
| Des.Cu.2 | `COO0013` |
| Des.Cu.1/0 | `COO0014` |
| Des.Cu.2/0 | `COO0015` |
| Des.Cu.3/0 | `COO0016` |
| Des.Cu.4/0 | `COO0185` |
| Des.Cu.250 | `COO0274` |
| Des.Cu.350 | `COO0275` |

### UP_TBA_ACOMETIDA
<a id="uptbaacometida"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 232

Muestra (primeros 10 de 232):

| Nombre | Valor |
|---|---|
| Des.Cu.8 | `COO0184` |
| Des.Cu.6 | `COO0011` |
| Des.Cu.4 | `COO0012` |
| Des.Cu.2 | `COO0013` |
| Des.Cu.1/0 | `COO0014` |
| Des.Cu.2/0 | `COO0015` |
| Des.Cu.3/0 | `COO0016` |
| Des.Cu.4/0 | `COO0185` |
| Des.Cu.250 | `COO0274` |
| Des.Cu.350 | `COO0275` |

### UP_PO_HORMIGON
<a id="uppohormigon"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 228

Muestra (primeros 10 de 228):

| Nombre | Valor |
|---|---|
| PHC6_350 | `POO8401` |
| PHR6_350 | `POO9701` |
| PHO6_350 | `POO8801` |
| PHC7_350 | `POO8501` |
| PHR7_300 | `POO6524` |
| PHR7_350 | `POO6501` |
| PHO7_350 | `POO8901` |
| PHC8_350 | `POO4901` |
| PHC8_500 | `POO4904` |
| PHC8_600 | `POO4905` |

### Cantones
<a id="cantones"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 224

Muestra (primeros 10 de 224):

| Nombre | Valor |
|---|---|
| CUENCA | `0101` |
| GIRON | `0102` |
| GUALACEO | `0103` |
| NABON | `0104` |
| PAUTE | `0105` |
| PUCARA | `0106` |
| SAN FERNANDO | `0107` |
| SANTA ISABEL | `0108` |
| SIGSIG | `0109` |
| ONA | `0110` |

### Dom_Arrendatarios
<a id="domarrendatarios"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 210

Muestra (primeros 10 de 210):

| Nombre | Valor |
|---|---|
| CNT EP | `04_CNT` |
| SETEL GRUPO TV CABLE SA | `04_TVCABLE` |
| TELCONET | `04_TELCONET` |
| CABLEZAR | `04_CABLEZAR` |
| PUNTONET | `04_PUNTONET` |
| TVNET | `04_TVNET` |
| COLORADOS VISION | `04_COLORADOS` |
| DAULE VISION | `04_DAULE` |
| ELITE TV | `04_ELITE` |
| ANTEL ANTENAS Y TELECOMUNICACIONES SA | `04_ANTEL` |

### Instituciones
<a id="instituciones"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer · **Nº de miembros:** 209

Muestra (primeros 10 de 209):

| Nombre | Valor |
|---|---|
| CNT EP | `1` |
| SETEL GRUPO TV CABLE SA | `2` |
| TELCONET | `3` |
| CABLEZAR | `4` |
| PUNTONET | `5` |
| TVNET | `6` |
| COLORADOS VISION | `7` |
| DAULE VISION | `8` |
| ELITE TV | `9` |
| ANTEL ANTENAS Y TELECOMUNICACIONES SA | `10` |

### UP_TRF_BANCO_3_CABINA
<a id="uptrfbanco3cabina"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 209

Muestra (primeros 10 de 209):

| Nombre | Valor |
|---|---|
| 3I30R | `TRR0153` |
| 3I35R | `TRR0154` |
| 3I45R | `TRR0155` |
| 3I50R | `TRR0156` |
| 3I55R | `TRR0157` |
| 3I65R | `TRR0158` |
| 3I67.5R | `TRR0159` |
| 3I75R | `TRR0160` |
| 3I80R | `TRR0440` |
| 3I87.5R | `TRR0161` |

### UP_AP_LUMIN_LED
<a id="upapluminled"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 192

Muestra (primeros 10 de 192):

| Nombre | Valor |
|---|---|
| LDPL3.6PCC | `APO0701` |
| LDPL5ACC | `APO0718` |
| LDPL10ACC | `APO0709` |
| LDPL15ACC | `APO0710` |
| LDPL20ACC | `APO0711` |
| LDPL25ACC | `APO0713` |
| LDPL30ACC | `APO0714` |
| LDPL39PCC | `APO0734` |
| LDPL39ACC | `APO0735` |
| LDOL39ACC | `APO0736` |

### UP_TRF_3F_PAD_EXT
<a id="uptrf3fpadext"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 172

Muestra (primeros 10 de 172):

| Nombre | Valor |
|---|---|
| 3P5R | `TRR0344` |
| 3P15R | `TRR0037` |
| 3P20R | `TRR0255` |
| 3P25R | `TRR0276` |
| 3P30R | `TRR0038` |
| 3P37.5R | `TRR0039` |
| 3P45R | `TRR0040` |
| 3P50R | `TRR0041` |
| 3P60R | `TRR0303` |
| 3P75R | `TRR0042` |

### UP_TMA_TRAMO
<a id="uptmatramo"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 167

Muestra (primeros 10 de 167):

| Nombre | Valor |
|---|---|
| Des.Cu.8 | `COO0184` |
| Des.Cu.6 | `COO0011` |
| Des.Cu.4 | `COO0012` |
| Des.Cu.2 | `COO0013` |
| Des.Cu.1/0 | `COO0014` |
| Des.Cu.2/0 | `COO0015` |
| Des.Cu.3/0 | `COO0016` |
| Des.Cu.4/0 | `COO0185` |
| Des.Cu.250 | `COO0274` |
| Des.Cu.350 | `COO0275` |

### UP_TRF_3F_POSTE
<a id="uptrf3fposte"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 159

Muestra (primeros 10 de 159):

| Nombre | Valor |
|---|---|
| 3C5R | `TRR0342` |
| 3C10R | `TRR0269` |
| 3C15R | `TRR0017` |
| 3C20R | `TRR0220` |
| 3C25R | `TRR0270` |
| 3C30R | `TRR0018` |
| 3C37.5R | `TRR0271` |
| 3C45R | `TRR0019` |
| 3C50R | `TRR0020` |
| 3C60R | `TRR0021` |

### UP_PPD_INTERRUPTOR
<a id="upppdinterruptor"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 152

Muestra (primeros 10 de 152):

| Nombre | Valor |
|---|---|
| 1I100_95R | `SPR0013` |
| 1I100_125R | `SPR0014` |
| 1I100_150R | `SPR0070` |
| 1I200_95R | `SPR0015` |
| 1I200_125R | `SPR0016` |
| 1I200_150R | `SPR0071` |
| 3I100_95R | `SPR0053` |
| 3I100_125R | `SPR0054` |
| 3I100_150R | `SPR0055` |
| 3I200_95R | `SPR0056` |

### UP_PR_TODOS
<a id="upprtodos"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 146

Muestra (primeros 10 de 146):

| Nombre | Valor |
|---|---|
| C1RM50R | `ECR0013` |
| C1RM100R | `ECR0014` |
| C1RM127R | `ECR0047` |
| C1RM144R | `ECR0048` |
| C1RM167R | `ECR0049` |
| C1RM200R | `ECR0015` |
| C1RM288R | `ECR0050` |
| C1RM300R | `ECR0016` |
| C1RE50R | `ECR0017` |
| C1RE76.2R | `ECR0046` |

### UP_PC_TODOS
<a id="uppctodos"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 144

Muestra (primeros 10 de 144):

| Nombre | Valor |
|---|---|
| C1C50R | `ECR0001` |
| C1C100R | `ECR0002` |
| C1C150R | `ECR0061` |
| C1C200R | `ECR0003` |
| C1C300R | `ECR0004` |
| C1C400R | `ECR0044` |
| C1C600R | `ECR0045` |
| C3C50R | `ECR0005` |
| C3C100R | `ECR0006` |
| C3C150R | `ECR0056` |

### Marcas
<a id="marcas"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 143

Muestra (primeros 10 de 143):

| Nombre | Valor |
|---|---|
| ABB | `ABB` |
| AEG | `AEG` |
| AEG Brazil | `AEGB` |
| AEG Iberia | `AEGI` |
| Allis Chalmers | `ALLI` |
| American Fuse | `AMFU` |
| Asia Electric | `ASEL` |
| Arkansas | `ASKA` |
| Bown Boveri | `BOWB` |
| Cancpa Tabim | `CENW` |

### UP_AP_LUMIN_NA_CERRADA
<a id="upapluminnacerrada"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 139

Muestra (primeros 10 de 139):

| Nombre | Valor |
|---|---|
| LDPS70PCC | `APO0301` |
| LCPS100PCC | `APO0302` |
| LCPS150PCC | `APO0303` |
| LDPS100PCC | `APO0304` |
| LDPS150PCC | `APO0305` |
| LDPS250PCC | `APO0306` |
| LDPS400PCC | `APO0307` |
| LCPS70ACC | `APO0628` |
| LDPS70ACC | `APO0308` |
| LDPS75ACC | `APO0611` |

### Marca
<a id="marca"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 135

Muestra (primeros 10 de 135):

| Nombre | Valor |
|---|---|
| Aclara | `ACL` |
| Actaris | `ACT` |
| Asea Brown Boveri | `ABB` |
| AEG | `AEG` |
| AEM | `AEM` |
| Ampy | `AMP` |
| Bluestar | `BLU` |
| Canadian | `CAN` |
| CDC | `CDC` |
| Centrom | `CEN` |

### UP_TRF_1F_POSTE
<a id="uptrf1fposte"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 129

Muestra (primeros 10 de 129):

| Nombre | Valor |
|---|---|
| 1C1R | `TRR0264` |
| 1C1.5R | `TRR0299` |
| 1C3R | `TRR0001` |
| 1C5R | `TRR0002` |
| 1C7.5R | `TRR0257` |
| 1C10R | `TRR0003` |
| 1C15R | `TRR0004` |
| 1C20R | `TRR0266` |
| 1C25R | `TRR0005` |
| 1C30R | `TRR0211` |

### Categoria
<a id="categoria"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 127

Muestra (primeros 10 de 127):

| Nombre | Valor |
|---|---|
| EEASA_ResidencialUrbano | `01` |
| EEASA_ResidencialRural | `02` |
| EEASA_IndustrialUrbano | `03` |
| EEASA_IndustrialRural | `04` |
| EEASA_ComercialUrbano | `05` |
| EEASA_ComercialRural | `06` |
| EEQ_Costa_Residencial | `07` |
| EEQ_Costa_Comercial | `08` |
| EEQ_Costa_Industrial | `09` |
| EEQ_Oriente_Residencial | `10` |

### UP_TMS_TRAMO
<a id="uptmstramo"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 125

Muestra (primeros 10 de 125):

| Nombre | Valor |
|---|---|
| Des.Cu.8 | `COO0184` |
| Des.Cu.6 | `COO0011` |
| Des.Cu.4 | `COO0012` |
| Des.Cu.2 | `COO0013` |
| Des.Cu.1/0 | `COO0014` |
| Des.Cu.2/0 | `COO0015` |
| Des.Cu.3/0 | `COO0016` |
| Des.Cu.4/0 | `COO0185` |
| Des.Cu.250 | `COO0274` |
| Des.Cu.350 | `COO0275` |

### UP_PPD_RECONECTADOR
<a id="upppdreconectador"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 120

Muestra (primeros 10 de 120):

| Nombre | Valor |
|---|---|
| 1R400_95R | `SPR0017` |
| 1R400_125R | `SPR0018` |
| 1R600_95R | `SPR0019` |
| 1R600_125R | `SPR0020` |
| 3R400_75R | `SPR0109` |
| 3R400_95R | `SPR0059` |
| 3R400_125R | `SPR0060` |
| 3R400_150R | `SPR0074` |
| 3R560_75R | `SPR0077` |
| 3R560_95R | `SPR0078` |

### Usocod Energia
<a id="usocod-energia"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 117

Muestra (primeros 10 de 117):

| Nombre | Valor |
|---|---|
| ASISTENCIA SOCIAL BT CON DEMANDA HORARIA | `A3` |
| AS/BP BT CON DEMANDA | `AB` |
| AUTOCONSUMO CON DEMANDA EN BT | `AC` |
| ASISTENCIA SOCIAL MT | `AD` |
| ASISOC. DEM. HORARIA | `AH` |
| AUTOCONSUMO PARA LOCALES EMPRESA MT | `AM` |
| ALUMBRADO PUBLICO | `AP` |
| ASISTENCIA SOCIAL | `AS` |
| AUTOCONSUMO | `AU` |
| BENEFICIO PUBLICO BT CON DEMANDA HORARIA | `B3` |

### UP_TRF_BANCO_3_POSTE
<a id="uptrfbanco3poste"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 97

Muestra (primeros 10 de 97):

| Nombre | Valor |
|---|---|
| 3N9R | `TRR0307` |
| 3N15R | `TRR0260` |
| 3N22.5R | `TRR0287` |
| 3N23R | `TRR0308` |
| 3N25R | `TRR0288` |
| 3N30R | `TRR0111` |
| 3N35R | `TRR0112` |
| 3N40R | `TRR0252` |
| 3N45R | `TRR0113` |
| 3N50R | `TRR0114` |

### UP_TRF_1F_CABINA
<a id="uptrf1fcabina"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 91

Muestra (primeros 10 de 91):

| Nombre | Valor |
|---|---|
| 1O3R | `TRR0068` |
| 1O5R | `TRR0069` |
| 1O10R | `TRR0070` |
| 1O15R | `TRR0071` |
| 1O25R | `TRR0072` |
| 1O30R | `TRR0423` |
| 1O35R | `TRR0425` |
| 1O37.5R | `TRR0073` |
| 1O45R | `TRR0439` |
| 1O50R | `TRR0074` |

### Capacidad Fusible
<a id="capacidad-fusible"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 86

Muestra (primeros 10 de 86):

| Nombre | Valor |
|---|---|
| 0.2SF | `0.2SF` |
| 0.3SF | `0.3SF` |
| 0.4SF | `0.4SF` |
| 0.6SF | `0.6SF` |
| 0.7SF | `0.7SF` |
| 1.0SF | `1.0SF` |
| 1.3SF | `1.3SF` |
| 1.4SF | `1.4SF` |
| 1.6SF | `1.6SF` |
| 2.1SF | `2.1SF` |

### TipoTarifaCIS
<a id="tipotarifacis"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 84

Muestra (primeros 10 de 84):

| Nombre | Valor |
|---|---|
| AT Abonados Especiales con Dem Hor PO | `ATCGCD03O` |
| AT Bombeo de Agua con Dem Horaria PO | `ATCGCD04O` |
| AT Industrial con Dem Hor Dif PO | `ATCGCD07O` |
| AT Servicio Comunitario con Dem Hor PO | `ATCGCD08O` |
| AT Comercial con Demanda Horaria PO | `ATCGCD09O` |
| AT Entidades Oficiales con Dem Hor PO | `ATCGCD10O` |
| AT Escenarios Deportivos con Dem Hor PO | `ATCGCD11O` |
| AT Autoconsumo con Demanda Horaria PO | `ATCGCD12O` |
| AT Bombeo de agua S.P. agua pot. dem hor | `ATCGCD13O` |
| AT Peajes de distribución | `ATPDIS01O` |

### Potencia Nominal Transformador Distribucion
<a id="potencia-nominal-transformador-distribucion"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 82

Muestra (primeros 10 de 82):

| Nombre | Valor |
|---|---|
| 1 kVA | `1` |
| 1.5 kVA | `1.5` |
| 3 kVA | `3` |
| 5 kVA | `5` |
| 7.5 kVA | `7.5` |
| 10 kVA | `10` |
| 15 kVA | `15` |
| 20 kVA | `20` |
| 25 kVA | `25` |
| 30 kVA | `30` |

### UP_PR_1F
<a id="uppr1f"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 82

Muestra (primeros 10 de 82):

| Nombre | Valor |
|---|---|
| C1RM50R | `ECR0013` |
| C1RM100R | `ECR0014` |
| C1RM127R | `ECR0047` |
| C1RM144R | `ECR0048` |
| C1RM167R | `ECR0049` |
| C1RM200R | `ECR0015` |
| C1RM288R | `ECR0050` |
| C1RM300R | `ECR0016` |
| C1RE50R | `ECR0017` |
| C1RE76.2R | `ECR0046` |

### UP_PA_CAPACIDAD_FUSIBLE
<a id="uppacapacidadfusible"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 80

Muestra (primeros 10 de 80):

| Nombre | Valor |
|---|---|
| 2F3S | `SSS0038` |
| 2F6S | `SSS0039` |
| 2F8S | `SSS0040` |
| 2F10S | `SSS0041` |
| 2F12S | `SSS0042` |
| 2F18S | `SSS0043` |
| 2F20S | `SSS0044` |
| 2F25S | `SSS0045` |
| 2F30S | `SSS0046` |
| 2F40S | `SSS0047` |

### UP_PC_Fijo
<a id="uppcfijo"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 76

Muestra (primeros 10 de 76):

| Nombre | Valor |
|---|---|
| C1C50R | `ECR0001` |
| C1C100R | `ECR0002` |
| C1C150R | `ECR0061` |
| C1C200R | `ECR0003` |
| C1C300R | `ECR0004` |
| C1C400R | `ECR0044` |
| C1C600R | `ECR0045` |
| C3C50R | `ECR0005` |
| C3C100R | `ECR0006` |
| C3C150R | `ECR0056` |

### UP_PC_Automatico
<a id="uppcautomatico"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 68

Muestra (primeros 10 de 68):

| Nombre | Valor |
|---|---|
| C1A50R | `ECR0069` |
| C1A100R | `ECR0070` |
| C1A150R | `ECR0071` |
| C1A200R | `ECR0009` |
| C1A300R | `ECR0010` |
| C1A400R | `ECR0072` |
| C1A600R | `ECR0073` |
| C3A150R | `ECR0062` |
| C3A200R | `ECR0011` |
| C3A250R | `ECR0063` |

### UP_MEDIDORES
<a id="upmedidores"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 65

Muestra (primeros 10 de 65):

| Nombre | Valor |
|---|---|
| 1E100_1AC | `MEC0001` |
| 1D200_2SD | `MED0001` |
| 1E100_2AD | `MED0002` |
| 1R20_4SD | `MED0003` |
| 1R200_2SD | `MED0004` |
| 2D200_12SD | `MED0005` |
| 3R200_12SD | `MED0006` |
| 3R20_9SD | `MED0007` |
| 3R20_10AD | `MED0008` |
| 3R200_16SD | `MED0009` |

### UP_PR_3F
<a id="uppr3f"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 64

Muestra (primeros 10 de 64):

| Nombre | Valor |
|---|---|
| C3RM50R | `ECR0021` |
| C3RM100R | `ECR0022` |
| C3RM200R | `ECR0023` |
| C3RM300R | `ECR0024` |
| C3RM381R | `ECR0051` |
| C3RM432R | `ECR0052` |
| C3RM501R | `ECR0053` |
| C3RM864R | `ECR0054` |
| C3RE50R | `ECR0025` |
| C3RE100R | `ECR0026` |

### UP_AP_LUMIN_HG_CERRADA
<a id="upapluminhgcerrada"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 61

Muestra (primeros 10 de 61):

| Nombre | Valor |
|---|---|
| LDPM125PCC | `APO0201` |
| LDPM175PCC | `APO0202` |
| LDPM250PCC | `APO0203` |
| LDPM400PCC | `APO0204` |
| LCPM70ACC | `APO0238` |
| LDPM70ACC | `APO0239` |
| LDPM75ACC | `APO0236` |
| LCPM100ACC | `APO0240` |
| LDPM100ACC | `APO0241` |
| LDPM125ACC | `APO0205` |

### UP_AP_PROYECTOR_HG
<a id="upapproyectorhg"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 61

Muestra (primeros 10 de 61):

| Nombre | Valor |
|---|---|
| PDPM100PCC | `APO0401` |
| PDPM150PCC | `APO0402` |
| PDPM250PCC | `APO0436` |
| PDPM400PCC | `APO0438` |
| PDPM500PCC | `APO0403` |
| PDPM1000PCC | `APO0404` |
| PDPM1500PCC | `APO0439` |
| PDPM100ACC | `APO0405` |
| PDPM125ACC | `APO0447` |
| PDPM150ACC | `APO0406` |

### UP_TS_TRAMO
<a id="uptstramo"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 56

Muestra (primeros 10 de 56):

| Nombre | Valor |
|---|---|
| AAAC5005.1/0 | `COO0020` |
| AAAC5005.2/0 | `COO0021` |
| AAAC5005.3/0 | `COO0022` |
| AAAC5005.4/0 | `COO0248` |
| AAAC5005.266.8 | `COO0238` |
| AAAC5005.281.4 | `COO0266` |
| AAAC5005.312.8 | `COO0239` |
| AAAC5005.336.4 | `COO0240` |
| AAAC5005.397.5 | `COO0241` |
| AAAC5005.477 | `COO0242` |

### UP_PM_BARRAJE
<a id="uppmbarraje"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 49

Muestra (primeros 10 de 49):

| Nombre | Valor |
|---|---|
| 3A6_525D | `SSD0042` |
| 2B2_200S | `SSS0016` |
| 2B2_600S | `SSS0017` |
| 2B3_200S | `SSS0018` |
| 2B3_600S | `SSS0019` |
| 2B4_200S | `SSS0020` |
| 2B4_600S | `SSS0021` |
| 3B2_200S | `SSS0022` |
| 3B2_600S | `SSS0023` |
| 3B3_200S | `SSS0024` |

### UP_AP_PROYECTOR_NA
<a id="upapproyectorna"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 47

Muestra (primeros 10 de 47):

| Nombre | Valor |
|---|---|
| PDPS70PCC | `APO0522` |
| PDPS150PCC | `APO0501` |
| PDPS250PCC | `APO0502` |
| PDPS400PCC | `APO0521` |
| PDPS1000PCC | `APO0520` |
| PDPS1500PCC | `APO0524` |
| PDPS100ACC | `APO0532` |
| PDPS125ACC | `APO0533` |
| PDPS150ACC | `APO0503` |
| PDPS250ACC | `APO0504` |

### UP_TRF_2F_POSTE
<a id="uptrf2fposte"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 46

Muestra (primeros 10 de 46):

| Nombre | Valor |
|---|---|
| 2C3R | `TRR0212` |
| 2C5R | `TRR0213` |
| 2C10R | `TRR0214` |
| 2C15R | `TRR0215` |
| 2C25R | `TRR0216` |
| 2C37.5R | `TRR0217` |
| 2C50R | `TRR0218` |
| 2C75R | `TRR0219` |
| 2C3S | `TRS0001` |
| 2C5S | `TRS0002` |

### UP_PSC_UNIPOL
<a id="uppscunipol"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 45

Muestra (primeros 10 de 45):

| Nombre | Valor |
|---|---|
| 2C100S | `SPS0036` |
| 3C100S | `SPS0011` |
| 2C200S | `SPS0037` |
| 3C200S | `SPS0047` |
| 2C300S | `SPS0038` |
| 3C300S | `SPS0048` |
| 2C600S | `SPS0039` |
| 3C600S | `SPS0049` |
| 1C100T | `SPT0005` |
| 2C100T | `SPT0025` |

### UP_PO_METALICO
<a id="uppometalico"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 43

Muestra (primeros 10 de 43):

| Nombre | Valor |
|---|---|
| PEC3 | `POO3000` |
| PEC4 | `POO6700` |
| PEC4.5 | `POO4600` |
| PEC5 | `POO6800` |
| PEC6 | `POO2900` |
| PEC7 | `POO6900` |
| PEC8 | `POO3600` |
| PEC9 | `POO0400` |
| PEC10 | `POO0800` |
| PEC10.5 | `POO10700` |

### UP_PSC_UNIPOL_ROMPE
<a id="uppscunipolrompe"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 43

Muestra (primeros 10 de 43):

| Nombre | Valor |
|---|---|
| 1O100R | `SPR0009` |
| 1O200R | `SPR0010` |
| 1O300R | `SPR0011` |
| 1O600R | `SPR0012` |
| 2O100R | `SPR0029` |
| 2O200R | `SPR0030` |
| 2O300R | `SPR0031` |
| 2O600R | `SPR0032` |
| 3O100R | `SPR0041` |
| 3O200R | `SPR0042` |

### UP_AP_PROYECTOR_LED
<a id="upapproyectorled"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String · **Nº de miembros:** 42

Muestra (primeros 10 de 42):

| Nombre | Valor |
|---|---|
| PDPL500PCC | `APO0941` |
| PDPL200PCC | `APO0942` |
| AODIPL3.6A | `AOD0032` |
| AODIPL3.6P | `AOD0090` |
| AODIPL6P | `AOD0125` |
| AODIPL9A | `AOD0135` |
| AODIPL10P | `AOD0122` |
| AODIPL15A | `AOD0031` |
| AODIPL15P | `AOD0089` |
| AODIPL18A | `AOD0103` |

---

## 🟦 Dominios de rango

| Dominio | Tipo de campo | Mínimo | Máximo |
|---|---|---|---|
| [Cantidad de Cables](#cantidad-de-cables) | Integer | 1 | 8 |
| [Measured Length](#measured-length) | Double | 1 | 1000000000 |

### Cantidad de Cables
<a id="cantidad-de-cables"></a>
- **Tipo:** Range Domain · **Tipo de campo:** Integer · **Rango válido:** 1 – 8

### Measured Length
<a id="measured-length"></a>
- **Tipo:** Range Domain · **Tipo de campo:** Double · **Rango válido:** 1 – 1000000000

---

## 🟩 Catálogos pequeños fijos (≤40 miembros)

**136 dominios.** Se listan completos — son estables y seguros de referenciar en código.

Índice rápido: [Activacion](#activacion) · [AncillaryRoleDomain](#ancillaryroledomain) · [AnnotationStatus](#annotationstatus) · [Capacidad PBT](#capacidad-pbt) · [Capacidad Regulador Tension Unidad](#capacidad-regulador-tension-unidad) · [Circuito BV](#circuito-bv) · [Config Lado Baja Banco Transf](#config-lado-baja-banco-transf) · [Configuracion Conexion](#configuracion-conexion) · [Configuracion de Alimentador](#configuracion-de-alimentador) · [Configuracion de Conductores](#configuracion-de-conductores) · [Corriente Corto Circuito](#corriente-corto-circuito) · [Corriente Nominal](#corriente-nominal) · [DominioRamal](#dominioramal) · [Empresas](#empresas) · [EnabledDomain](#enableddomain) · [EstCliente](#estcliente) · [Estado](#estado) · [Estado Interruptor](#estado-interruptor) · [Estado Operacion](#estado-operacion) · [Estruc Linea Subterr](#estruc-linea-subterr) · [Estructura Alumbrado Publ](#estructura-alumbrado-publ) · [Estructura Pararrayo](#estructura-pararrayo) · [Estructura Punta Terminal](#estructura-punta-terminal) · [Estructura Subterranea](#estructura-subterranea) · [ExisteNovedad](#existenovedad) · [Fase Conexion](#fase-conexion) · [Fase Conexion Bifasica](#fase-conexion-bifasica) · [Fase Conexion Monofasica](#fase-conexion-monofasica) · [Fase Conexion Trifasica](#fase-conexion-trifasica) · [FdrMgrNonTraceable](#fdrmgrnontraceable) · [Fuente Medicion](#fuente-medicion) · [FuenteEnergia](#fuenteenergia) · [Generador ConexiónConfiguración](#generador-conexionconfiguracion) · [Generador VoltajeNominal](#generador-voltajenominal) · [HorizontalAlignment](#horizontalalignment) · [Indicador Si-No](#indicador-si-no) · [Indicador Si-No (entero)](#indicador-si-no-entero) · [IndicadorTerna](#indicadorterna) · [Lum_Clasificacion_AP](#lumclasificacionap) · [Lum_Propiedad](#lumpropiedad) · [Marca Switch](#marca-switch) · [Material Estruct. Subt.](#material-estruct-subt) · [Material Relleno](#material-relleno) · [MaterialTapa](#materialtapa) · [Medio Aislante](#medio-aislante) · [NoVias](#novias) · [Novedades](#novedades) · [PCB](#pcb) · [PS_TipoUso](#pstipouso) · [PT_TipoRed](#pttipored) · [P_Control](#pcontrol) · [P_TipoUso](#ptipouso) · [Phase Designation](#phase-designation) · [Posicion Abertura](#posicion-abertura) · [Potencia Nominal Transformador Potencia Unidad](#potencia-nominal-transformador-potencia-unidad) · [ProcedenciaTapa](#procedenciatapa) · [Propietario](#propietario) · [Proteccion Puesto Baja Tension](#proteccion-puesto-baja-tension) · [Provincias](#provincias) · [Secuencia Fase](#secuencia-fase) · [Secuencia Fase BV](#secuencia-fase-bv) · [Surface Structure - Pad Material](#surface-structure---pad-material) · [Tap Neutral](#tap-neutral) · [Tap Normal](#tap-normal) · [Tap Porcentaje](#tap-porcentaje) · [Taps Numero](#taps-numero) · [Tension de Circuito Fuente](#tension-de-circuito-fuente) · [Tipo Alimentador](#tipo-alimentador) · [Tipo Material](#tipo-material) · [Tipo Poste](#tipo-poste) · [Tipo Subestacion](#tipo-subestacion) · [Tipo Tramo Baja](#tipo-tramo-baja) · [Tipo de Cimiento de Poste](#tipo-de-cimiento-de-poste) · [Tipo de Tap Transformador Unidad](#tipo-de-tap-transformador-unidad) · [TipoContratoGenerador](#tipocontratogenerador) · [TipoFusible](#tipofusible) · [TipoGeneradorDist](#tipogeneradordist) · [TipoMedidorCIS](#tipomedidorcis) · [TipoReguladorGenerador](#tiporeguladorgenerador) · [TipoSecciFusible](#tiposeccifusible) · [TipoTrafo](#tipotrafo) · [TipoTrafoPotencia](#tipotrafopotencia) · [ULS Material - Duct Bank](#uls-material---duct-bank) · [ULS Size](#uls-size) · [UP_AP_INDUCCION](#upapinduccion) · [UP_AP_LUMIN_HG_ABIERTA](#upapluminhgabierta) · [UP_AP_LUMIN_MH](#upapluminmh) · [UP_AP_PROYECTOR_MH](#upapproyectormh) · [UP_CS_A](#upcsa) · [UP_CS_C](#upcsc) · [UP_CS_P](#upcsp) · [UP_CS_V](#upcsv) · [UP_PA_PORTAFUSIBLE](#uppaportafusible) · [UP_PA_TIPO_CODO](#uppatipocodo) · [UP_PA_TIPO_T](#uppatipot) · [UP_PO_MADERA](#uppomadera) · [UP_PO_PLASTICO](#uppoplastico) · [UP_PO_SEMAFORO](#upposemaforo) · [UP_PPBT_ESTANCO](#upppbtestanco) · [UP_PPBT_IT](#upppbtit) · [UP_PPBT_NH](#upppbtnh) · [UP_PPD_CELDA_INT](#upppdceldaint) · [UP_PPD_CELDA_PROT](#upppdceldaprot) · [UP_PPD_CELDA_SEC](#upppdceldasec) · [UP_PPD_INTERRUPTORES_SUB](#upppdinterruptoressub) · [UP_PR_2F](#uppr2f) · [UP_PSC_TRIPOL](#uppsctripol) · [UP_PSC_TRIPOL_ROMPE](#uppsctripolrompe) · [UP_PSF_UNIPOL_ABIERTO](#uppsfunipolabierto) · [UP_PSF_UNIPOL_ABIERTO_ROMPE](#uppsfunipolabiertorompe) · [UP_PSF_UNIPOL_CERRADO](#uppsfunipolcerrado) · [UP_PUESTA_TIERRA](#uppuestatierra) · [UP_TE_BT](#uptebt) · [UP_TE_MT](#uptemt) · [UP_TE_ST](#uptest) · [UP_TF_BT](#uptfbt) · [UP_TF_DOBLE](#uptfdoble) · [UP_TF_MT](#uptfmt) · [UP_TORRE](#uptorre) · [UP_TP_BT](#uptpbt) · [UP_TP_DOBLE](#uptpdoble) · [UP_TP_MT](#uptpmt) · [UP_TRF_1F_PAD_EXT](#uptrf1fpadext) · [UP_TRF_2F_CABINA](#uptrf2fcabina) · [UP_TRF_2F_PAD_EXT](#uptrf2fpadext) · [UP_TT_BT](#upttbt) · [UP_TT_DOBLE](#upttdoble) · [UP_TT_MT](#upttmt) · [Ubicacion Switch](#ubicacion-switch) · [VerticalAlignment](#verticalalignment) · [Voltaje AT](#voltaje-at) · [Voltaje AT/MT](#voltaje-atmt) · [Voltaje BT](#voltaje-bt) · [Voltaje MT](#voltaje-mt) · [ZONA](#zona) · [kVAR Capacitor Unidad](#kvar-capacitor-unidad)

### Activacion
<a id="activacion"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer

| Nombre | Valor |
|---|---|
| Manual | `1` |
| Automática | `2` |
| Motorizado | `3` |

### AncillaryRoleDomain
<a id="ancillaryroledomain"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer

| Nombre | Valor |
|---|---|
| None | `0` |
| Source | `1` |
| Sink | `2` |

### AnnotationStatus
<a id="annotationstatus"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer
- **Descripción:** Valid annotation state values.

| Nombre | Valor |
|---|---|
| Placed | `0` |
| Unplaced | `1` |

### Capacidad PBT
<a id="capacidad-pbt"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Capacidad del Puesto Proteccion Baja Tension

| Nombre | Valor |
|---|---|
| 20 A | `20` |
| 25 A | `25` |
| 36 A | `36` |
| 63 A | `63` |
| 80 A | `80` |
| 100 A | `100` |
| 125 A | `125` |
| 160 A | `160` |
| 225 A | `225` |
| 250 A | `250` |
| 315 A | `315` |
| 400 A | `400` |
| 500 A | `500` |
| 630 A | `630` |
| 700 A | `700` |
| 1000 A | `1000` |

### Capacidad Regulador Tension Unidad
<a id="capacidad-regulador-tension-unidad"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Capacidad Regulador Tension Unidad

| Nombre | Valor |
|---|---|
| 50 kVA | `50` |
| 76.2 kVA | `76.2` |
| 100 kVA | `100` |
| 127 kVA | `127` |
| 144 kVA | `144` |
| 150 kVA | `150` |
| 167 kVA | `167` |
| 200 kVA | `200` |
| 288 kVA | `288` |
| 300 kVA | `300` |
| 381 kVA | `381` |
| 400 kVA | `400` |
| 432 kVA | `432` |
| 501 kVA | `501` |
| 864 kVA | `864` |

### Circuito BV
<a id="circuito-bv"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Configuracion de los circuitos de bajo voltaje

| Nombre | Valor |
|---|---|
| A | `A` |
| B | `B` |
| C | `C` |
| AB | `AB` |
| BC | `BC` |
| AC | `AC` |
| ABC | `ABC` |
| F1 | `F1` |
| F2 | `F2` |
| F12 | `F12` |

### Config Lado Baja Banco Transf
<a id="config-lado-baja-banco-transf"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| Linea Monofasica | `L` |
| Estrella | `Y` |
| Estrella Abierta | `YA` |
| Delta | `DE` |
| Delta Aterrado | `DT` |
| Delta Abierta | `D` |

### Configuracion Conexion
<a id="configuracion-conexion"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| Estrella | `Y` |
| Delta | `DE` |
| Linea Monofasica | `L` |

### Configuracion de Alimentador
<a id="configuracion-de-alimentador"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| Radial | `R` |
| Malla | `M` |

### Configuracion de Conductores
<a id="configuracion-de-conductores"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| 1F1C | `11` |
| 1F2C | `12` |
| 1F3C | `13` |
| 1F4C | `14` |
| 2F2C | `22` |
| 2F3C | `23` |
| 2F4C | `24` |
| 2F5C | `25` |
| 3F3C | `33` |
| 3F4C | `34` |
| 3F5C | `35` |

### Corriente Corto Circuito
<a id="corriente-corto-circuito"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Integer
- **Descripción:** Corriente Corto Circuito

| Nombre | Valor |
|---|---|
| 2.5 kA | `2500` |
| 4 kA | `4000` |
| 6 kA | `6000` |
| 8 kA | `8000` |
| 10 kA | `10000` |
| 12 kA | `12000` |
| 12.5 kA | `12500` |
| 16 kA | `16000` |
| 18 kA | `18000` |
| 20 kA | `20000` |
| 25 kA | `25000` |
| 30 kA | `31000` |
| 31.5 kA | `31500` |
| 40 kA | `40000` |

### Corriente Nominal
<a id="corriente-nominal"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Double
- **Descripción:** Corriente Nominal

| Nombre | Valor |
|---|---|
| 50 A | `50` |
| 100 A | `100` |
| 200 A | `200` |
| 250 A | `250` |
| 280 A | `280` |
| 300 A | `300` |
| 400 A | `400` |
| 560 A | `560` |
| 600 A | `600` |
| 630 A | `630` |
| 800 A | `800` |
| 900 A | `900` |
| 1200 A | `1200` |
| 1250 A | `1250` |
| 2000 A | `2000` |

### DominioRamal
<a id="dominioramal"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| Troncal | `Troncal` |
| Ramal Primario | `Primario` |
| Ramal Secundario | `Secundario` |
| Ramal Terciario | `Terciario` |
| Ramal Trafo | `Trafo` |

### Empresas
<a id="empresas"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| CNELEP-MANABI | `CNELMANABI` |
| CNELEP-EL ORO | `CNELELORO` |
| CNELEP-SANTO DOMINGO | `CNELSTODGO` |
| CNELEP-SANTA ELENA | `CNELSTAELE` |
| CNELEP-GUAYAS LOS RIOS | `CNELGYERIO` |
| CNELEP-SUCUMBIOS | `CNELSUC` |
| CNELEP-MILAGRO | `CNELMLG` |
| CNELEP-ESMERALDAS | `CNELESM` |
| CNELEP-LOS RIOS | `CNELLRS` |
| CNELEP-BOLIVAR | `CNELBOL` |
| EERCS | `EERCS` |
| EERSA | `EER` |
| ELEPCO | `EEC` |
| EMELNORTE | `EEN` |
| EERSSA | `EERSSA` |
| EEQ | `EEQ` |
| EEA | `EEA` |
| EEASA | `EEASA` |
| CNELEP-GUAYAQUIL | `CNELGYE` |
| EEG | `EEG` |

### EnabledDomain
<a id="enableddomain"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer

| Nombre | Valor |
|---|---|
| False | `0` |
| True | `1` |

### EstCliente
<a id="estcliente"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| Suspendido Definitivo | `W` |
| Activo | `A` |
| Cambio de Medidor | `Y` |
| Cortado | `C` |
| Eliminado | `E` |
| En convenio de Pago | `D` |
| En Proceso de Retiro | `J` |
| Eventual | `V` |
| Para Corte | `P` |
| Para Reconexión | `R` |
| Para Reinstalación | `G` |
| Para Retiro | `I` |
| Para Suspensión | `T` |
| Retirado | `F` |
| Suspendido Definitivo | `U` |
| Suspensión Temporal | `S` |
| Convenio, Cortado | `B` |
| Convenio, Reconectado | `H` |
| Convenio, Para Corte | `K` |
| Convenio, Para Reconexion | `L` |
| Convenio, Para Retiro | `N` |
| Reconectados | `M` |
| Convenio, Proc.Retiro | `Q` |
| Gestion Comercial | `1` |
| Cliente en Directorio | `4` |
| Incobrable | `5` |
| En Directorio x Depos | `6` |
| Susp.Definitiva Antig | `7` |
| Liquidacion en Proceso | `2` |
| Gestion Legal | `3` |

### Estado
<a id="estado"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer

| Nombre | Valor |
|---|---|
| Buen Estado | `1` |
| Mal Estado | `2` |

### Estado Interruptor
<a id="estado-interruptor"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| NA | `NA` |
| NC | `NC` |

### Estado Operacion
<a id="estado-operacion"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| NA | `NA` |
| NC | `NC` |

### Estruc Linea Subterr
<a id="estruc-linea-subterr"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| D1 | `E404001` |
| D2 | `E404002` |
| D3 | `E404003` |
| D4 | `E404004` |
| Z0 | `E403000` |
| Z1 | `E403001` |
| Z2 | `E403002` |
| Z3 | `E403003` |
| 0B1x2B1 | `EU0003` |
| 0B1x3B1 | `EU0004` |
| 0B1x4B1 | `EU0005` |
| 0B2x2B1 | `EU0006` |
| 0B2x3B1 | `EU0007` |
| 0B2x4B1 | `EU0008` |
| 0B3x2B1 | `EU0009` |
| 0B3x3B1 | `EU0010` |
| 0B3x4B1 | `EU0011` |
| 0B4x2B1 | `EU0012` |
| 0B4x3B1 | `EU0013` |
| 0B1x2C1 | `EU0014` |
| 0B2x2C1 | `EU0015` |
| 0B(1x2C+2x2B)1 | `EU0016` |
| 0B(2x2C+1x2B)1 | `EU0017` |
| 0B1x2B2 | `EU0018` |
| 0B1x3B2 | `EU0019` |
| 0B1x4B2 | `EU0020` |
| 0B2x2B2 | `EU0021` |
| 0B2x3B2 | `EU0022` |
| 0B2x4B2 | `EU0023` |
| 0B3x2B2 | `EU0024` |
| 0B3x3B2 | `EU0025` |
| 0B3x4B2 | `EU0026` |
| 0B4x2B2 | `EU0027` |
| 0B4x3B2 | `EU0028` |
| 0B1x2C2 | `EU0029` |
| 0B2x2C2 | `EU0030` |
| 0B(1x2C+2x2B)2 | `EU0031` |
| 0B(2x2C+1x2B)2 | `EU0032` |

### Estructura Alumbrado Publ
<a id="estructura-alumbrado-publ"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| CAPRL | `L852400` |
| CAF | `L852401` |
| CAPRLJ | `L852402` |

### Estructura Pararrayo
<a id="estructura-pararrayo"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

_(sin miembros registrados)_

### Estructura Punta Terminal
<a id="estructura-punta-terminal"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| Terminal Cable Subestación Exterior Caucho Silicon 3P 25 Kv (3/0) | `P201320` |
| Terminal Cable Subestación Exterior Caucho Silicon 3P 25 Kv (350) | `P201323` |
| Terminal Cable Subestación Exterior Tripolar 7693-5A-P (250 MCM) | `P201752` |
| Terminal Cable Subestación Interior Caucho Silicon 3P 25Kv | `P202325` |
| Terminal Cable Subestación Exterior Resina 3P 6Kv | `P201306` |
| Punta terminal 3M contraible en frio exterior | `P201031` |
| Punta terminal 3M contraible en frio interior | `P202031` |
| Punta terminal interior polimérico | `P202041` |
| Punta terminal exterior polimérico | `P201061` |

### Estructura Subterranea
<a id="estructura-subterranea"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| 0CS | `EU0001` |
| 0CN | `EU0002` |
| 0PA | `EU0033` |
| 0PB | `EU0034` |
| 0PC | `EU0035` |
| 0PD | `EU0036` |
| 0PE | `EU0037` |
| 0PX | `EU0038` |
| 0PY | `EU0039` |
| 0PZ | `EU0040` |

### ExisteNovedad
<a id="existenovedad"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer

| Nombre | Valor |
|---|---|
| Si | `1` |
| No | `2` |

### Fase Conexion
<a id="fase-conexion"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Integer

| Nombre | Valor |
|---|---|
| A | `4` |
| B | `2` |
| C | `1` |
| AC | `5` |
| AB | `6` |
| BC | `3` |
| ABC | `7` |

### Fase Conexion Bifasica
<a id="fase-conexion-bifasica"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Integer

| Nombre | Valor |
|---|---|
| AB | `6` |
| AC | `5` |
| BC | `3` |

### Fase Conexion Monofasica
<a id="fase-conexion-monofasica"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Integer

| Nombre | Valor |
|---|---|
| A | `4` |
| B | `2` |
| C | `1` |

### Fase Conexion Trifasica
<a id="fase-conexion-trifasica"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Integer

| Nombre | Valor |
|---|---|
| ABC | `7` |

### FdrMgrNonTraceable
<a id="fdrmgrnontraceable"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Integer

| Nombre | Valor |
|---|---|
| Non-Traceable | `1` |
| Traceable | `0` |

### Fuente Medicion
<a id="fuente-medicion"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| Medicion de Campo | `MC` |
| Sistema de Mapeo | `SM` |

### FuenteEnergia
<a id="fuenteenergia"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Fuente de Energía

| Nombre | Valor |
|---|---|
| Convencional | `Convencional` |
| Fotovoltaico | `Fotovoltaico` |
| Eólica | `Eólica` |
| Biomasa | `Biomasa` |
| Mini Hidráulica | `Mini Hidráulica` |

### Generador ConexiónConfiguración
<a id="generador-conexionconfiguracion"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Generador Conexión Configuración

| Nombre | Valor |
|---|---|
| Delta | `DE` |
| Estrella | `Y` |

### Generador VoltajeNominal
<a id="generador-voltajenominal"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Generador VoltajeNominal

| Nombre | Valor |
|---|---|
| 4.16 kV Grounded Y | `120` |
| 7.2 kV Grounded Y | `160` |
| 12.5 kV Grounded Y | `210` |
| 13.2 kV Grounded Y | `230` |
| 13.8 kV Grounded Y | `270` |
| 24.9 kV Grounded Y | `340` |
| 34.5 kV Grounded Y | `380` |
| 2400 V Delta | `80` |
| 4160 V Delta | `110` |
| 7200 V Delta | `150` |
| 13800 V Delta | `260` |

### HorizontalAlignment
<a id="horizontalalignment"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer
- **Descripción:** Valid horizontal symbol alignment values.

| Nombre | Valor |
|---|---|
| Left | `0` |
| Center | `1` |
| Right | `2` |
| Full | `3` |

### Indicador Si-No
<a id="indicador-si-no"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| No | `N` |
| Si | `S` |

### Indicador Si-No (entero)
<a id="indicador-si-no-entero"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer

| Nombre | Valor |
|---|---|
| Si | `1` |
| No | `0` |

### IndicadorTerna
<a id="indicadorterna"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| DOBLE | `2` |
| TRIBLE | `3` |

### Lum_Clasificacion_AP
<a id="lumclasificacionap"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Clasificacion Luminarias AP

| Nombre | Valor |
|---|---|
| General | `General` |
| Ornamental | `Ornamental` |
| Intervenido | `Intervenido` |
| Escenario Deportivo | `Escenario Deportivo` |

### Lum_Propiedad
<a id="lumpropiedad"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Propiedad de las Luminarias

| Nombre | Valor |
|---|---|
| Distribuidora | `Distribuidora` |
| Municipal | `Municipal` |

### Marca Switch
<a id="marca-switch"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer

| Nombre | Valor |
|---|---|
| SCHNEIDER | `1` |
| S&C | `2` |
| MENCO | `3` |
| KEARNEY | `4` |
| JOSLYN | `5` |
| G&W | `6` |
| ABB | `7` |
| MORPAC | `8` |
| PORTER | `9` |
| TURNER | `10` |

### Material Estruct. Subt.
<a id="material-estruct-subt"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Material Estructura Subterranea

| Nombre | Valor |
|---|---|
| Manpostería | `1` |
| Hormigón | `2` |
| Otros | `3` |

### Material Relleno
<a id="material-relleno"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| Ladrillo y Arena | `LAA` |
| Concreto | `CON` |
| Piedra y Arena | `PIA` |

### MaterialTapa
<a id="materialtapa"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer
- **Descripción:** Material Tapa de Paso

| Nombre | Valor |
|---|---|
| Grafito | `0` |
| Hormigon | `1` |
| Metalico | `2` |

### Medio Aislante
<a id="medio-aislante"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| Aire | `Aire` |
| Aceite | `Aceite` |
| Gas | `Gas` |
| Fusible | `Fusible` |
| Papel | `Papel` |

### NoVias
<a id="novias"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| 1 | `1` |
| 2 | `2` |
| 3:2:1 | `3:2:1` |
| 5:1:4 | `5:1:4` |
| 5:2:3 | `5:2:3` |
| 5:3:2 | `5:3:2` |
| 6:1:5 | `6:1:5` |
| 6:2:4 | `6:2:4` |
| 6:3:3 | `6:3:3` |
| 6:4:2 | `6:4:2` |

### Novedades
<a id="novedades"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer

| Nombre | Valor |
|---|---|
| Hurto | `5` |
| Sin Novedad | `0` |
| Medidor Alto (se requiere escalera) | `1` |
| Medidor dentro del Predio | `2` |
| Puerta Cerrada / No dejan inspeccionar | `3` |
| Servicio Convenido | `4` |
| Acometida Subterránea o Empotrada | `6` |
| Revisar Medidor | `7` |
| Revisar Medidor especial | `8` |
| Medidor sin sello, caja, tapa | `9` |
| Revisar Acometida | `10` |
| Luminaria con conexión directa | `11` |
| Medidor Quemado - Destruido o Dañado | `12` |
| Medidor Abandonado | `13` |
| Revisar Caja de Distribución | `14` |

### PCB
<a id="pcb"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** PCB

| Nombre | Valor |
|---|---|
| SI | `SI` |
| No | `No` |
| No Determinado | `NoDetermin` |

### PS_TipoUso
<a id="pstipouso"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** PS_TipoUso

| Nombre | Valor |
|---|---|
| Línea | `Línea` |
| Transferencia | `Transferencia` |
| Celda | `Celda` |
| Cabecera Alimentador | `Cabecera Alimentador` |
| Totalizador | `Totalizador` |

### PT_TipoRed
<a id="pttipored"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** PT_TipoRed

| Nombre | Valor |
|---|---|
| Abierta | `Abierta` |
| Preensamblada | `Preensamblada` |
| Mixta | `Mixta` |
| Subterranea | `Subterranea` |
| MultiAluminio | `MultiAluminio` |
| Antihurto | `Antihurto` |

### P_Control
<a id="pcontrol"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** P_Control

| Nombre | Valor |
|---|---|
| Manual | `Manual` |
| Telecomandado | `Telecomandado` |

### P_TipoUso
<a id="ptipouso"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** P_TipoUso

| Nombre | Valor |
|---|---|
| Línea | `Línea` |
| Transferencia | `Transferencia` |
| Cabecera Alimentador | `Cabecera Alimentador` |
| Celda | `Celda` |

### Phase Designation
<a id="phase-designation"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Integer

| Nombre | Valor |
|---|---|
| A | `4` |
| B | `2` |
| C | `1` |
| AC | `5` |
| AB | `6` |
| BC | `3` |
| ABC | `7` |

### Posicion Abertura
<a id="posicion-abertura"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Integer

| Nombre | Valor |
|---|---|
| Abierto | `0` |
| Cerrado | `1` |
| No Aplicable | `2` |

### Potencia Nominal Transformador Potencia Unidad
<a id="potencia-nominal-transformador-potencia-unidad"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| 2.5 MVA | `25` |
| 5 MVA | `5` |
| 6 MVA | `6` |
| 6.5 MVA | `65` |
| 10 MVA | `10` |
| 12.5 MVA | `125` |
| 15 MVA | `15` |
| 20 MVA | `20` |
| 18 MVA | `18` |
| 12 MVA | `12` |
| 16 MVA | `16` |
| 6.25 MVA | `625` |
| 2 MVA | `2` |
| 4 MVA | `4` |
| 3.75 MVA | `375` |
| 7 MVA | `7` |

### ProcedenciaTapa
<a id="procedenciatapa"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer
- **Descripción:** Procedencia de Tapa

| Nombre | Valor |
|---|---|
| E.E | `0` |
| Brasilera | `1` |
| Francesa | `2` |

### Propietario
<a id="propietario"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| PARTICULAR | `PARTICULAR` |
| CNELEP-MANABI | `CNELMANABI` |
| CNELEP-SANTO DOMINGO | `CNELSTODGO` |
| CNELEP-SANTA ELENA | `CNELSTAELE` |
| CNELEP-EL ORO | `CNELELORO` |
| CNELEP-GUAYAS LOS RIOS | `CNELGYERIO` |
| CNELEP-SUCUMBIOS | `CNELSUC` |
| CNELEP-MILAGRO | `CNELMLG` |
| CNELEP-ESMERALDAS | `CNELESM` |
| CNELEP-LOS RIOS | `CNELLRS` |
| CNELEP-BOLIVAR | `CNELBOL` |
| EERCS | `EERCS` |
| EERSA | `EER` |
| ELEPCO | `EEC` |
| EMELNORTE | `EEN` |
| EERSSA | `EERSSA` |
| EEQ | `EEQ` |
| EEA | `EEA` |
| EEASA | `EEASA` |
| CNELEP-GUAYAQUIL | `CNELGYE` |
| EEG | `EEG` |

### Proteccion Puesto Baja Tension
<a id="proteccion-puesto-baja-tension"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| P15 | `P301015` |
| P20 | `P301020` |
| P30 | `P301030` |
| P40 | `P301040` |
| P50 | `P301050` |
| P60 | `P301060` |
| P70 | `P301070` |
| P100 | `P301100` |
| P125 | `P301125` |
| P175 | `P301175` |
| P225 | `P301225` |
| P300 | `P301300` |
| P350 | `P301350` |
| F20A | `P302020` |
| F30A | `P302030` |
| F35A | `P302035` |
| F36A | `P302036` |
| F50A | `P302050` |
| F60A | `P302060` |
| F63A | `P302063` |
| F80A | `P302080` |
| F100A | `P302100` |
| F125A | `P302125` |
| F160A | `P302160` |
| F200A | `P302200` |
| F224A | `P302224` |
| F250A | `P302250` |
| F315A | `P302315` |
| F355A | `P302355` |
| F400A | `P302400` |

### Provincias
<a id="provincias"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| AZUAY | `01` |
| BOLIVAR | `02` |
| CANAR | `03` |
| CARCHI | `04` |
| COTOPAXI | `05` |
| CHIMBORAZO | `06` |
| EL ORO | `07` |
| ESMERALDAS | `08` |
| GUAYAS | `09` |
| IMBABURA | `10` |
| LOJA | `11` |
| LOS RIOS | `12` |
| MANABI | `13` |
| MORONA SANTIAGO | `14` |
| NAPO | `15` |
| PASTAZA | `16` |
| PICHINCHA | `17` |
| TUNGURAHUA | `18` |
| ZAMORA CHINCHIPE | `19` |
| GALAPAGOS | `20` |
| SUCUMBIOS | `21` |
| ORELLANA | `22` |
| SANTO DOMINGO DE LOS TSACHILAS | `23` |
| SANTA ELENA | `24` |
| ZONA NO DELIMITADA | `90` |

### Secuencia Fase
<a id="secuencia-fase"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Secuencia Fase

| Nombre | Valor |
|---|---|
| A | `A` |
| B | `B` |
| C | `C` |
| AB | `AB` |
| BA | `BA` |
| AC | `AC` |
| CA | `CA` |
| BC | `BC` |
| CB | `CB` |
| ABC | `ABC` |
| ACB | `ACB` |
| BAC | `BAC` |
| BCA | `BCA` |
| CBA | `CBA` |
| CAB | `CAB` |

### Secuencia Fase BV
<a id="secuencia-fase-bv"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Secuencia Fase de Bajo Voltaje

| Nombre | Valor |
|---|---|
| a | `a` |
| b | `b` |
| c | `c` |
| ab | `ab` |
| ac | `ac` |
| bc | `bc` |
| abc | `abc` |

### Surface Structure - Pad Material
<a id="surface-structure---pad-material"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| Other | `OTH` |
| Fibra de Vidrio | `B` |
| Concreto | `C` |

### Tap Neutral
<a id="tap-neutral"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer

| Nombre | Valor |
|---|---|
| 0 | `0` |
| 1 | `1` |
| 2 | `2` |
| 3 | `3` |
| 4 | `4` |
| 5 | `5` |
| 6 | `6` |
| 7 | `7` |
| 8 | `8` |
| 9 | `9` |
| 10 | `10` |
| 11 | `11` |
| 12 | `12` |
| 13 | `13` |
| 14 | `14` |
| 15 | `15` |
| 16 | `16` |
| 17 | `17` |
| 18 | `18` |
| 19 | `19` |
| 20 | `20` |
| 21 | `21` |
| 22 | `22` |
| 23 | `23` |
| 24 | `24` |
| 25 | `25` |
| 26 | `26` |
| 27 | `27` |
| 28 | `28` |
| 29 | `29` |
| 30 | `30` |
| 31 | `31` |
| 32 | `32` |

### Tap Normal
<a id="tap-normal"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer

| Nombre | Valor |
|---|---|
| 0 | `0` |
| 1 | `1` |
| 2 | `2` |
| 3 | `3` |
| 4 | `4` |
| 5 | `5` |
| 6 | `6` |
| 7 | `7` |
| 8 | `8` |
| 9 | `9` |
| 10 | `10` |
| 11 | `11` |
| 12 | `12` |
| 13 | `13` |
| 14 | `14` |
| 15 | `15` |
| 16 | `16` |
| 17 | `17` |
| 18 | `18` |
| 19 | `19` |
| 20 | `20` |
| 21 | `21` |
| 22 | `22` |
| 23 | `23` |
| 24 | `24` |
| 25 | `25` |
| 26 | `26` |
| 27 | `27` |
| 28 | `28` |
| 29 | `29` |
| 30 | `30` |
| 31 | `31` |
| 32 | `32` |

### Tap Porcentaje
<a id="tap-porcentaje"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer

| Nombre | Valor |
|---|---|
| 0 | `0` |
| 0.625 | `625` |
| 1 | `1` |
| 2 | `2` |
| 2.5 | `25` |
| 5 | `5` |
| 7.5 | `75` |
| 8.75 | `875` |
| 9.4 | `94` |
| 10 | `10` |
| 11.3 | `113` |
| 13.1 | `131` |
| 15 | `15` |

### Taps Numero
<a id="taps-numero"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer

| Nombre | Valor |
|---|---|
| 0 | `0` |
| 5 | `5` |
| 32 | `32` |

### Tension de Circuito Fuente
<a id="tension-de-circuito-fuente"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Integer

| Nombre | Valor |
|---|---|
| 34.5 kV | `34500` |
| 23.0 kV | `23000` |
| 22.8 kV | `22800` |
| 22.0 kV | `22000` |
| 19.92 kV | `19919` |
| 13.8 kV | `13800` |
| 13.28 kV | `13279` |
| 13.2 kV | `13200` |
| 13.16 kV | `13164` |
| 12.70 kV | `12702` |
| 7.97 kV | `7967` |
| 7.62 kV | `7621` |
| 6.3 kV | `6300` |
| 4.16 kV | `4160` |

### Tipo Alimentador
<a id="tipo-alimentador"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| Rural | `R` |
| Urbano | `U` |

### Tipo Material
<a id="tipo-material"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| Metalico | `1` |
| Plastico | `2` |

### Tipo Poste
<a id="tipo-poste"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer
- **Descripción:** Tipo Poste

| Nombre | Valor |
|---|---|
| Alumbrado Público | `1` |
| Baja | `2` |
| Media | `3` |
| Media Baja | `4` |
| Acometida | `5` |
| Tensor | `6` |
| Subtransmision | `7` |
| Semaforización | `8` |
| Vigilancia | `9` |
| Sin Red | `10` |

### Tipo Subestacion
<a id="tipo-subestacion"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| Exterior 69/22kV a nivel | `S102692` |
| Exterior 69/13.8kV a nivel | `S102691` |
| Exterior 69/34.5kV a nivel | `S102693` |
| Interior 22/6.3kV a nivel | `S101220` |

### Tipo Tramo Baja
<a id="tipo-tramo-baja"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer
- **Descripción:** Tipo Tramo Baja Aereo y Subt.

| Nombre | Valor |
|---|---|
| Distribución | `0` |
| Alumbrado Público | `1` |
| Particular | `2` |
| Semaforización - Vigilancia | `3` |

### Tipo de Cimiento de Poste
<a id="tipo-de-cimiento-de-poste"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| Directamente a Tierra | `DT` |
| Fundido Hormigon | `FH` |
| Canastilla de Hormigon | `CH` |

### Tipo de Tap Transformador Unidad
<a id="tipo-de-tap-transformador-unidad"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| 1 Arriba/3 Abajo | `13` |
| 2 Arriba/2 abajo | `22` |
| 4 Arriba | `4A` |
| 5 Arriba | `5` |
| 16 Arriba/16 abajo | `16` |
| Otro | `O` |
| Ninguno | `NN` |

### TipoContratoGenerador
<a id="tipocontratogenerador"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Tipo Contrato Generador

| Nombre | Valor |
|---|---|
| Estándar | `0` |
| Especial | `1` |

### TipoFusible
<a id="tipofusible"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| K | `K` |
| NX | `NX` |
| NXD | `NXD` |
| PEPA | `PEPA` |
| XC | `XC` |

### TipoGeneradorDist
<a id="tipogeneradordist"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer
- **Descripción:** Tipo Generador Distribuido

| Nombre | Valor |
|---|---|
| Convencional | `0` |
| No Convencional | `1` |

### TipoMedidorCIS
<a id="tipomedidorcis"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Tipo de Medidor CIS

| Nombre | Valor |
|---|---|
| Eletromecánico-Directa-Bornera | `0601` |
| Eletromecánico-Directa-Socket | `0602` |
| Eletromec-Indirecta-Bornera | `0603` |
| Eletromec-Indirecta-Socket | `0604` |
| Ciclométrico-Directa-Bornera | `0605` |
| Ciclométrico-Directa-Socket | `0606` |
| Electrónico-Directa-Bornera | `0607` |
| Electrónico-Directa-Socket | `0608` |
| Electrónico-Indirecta-Bornera | `0609` |
| Electrónico-Indirecta-Socket | `0610` |
| Electrónico-TotalizadorS/E-S/T | `0612` |
| Electrónico-Telemedición | `0620` |
| Electrónico-Prepago | `0625` |
| M-TC-Ventana-Interior | `1501` |
| M-TC-Ventana-Exterior | `1502` |
| M-TC-Devanado-Interio | `1503` |
| M-TC-Devanado-Exterio | `1504` |
| M-TP-Interior | `1505` |
| M-TP-Exterior | `1506` |
| M-Combinado-Exterior | `1507` |
| T-2elementos-Combinado-Exterior | `1508` |
| T-3elementos-Combinado-Exterior | `1509` |
| M-TC-Conmutable | `1510` |
| T-COMBINADO-AUTORANGO | `1511` |

### TipoReguladorGenerador
<a id="tiporeguladorgenerador"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer
- **Descripción:** Tipo de Regulador del Generador

| Nombre | Valor |
|---|---|
| Regulador P0 | `0` |
| Regulador QV | `1` |
| Ambos | `2` |

### TipoSecciFusible
<a id="tiposeccifusible"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer

| Nombre | Valor |
|---|---|
| Secc.Fusib. de Linea | `1` |
| Secc.Fusib. de Trafo | `2` |
| Secc.Fusib. Virtual | `3` |
| Secc.Fusib. Transferencia | `4` |
| Secc.Fusib. de Capacitor | `5` |
| Secc.Fusib. de Celda | `6` |

### TipoTrafo
<a id="tipotrafo"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer
- **Descripción:** Tipo de Transformador

| Nombre | Valor |
|---|---|
| Distribución | `1` |
| Alumbrado Publico | `2` |
| Expreso | `3` |
| Arrendado | `4` |
| Medición | `5` |
| Desconectado | `6` |

### TipoTrafoPotencia
<a id="tipotrafopotencia"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer
- **Descripción:** Tipo de Transformador de Potencia

| Nombre | Valor |
|---|---|
| Distribución | `1` |
| Subestación | `2` |

### ULS Material - Duct Bank
<a id="uls-material---duct-bank"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| Fibra | `FIB` |
| Acero | `STL` |
| Madera | `WOD` |
| Concreto | `CON` |
| Otro | `OTH` |
| Desconocido | `UNK` |
| Asbesto | `ASB` |
| PVC | `PVC` |

### ULS Size
<a id="uls-size"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| 1" | `1` |
| 2" | `2` |
| 3/4" | `3` |
| 4" | `4` |
| 6" | `6` |
| 8" | `8` |

### UP_AP_INDUCCION
<a id="upapinduccion"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Alumbrado Publico Luminaria de Induccion

| Nombre | Valor |
|---|---|
| LDPI80ACC | `APO0801` |
| AODFPI90A | `AOD0026` |
| AODFPI90P | `AOD0078` |

### UP_AP_LUMIN_HG_ABIERTA
<a id="upapluminhgabierta"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Alumbrado Publico Luminaria Hg Abierto

| Nombre | Valor |
|---|---|
| LDPM125PCA | `APO0101` |
| LDPM175PCA | `APO0102` |
| LDPM250PCA | `APO0103` |
| LDPM125ACA | `APO0104` |
| LDPM175ACA | `APO0105` |
| LCPM250ACA | `APO0131` |
| LDPM250ACA | `APO0106` |
| LDSM125PCA | `APO0107` |
| LDSM175PCA | `APO0108` |
| LDSM250PCA | `APO0109` |
| LDSM125ACA | `APO0110` |
| LDSM175ACA | `APO0111` |
| LDSM250ACA | `APO0112` |
| LDFM125PCA | `APO0113` |
| LDFM175PCA | `APO0114` |
| LDFM250PCA | `APO0115` |
| LDFM125ACA | `APO0116` |
| LDFM175ACA | `APO0117` |
| LDFM250ACA | `APO0118` |
| LDAM125PCA | `APO0119` |
| LDAM175PCA | `APO0120` |
| LDAM250PCA | `APO0121` |
| LDAM125ACA | `APO0122` |
| LDAM175ACA | `APO0123` |
| LDAM250ACA | `APO0124` |
| LDOM125ACA | `APO0125` |
| LDOM175ACA | `APO0126` |
| LDOM250ACA | `APO0127` |
| LDPM75ACA | `APO0128` |
| LDPM400PCA | `APO0129` |
| LDFM40PCA | `APO0130` |

### UP_AP_LUMIN_MH
<a id="upapluminmh"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Codigo Estuctura de Luminaria Metal Halide

| Nombre | Valor |
|---|---|
| AODPLH70A | `AOD0005` |
| AODPLH100A | `AOD0006` |
| AODPLH150A | `AOD0007` |
| AODPLH250A | `AOD0036` |
| AODPLH400A | `AOD0101` |
| AODPLH150P | `AOD0035` |
| AODPLH250P | `AOD0085` |
| AODPLH400P | `AOD0100` |
| AODFLH70A | `AOD0017` |
| AODFLH100A | `AOD0018` |
| AODFLH150A | `AOD0019` |
| AOCFLH54P | `AOC0001` |
| AODFLH250A | `AOD0104` |
| AODFLH250P | `AOD0105` |
| AODPLH450A | `AOD0132` |

### UP_AP_PROYECTOR_MH
<a id="upapproyectormh"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Codigo Estuctura de Proyector Metal Halide

| Nombre | Valor |
|---|---|
| AODPPH50A | `AOD0062` |
| AODIPH70A | `AOD0008` |
| AODPPH70P | `AOD0074` |
| AODIPH100A | `AOD0009` |
| AODPPH125A | `AOD0110` |
| AODIPH150A | `AOD0010` |
| AODIPH150P | `AOD0030` |
| AODPPH250A | `AOD0060` |
| AODIPH250A | `AOD0011` |
| AODPPH250P | `AOD0097` |
| AODPPH400A | `AOD0061` |
| AODIPH400A | `AOD0022` |
| AODPPH400P | `AOD0073` |
| AODPPH800A | `AOD0063` |
| AODPPH800P | `AOD0092` |
| AODPPH1000A | `AOD0059` |
| AODPPH1000P | `AOD0082` |

### UP_CS_A
<a id="upcsa"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Control Semaforización Acústica

| Nombre | Valor |
|---|---|
| SCPA1 | `CSP0006` |

### UP_CS_C
<a id="upcsc"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Control Semaforización Cámara

| Nombre | Valor |
|---|---|
| SCPC50 | `CSP0007` |

### UP_CS_P
<a id="upcsp"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Control Semaforización Peatonal

| Nombre | Valor |
|---|---|
| SCPP6M2 | `CSP0005` |

### UP_CS_V
<a id="upcsv"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Control Semaforización Vehicular

| Nombre | Valor |
|---|---|
| SCPV7M1 | `CSP0001` |
| SCPV14M2 | `CSP0002` |
| SCPV21M3 | `CSP0003` |
| SCPV28M4 | `CSP0004` |

### UP_PA_PORTAFUSIBLE
<a id="uppaportafusible"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Seccionador Portafusible

| Nombre | Valor |
|---|---|
| 2P200S | `SSS0008` |
| 3P200S | `SSS0009` |
| 1P200T | `SST0007` |
| 2P200T | `SST0008` |
| 3P200T | `SST0009` |
| 1P200V | `SSV0007` |
| 2P200V | `SSV0008` |
| 3P200V | `SSV0009` |

### UP_PA_TIPO_CODO
<a id="uppatipocodo"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Seccionador tipo Codo

| Nombre | Valor |
|---|---|
| 2C200S | `SSS0002` |
| 3C200S | `SSS0003` |
| 1C200T | `SST0001` |
| 2C200T | `SST0002` |
| 3C200T | `SST0003` |
| 1C200V | `SSV0001` |
| 2C200V | `SSV0002` |
| 3C200V | `SSV0003` |

### UP_PA_TIPO_T
<a id="uppatipot"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Seccionador tipo T

| Nombre | Valor |
|---|---|
| 2T600S | `SSS0005` |
| 3T600S | `SSS0006` |
| 1T600T | `SST0004` |
| 2T600T | `SST0005` |
| 3T600T | `SST0006` |
| 1T600V | `SSV0004` |
| 2T600V | `SSV0005` |
| 3T600V | `SSV0006` |

### UP_PO_MADERA
<a id="uppomadera"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Poste Madera

| Nombre | Valor |
|---|---|
| PMC3 | `POO10100` |
| PMC4 | `POO10200` |
| PMC5 | `POO10300` |
| PMC6 | `POO6300` |
| PMC7 | `POO10400` |
| PMC8 | `POO4700` |
| PMC8.5 | `POO3900` |
| PMC9 | `POO0500` |
| PMC10 | `POO0900` |
| PMC11 | `POO1400` |
| PMC12 | `POO1900` |
| PMC15 | `POO10500` |
| PMC19 | `POO10600` |

### UP_PO_PLASTICO
<a id="uppoplastico"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Poste Plastico

| Nombre | Valor |
|---|---|
| PPC9_350 | `POO0301` |
| PPC9_400 | `POO0302` |
| PPC9_500 | `POO0304` |
| PPC10_400 | `POO0702` |
| PPC10_200 | `POO0730` |
| PPC10_500 | `POO0704` |
| PPC11_400 | `POO1202` |
| PPC11_500 | `POO1204` |
| PPC11_750 | `POO1214` |
| PPC11_1000 | `POO1209` |
| PPC12_350 | `POO1701` |
| PPC12_400 | `POO1702` |
| PPC12_500 | `POO1704` |
| PPC12_750 | `POO1714` |
| PPC12_1000 | `POO1709` |
| PPC12_2000 | `POO1712` |
| PPC14_350 | `POO11001` |
| PPC14_500 | `POO11004` |
| PPC14_700 | `POO11007` |
| PPC14_1000 | `POO11009` |
| PPC14_2000 | `POO11012` |
| PPC16_1000 | `POO11409` |
| PPC18_1000 | `POO6609` |
| PPC18_1800 | `POO6629` |
| PPC18_2350 | `POO6626` |
| PPC14_1600 | `POO9914` |

### UP_PO_SEMAFORO
<a id="upposemaforo"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Poste Semaforizacion

| Nombre | Valor |
|---|---|
| PEC3 | `POO3000` |
| PEC4.5 | `POO4600` |
| PEB4.5 | `POO5200` |
| PEC5 | `POO6800` |
| PEC6 | `POO2900` |
| PEC7 | `POO6900` |
| PEC8 | `POO3600` |
| PEC9 | `POO0400` |
| PEC10 | `POO0800` |
| PEC10.5 | `POO10700` |
| PEC11 | `POO1300` |
| PEC12 | `POO1800` |
| PEC12.5 | `POO7000` |
| PEC14 | `POO2700` |
| PEC15 | `POO5300` |
| PEC16 | `POO2800` |
| PEC18 | `POO4400` |
| PEC19 | `POO7100` |
| PEC21 | `POO5100` |
| PEC24 | `POO4500` |
| PEC31 | `POO7200` |
| PER3 | `POO7300` |
| PER4 | `POO7400` |
| PER5 | `POO7500` |
| PER6 | `POO7600` |
| PER7 | `POO7700` |
| PER8 | `POO7800` |
| PER9 | `POO7900` |
| PER10.5 | `POO11300` |
| PER21 | `POO8000` |
| PER11 | `POO8100` |
| PER24 | `POO8200` |

### UP_PPBT_ESTANCO
<a id="upppbtestanco"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Puesto Proteccion BT Estanco

| Nombre | Valor |
|---|---|
| 1TA | `SPD0001` |
| 1TD | `SPD0002` |
| 1TC | `SPD0003` |

### UP_PPBT_IT
<a id="upppbtit"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Puesto Protección Baja Tensión Interruptor Termomagnetico

| Nombre | Valor |
|---|---|
| 3M40 | `SPD0034` |
| 3M50 | `SPD0035` |
| 3M60 | `SPD0036` |
| 3M75 | `SPD0037` |
| 3M80 | `SPD0038` |
| 3M100 | `SPD0039` |
| 3M125 | `SPD0040` |
| 3M150 | `SPD0041` |
| 3M160 | `SPD0042` |
| 3M175 | `SPD0043` |
| 3M200 | `SPD0044` |
| 3M225 | `SPD0045` |
| 3M250 | `SPD0046` |
| 3M300 | `SPD0047` |
| 3M320 | `SPD0048` |
| 3M350 | `SPD0049` |
| 3M400 | `SPD0050` |
| 3M500 | `SPD0051` |
| 3M600 | `SPD0052` |
| 3M630 | `SPD0053` |
| 3M1200 | `SPD0054` |
| 2N15D | `SSD0001` |
| 2N20D | `SSD0002` |
| 2N30D | `SSD0003` |
| 2N40D | `SSD0004` |
| 2N50D | `SSD0005` |
| 2N60D | `SSD0006` |
| 2N70D | `SSD0007` |
| 2N100D | `SSD0008` |
| 3N70D | `SSD0009` |
| 3N100D | `SSD0010` |
| 3N125D | `SSD0011` |
| 3N150D | `SSD0012` |
| 3N175D | `SSD0013` |
| 3N200D | `SSD0014` |
| 3N225D | `SSD0015` |
| 3N250D | `SSD0016` |
| 3N300D | `SSD0017` |
| 3N350D | `SSD0018` |

### UP_PPBT_NH
<a id="upppbtnh"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Puesto Proteccion BT NH

| Nombre | Valor |
|---|---|
| 1L25 | `SPD0033` |
| 2L25 | `SPD0004` |
| 2L35 | `SPD0005` |
| 2L63 | `SPD0006` |
| 2L80 | `SPD0007` |
| 2L100 | `SPD0008` |
| 2L125 | `SPD0009` |
| 2L160 | `SPD0010` |
| 2D160 | `SPD0030` |
| 2L224 | `SPD0011` |
| 2L250 | `SPD0012` |
| 2L355 | `SPD0032` |
| 2L400 | `SPD0013` |
| 2L500 | `SPD0014` |
| 2L630 | `SPD0015` |
| 2L800 | `SPD0016` |
| 3L25 | `SPD0017` |
| 3L35 | `SPD0018` |
| 3L63 | `SPD0019` |
| 3L80 | `SPD0020` |
| 3L100 | `SPD0021` |
| 3L125 | `SPD0022` |
| 3L160 | `SPD0023` |
| 3D160 | `SPD0031` |
| 3L224 | `SPD0024` |
| 3L250 | `SPD0025` |
| 3L400 | `SPD0026` |
| 3L500 | `SPD0027` |
| 3L630 | `SPD0028` |
| 3L800 | `SPD0029` |

### UP_PPD_CELDA_INT
<a id="upppdceldaint"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Puesto de Proteccion Dinamico de Celdas de Inteconexión

| Nombre | Valor |
|---|---|
| 3EI600_150S | `SSS0069` |
| 3EI600_150T | `SST0069` |
| 3EI600_150V | `SSV0069` |

### UP_PPD_CELDA_PROT
<a id="upppdceldaprot"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Puesto de Proteccion Dinamico de Celdas de Proteccion

| Nombre | Valor |
|---|---|
| 3EP400_150S | `SSS0068` |
| 3EP400_150T | `SST0068` |
| 3EP630_95T | `SST0076` |
| 3EP400_150V | `SSV0068` |

### UP_PPD_CELDA_SEC
<a id="upppdceldasec"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Puesto de Proteccion Dinamico de Celdas de Seccionamiento

| Nombre | Valor |
|---|---|
| 3ES600_150S | `SSS0067` |
| 3ES600_150T | `SST0067` |
| 3ES600_150V | `SSV0067` |

### UP_PPD_INTERRUPTORES_SUB
<a id="upppdinterruptoressub"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Interruptores Subterraneos

| Nombre | Valor |
|---|---|
| 3I4_200S | `SSS0061` |
| 3I4_600S | `SSS0062` |
| 3I4_900S | `SSS0063` |
| 3I6_200S | `SSS0064` |
| 3I6_600S | `SSS0065` |
| 3I6_900S | `SSS0066` |
| 3I4_200T | `SST0061` |
| 3I4_600T | `SST0062` |
| 3I4_900T | `SST0063` |
| 3I6_200T | `SST0064` |
| 3I6_600T | `SST0065` |
| 3I6_900T | `SST0066` |
| 3I4_200V | `SSV0061` |
| 3I4_600V | `SSV0062` |
| 3I4_900V | `SSV0063` |
| 3I6_200V | `SSV0064` |
| 3I6_600V | `SSV0065` |
| 3I6_900V | `SSV0066` |

### UP_PR_2F
<a id="uppr2f"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Regulador 2F

_(sin miembros registrados)_

### UP_PSC_TRIPOL
<a id="uppsctripol"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Puesto Seccionador Cuchilla Tripolar

| Nombre | Valor |
|---|---|
| 3A100R | `SPR0045` |
| 3A200R | `SPR0046` |
| 3A300R | `SPR0047` |
| 3A600R | `SPR0048` |
| 3A100S | `SPS0054` |
| 3A200S | `SPS0055` |
| 3A300S | `SPS0056` |
| 3A600S | `SPS0057` |
| 3A100T | `SPT0045` |
| 3A200T | `SPT0046` |
| 3A300T | `SPT0047` |
| 3A600T | `SPT0048` |
| 3A100V | `SPV0039` |
| 3A200V | `SPV0040` |
| 3A300V | `SPV0041` |
| 3A600V | `SPV0042` |
| 3C600E | `SPE0001` |
| 3C1200E | `SPE0002` |
| 3C1250E | `SPE0003` |
| 3C2000E | `SPE0004` |
| 3A600E | `SPE0005` |
| 3A1200E | `SPE0006` |

### UP_PSC_TRIPOL_ROMPE
<a id="uppsctripolrompe"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Puesto Seccionador Cuchilla Tripolar con Dispositivo Rompe Arcos

| Nombre | Valor |
|---|---|
| 3N100S | `SPS0058` |
| 3N200S | `SPS0059` |
| 3N300S | `SPS0060` |
| 3N600S | `SPS0061` |
| 3N100T | `SPT0049` |
| 3N200T | `SPT0050` |
| 3N300T | `SPT0051` |
| 3N600T | `SPT0052` |
| 3N100V | `SPV0043` |
| 3N200V | `SPV0044` |
| 3N300V | `SPV0045` |
| 3N600V | `SPV0046` |
| 3N100R | `SPR0049` |
| 3N200R | `SPR0050` |
| 3N300R | `SPR0051` |
| 3N600R | `SPR0052` |

### UP_PSF_UNIPOL_ABIERTO
<a id="uppsfunipolabierto"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Puesto Seccionador Fusible Unipolar Abierto

| Nombre | Valor |
|---|---|
| 2S100S | `SPS0007` |
| 3S100S | `SPS0008` |
| 2S200S | `SPS0033` |
| 3S200S | `SPS0044` |
| 1S100T | `SPT0001` |
| 2S100T | `SPT0021` |
| 3S100T | `SPT0033` |
| 1S200T | `SPT0002` |
| 2S200T | `SPT0022` |
| 3S200T | `SPT0034` |
| 1S100V | `SPV0001` |
| 2S100V | `SPV0017` |
| 3S100V | `SPV0027` |
| 1S200V | `SPV0002` |
| 2S200V | `SPV0018` |
| 3S200V | `SPV0028` |
| 1S100R | `SPR0001` |
| 2S100R | `SPR0021` |
| 3S100R | `SPR0033` |
| 1S200R | `SPR0002` |
| 2S200R | `SPR0022` |
| 3S200R | `SPR0034` |

### UP_PSF_UNIPOL_ABIERTO_ROMPE
<a id="uppsfunipolabiertorompe"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Puesto Seccionador Fusible Unipolar Abierto con Dispositivo Rompearcos

| Nombre | Valor |
|---|---|
| 1E100R | `SPR0003` |
| 2E100R | `SPR0023` |
| 3E100R | `SPR0035` |
| 1E200R | `SPR0004` |
| 2E200R | `SPR0024` |
| 3E200R | `SPR0036` |
| 1E300R | `SPR0115` |
| 2E300R | `SPR0116` |
| 3E300R | `SPR0117` |
| 2E100S | `SPS0034` |
| 3E100S | `SPS0045` |
| 2E200S | `SPS0035` |
| 3E200S | `SPS0046` |
| 2E300S | `SPS0119` |
| 3E300S | `SPS0120` |
| 1E100T | `SPT0003` |
| 2E100T | `SPT0023` |
| 3E100T | `SPT0035` |
| 1E200T | `SPT0004` |
| 2E200T | `SPT0024` |
| 3E200T | `SPT0036` |
| 1E300T | `SPT0120` |
| 2E300T | `SPT0121` |
| 3E300T | `SPT0122` |
| 1E100V | `SPV0003` |
| 2E100V | `SPV0019` |
| 3E100V | `SPV0029` |
| 1E200V | `SPV0004` |
| 2E200V | `SPV0020` |
| 3E200V | `SPV0030` |
| 1E300V | `SPV0113` |
| 2E300V | `SPV0114` |
| 3E300V | `SPV0115` |

### UP_PSF_UNIPOL_CERRADO
<a id="uppsfunipolcerrado"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Puesto Seccionador Fusible Unipolar Cerrado

| Nombre | Valor |
|---|---|
| 1D100R | `SPR0076` |
| 2D100R | `SPR0072` |
| 3D100R | `SPR0073` |
| 2D100S | `SPS0001` |
| 3D100S | `SPS0010` |
| 3D200S | `SPS0002` |
| 1D100T | `SPT0076` |
| 2D100T | `SPT0072` |
| 3D100T | `SPT0073` |
| 1D100V | `SPV0054` |
| 2D100V | `SPV0055` |
| 3D100V | `SPV0056` |

### UP_PUESTA_TIERRA
<a id="uppuestatierra"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Pararrayos Puesta Tierra

| Nombre | Valor |
|---|---|
| PTAC8_1 | `PTO0001` |
| PTDA9_1 | `PTO0002` |
| PTDC2_1 | `PTO0003` |
| PTPA9_1 | `PTO0004` |
| PTPC2_1 | `PTO0005` |
| PTAC2_4 | `PTO0006` |
| PTDC1/0_1 | `PTO0007` |
| PTPC1/0_1 | `PTO0013` |
| PTDC1/0_2 | `PTO0008` |
| PTDC2_2 | `PTO0009` |
| PTDC4_1 | `PTO0010` |
| PTDC4/0_1 | `PTO0011` |
| PTPC4/0_1 | `PTO0012` |

### UP_TE_BT
<a id="uptebt"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Tensor Empuje BT

| Nombre | Valor |
|---|---|
| TESD | `TAD0004` |
| TASD | `TAD0005` |

### UP_TE_MT
<a id="uptemt"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Tensor Empuje MT

| Nombre | Valor |
|---|---|
| TASV | `TAV0009` |
| TESV | `TAV0010` |
| TAST | `TAT0009` |
| TEST | `TAT0010` |
| TASR | `TAR0009` |
| TESR | `TAR0010` |
| TASS | `TAS0009` |
| TESS | `TAS0010` |

### UP_TE_ST
<a id="uptest"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Tensor de Subtransmisión

| Nombre | Valor |
|---|---|
| TASE | `TAE0001` |
| TTSE | `TAE0002` |
| TTDE | `TAE0003` |
| TTTE | `TAE0004` |

### UP_TF_BT
<a id="uptfbt"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Tensor Farol BT

| Nombre | Valor |
|---|---|
| TFSD | `TAD0001` |

### UP_TF_DOBLE
<a id="uptfdoble"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Tensor Farol Doble

| Nombre | Valor |
|---|---|
| TFDV | `TAV0003` |
| TFDT | `TAT0003` |
| TFDR | `TAR0003` |
| TFDS | `TAS0003` |

### UP_TF_MT
<a id="uptfmt"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Tensor Farol MT

| Nombre | Valor |
|---|---|
| TFSV | `TAV0002` |
| TFST | `TAT0002` |
| TFSR | `TAR0002` |
| TFSS | `TAS0002` |

### UP_TORRE
<a id="uptorre"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Torre

| Nombre | Valor |
|---|---|
| ET18 | `TOO0001` |
| ET19.5 | `TOO0002` |
| ET26 | `TOO0003` |
| ET49 | `TOO0004` |
| ET22 | `TOO0005` |

### UP_TP_BT
<a id="uptpbt"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Tensor Poste a Poste BT

| Nombre | Valor |
|---|---|
| TPSD | `TAD0002` |

### UP_TP_DOBLE
<a id="uptpdoble"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Tensor Poste a Poste Doble

| Nombre | Valor |
|---|---|
| TPDV | `TAV0005` |
| TPDT | `TAT0005` |
| TPDR | `TAR0005` |
| TPDS | `TAS0005` |

### UP_TP_MT
<a id="uptpmt"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Tensor Poste a Poste MT

| Nombre | Valor |
|---|---|
| TPSV | `TAV0004` |
| TSSV | `TAV0008` |
| TPST | `TAT0004` |
| TSST | `TAT0008` |
| TPSR | `TAR0004` |
| TSSR | `TAR0008` |
| TPSS | `TAS0004` |
| TSSS | `TAS0008` |

### UP_TRF_1F_PAD_EXT
<a id="uptrf1fpadext"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Transformador 1F Padmounted

| Nombre | Valor |
|---|---|
| 1P10R | `TRR0026` |
| 1P15R | `TRR0027` |
| 1P25R | `TRR0028` |
| 1P37.5R | `TRR0029` |
| 1P50R | `TRR0030` |
| 1P75R | `TRR0031` |
| 1P100R | `TRR0032` |
| 1P112.5R | `TRR0033` |
| 1P125R | `TRR0209` |
| 1P150R | `TRR0034` |
| 1P167R | `TRR0035` |
| 1P225R | `TRR0446` |
| 1P250R | `TRR0336` |
| 1P300R | `TRR0036` |
| 1P10T | `TRT0026` |
| 1P15T | `TRT0027` |
| 1P25T | `TRT0028` |
| 1P37.5T | `TRT0029` |
| 1P50T | `TRT0030` |
| 1P60T | `TRT0481` |
| 1P75T | `TRT0031` |
| 1P100T | `TRT0032` |
| 1P112.5T | `TRT0033` |
| 1P125T | `TRT0209` |
| 1P150T | `TRT0034` |
| 1P167T | `TRT0035` |
| 1P225T | `TRT0342` |
| 1P250T | `TRT0329` |
| 1P300T | `TRT0036` |
| 1P10V | `TRV0027` |
| 1P15V | `TRV0028` |
| 1P25V | `TRV0029` |
| 1P37.5V | `TRV0030` |
| 1P50V | `TRV0031` |
| 1P75V | `TRV0032` |
| 1P100V | `TRV0033` |
| 1P125V | `TRV0101` |
| 1P225V | `TRV0401` |
| 1P250V | `TRV0366` |

### UP_TRF_2F_CABINA
<a id="uptrf2fcabina"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Transformador 2F en Cabina

| Nombre | Valor |
|---|---|
| 2O3R | `TRR0323` |
| 2O5R | `TRR0324` |
| 2O10R | `TRR0325` |
| 2O15R | `TRR0326` |
| 2O25R | `TRR0327` |
| 2O37.5R | `TRR0328` |
| 2O50R | `TRR0329` |
| 2O75R | `TRR0330` |
| 2O3S | `TRS0199` |
| 2O5S | `TRS0200` |
| 2O10S | `TRS0201` |
| 2O15S | `TRS0202` |
| 2O25S | `TRS0203` |
| 2O37.5S | `TRS0204` |
| 2O50S | `TRS0205` |
| 2O75S | `TRS0206` |
| 2O3T | `TRT0442` |
| 2O5T | `TRT0443` |
| 2O10T | `TRT0444` |
| 2O15T | `TRT0445` |
| 2O25T | `TRT0446` |
| 2O37.5T | `TRT0447` |
| 2O50T | `TRT0448` |
| 2O75T | `TRT0449` |
| 2O3V | `TRV0358` |
| 2O5V | `TRV0359` |
| 2O10V | `TRV0360` |
| 2O15V | `TRV0361` |
| 2O25V | `TRV0362` |
| 2O37.5V | `TRV0363` |
| 2O50V | `TRV0364` |
| 2O75V | `TRV0365` |

### UP_TRF_2F_PAD_EXT
<a id="uptrf2fpadext"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Transformador 2F Padmounted

| Nombre | Valor |
|---|---|
| 2P10S | `TRS0066` |
| 2P15S | `TRS0067` |
| 2P25S | `TRS0068` |
| 2P37.5S | `TRS0069` |
| 2P50S | `TRS0070` |
| 2P75S | `TRS0071` |
| 2P100S | `TRS0072` |
| 2P125S | `TRS0073` |

### UP_TT_BT
<a id="upttbt"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Tensor a Tierra BT

| Nombre | Valor |
|---|---|
| TTSD | `TAD0003` |

### UP_TT_DOBLE
<a id="upttdoble"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String

| Nombre | Valor |
|---|---|
| TTDR | `TAR0001` |
| TVDR | `TAR0011` |
| TTDS | `TAS0001` |
| TVDS | `TAS0011` |
| TTDT | `TAT0001` |
| TVDT | `TAT0011` |
| TTDV | `TAV0001` |
| TVDV | `TAV0011` |

### UP_TT_MT
<a id="upttmt"></a>

- **Tipo:** Coded Value · **Tipo de campo:** String
- **Descripción:** Tensor a Tierra MT

| Nombre | Valor |
|---|---|
| TTSV | `TAV0006` |
| TVSV | `TAV0007` |
| TTST | `TAT0006` |
| TVST | `TAT0007` |
| TTSR | `TAR0006` |
| TVSR | `TAR0007` |
| TTSS | `TAS0006` |
| TVSS | `TAS0007` |

### Ubicacion Switch
<a id="ubicacion-switch"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer

| Nombre | Valor |
|---|---|
| ACERA | `1` |
| VEREDA | `2` |
| BOVEDA | `3` |
| SUBESTACION | `4` |
| LOTE | `5` |
| PARTERRE | `6` |
| PEATONAL | `7` |
| CUARTO | `8` |
| POSTE | `9` |

### VerticalAlignment
<a id="verticalalignment"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer
- **Descripción:** Valid symbol vertical alignment values.

| Nombre | Valor |
|---|---|
| Top | `0` |
| Center | `1` |
| Baseline | `2` |
| Bottom | `3` |

### Voltaje AT
<a id="voltaje-at"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Integer
- **Descripción:** Voltaje Alta Tension

| Nombre | Valor |
|---|---|
| 500 kV | `500000` |
| 230 kV | `230000` |
| 138 kV | `138000` |
| 69 kV | `69000` |
| 46 kV | `46000` |
| 34.5 kV | `34500` |

### Voltaje AT/MT
<a id="voltaje-atmt"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Integer
- **Descripción:** Voltaje Alta Tension/Media Tension

| Nombre | Valor |
|---|---|
| 500 kV | `500000` |
| 230 kV | `230000` |
| 138 kV | `138000` |
| 69 kV | `69000` |
| 46 kV | `46000` |
| 34.5 kV | `34500` |
| 23.0 kV | `23000` |
| 22.8 kV | `22800` |
| 22.0 kV | `22000` |
| 19.92 kV | `19919` |
| 13.8 kV | `13800` |
| 13.28 kV | `13279` |
| 13.2 kV | `13200` |
| 13.16 kV | `13164` |
| 12.70 kV | `12702` |
| 7.97 kV | `7967` |
| 7.62 kV | `7621` |
| 6.3 kV | `6300` |
| 4.16 kV | `4160` |

### Voltaje BT
<a id="voltaje-bt"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Integer
- **Descripción:** Voltaje Baja Tensión

| Nombre | Valor |
|---|---|
| 120 V | `120` |
| 121 V | `121` |
| 127 V | `127` |
| 208 V | `208` |
| 210 V | `210` |
| 219 V | `219` |
| 220 V | `220` |
| 240 V | `240` |
| 231 V | `231` |
| 254 V | `254` |
| 266 V | `266` |
| 277 V | `277` |
| 380 V | `380` |
| 400 V | `400` |
| 440 V | `440` |
| 460 V | `460` |
| 480 V | `480` |

### Voltaje MT
<a id="voltaje-mt"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Integer
- **Descripción:** Voltaje Media Tension

| Nombre | Valor |
|---|---|
| 34.5 kV | `34500` |
| 23.0 kV | `23000` |
| 22.8 kV | `22800` |
| 22.0 kV | `22000` |
| 19.92 kV | `19919` |
| 13.8 kV | `13800` |
| 13.28 kV | `13279` |
| 13.2 kV | `13200` |
| 13.16 kV | `13164` |
| 12.70 kV | `12702` |
| 7.97 kV | `7967` |
| 7.62 kV | `7621` |
| 6.3 kV | `6300` |
| 4.16 kV | `4160` |

### ZONA
<a id="zona"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Small Integer

| Nombre | Valor |
|---|---|
| CABECERA PROVINCIAL | `1` |
| CABECERA CANTONAL | `2` |
| RURAL | `3` |
| ZONA 1 | `4` |
| ZONA 2 | `5` |
| ZONA 3 | `6` |

### kVAR Capacitor Unidad
<a id="kvar-capacitor-unidad"></a>

- **Tipo:** Coded Value · **Tipo de campo:** Integer
- **Descripción:** kVAR Capacitor Unidad

| Nombre | Valor |
|---|---|
| 50 kVAr | `50` |
| 100 kVAr | `100` |
| 150 kVAr | `150` |
| 200 kVAr | `200` |
| 300 kVAr | `300` |
| 400 kVAr | `400` |
