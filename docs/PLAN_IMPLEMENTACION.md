# Plan de implementación por incrementos — SIGEC-Campo

| Campo | Valor |
|---|---|
| Código | PLAN-SIGEC-001 |
| Versión | 1.1 |
| Fecha | 21 de septiembre de 2026 |
| Base | `SRS.md` v1.1 · `ADDENDUM-01-ArcGIS-FieldMaps-Oracle.md` v1.1 · `GUIA_ENTRENAMIENTO_MODELOS.md` v1.1 |
| Cambios v1.3 | Resueltas D2, D9 y D11, así que I1 pierde sus tres bloqueos y se concentra en medir. El alcance de escritura del agente queda fijado: solo campos del proceso. |
| Cambios v1.2 | I1 pasa a ser prueba de concepto del **agente arcpy** (ADR-008); habilitar sync en la geodatabase deja de ser prerrequisito. I0 añade el esqueleto del agente. D10 resuelta: el cliente tiene DBA. |
| Cambios v1.1 | I0 vuelve a PostgreSQL + PostGIS (ADR-006); I12 pierde el RAG y gana alcance en agentes (ADR-007); I0 deja de estar bloqueado por D1, ya resuelta; I6 precisa que la aplicación en ArcFM es del cliente |
| Reemplaza a | Sección 10.2 del SRS (épicas E0–E12) |

## Cómo leer este plan

Trece incrementos (`I0`–`I12`). Cada uno termina en **algo que se puede mostrar y usar**, no en un entregable interno. La regla es la del SRS 10.3: no se inicia un incremento sin que el anterior pase su *Definition of Done*.

Diferencia principal respecto a las épicas del SRS: **la integración con ArcGIS y la abstracción del modelo de datos pasan al frente.** El motivo es directo — son las dos piezas de mayor riesgo y todo lo demás depende de ellas. Construir el móvil antes de saber si la geodatabase se puede sincronizar sería construir sobre una suposición.

Los cuatro primeros incrementos (`I0`–`I3`) son el arranque completo que se aprobó: prueba de concepto ArcGIS, capa de abstracción, núcleo de OT con asignación, y móvil offline. En ese orden, porque cada uno desbloquea al siguiente.

| Símbolo | Significado |
|---|---|
| 🔴 | Riesgo técnico alto: si falla, cambia la arquitectura |
| 🟢 | Valor visible para el usuario final |
| 📋 | Requiere una decisión pendiente resuelta (D1–D8 del addendum) |

---

## Resumen

| Inc. | Nombre | Dur. ref. | Depende de | Marca |
|---|---|---|---|---|
| **I0** | Fundaciones | 2 sem | — | — |
| **I1** | Prueba de concepto del agente arcpy | 3 sem | I0 | 🔴 |
| **I2** | Capa de abstracción del modelo de datos | 4 sem | I1 | 🔴 en curso |
| **I3** | Núcleo de OT, planificadores y asignación | 5 sem | I2 | 🟢 📋 D3 |
| **I4** | Móvil offline: mapa, base cifrada y sync | 6 sem | I3 | 🔴 🟢 en curso |
| **I5** | Motor de formularios y evidencias | 5 sem | I4 | 🟢 backend listo |
| **I6** | Revisión web y staging as-built | 4 sem | I5 | 🟢 backend listo · 📋 D4 |
| **I7** | Voz → formulario | 6 sem | I5 | 🟢 |
| **I8** | Integraciones corporativas | 4 sem | I3 | 📋 D3 |
| **I9** | **Piloto 1** | 8 sem | I6, I7, I8 | 🟢 📋 D6 |
| **I10** | MLOps y paquetes de modelos | 4 sem (‖ I9) | I7 | — |
| **I11** | Visión on-device | 6 sem | I9, I10 | 🟢 |
| **I12** | Agentes y endurecimiento | 7 sem | I11 | 🟢 |

Duración de referencia: **11 a 13 meses** (retirar el RAG ahorra del orden de tres semanas en I12 y el programa de calidad que lo acompañaba). Equipo del SRS 10.2, con dos ajustes: el frontend web pasa a tiempo completo (el diseñador de perfiles y la bandeja GIS son trabajo de web sustancial) y se requiere **un enlace formal con el equipo GIS** desde I1, no como consulta ocasional.

---

## I0 — Fundaciones · 2 semanas

**Objetivo:** el equipo puede levantar todo el entorno con un comando y el CI protege las reglas desde el primer commit.

| Entregable | Detalle |
|---|---|
| Monorepo | Estructura del SRS 10.1, con los módulos nuevos del addendum 7.2 |
| Docker Compose de desarrollo | PostgreSQL 16 + PostGIS, Redis, SeaweedFS, Keycloak con realm de prueba, backend, web, `llama.cpp` con Qwen2.5-1.5B tras la pasarela de modelos, `tools/arcgis-mock` y `tools/legacy-ot-mock` |
| Esqueleto del agente arcpy | Paquete `gis-agent/` en Python 2.7 con el contrato HTTP hacia el backend, las invariantes de ADR-008 en `guards.py`, y **tests que corren sin arcpy** con un doble de prueba. Así el agente se desarrolla y se prueba en CI sin ArcMap |
| Esquema base | Migraciones Alembic sobre PostgreSQL; PostGIS y JSONB con índice GIN probados con un ida y vuelta. **Ninguna conexión a Oracle**: el backend no lleva driver Oracle (ADR-006) |
| CI | Lint, tests, verificación de licencias, `THIRD_PARTY_LICENSES.md` automático, **prueba de fuga de modelo de datos** (RF-305) y **rechazo de artefactos `com.esri.*`** en el módulo Android (ADR-003), desde el día uno |
| Autenticación | Keycloak con OIDC y el flujo de login corporativo (RF-001), federación LDAP/AD documentada aunque se conecte después |
| ADR | Los siete ADR del addendum versionados en el repo, con los sustituidos marcados |

**Aceptación:** un desarrollador nuevo clona, ejecuta un comando y tiene el entorno corriendo con login funcional. El CI rechaza tres cosas: un commit con el literal `PuestoTransfDistribucion` en `backend/app/`, una dependencia `com.esri.*` en Android, y una dependencia con licencia AGPL o GPL en el binario distribuido.

**Sin decisiones bloqueantes.** D10 quedó resuelta: el cliente cuenta con DBA para la base de la plataforma.

---

## I1 — Prueba de concepto del agente arcpy · 3 semanas 🔴

