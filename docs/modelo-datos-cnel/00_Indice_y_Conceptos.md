# 00 · Índice y Conceptos del Modelo de Datos Eléctrico — CNEL EP (Unidad de Negocio Guayaquil)

**Fuentes de este documento:**
- `Modelo_Datos.htm` — reporte ArcGIS Diagrammer de la geodatabase eléctrica, Unidad de Negocio Guayaquil (GYE), corte 12/mayo/2025 (workspace exportado desde `GYE.XML`).
- `MN-TEC-OPE-100` — *Manual sobre la metodología para el ingreso de información de las redes de Distribución Eléctrica de CNEL EP a una Geodatabase SIG*, versión 01 (feb. 2021). Documento de **aplicación nacional**: aplica a todas las Unidades de Negocio de CNEL EP y, en general, a cualquier distribuidora del país que use este modelo de datos homologado.

**Propósito de este set de archivos:** ser la fuente de referencia única para escribir queries, scripts, ETLs o cualquier programa que consuma esta geodatabase, sin tener que volver a abrir el HTML de 5.8 MB ni el PDF de 159 páginas cada vez.

---

## Mapa de archivos

| Archivo | Contenido |
|---|---|
| **00_Indice_y_Conceptos.md** (este archivo) | Conceptos del modelo, convenciones, estructura general, conectividad eléctrica |
| [01_Dominios.md](01_Dominios.md) | Los 196 dominios (listas de valores válidos / rangos) — con aviso claro de cuáles varían por Unidad de Negocio |
| [02_Relaciones.md](02_Relaciones.md) | Las 79 relaciones formales del esquema (relationship classes), con claves de join |
| [03_Clases_Redes_y_Soporte.md](03_Clases_Redes_y_Soporte.md) | Tramos MT/BT/Subtransmisión, Barra, postes y estructuras de soporte (18 clases) |
| [04_Clases_Proteccion_y_Potencia.md](04_Clases_Proteccion_y_Potencia.md) | Protección, maniobra, transformadores, reguladores, capacitores (16 clases) |
| [05_Clases_Generacion_Subestaciones_Fuentes.md](05_Clases_Generacion_Subestaciones_Fuentes.md) | Generación, motores, subestaciones, `CIRCUITOFUENTE` (7 clases) |
| [06_Clases_Consumidores_y_Alumbrado.md](06_Clases_Consumidores_y_Alumbrado.md) | Puntos de carga, conexión de consumidor, luminarias, semáforos (6 clases) |

**Cobertura total:** 47 clases (28 FeatureClass espaciales + 19 tablas no espaciales) · 196 dominios · 79 relaciones.

Cada clase, dominio y relación tiene un ancla estable (`#nombre-en-minusculas`) para enlazar directo desde código, documentación o un buscador de texto.

---

## Convenciones usadas en todo el set de archivos

### Categoría de campo (en las tablas "Campos" de cada clase)

Como pediste, los campos **no esenciales para el modelo eléctrico** quedan identificados aparte para que puedas filtrarlos fácilmente. Cada campo de cada clase tiene una de estas 4 categorías:

