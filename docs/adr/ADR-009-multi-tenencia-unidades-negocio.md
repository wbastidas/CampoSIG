# ADR-009 — Una plataforma, varias unidades de negocio

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-09-21 |
| Decide | Cómo sirve una sola instancia de la plataforma a la matriz y a varias unidades de negocio |
| Se apoya en | [ADR-004](ADR-004-capa-abstraccion-modelo-datos.md) y [ADR-008](ADR-008-agente-arcpy.md) |

## Contexto

La empresa tiene dos niveles: una **matriz** y varias **unidades de negocio**, cada una con su propia
red de distribución y su propia geodatabase ArcSDE. Un técnico de una unidad sincroniza contra la
plataforma, y lo que capturó tiene que terminar en la geodatabase **de su unidad**, no en otra.

La pieza que hace esto tratable viene del propio material de origen. `01_Dominios.md` lo dice sin
ambigüedad: el modelo de datos es **nacional** —las mismas 47 clases, los mismos campos, las mismas
79 relaciones en toda unidad— mientras que tres dominios (`Codigo Alimentador`, `Numero Estacion`,
`Subestacion`) contienen los códigos de la red física de cada unidad y por tanto difieren.

Eso separa con precisión qué se comparte y qué no.

## Decisión

Una sola instancia de la plataforma, con tres niveles de alcance:

| Artefacto | Alcance | Por qué |
|---|---|---|
| **Perfil de mapeo** (ADR-004) | Normalmente **compartido** por todas las unidades | El esquema es nacional. Mantener un perfil por unidad sería duplicar lo idéntico y garantizar que se desincronicen |
| **Snapshot de metadatos** | **Por unidad** | Los dominios difieren. Indexarlos por perfil dejaría que los catálogos de una unidad sobrescriban los de otra |
| **Agente arcpy** | **Por unidad** | Cada unidad tiene su geodatabase y su máquina con ArcMap |

Y una regla dura: **nada cruza entre unidades.**

1. Un dispositivo pertenece a exactamente una unidad. La plataforma enruta lo que captura sin que el
   dispositivo sepa que esto existe.
2. La unidad de un agente sale de su **registro**, nunca del payload que envía. Al agente no se le
   pregunta a qué unidad sirve, así que no puede declarar otra.
3. Un agente que reporta sobre un lote de otra unidad recibe `404`, no `403`: sondear identificadores
   de lotes ajenos no debe enseñarle nada.
4. Desactivar una unidad detiene a su agente, no solo la oculta de los listados.
5. Un perfil que el agente reporte y que no sea el de su unidad es un error de configuración y se
   rechaza. Aceptarlo guardaría los catálogos de una unidad bajo el esquema de otra.

La unicidad del código de unidad es **por organización**, no global, para que una fusión no colisione.

## Consecuencias

**A favor:**

- Una instancia que operar, respaldar y actualizar, en lugar de una por unidad.
- El trabajo transversal que la matriz necesita —reportería consolidada, parámetros regulatorios,
  catálogos homologados— es una consulta, no una integración entre instancias.
- El aislamiento es una propiedad verificada, no una convención: cada regla de arriba tiene su test.
- Una unidad puede migrar a otro esquema sola, cambiando su `profile_id`, sin tocar a las demás. Es
  el camino por el que pasará la migración a ArcGIS Pro y Utility Network, unidad por unidad.

**En contra:**

- Toda consulta debe estar acotada por unidad. Un olvido filtra datos entre unidades, que es el fallo
  más grave que esta arquitectura admite. Se mitiga con el alcance obligatorio en el servicio y con
  tests que intentan cruzar explícitamente.
- La base de la plataforma crece con la suma de todas las unidades. Aceptable: las evidencias, que
  son el volumen real, viven en el almacenamiento de objetos.
- Un incidente en la plataforma afecta a todas las unidades a la vez. Es el precio de la instancia
  única, y se compensa con que el móvil funciona sin conexión: una caída del servidor no detiene el
  trabajo de campo, solo lo diferido.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Una instancia por unidad de negocio | Aislamiento perfecto y multiplica por N el despliegue, el respaldo y la actualización. Además vuelve imposible la reportería consolidada de la matriz sin construir integración entre instancias |
| Un esquema de base de datos por unidad en la misma instancia | Aislamiento fuerte, pero cada migración se multiplica por N y una consulta consolidada necesita SQL entre esquemas. El alcance por columna, verificado con tests, da suficiente garantía a mucho menor costo |
| Un perfil de mapeo por unidad | Duplica lo que es idéntico por definición nacional, y garantiza que los perfiles se desincronicen con el tiempo |