**Objetivo:** convertir los supuestos del addendum sección 5 en hechos medidos, con arcpy real contra una copia real. Este incremento puede cambiar la arquitectura; por eso va antes que todo lo demás.

Se trabaja **sobre una copia** de la geodatabase, nunca sobre producción, y **en una versión de trabajo**, nunca en DEFAULT.

| Entregable | Detalle |
|---|---|
| **Verificación de entorno** | Oracle **11.2.0.4** y ArcGIS Desktop **Advanced** ya están confirmados (D9, D2). Queda una sola comprobación, y es la que ahora puede cambiar la conversación: que estén los parches de Esri para `Append` sobre redes geométricas (R-N10) |
| Agente de bajada | `metadata.py` y `extract.py`: `ListDomains`, `Describe` de subtipos y relaciones, y `da.SearchCursor` por zona → GeoJSON. Subida al backend por el contrato HTTP |
| Agente de subida | `apply_batch.py` con el algoritmo obligado por H13 y H14: staging fuera de la red → `arcpy.da.Editor` → `Append_management` → verificar y reconstruir conectividad → reportar por propuesta |
| **Informe de medición** | Tiempo y volumen de extracción por zona y alimentador; viabilidad del incremento por fecha de modificación clase por clase; tiempo de aplicación de un lote de 50 elementos; tiempo de reconstrucción de conectividad; qué ocurre exactamente al intentar escribir conectividad |
| **Alcance de escritura verificado** | Confirmar en la copia que escribir solo los campos del proceso (D11, addendum 5.5) deja elementos utilizables: que el trace los reconozca y que ArcFM pueda completar lo suyo después. Es la validación de que el límite de alcance elegido funciona en la práctica |
| Verificación de hipótesis | Cada hallazgo H1–H16 del addendum 5.1 confirmado, corregido o refutado, con evidencia |
| Doble de prueba de arcpy | `tools/arcpy-double`: implementación mínima de la superficie de arcpy que usa el agente, para que sus tests corran en CI sin ArcMap. Es lo que permite desarrollar el agente sin depender de la máquina Windows |

**Aceptación:** existe un informe firmado con el equipo GIS que responde, con números medidos: ¿se puede leer la geodatabase con arcpy y a qué costo?, ¿se puede aplicar un lote sin dejar la red inconsistente?, ¿qué campos de AU quedan sin calcular y qué se hace con ellos?, ¿cuánto tarda el ciclo completo? Los tests del agente pasan en CI contra el doble de prueba. Si alguna respuesta invalida el diseño, se revisa el addendum **antes** de I2.

**Sin decisiones bloqueantes.** D2, D9 y D11 quedaron resueltas. Solo hace falta el acceso: la máquina con ArcGIS Desktop Advanced y la copia de la geodatabase.

> **Punto de no retorno.** Dos salidas posibles si algo falla. Si `Append` no resulta fiable sobre las clases de red, la aplicación de esas clases vuelve a ser manual en ArcFM (ADR-001 original) y el agente se queda con la bajada y con las clases fuera de la red — el resto del plan sobrevive intacto. Si arcpy no resulta viable en absoluto, se recupera la ruta de feature services REST, que exige habilitar Global IDs, archiving y versionado (R-N2 vuelve a ser alto) pero no cambia nada más: el contrato del backend con el móvil es el mismo.

---

## I2 — Capa de abstracción del modelo de datos · 4 semanas 🔴

**Objetivo:** la plataforma entiende el modelo de CNEL GYE sin conocerlo, y se demuestra con un segundo modelo distinto.

| Entregable | Detalle |
|---|---|
| AMD v1 | Vocabulario canónico con los seis tipos de activo del piloto: estructura de soporte, transformador de distribución, luminaria, seccionador fusible, tramo, punto de carga |
| `model_profile/resolver.py` | El **único** punto del código que conoce nombres reales. Todo lo demás pasa por él |
| Perfil `cnel-gye-arcgis-1081` | Bindings completos de los seis tipos, con relaciones Puesto/Unidad y los tres dominios volátiles marcados |
| `metadata_sync` | Importación de dominios, subtipos y relaciones; refresco de dominios volátiles (RF-304) |
| Generador de formularios | Metadatos → JSON Schema + UI Schema, con las reglas del addendum 3.3: dominios a enum, `CORE` a requerido, relaciones a tabla repetible, subtipos a `if/then`, campos `Sistema` y `Conectividad` ocultos |
| Importador con coincidencia asistida | Web `/admin/model-profile`: propone bindings, muestra huecos, valida y versiona el perfil |
| **Perfil alterno de prueba** | Un segundo perfil sintético, con nombres y estructura deliberadamente distintos, que pasa los mismos tests. Es la prueba real de que la abstracción funciona |

**Avance a la fecha.** Construido y en verde, sin depender de arcpy ni de acceso al GIS:

| Pieza | Estado |
|---|---|
| Vocabulario canónico (AMD) con los seis tipos del piloto | Listo |
| Perfil `cnel-gye` y perfil `alt-synthetic` de verificación | Listo |
| `resolver.py`, único punto que conoce nombres reales | Listo |
| Diagnóstico de completitud del perfil (RF-302) | Listo |
| Generador de JSON Schema + UI Schema (RF-303) | Listo |
| Contrato HTTP con el agente: ingesta de metadatos y resultados por propuesta | Listo |
| Persistencia de snapshots de metadatos, versionada y no destructiva | Listo |
| Importador web con coincidencia asistida (`/admin/model-profile`) | ✅ propone bindings con la evidencia de cada uno, versiona y publica |
| Verificación contra metadatos reales de la geodatabase | Bloqueada por el acceso de I1 |

Lo que falta de I2 es la validación contra metadatos reales, que depende del acceso de I1. El
motor y el importador están completos y probados contra dos modelos de datos deliberadamente
distintos.

### El importador: lo que propone, y lo que se niega a decidir

Esto era el hueco de I2. Estaban el motor que usa el perfil y el validador que lo revisa, y
ninguna forma de llegar a él: alguien tenía que escribir el YAML a mano adivinando cuál de
doscientas clases es la que el `support_structure` canónico quiere decir.

`model_profile/matching.py` lee un snapshot del agente y propone bindings **con la razón de
cada uno escrita en castellano**: qué término del nombre coincidió, cuántos atributos
canónicos encuentran campo, si la geometría es la que el tipo pide, y cuántos valores del
enum canónico ofrece el dominio. La confianza se presenta en palabras, no como porcentaje:
un «0,62» invita a tratar una conjetura como una medición.

Tres reglas, y cada una viene de una forma de equivocarse:

| Regla | El fallo que impide |
|---|---|
| Una propuesta no es un binding | Un importador que eligiera mal la clase produce un perfil que *funciona* —los formularios se generan, la sincronización corre— mientras los datos de campo aterrizan en la clase equivocada. No se nota en semanas |
| La ambigüedad se reporta, no se resuelve | Preseleccionar una cara de la moneda y llamarlo valor por defecto es cómo un binding equivocado lo acepta alguien pasando pantallas |
| Conectividad y auditoría nunca son candidatos | Un campo de la red geométrica se rechaza por categoría aunque el alias encaje perfecto (ADR-001), y también como anulación manual; y `OBJECTID` no es clave de negocio, que es lo que parecería si nadie lo impidiera |

**Y una regla que descubrió la propia suite.** Con un snapshot de una sola clase puntual,
cinco de los seis tipos canónicos recibían candidato: coincidir en `code` y `feeder_code`
bastaba para pasar el piso de puntuación. Pero tener código y pertenecer a un alimentador lo
cumple toda clase de una geodatabase eléctrica. Ahora la evidencia estructural solo cuenta si
se apoya en atributos que **distinguen**, y el conjunto de los que distinguen se deriva del
AMD. Consecuencia honesta: `service_point`, que no tiene ningún atributo propio, solo se
identifica por el nombre de la clase, y eso se dice en vez de adivinarse.

**Publicar tiene efecto y deja rastro.** `profile_draft` guarda versión, decisiones,
documento y huecos; publicar **supersede** en vez de editar, porque un formulario generado en
marzo tiene que seguir explicándose en septiembre. Dos índices parciales imponen un solo
borrador abierto y una sola versión publicada por unidad y perfil — dos administradores en
paralelo es cómo se pierde la mitad del trabajo de uno, y lo rechaza la base, no la pantalla.
`resolver_for_unit` prefiere el perfil publicado con recaída al archivo, que es lo que hace
verdadero el «sin recompilar»; el YAML se exporta igual, porque un mapeo de esquema que solo
existió en una base de producción es uno que nadie puede diferenciar cuando los datos salen
mal.

La verificación más fuerte que se puede montar sin geodatabase: se generan los metadatos que
el agente habría exportado de un perfil conocido, y la propuesta vuelve a ese mismo perfil
—clase por clase y campo por campo—, con el resolver construido sobre lo propuesto
contestando lo mismo que el original. Con los dos perfiles, que están en idiomas distintos,
así que lo verificado es el mecanismo y no un diccionario afinado a un cliente.

**Aceptación (RF-301):** partiendo del export de metadatos de otra Unidad de Negocio, un administrador funcional produce un perfil operativo y genera los formularios de los seis tipos **sin escribir código ni recompilar**. El CI ejecuta la suite completa dos veces, con el perfil CNEL y con el alterno, y ambas pasan.

---

## I3 — Núcleo de OT, planificadores y asignación · 5 semanas 🟢

**Objetivo:** un planificador crea, prioriza, asigna y reasigna trabajo desde la web, y varios planificadores trabajan a la vez sin pisarse.

| Entregable | Detalle |
|---|---|
| Dominio de OT | Entidades y máquina de estados del SRS 3.3, con transiciones auditadas (usuario, hora de dispositivo y de servidor, GPS, motivo) |
| API | `/work-orders`, transiciones, asignación, despacho (SRS sección 9) |
| Web de planificación | Bandeja, mapa MapLibre, creación, priorización, agrupación geográfica, asignación a cuadrilla y dispositivos |
| Planificadores múltiples | RF-310 a RF-313: ámbito, bloqueo optimista, dueño explícito, tablero compartido |
| Asignación y custodia | RF-320, RF-321, RF-324: asignación a dispositivos, reasignación con motivo, historial de custodia |
| Importación de trabajo | Adaptador del sistema de OT en modo satélite (RF-120) con idempotencia por `external_ref`; simulador `tools/legacy-ot-mock` |
| Auditoría | M16 del SRS completo |

**Aceptación:** dos planificadores con ámbitos solapados asignan trabajo en paralelo sin pérdida ni sobrescritura; una OT importada del simulador conserva su número externo y no se duplica al reenviarla; reasignar una OT deja rastro completo de custodia.

**Decisión necesaria:** D3.

---

## I4 — Móvil offline: mapa, base cifrada y sync · 6 semanas 🔴 🟢

**Objetivo:** el técnico ve su trabajo en un mapa, sin conexión, y lo que captura llega al servidor cuando hay red.

Aquí se materializa ADR-003: el móvil no conoce ArcGIS.

| Entregable | Detalle |
|---|---|
| App Kotlin/Compose | Login corporativo, sesión offline con PIN o biometría (RF-003), bandeja y detalle de OT |
| Base local | Room + SQLCipher como fuente de verdad (RF-100) |
| Mapa offline | MapLibre Native + PMTiles por zona: red, activos, mapa base |
| `offline_package_builder` | Backend: paquete por zona con teselas, activos, historial del activo, formularios, catálogos y manifiesto de modelos; firmado y verificable por hash (RF-360) |
| Motor de sync | Outbox idempotente, reintentos exponenciales, restricciones de red, delta sync, subida por prioridad y resumible (RF-101 a RF-106) |
| Resolución de conflictos | RF-105 y **RF-322**: reasignación sin pérdida de lo capturado offline |
| Traspaso entre dispositivos | RF-323: paquete firmado por QR o enlace local, probado en modo avión |
| Gestión de dispositivos | Enrolamiento, bloqueo y borrado remoto (RF-004) |

**Avance a la fecha.** El motor de decisión está construido y probado; la capa Android no.

| Pieza | Estado |
|---|---|
| Outbox: prioridad de subida, presupuesto de transferencia, reintentos con jitter | Listo, 36 tests |
| Resolución de conflictos device/servidor y compuerta de liberación (RF-322) | Listo, 16 tests |
| Contrato del servidor: enrolamiento, bloqueo remoto, pull delta, push idempotente | Listo |
| Paquete offline por zona con hash de contenido y partes reanudables | Listo |
| **Registro de entrega por dispositivo** y tablero de despliegue en la web | Listo, 15 tests + 19 en la web |
| Construcción de teselas PMTiles (`tools/tiles/build_pmtiles.sh`) | Listo; ejecutarlo necesita tippecanoe y pmtiles instalados |
| App Android: Room + SQLCipher, WorkManager, Compose, MapLibre Native, CameraX | Pendiente |
| Traspaso directo entre dispositivos (RF-323) | Pendiente |