| Ícono | Categoría | Significado |
|---|---|---|
| ✅ | **CORE** | Aparece explícitamente como obligatorio en una de las 30 tablas "Campos obligatorios" del manual `MN-TEC-OPE-100` (Tablas 11 a 40). Es la fuente más confiable de "qué es esencial" porque es la política oficial de captura de CNEL EP. |
| 🔌 | **Conectividad** | Campos que usa el motor de red geométrica para el trazado eléctrico: `ANCILLARYROLE`, `ELECTRICTRACEWEIGHT`, `CIRCUITSOURCEGUID`, `PARENTCIRCUITSOURCEGUID`, `ENABLED`. Ver sección [Conectividad eléctrica](#conectividad-eléctrica-y-trazado-source--sink) más abajo. |
| 🔧 | **Sistema** | Campos de auditoría/metadatos técnicos que se repiten en casi todas las clases: usuario y fecha de registro/modificación, identificadores internos (`OBJECTID`, `GLOBALID`, `MIOID`, `MIGUID`), geometría (`SHAPE`), ubicación administrativa (`PROVINCIA`/`CANTON`/`PARROQUIA`), proyecto de construcción, orden de trabajo, comentarios/observaciones, hipervínculo, subtipo. |
| ▫️ | **Otro** | El resto de atributos propios de cada clase. **Importante:** "Otro" no significa "innecesario" — solo significa que el manual no lo lista como obligatorio explícitamente. Para 19 de las 47 clases el manual no tiene una tabla de campos obligatorios dedicada (p. ej. `Subestacion`, `Generador`, `Barra`, `CATALOGOESTRUCTURA`); en esas clases **todo** queda en 🔧 Sistema o ▫️ Otro, y la elección de qué usar depende de tu caso de uso — no la reinterpretes como jerarquía oficial. |

**Para "no considerar" los no-prioritarios en un query:** filtra por la categoría (`CORE`/`CONECTIVIDAD` vs `SISTEMA`/`OTRO`) usando el `field_name` listado en la tabla de cada clase.

### Dominios: variables por Unidad de Negocio vs. fijos

Ya lo señalaste y quedó documentado con aviso ⚠️ en cada lugar donde aparece: los dominios **`Codigo Alimentador`**, **`Numero Estacion`** y **`Subestacion`** contienen los códigos de la red física de Guayaquil (GYE) — en cualquier otra Unidad de Negocio de CNEL EP tendrán una lista de miembros distinta, aunque el modelo de datos (nombres de dominio, clases, campos) sea idéntico a nivel nacional. Ver el detalle en [01_Dominios.md → 🟥 Dominios variables por Unidad de Negocio](01_Dominios.md#🟥-dominios-variables-por-unidad-de-negocio).

### Nombres técnicos vs. alias

Cada campo tiene un `field_name` (nombre técnico, el que usarías en SQL/arcpy) y un `alias_name` (nombre amigable en español, el que ve el editor en ArcMap). En varias clases el alias no está definido y por defecto repite el nombre técnico en mayúsculas (ej. `HIPERVINCULO` → alias `HIPERVINCULO`). Las tablas de campos en cada archivo de clases muestran ambos.

---

## Conceptos estructurales del modelo (según el manual)

### Feature Dataset y Red Geométrica

- El modelo eléctrico vive en el Feature Dataset **`Electrico`** (con un dataset complementario **`Electrico_Complementos`** para clases auxiliares). Sistema de referencia espacial de ambos: **UTM Zona 17S, WGS 1984 (EPSG:32717)**.
- Dentro de `Electrico` se define la red geométrica **`Electrico_RedGeom`**, con reglas de conectividad, auto-actualizadores y una base de conocimientos configurada vía ArcFM. Participan **20 clases**:

| Rol en la red | Clases |
|---|---|
| **Edge** (línea / tramo) — 7 clases | `Barra`, `TramoBajaTensionAereo`, `TramoBajaTensionSubterraneo`, `TramoDistribucionAereo`, `TramoDistribucionSubterraneo`, `TramoSubtransmisionAereo`, `TramoSubtransmisionSubterraneo` |
| **Junction** (punto de conexión) — 13 clases | `Electrico_RedGeom_Junctions`, `Luminaria`, `PuestoCorrectorFactorPotencia`, `PuestoProteccionBajaTension`, `PuestoProteccionDinamico`, `PuestoReguladorTension`, `PuestoSeccionador`, `PuestoSeccionadorFusible`, `PuestoTransfDistribucion`, `PuestoTransfPotencia`, `PuntoApertura`, `PuntoCarga`, `Semaforo` |

  > Nota: `Generador`, `GeneradorDistribuido` y `Pararrayos` tienen campos de conectividad (`ANCILLARYROLE`, `PARENTCIRCUITSOURCEGUID`) pero **no** figuran como participantes formales de `Electrico_RedGeom` en este export — probablemente se vinculan a la red vía relación con una clase que sí participa (p. ej. `Barra`), no directamente.

- **MT** en la nomenclatura del manual = Media Tensión = las clases `TramoDistribucion*` en el esquema técnico. **BT** = Baja Tensión = `TramoBajaTension*`. Subtransmisión es un nivel de tensión superior a MT, con sus propias clases `TramoSubtransmision*`.

### Concepto de Puesto vs. Unidad

El manual distingue dos tipos de objetos que se repiten en todo el modelo:

- **Puesto**: representa la ubicación geográfica del elemento. Es un feature de tipo punto, con geometría propia, y **siempre es único** (ej. `PuestoTransfDistribucion`, `PuestoCorrectorFactorPotencia`, `PuestoProteccionDinamico`, `PuntoCarga`, `EstructuraSoporte`/postes).
- **Unidad**: tabla de atributos relacionada al Puesto mediante un campo/relación, **sin ubicación geográfica propia**, que documenta los atributos constructivos. Puede haber varias Unidades por Puesto (típicamente una por fase A/B/C) — ej. `UNIDADTRANSFDISTRIBUCION`, `UNIDADCAPACITOR`, `ESTRUCTURAENPOSTE`, `CONEXIONCONSUMIDOR`.

Ejemplo del manual: un banco de 3 transformadores monofásicos trifilar = **1 Puesto** (representa el banco completo) + **3 Unidades** (una por fase A, B, C). Un poste con estructuras de MT y BT = 1 Puesto (el poste) + 2 Unidades `ESTRUCTURAENPOSTE` (una por nivel de tensión).

En los archivos 03-06, cada par Puesto/Unidad está documentado consecutivamente y enlazado por su relación formal (ver [02_Relaciones.md](02_Relaciones.md)).

### Source y Sink (inicio y fin del flujo eléctrico)

Concepto clave para digitalización y para cualquier trazado/análisis de conectividad:

- **Source** (fuente): el punto donde inicia el flujo. El manual identifica a `PuestoProteccionDinamico` como el elemento fuente por excelencia (el reconectador/disyuntor de cabecera de alimentador).
- **Sink** (sumidero): el punto donde termina el flujo — típicamente `PuntoCarga` (usuario final) o `Luminaria`.
- Las redes **deben digitalizarse siempre desde la fuente hacia la carga**; un elemento digitalizado en sentido inverso no es reconocido correctamente por el trace de ArcGIS.
- El dominio **`AncillaryRoleDomain`** formaliza este rol a nivel de atributo (campo `ANCILLARYROLE`, presente en 14 clases): `0 = None`, `1 = Source`, `2 = Sink`. Ver [01_Dominios.md#ancillaryroledomain](01_Dominios.md#ancillaryroledomain).

---

## Conectividad eléctrica y trazado (Source / Sink)
<a id="conectividad-eléctrica-y-trazado-source--sink"></a>

> Esta sección responde específicamente a la relación **`CircuitSourceGUID` ↔ `ParentCircuitSourceGUID`**, que es estructuralmente una de las piezas más importantes del modelo para cualquier análisis de trazabilidad/alimentación real de la red — se documenta aquí de forma centralizada porque estos campos aparecen repartidos en muchas clases.

### Los tres mecanismos de conectividad, de más "declarativo" a más "topológico"

1. **`ALIMENTADORID` / `ALIMENTADOR` (texto descriptivo)** — presente en casi todas las clases de red. Es el código/nombre del alimentador tal como lo captura el editor manualmente. Útil para reportes y para filtrar rápido, pero **puede desactualizarse** si la topología cambia y nadie corrige el atributo a mano.

2. **`CircuitSourceGUID` (marca una clase como fuente)** — campo GUID presente **solo** en las 3 clases que pueden actuar como cabecera de circuito:
   - [`PuestoProteccionDinamico`](04_Clases_Proteccion_y_Potencia.md#puestoprotecciondinamico) (el caso típico: reconectador/disyuntor de cabecera)
   - [`PuestoTransfDistribucion`](04_Clases_Proteccion_y_Potencia.md#puestotransfdistribucion)
   - [`PuestoTransfPotencia`](04_Clases_Proteccion_y_Potencia.md#puestotransfpotencia)

   Estas clases también tienen `ANCILLARYROLE` (rol Source/Sink) y participan en la red geométrica como Junction.

3. **`ParentCircuitSourceGUID` (marca de qué fuente cuelga cada elemento aguas abajo)** — presente en prácticamente **todas** las clases de red (`Barra`, todos los `Tramo*`, `Luminaria`, `PuntoCarga`, `Semaforo`, `PuntoApertura`, todos los `Puesto*`, `Generador`, `GeneradorDistribuido`). Este campo **no se llena a mano**: lo calcula el trace/auto-actualizador de ArcFM al recorrer la red geométrica desde cada Source, y queda "estampado" en cada elemento aguas abajo con el GUID del `CircuitSourceGUID` de la fuente que realmente lo energiza según la topología real (no según lo que diga el atributo `ALIMENTADORID`).

### La tabla `CIRCUITOFUENTE` conecta todo esto con el alimentador administrativo

[`CIRCUITOFUENTE`](05_Clases_Generacion_Subestaciones_Fuentes.md#circuitofuente) (alias *"Alimentador Cabecera"*) es una tabla no espacial — **un registro por alimentador** — con los parámetros eléctricos de cabecera (tensión nominal/operación, capacidades, impedancias de secuencia, demanda máxima, `CODIGOALIMENTADOR`, `IDSUBESTACION`). Se vincula formalmente al disyuntor de cabecera mediante la relación 1:1:

```
PuestoProteccionDinamico.GLOBALID  →  CIRCUITOFUENTE.PUESTOPROTDINAMGLOBALID
```
(relación [`PuestoProtDinam_CircuitoFuente`](02_Relaciones.md#puestoprotdinamcircuitofuente))

### Cómo usar esto en un query / programa

- **Para saber qué alimenta administrativamente algo** (reportes, agrupación simple): usa `ALIMENTADORID`/`ALIMENTADOR`, cruzando contra el dominio [Codigo Alimentador](01_Dominios.md#codigo-alimentador) ⚠️ (variable por UN) o contra `CIRCUITOFUENTE.CODIGOALIMENTADOR`.
- **Para saber qué alimenta *realmente* algo según la topología de red** (análisis de contingencia, trazabilidad, "qué se queda sin servicio si abro este seccionador"): compara `ParentCircuitSourceGUID` del elemento contra `CircuitSourceGUID` de las 3 clases fuente — esto refleja el resultado del último trace ejecutado en ArcFM, no un cálculo en tiempo real. Si necesitas el estado *actual* exacto, hay que re-ejecutar el trace (o repetirlo algorítmicamente sobre la topología si trabajas fuera de ArcGIS).
- Este enlace **no es una relationship class formal** del esquema (no aparece en [02_Relaciones.md](02_Relaciones.md)) — es una convención de atributos que ArcFM mantiene mediante auto-actualizadores y la herramienta de trace, por lo que no se refuerza con integridad referencial de geodatabase; puede haber GUIDs "huérfanos" si el trace no se ha vuelto a correr después de una edición.

---

## Preguntas frecuentes para quien escriba queries/programas

**¿Cómo sé si un campo es obligatorio de verdad?** → Filtra por categoría `CORE` (✅) en la tabla de campos de la clase. Si la clase no tiene tabla de obligatorios en el manual, no hay una fuente oficial — usa criterio según tu caso de uso.

**¿Puedo asumir que `Codigo Alimentador` tiene los mismos 246 valores en otra Unidad de Negocio?** → No. Ver [01_Dominios.md](01_Dominios.md#🟥-dominios-variables-por-unidad-de-negocio).

**¿Un mismo campo puede tener distinto dominio según el subtipo?** → Sí, es común (ej. `VOLTAJE` en `Barra` usa el dominio `Voltaje BT`, `Voltaje MT` o `Voltaje AT` según el subtipo). Por eso los dominios se documentan **por subtipo**, no en la tabla plana de campos — ver la sección "Subtipos y dominios asignados" de cada clase.

**¿Cómo relaciono Puesto y Unidad en SQL?** → Por la relationship class correspondiente en [02_Relaciones.md](02_Relaciones.md); casi siempre es `GLOBALID` (Puesto, PK) → `<Puesto>GLOBALID` u `<Puesto>OBJECTID` (Unidad, FK).

**Encontré una tabla del manual que no mapea a ninguna clase (Tabla 39/40, "Estructura Subterránea").** → Correcto, están documentadas como ausentes de este export — ver la nota en el archivo de clases correspondiente; probablemente corresponden a la extensión Conduit Manager de ArcFM (Capítulo 7 del manual), gestionada aparte.

---

## Estado de cobertura y transparencia del cruce manual↔esquema

- 30 tablas de "Campos obligatorios" del manual (Tablas 11–40) fueron extraídas y mapeadas a 28 clases del esquema (2 tablas — Estructura Subterránea y Estructura de Línea Subterránea — no tienen clase correspondiente en este export).
- De ~500 campos obligatorios individuales, se auto-emparejaron ~98% contra el nombre técnico o alias del esquema. Los 5 casos no resueltos automáticamente están anotados en la clase correspondiente (ej. *"Potencia Nominal"* en `PuestoReguladorTension`, *"Año Fabricación"/"País Origen"* en `UNIDADTRANSFPOTENCIA`) — son campos que probablemente existan con otro nombre o que genuinamente no estén modelados; revísalos puntualmente si son críticos para tu caso de uso.
- Las 19 clases sin tabla de obligatorios en el manual están señaladas explícitamente en su ficha (nota ℹ️) — no se les asignó CORE por inferencia para no introducir criterio no verificado.

---

*Generado a partir de `Modelo_Datos.htm` (ArcGIS Diagrammer, GYE, corte 2025-05-12) y `MN-TEC-OPE-100` v01 (CNEL EP, 2021-02). Este set de archivos no reemplaza al manual oficial para procedimientos de digitalización — está orientado a consulta y desarrollo de queries/programas sobre la geodatabase.*