**Asignar no es entregar.** Hasta ahora la plataforma sabía a quién estaba asignada una OT,
pero no si el teléfono la tenía. Son preguntas distintas y a las seis de la mañana solo
importa la segunda: una OT asignada que nunca llegó al dispositivo es una cuadrilla que sale
sin trabajo. `work_order_delivery` registra cada entrega en el momento en que ocurre —dentro
del propio endpoint de bajada, no después— con la versión entregada, de modo que el tablero
también distingue el segundo modo de fallo: la cuadrilla tiene la OT, pero en la versión que
el planificador cambió anoche.

`core:sync` es un módulo Kotlin/JVM sin dependencias de Android (ADR-010), así que sus 52 tests
corren sin SDK, emulador ni dispositivo. La capa Android lo envuelve y no contiene decisiones.

**Nota de verificación:** el entorno de construcción tiene JDK 21 y Gradle 8.14 pero **no SDK de
Android**, de modo que la app no se ha compilado. Las pruebas instrumentadas en modo avión —que
son el criterio de aceptación real de este incremento— siguen pendientes y requieren un
dispositivo.

**Aceptación:** todo el ciclo probado **en modo avión** en el dispositivo de referencia. Un segundo sync sin cambios transfiere menos de 50 KB. Cortar la red al 50 % de una subida y reanudar no reinicia. Reasignar una OT con trabajo capturado offline no pierde un solo dato. Dos teléfonos en modo avión se traspasan una OT.

---

## I5 — Motor de formularios y evidencias · 5 semanas 🟢

**Objetivo:** el técnico llena formularios reales, con fotos, sin conexión. Los formularios vienen del generador de I2, no codificados.

| Entregable | Detalle |
|---|---|
| Renderizador Android | JSON Schema + UI Schema en Compose, con los doce bloques del SRS 4.2 |
| Renderizador web | RJSF con widgets propios, misma semántica |
| Validación compartida | JSON Schema + JSON Logic con idéntico comportamiento en backend, web y móvil (una suite de casos común a los tres) |
| Diseñador de formularios | M04: ajuste sobre lo generado, versionado, publicación que genera GBNF y prompts (RF-033) |
| Seis formularios del piloto | F-TR-01, F-TR-02, F-OP-01, F-MT-01, F-AP-01, F-IC-03 — **generados desde el perfil** y ajustados, no escritos a mano |
| Evidencias | CameraX con encuadres guiados, EXIF, GPS, hash, marca de agua, control de calidad de imagen (M07) |
| ATS bloqueante | Sin ATS aprobado no se habilita el registro de ejecución (etapa 6 del macroproceso) |

**Aceptación:** los seis formularios se llenan de punta a punta en modo avión, con evidencias, y el ATS bloquea de verdad. Cambiar un dominio en el GIS y re-sincronizar metadatos actualiza las opciones del formulario sin desplegar nada.

---

## I6 — Revisión web y staging as-built · 4 semanas 🟢

**Objetivo:** el supervisor cierra el ciclo, y los cambios de red llegan al GIS por la ruta segura.

| Entregable | Detalle |
|---|---|
| Bandeja de revisión | M11: filtros, paginación de servidor, vista de formulario, línea de tiempo, mapa, fotos antes/después |
| Decisión del supervisor | Aprobar, devolver con observaciones por campo, anular. La devolución regresa al móvil junto al campo exacto |
| Acta PDF | ✅ WeasyPrint con fotos, firmas, resumen y QR de verificación (RF-115) |
| `staging_asbuilt` | RF-342: propuestas con `proposal_id`, `GLOBALID` de origen, OT, y resultado de aplicación |
| **Bandeja de revisión GIS** | RF-343: agrupación por zona y alimentador, antes/después, aprobación por lotes, rol de editor GIS |
| Exportación para ArcFM | RF-344: lote aprobado como GeoJSON y CSV de trabajo, una fila por elemento con su acción, atributos y enlace a la OT, fotos y detecciones. **La aplicación en ArcFM la ejecuta el equipo de la distribuidora**; no se construye complemento de ArcMap ni se usa ArcObjects (ADR-001) |
| Controles de calidad del SIG | RF-350 y RF-351: reglas sobre el AMD → trabajos de verificación en campo |

**Aceptación:** una OT con un poste nuevo recorre todo el camino: captura offline → sync → revisión del supervisor → staging → bandeja GIS → lote exportado → el editor del cliente lo aplica en ArcFM → el elemento existe en la geodatabase con su conectividad correcta. La plataforma registra el resultado de cada propuesta (aplicada, rechazada, pendiente) para cerrar la traza. Se mide el tiempo del ciclo completo (insumo de R-N3).

**Decisión necesaria:** D4.

---

### Avance de la pantalla de revisión (mitad web de I6)

| Entregable | Estado |
|---|---|
| API de revisión | ✅ `api/review.py`: cola, detalle **armado en una sola llamada**, decisión y bandeja GIS |
| Cola priorizada | ✅ vencido primero, luego prioridad, luego lo que más lleva esperando — es un atraso, no un buzón |
| Auditoría de valores de IA | ✅ propuesto, final, confianza, modelo, quién confirmó y **de dónde salió** (fragmento dictado o recorte de la foto) |
| Hallazgos normativos con cita | ✅ y un límite sin verificar **no** se presenta como cita del texto oficial |
| Antes/después | ✅ con la misma foto enviada dos veces detectada por hash, y la evidencia cuyo hash no cuadra destacada |
| Impedimentos antes de pulsar Aprobar | ✅ y si el servidor rechaza, devuelve la lista y la pantalla la muestra como lista |
| Bandeja hacia el GIS | ✅ propuestas y lotes, con las que requieren ArcFM contadas aparte (ADR-001) |
| Render en un navegador | ✅ 26 tests de lógica y 14 de render en jsdom |
| Acta PDF con QR de verificación (RF-115) | ✅ `app/reports/`, WeasyPrint + segno |

### El acta, y qué significa que un QR verifique (RF-115)

Un QR que solo abre una página mostrando el mismo hash impreso al lado no verifica nada: sería
la página haciendo eco del papel. Lo que la convierte en verificación es que la plataforma
**reconozca el código** —uno impredecible, para que lo emitido no se pueda enumerar— y pueda
decir **«no consta»** de uno que nunca emitió. Esa frase es la razón de imprimir el QR.

La página es pública a propósito: la abre el cliente cuya luminaria se repuso, que no tiene
cuenta corporativa. Lo que compensa es que revela lo mínimo —si el documento consta, de qué OT
es, cuándo se emitió y su huella— y nada de la persona, la dirección ni las respuestas. Es la
octava y última excepción de la lista de rutas sin identidad, y la lista está en su tope
deliberadamente.

El acta se compone de los **bloques del propio formulario, en su orden**, no de una lista de
campos escrita en el código: una lista a mano deja de mencionar el campo que un administrador
funcional añade mañana, y el acta sigue pareciendo completa. Y seis cosas se imprimen porque el
papel mentiría sin ellas:

| En el papel | Lo que evita |
|---|---|
| Cada valor de IA con su modelo, versión, confianza y quién lo confirmó | Imprimir lo que un modelo adivinó como si lo hubiera escrito una persona (regla 8) |
| Un límite sin verificar marcado **provisional**, nunca citado | Una cifra que nadie leyó en la resolución, con una referencia de aspecto oficial debajo (ADR-007) |
| Una foto cuyo hash no cuadra, impresa diciéndolo | Que el acta parezca más ordenada que la evidencia |
| «Sin firma» donde no hubo firma | Un hueco bajo un pie de firma se lee como una firma mal escaneada |
| «BORRADOR» cruzando la página de una OT sin aprobar | Que una cuadrilla entregue como definitivo lo que no lo es |
| Los avisos del compositor del formulario | Un acta salida de un formulario incompleto que no lo dice |

**Y un supuesto que hubo que corregir.** El primer diseño daba por hecho que volver a renderizar
reproduce los mismos bytes —la salida de WeasyPrint sí es estable byte a byte para una página
trivial, que es lo que muestra una comprobación rápida— y el test lo desmintió: con subconjuntos
de fuentes reales incrustados deja de estarlo. Así que el registro guarda la huella de **los bytes
que se entregaron** y la verificación compara el archivo que alguien tiene contra esa huella; nunca
se vuelve a renderizar para comprobar. Reimprimir emite un documento nuevo, con su propia fila: la
OT puede haberse corregido en medio, y dos papeles distintos afirmando ser el mismo documento es
lo que un registro tiene que poder distinguir.

Y una inconsistencia que apareció al probar: `create_work_order` no asigna código legible —solo
las OT importadas traen número externo—, así que el identificador suele ser el id. El acta
imprimía el id y la página de verificación mostraba una raya, de modo que verificar fallaba justo
en las OT que son la mayoría. Ahora las dos leen la misma función.

---

## I7 — Voz → formulario · 6 semanas 🟢

**Objetivo:** el técnico dicta y el formulario se llena, offline, en español ecuatoriano.

Sigue la guía de entrenamiento sin cambios de fondo; el aporte del addendum es RF-331.

| Entregable | Detalle |
|---|---|
| ASR on-device | sherpa-onnx + Silero VAD. Evaluación en paralelo de la Ruta T (Zipformer con *hotwords*) y la Ruta W (Whisper small + léxico), y elección por error de entidades |
| Extractor | llama.cpp + Qwen2.5-1.5B-Instruct Q4_K_M con gramática GBNF del sub-esquema |
| Normalizador es-EC | Números, unidades, fechas y códigos según las normas de transcripción de la guía 4.3 |
| **Léxico desde el perfil** | RF-331 y RF-332: *hotwords* y sinónimos generados de los dominios del perfil y del contexto de la OT |
| UI de revisión IA | Cada campo propuesto resaltado, con confianza, confirmable o corregible. Se guarda propuesta y valor final (`field_provenance`) |
| `tools/bench-app` | Benchmark on-device: latencia p50 y p90, RAM pico, temperatura, en los tres teléfonos de referencia |
| Informe de línea base | Métricas de la guía 4.7 y 5.5 sobre un set inicial de 2–3 h de audio y 300 transcripciones |

**Aceptación:** dictado de 60 s procesado en menos de 25 s (p90) en el teléfono objetivo, con validez JSON del 100 % bajo gramática, en modo avión. Cada valor de IA queda con origen, versión de modelo y confianza.

### Avance de I7

Construido y ejecutado (sin un solo modelo en disco, que es lo que hace que se pueda probar):

| Entregable | Estado |
|---|---|
| Normalizador es-EC | ✅ `backend/app/voice/normalizer.py` — números, unidades, decimales, fechas, códigos deletreados y plegado de sonidos |
| Léxico desde el perfil (RF-331, RF-332) | ✅ `lexicon.py` — *hotwords* con refuerzo, sinónimos canónicos, etiquetas de la unidad y catálogos de códigos de la OT abierta |
| Gramática GBNF del sub-esquema | ✅ `grammar.py`, probada por lo que acepta y rechaza con un intérprete GBNF propio |
| Extractor | ✅ línea base determinista `RuleBasedExtractor` + contrato con la pasarela. Los pesos (Qwen2.5-1.5B) son lo pendiente |
| Propuesta ≠ respuesta | ✅ `service.py` + API: escribe `field_provenance` sin confirmar, y la compuerta de aprobación de I6 lo bloquea |
| Vocabulario hablado canónico | ✅ `profiles/amd/voice-es-EC.yaml` — español del Ecuador, sin nombres reales del modelo de datos |

Decisiones en [ADR-011](adr/ADR-011-voz-propuesta-con-gramatica.md).

Pendiente, y todo depende de hardware o de audio real que aquí no hay: la elección entre la
Ruta T y la Ruta W, el paquete de modelos del teléfono, la UI de revisión IA en la web,
`tools/bench-app` y el informe de línea base.

---

## I8 — Integraciones corporativas · 4 semanas

**Objetivo:** la plataforma deja de ser una isla.

| Entregable | Detalle |
|---|---|
| Bus de eventos interno | RF-125: bitácora consultable de cada intercambio, con reintento manual |
| Adaptador de OT | RF-120 completo y bidireccional: estados, datos, resumen y evidencias de vuelta |
| Adaptador de call center | RF-124: OT desde reclamos, cierre del reclamo al aprobar |
| Conector ArcGIS de bajada programada | RF-340 en operación continua, con métricas y alertas |
| Pantalla de integraciones | Errores, reintentos, estado de cada conector |

**Aceptación:** pruebas de contrato contra los simuladores; un reclamo entrante genera OT y se cierra automáticamente al aprobarse; la réplica de bajada corre sola durante una semana sin intervención.

### Avance de I8

| Entregable | Estado |
|---|---|
| Bus de eventos interno (RF-125) | ✅ `integration_event` como **outbox transaccional**: el evento se escribe en la transacción de la aprobación, así que no se puede perder ([ADR-012](adr/ADR-012-bus-de-eventos-transaccional.md)) |
| Bitácora consultable con reintento manual | ✅ API + pantalla web; el botón reencola de verdad y reinicia el contador |
| Adaptador de OT bidireccional (RF-120) | ✅ importación idempotente por referencia externa, y empuje de estado y resultado |
| Adaptador de call center (RF-124) | ✅ reclamo → OT una sola vez; aprobar la OT encola el cierre del reclamo |
| Simulador de call center | ✅ `tools/call-centre-mock`, en el Compose de desarrollo |
| Pruebas de contrato contra los simuladores | ✅ los simuladores se **levantan dentro del test** y se verifica el ida y vuelta completo |
| *Worker* periódico de entrega | ✅ `app/workers/`: drena los eventos vencidos cada minuto, **una transacción por evento** |
| Conector ArcGIS de bajada programada (RF-340) | Pendiente: necesita el agente contra un ArcMap real (I1) |

**El fallo que esto impide.** Una cuadrilla repone la luminaria, el supervisor aprueba, todos
consideran el caso cerrado — y el reclamo del cliente sigue abierto, porque cerrarlo era un
efecto secundario que nadie garantizó. Ahora el cierre se escribe junto con la aprobación: si
la aprobación se guardó, el evento existe.

**Y el worker no puede perderlo.** Cada evento se entrega y se marca en su propia transacción:
un worker que muera a mitad de un pase deja entregado lo entregado y el resto intacto, listo
para el siguiente pase. Una transacción alrededor del lote reenviaría todo tras un reinicio. Un
conector en mantenimiento no detiene a los otros, y uno sin URL configurada se salta en vez de
quemarle los reintentos: que un conector no esté desplegado todavía no es un error.

---

## Autenticación corporativa (RF-001, RF-002)

Esto no era un incremento pendiente: era un **hueco**. Había realm de Keycloak desde I0 y
`python-jose` en las dependencias, y ni una comprobación de token en toda la API. Peor: cada
identidad de auditoría llegaba en el cuerpo de la petición que la registraba. El `reviewer_sub`
de una aprobación, el `confirmed_by` de un valor de IA, el `requested_by` de un reintento — todos
valían lo que valiera la afirmación de quien llamaba. Es decir, nada: el rastro que la regla 0.5
del SRS exige era una cadena de texto que cualquiera escribía.

| Entregable | Estado |
|---|---|
| Verificación real de tokens | ✅ firma contra las claves del emisor, emisor, audiencia y caducidad, con tokens firmados de verdad en los tests |
| Rechazos explícitos | ✅ firma ajena, sin caducidad, otra audiencia, otro emisor, `kid` desconocido — cada uno con su test |
| Ámbito por unidad en la puerta del router | ✅ un endpoint nuevo no puede olvidarlo; y responder 403 tanto para una unidad ajena como para una inexistente impide enumerarlas |
| Roles por operación | ✅ aprobar exige supervisor o inspector; reintentar una integración, administración |
| Identidades fuera del cuerpo | ✅ no se ignoran: **no existen**, para que nadie las vuelva a leer por costumbre |
| Guarda en CI de que ninguna ruta quede abierta | ✅ con prueba en negativo, porque la primera versión recorría `app.routes` y encontraba **cero** rutas: pasaba sin mirar nada |
| Escotilla de desarrollo | ✅ requiere `SIGEC_ALLOW_DEV_IDENTITY=1` y entorno de desarrollo; un token presente siempre gana sobre ella |
| El token en la web | ✅ un solo sitio, y **no se persiste**: `localStorage` sobreviviría a un portátil cerrado en una sala de control |
| Login de la web contra Keycloak (PKCE) y renovación silenciosa | ✅ código de autorización con PKCE, `state` comprobado, verificador de un solo uso y renovación **antes** de que caduque |

Decisiones en [ADR-013](adr/ADR-013-identidad-verificada.md).

**Y una vulnerabilidad crítica de verdad.** `npm audit` reportó un *bypass* del sanitizador de
MapLibre 5.x (GHSA-jrc7-96c5-q579, XSS): el mapa del planificador muestra datos que vienen de
nuestra API. Subido a MapLibre 6, que quitó el export por defecto, con el código adaptado.
`npm audit --omit=dev --audit-level=high` es ahora un paso de CI: la Definition of Done no admite
vulnerabilidades críticas ni altas, y hasta hoy nadie lo comprobaba.

---

## Cumplimiento normativo determinista (ADR-007)

Lo que reemplazó al RAG normativo, y que hasta ahora era una promesa del addendum:

| Entregable | Estado |
|---|---|
| `regulatory_parameter` con vigencia y referencia a la norma | ✅ nunca se sobrescribe: una resolución nueva cierra el período anterior, así que una aprobación de marzo sigue explicándose con el límite de marzo |
| Reglas deterministas | ✅ plazo de reposición de APG, umbral de interrupción no computable y resistencia de puesta a tierra admisible |
| Hallazgos citados | ✅ cada hallazgo trae medición, límite, norma y numeral; un hallazgo sin cita es una opinión |
| Bloque de mediciones en los formularios | ✅ `B13`, con `x-regulatory-parameter` por campo — el **código** del parámetro, nunca su valor |
| Compuerta en la aprobación | ✅ solo bloquea un incumplimiento alto y **verificado**: un parámetro que nadie cargó es una omisión de la oficina, no de la cuadrilla |
| Valores confirmados contra el texto oficial | ⚠️ **Pendiente y deliberado.** `seeds/regulatory-ec.yaml` trae la estructura y la referencia, con todos los valores marcados `verified: false`. Nadie de este equipo ha leído las resoluciones vigentes, y una cifra inventada que se convierte en un veredicto de cumplimiento es peor que no tener la regla |
| Repositorio documental con búsqueda de texto completo | Pendiente (I12) |

Tres propiedades tienen su test porque cada una corresponde a una forma de equivocarse:
un hecho ausente **no** es un cumplimiento, un límite ausente **tampoco**, y un límite sin
verificar da un veredicto marcado como provisional en vez de una cita al texto oficial. Los
parámetros de consecuencia legal —la puesta a tierra— no se evalúan en absoluto sin verificar.

---

## I9 — Piloto 1 · 8 semanas 🟢

**Objetivo:** uso real con cuadrillas reales, y los datos que alimentan todo el aprendizaje posterior.

| Entregable | Detalle |
|---|---|
| Despliegue | Una o dos cuadrillas por área, en las zonas y con los dispositivos definidos en D6 |
| Capacitación | Técnicos, jefes de cuadrilla, supervisores, planificadores y editores GIS |
| **Recolección** | Audios con consentimiento, fotos con encuadres guiados, y sobre todo **correcciones humanas** — la etiqueta más valiosa según la guía |
| Medición | Los indicadores del SRS 10.4, más el tiempo de ciclo de la revisión GIS |
| Bitácora de fricción | Todo lo que estorba en campo, priorizado con las cuadrillas |

**Aceptación:** los criterios del SRS 10.4, en particular 100 % de OT cerradas offline sin pérdida de datos y −30 % de tiempo de registro. Metas de recolección de la guía 4.2: 20 h de audio transcrito y 3 000+ imágenes etiquetadas.

**Decisión necesaria:** D6.

---

## I10 — MLOps y paquetes de modelos · 4 semanas, en paralelo a I9

**Objetivo:** el ciclo de mejora funciona sin intervención manual.

| Entregable | Detalle |
|---|---|
| Etiquetado | CVAT (imágenes) y Label Studio (audio y texto), con pre-transcripción de servidor |
| Versionado y registro | DVC para datos, MLflow para experimentos y modelos |
| Compuertas de calidad | Guía sección 8.4, automatizadas: sin superar al modelo vigente no se publica |
| Selección activa | Job semanal según la guía 8.2 |
| Paquetes firmados | Manifiesto Ed25519 con `min_app_version`, despliegue sombra → canary → estable, con reversión |
| Verificación de licencias de datos | El pipeline falla si un dataset no aprobado participó en el entrenamiento |

**Aceptación:** un modelo candidato recorre el ciclo completo — entrenamiento, evaluación contra el set congelado, compuertas, firma, sombra, canary — y se revierte automáticamente al inyectar una regresión de prueba.

---

## I11 — Visión on-device · 6 semanas 🟢

**Objetivo:** la foto pre-llena el estado encontrado y compara el antes con el después.

| Entregable | Detalle |
|---|---|
| Detector | D-FINE-N/S ONNX int8, entrenado con el dataset propio del piloto, pesos base COCO |
| Clasificador de estado | MobileNetV3 sobre recortes, una cabeza por familia de elemento |
| Comparador antes/después | Reglas del SRS 7.4, calibrado con 200 pares anotados |
| Pre-llenado y hallazgos | RF-083 y RF-086: los campos con `x-vision-source` se proponen desde la detección |
| Resumen | Plantilla determinista primero, pulido opcional con LLM y verificación antialucinación |
| OT sugeridas | RF-013 y RF-114: hallazgo → propuesta con prioridad del Anexo C → bandeja del supervisor |
| Enlace taxonomía ↔ AMD | La clase visual apunta al tipo canónico, no al campo real |

**Aceptación:** metas de la guía 6.9 — mAP@0,5 ≥ 0,60, recall de elementos principales ≥ 0,90, **recall de estados críticos ≥ 0,80**, latencia p90 ≤ 2 s en el teléfono objetivo.

### Avance de I11

Construido y ejecutado, otra vez sin un solo peso en disco:

| Entregable | Estado |
|---|---|
| Enlace taxonomía ↔ AMD | ✅ `profiles/amd/vision-taxonomy.yaml` + `app/vision/taxonomy.py`, **validada** contra el vocabulario canónico: un clasificador que propusiera un valor inexistente no carga |
| Contratos del detector y del clasificador | ✅ `contracts.py` — `ObjectDetector`, `StateClassifier`, predicción con modelo, versión, confianza y recorte |
| Pre-llenado desde `x-vision-source` (RF-083) | ✅ `prefill.py`, con umbral por clase aplicado en el servidor, no en el teléfono |
| Hallazgos (RF-086) | ✅ separados de los valores de inventario: un poste inclinado no es un campo del activo |
| Comparador antes/después | ✅ `comparator.py` — pares de resolución declarados; una ausencia no es una resolución |
| Propuesta ≠ respuesta | ✅ `service.py`: procedencia sin confirmar, bloqueada por la compuerta de I6 |
| **Registro de datasets con compuerta de licencia** | ✅ `ml/datasets/registry.yaml` + `scripts/check_dataset_licenses.py`, cuarta verificación obligatoria de CI, probada en negativo |
| Detector, clasificador, OT sugeridas, resumen | Pendiente: son los modelos y los datos |

**Sobre los datasets.** La conclusión de la investigación ahora es una aserción de la suite,
no una nota al pie: todos los datasets públicos de activos eléctricos encontrados son
NonCommercial (InsPLAD), copyleft (STN PLAD, GPL-3.0), de acceso restringido (IDID) o sin
licencia declarada (CPLID). El modelo que se entrega se entrena con las fotografías de la
propia distribuidora. A eso se suma la diferencia de dominio: lo público es imagen aérea de
dron sobre transmisión, y lo nuestro es foto desde el suelo, con teléfono, en distribución
urbana.

De ahí una consecuencia operativa que conviene no postergar: **la app debe pedir encuadres
guiados desde el primer día del piloto**, aunque el modelo todavía no exista. Sin esas fotos
no hay dataset, y sin dataset no hay visión.

---

## I12 — Agentes y endurecimiento · 7 semanas 🟢

**Objetivo:** el supervisor revisa con ayuda, y la plataforma queda lista para producción.

Sin RAG (ADR-007). El nodo de normativa funciona con parámetros y reglas, no con recuperación semántica.

| Entregable | Detalle |
|---|---|
| Pasarela de modelos y planificador de GPU | M19: alias lógicos, colas día/noche, degradación a lote nocturno según perfil |
| **Cumplimiento normativo determinista** | `regulatory_parameter` con vigencia y referencia a la norma; reglas de cumplimiento (plazos de APG, umbral de interrupción no computable, resistencia de tierra admisible); repositorio documental con búsqueda de texto completo y enlace al numeral |
| Grafo de pre-revisión | M17: coherencia, catálogos y normativa, evidencia visual, anomalías, consolidador. Reglas deterministas primero; el LLM solo interpreta texto libre y redacta observaciones |
| Informe en la revisión | RF-111 con observaciones enlazadas a su evidencia, y RF-111a (muestra ciega) |
| Evaluación en CI | Conjuntos dorados de coherencia, evidencia visual, anomalías y seguridad; DeepEval, promptfoo, *red teaming*. **Sin RAGAS**: no hay recuperación que medir |
| **Instrumentación para decidir sobre M18** | Registrar las consultas normativas que hacen técnicos y supervisores y cuáles no resuelve la búsqueda de texto completo. Es el dato que falta para decidir si el RAG se justifica después (ADR-007) |
| Endurecimiento | Pentest, rendimiento, evaluación de impacto LOPDP, documentación de operación, despliegue escalonado |

**Aceptación:** criterios del SRS 10.4 para agentes — recall de inconsistencias ≥ 0,85, kappa supervisor–agente ≥ 0,6 en la muestra ciega, −30 % de tiempo de revisión. Sin vulnerabilidades críticas ni altas. Cero observaciones sin evidencia citada. Todo límite regulatorio evaluado sale de `regulatory_parameter`, ninguno codificado.

---

## Nota sobre el estado de verificación

Los tests de integración **se ejecutaron contra PostgreSQL 16 + PostGIS 3.4 real**, no solo en CI:
749 tests del backend en verde bajo ambos perfiles y en orden aleatorio, y las doce
migraciones aplicadas y revertidas sobre una base limpia (25 tablas de la aplicación, más
`alembic_version` y las de PostGIS).

Eso destapó cuatro defectos que ni el lint, ni `mypy --strict`, ni el renderizado de SQL offline
podían ver:

1. `server_default=func.false()` genera el SQL inválido `false()`. Solo falla al crear el
   esquema de verdad.
2. La tabla de staging `asbuilt_proposal` se buscaba en `Base.metadata` sin estar declarada ahí,
   porque no tiene modelo ORM. Ahora es una tabla Core en los metadatos, que es lo que siempre
   pretendió ser.
3. El composer descartaba la lista `required` que el generador calculaba, de modo que un
   formulario derivado del activo salía **sin ningún campo obligatorio**. Es la vía por la que
   trabajo incompleto habría llegado a una aprobación.
4. `now()` de PostgreSQL es el tiempo de **transacción**, así que todas las filas creadas en una
   transacción comparten `updated_at`. El cursor delta ya lo manejaba —por eso es una tupla— pero
   ahora hay un test que documenta ese caso.

**Un quinto defecto, y de los caros.** Escribiendo la consulta de la bandeja GIS de la pantalla
de revisión apareció que `asbuilt_proposal` **no tenía columna de unidad de negocio**, y que
`create_batch` seleccionaba toda propuesta aprobada de un tipo de activo sin importar de quién
era, para meterla en el lote de la unidad que lo pidió. Es decir: los datos de campo de una
unidad despachados al agente arcpy de otra y escritos en una geodatabase donde nadie estaba
trabajando. No es una fuga de lectura; es una escritura cruzada, más difícil de deshacer y
contraria a ADR-009. Corregido en la migración 0010, con cuatro tests de aislamiento y la
comprobación en negativo de que detectan la regresión.

Y con él, una recaída del defecto 2: `import_all_models()` descubre por nombre de módulo, así
que nunca alcanzaba `staging_table.py`. El resultado era un `create_all` sin la tabla de staging
salvo que otro import la arrastrara por casualidad — un fallo que dependía del orden de los
tests. Ahora el gateway la importa por su efecto.

**La web ya no era un conjunto de pantallas sin aplicación.** No había `index.html`, ni `main.tsx`,
ni `App.tsx`: cuatro pantallas construidas y ningún punto de entrada, así que `npm run build`
habría fallado y nadie lo había intentado. Ahora hay aplicación, se compila, y se verifica en tres
niveles:

| Nivel | Qué prueba | Cuántos |
|---|---|---|
| Lógica pura | Orden, severidad, PKCE, sesión, decisiones del importador | 127 |
| Render (jsdom) | Que las pantallas muestren lo que hay que ver | 58 |
| Navegador real (Chromium) | Que **el artefacto que se despliega** cargue y la puerta de login aguante | 3 |

`pnpm lint` también era un comando documentado que no existía: no había `eslint.config.js`, así
que fallaba con "couldn't find eslint.config.js". Ahora corre, está limpio y es un paso de CI.
Encontró un defecto real que `tsc` acepta: `String(valor)` sobre un valor que viene de JSONB
—una tabla repetible, un límite con rango— produce `[object Object]`, y el supervisor que
auditaba esa propuesta creía que se le había mostrado algo.

El mapa se carga bajo demanda: MapLibre es casi un megabyte y solo lo necesita una pantalla. El
bundle inicial bajó de 1 204 kB a 179 kB — un supervisor que pasa el día en la cola de revisión
estaba descargando el motor de mapas para no abrirlo nunca, por la conexión que de verdad tiene
una oficina de unidad de negocio.

Lo que sigue sin verificar: la app Android (falta el SDK) y el agente contra un ArcMap real.

## Definition of Done (todo incremento)

La del SRS 10.3, con tres adiciones del addendum:

- Requerimientos con tests que referencian su ID (`test_rf_322_reasignacion_sin_perdida`).
- OpenAPI actualizada y clientes regenerados.
- Flujos móviles probados **en modo avión** en el dispositivo de referencia.
- Sin vulnerabilidades críticas ni altas; licencias aprobadas.
- README del módulo y ADR si hubo decisiones de arquitectura.
- Demo al product owner con datos realistas.
- **La suite pasa con los dos perfiles de modelo de datos** (CNEL y alterno).
- **Ningún identificador del modelo real fuera de `profiles/`** (RF-305, verificado en CI).
- **Nada escribe campos de conectividad** de la red geométrica (verificado contra `tools/arcgis-mock`).

---

## Qué hacer ahora

El orden inmediato, para empezar de a poco:

1. **I0 está cerrado** y en la rama: monorepo, Docker Compose, esquema PostgreSQL, agente con sus invariantes y CI con las tres verificaciones, todas probadas en negativo.
2. **Acceso para I1:** la máquina Windows con ArcGIS Desktop Advanced (ya licenciado) preparada para un proceso desatendido, y una copia de la geodatabase. Es lo único que falta para arrancar I1.
3. **Mientras tanto, I2**, que no depende de arcpy: importador de metadatos, generador de formularios y el diagnóstico de completitud del perfil.
4. Con acceso, **lanzar I1** y tratar su informe como puerta: si invalida una hipótesis, se corrige el addendum antes de continuar.

Los seis tipos de activo del piloto (estructura de soporte, transformador de distribución, luminaria, seccionador fusible, tramo y punto de carga) y los seis formularios (F-TR-01, F-TR-02, F-OP-01, F-MT-01, F-AP-01, F-IC-03) son el alcance vertical de I2 a I7. Conviene no ampliarlo antes del piloto.
