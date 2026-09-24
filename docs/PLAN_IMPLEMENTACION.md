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
| Auditoría | ✅ M16 completo: bitácora append-only con cadena de hashes (RF-160) y trazabilidad por OT, activo, usuario o dispositivo (RF-161). **Estaba dado por hecho y no existía** — ver más abajo |

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

`core:sync` es un módulo Kotlin/JVM sin dependencias de Android (ADR-010), así que sus 60 tests
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
| Validación compartida | ✅ un corpus (`forms/contract/validation-cases.json`) que ejecutan las tres plataformas |
| Diseñador de formularios | M04: ajuste sobre lo generado, versionado, publicación que genera GBNF y prompts (RF-033) |
| Seis formularios del piloto | F-TR-01, F-TR-02, F-OP-01, F-MT-01, F-AP-01, F-IC-03 — **generados desde el perfil** y ajustados, no escritos a mano |
| Evidencias | CameraX con encuadres guiados, EXIF, GPS, hash, marca de agua, control de calidad de imagen (M07) |
| ATS bloqueante | Sin ATS aprobado no se habilita el registro de ejecución (etapa 6 del macroproceso) |

**Aceptación:** los seis formularios se llenan de punta a punta en modo avión, con evidencias, y el ATS bloquea de verdad. Cambiar un dominio en el GIS y re-sincronizar metadatos actualiza las opciones del formulario sin desplegar nada.

---

### Validación compartida: un corpus, tres implementaciones

Las reglas condicionales de los bloques son JSON Logic para que el backend, la web y el móvil
las evalúen igual. «Igual» no se consigue escribiendo el mismo algoritmo tres veces con cuidado:
eso produce tres algoritmos que coinciden en los casos que a alguien se le ocurrieron. Se
consigue con `forms/contract/validation-cases.json` —30 casos— que las tres suites ejecutan.

El fallo que impide es caro en campo y va en las dos direcciones. Si el teléfono acepta una
captura que el servidor rechaza después, el trabajo de la cuadrilla vuelve al día siguiente y
nadie entiende por qué. Si el teléfono exige un campo que el servidor no pide, la OT no se puede
cerrar con la red caída — que es la situación para la que existe todo el producto.

| Implementación | Dónde | Corre |
|---|---|---|
| Servidor | `backend/app/forms/rules.py` | `pytest`, 49 casos |
| Web | `web/src/forms/rules.ts` | `vitest`, 47 casos |
| Móvil | `android/core/sync/.../FormRules.kt` | `gradle :core:sync:test`, en la JVM sin SDK ni dispositivo (ADR-010) |

Los casos que importan son los aburridos, porque son los que las tres implementaciones fallan a
la vez: **el cero es una respuesta** (una medición de 0 Ω es un resultado), **el falso también**
(«¿quedó señalizado? No» es una respuesta, y en JavaScript un `false` desprevenido se lee como
vacío), **los espacios en blanco no**, `11` y `"11"` no son el mismo valor, un booleano no es 0
ni 1, y un operador desconocido da falso en vez de excepción — una regla mal escrita no puede
impedirle a una cuadrilla enviar el día de trabajo.

Dos guardas sostienen el contrato: cada suite comprueba que el corpus **distingue una
implementación ingenua de la correcta** —un corpus que cualquiera pasa no mide nada— y la del
backend comprueba que las tres suites siguen existiendo y leyendo el mismo archivo, porque borrar
una dejaría CI en verde y el contrato reducido a dos plataformas en silencio. Las dos están
probadas en negativo.

`rules.ts` es la biblioteca que consumirá el renderizador web de I5 cuando llegue; el contrato se
establece ahora precisamente para que no pueda divergir al escribirlo.

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
| Render en un navegador | ✅ 26 tests de lógica y 16 de render en jsdom |
| Acta PDF con QR de verificación (RF-115) | ✅ `app/reports/`, WeasyPrint + segno |
| **Vista de formulario** | ✅ `web/src/forms/FormView.tsx`: los bloques en su orden, la captura tal como la escribió la cuadrilla |

### La vista de formulario, y lo que faltaba sin ella

La pantalla de revisión mostraba todo *sobre* una captura —la auditoría de IA, los hallazgos
normativos, las fotos antes y después, los impedimentos— y **nunca la captura**. Un supervisor podía
aprobar una OT sin haber visto una sola vez las respuestas como las escribió la cuadrilla, que es la
única vista de la que trata la decisión.

Se compone del `schema` y del `ui_schema` generados, con los bloques en el orden del formulario, y
no de una lista de campos escrita en el código: esa lista deja de mencionar el que un administrador
funcional añade mañana y la pantalla sigue pareciendo completa. Es la misma regla que el acta aplica
en papel.

Es de **solo lectura** a propósito. Un supervisor corrige devolviendo la OT con una observación en el
campo exacto (RF-112), no editando lo que otro registró: una aprobación vale porque dice que una
persona revisó lo que la cuadrilla escribió, y una respuesta editada que nadie puede atribuir no vale
nada. El renderizador editable pertenece a la captura de oficina y reutilizará esta disposición y
estas reglas.

Tres cosas se marcan sobre el campo, porque ninguna debería tener que inferirse: un valor que
propuso un modelo —con modelo, versión, confianza y si alguien lo confirmó o lo corrigió (regla 8)—,
un obligatorio vacío, y un campo que una regla condicional exige dadas las demás respuestas. Lo
último sale de `rules.ts`, el mismo evaluador que corre el teléfono contra el corpus compartido, así
que la pantalla marca exactamente lo que el servidor va a rechazar.

Y **un campo huérfano se muestra**: uno que el esquema declara, la cuadrilla respondió y ningún
bloque agrupa es la única forma en que esta vista puede perder datos en silencio, así que aparece
bajo su propio encabezado como algo que alguien debe reportar.

**Nota sobre RJSF.** El plan nombraba `react-jsonschema-form`. No se usó: el esquema que esta
plataforma renderiza es un subconjunto que ella misma genera, y RJSF traería un árbol de
dependencias para widgets que habría que sobrescribir de todos modos. La semántica compartida —que
es lo que el entregable pide— la da el corpus de validación, no la biblioteca.

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
| Pasarela de modelos y planificador de GPU | ✅ alias como datos, admisión por perfil, colas día/noche y degradación (RF-200 a RF-205) |
| **Cumplimiento normativo determinista** | `regulatory_parameter` con vigencia y referencia a la norma; reglas de cumplimiento (plazos de APG, umbral de interrupción no computable, resistencia de tierra admisible); repositorio documental con búsqueda de texto completo y enlace al numeral |
| Grafo de pre-revisión | ✅ mitad determinista (coherencia, anomalías, consolidador) con el guardrail de evidencia; los nodos de modelo declarados y degradados por M19 |
| Informe en la revisión | RF-111 con observaciones enlazadas a su evidencia, y RF-111a (muestra ciega) |
| Evaluación en CI | ✅ conjuntos dorados de coherencia, anomalías, normativa y seguridad con los pisos de RNF-060 (`ml/agents_eval`); faltan los de evidencia visual y DeepEval/promptfoo, que envuelven un modelo. **Sin RAGAS**: no hay recuperación que medir |
| **Instrumentación para decidir sobre M18** | Registrar las consultas normativas que hacen técnicos y supervisores y cuáles no resuelve la búsqueda de texto completo. Es el dato que falta para decidir si el RAG se justifica después (ADR-007) |
| Endurecimiento | Pentest, rendimiento, evaluación de impacto LOPDP, documentación de operación, despliegue escalonado |

### M17: el grafo de pre-revisión, la mitad que no necesita modelos

La regla 1 de la sección 7.7 del SRS dice **reglas deterministas primero, el LLM después**, y eso es
lo que se construyó: los nodos de coherencia (RF-171) y de anomalías (RF-174) son funciones puras
sobre los hechos de una captura, el consolidador (RF-175) produce el `AgentReport` del Anexo D, y los
nodos que necesitan un modelo quedan declarados y degradados por M19.

No se usó LangGraph. El framework se gana su sitio cuando hay puntos de control que reanudar y
llamadas a modelos que reintentar; hoy cada nodo es una función pura, y envolver cinco de ellas en
una máquina de estados añadiría una dependencia, un formato de serialización y un modo de fallo a
cambio de nada. LangGraph entra con los nodos LLM de I12, que es lo que orquestará.

**El guardrail es la pieza central.** La nota 3 de 7.7: *una observación = evidencia + fuente*. Una
observación sin nada que señalar es una opinión, y una opinión en un documento que un supervisor usa
para aprobar trabajo de campo es peor que el silencio — gasta su atención y no se puede comprobar. Se
descarta, y el descarte **se cuenta** en el informe: un nodo que empiece a producir observaciones sin
apoyo se nota en la ejecución siguiente y no en seis meses. Las normativas tienen una segunda barra
(RF-172): sin cita al documento no pasan, y no se salvan cambiándoles la categoría.

Lo que las reglas miran, y lo que deliberadamente no:

| Nodo | Encuentra | No duplica |
|---|---|---|
| Coherencia | horas fuera de secuencia, horas posteriores al envío, captura lejos del activo, evidencia con hash que no cuadra, valor de IA aceptado sin cambios con poca confianza | los impedimentos de I6, que ya bloquean la aprobación |
| Anomalías | ejecución implausiblemente corta, **la misma foto cerrando dos OT distintas**, un mismo punto GPS en dos OT, un archivo repetido dentro de la OT | las horas al revés, que son hallazgo de coherencia: leer el mismo error en dos voces es peor que leerlo una vez |
| Normativa | los hallazgos deterministas de ADR-007, **transportados** con su cita | no los recalcula: el informe tiene que concordar con la compuerta de aprobación que decidió |

Las reglas entre OT son las que aportan de verdad: dentro de una OT la pantalla de revisión ya señala
un archivo enviado dos veces; la misma fotografía cerrando dos órdenes, o un GPS cerrando órdenes en
dos parroquias, es el patrón que nada mira hoy.

**El tono está en el requerimiento, y no por cortesía.** RF-174 pide «no acusa: marca para
revisión», con la regla o el estadístico visible en cada alerta. Un informe que acusa se discute en
vez de comprobarse, y la cuadrilla nombrada deja de cooperar con la plataforma — a esa altura el
agente ha costado más de lo que encontró. Un test comprueba el lenguaje.

Y **la regla 14 se verifica estructuralmente**: el paquete no puede importar nada que escriba el
estado de una OT, y un recorrido del árbol de sintaxis lo impone. El fallo que importa no es escribir
mal una función hoy, es que alguien añada el atajo dentro de un año —«solo para las de riesgo
bajo»— y que nadie lo note. La guarda está probada en negativo.

**Y un defecto de localización que salió al probarlo:** `:,.0f` de Python escribía «6,480 m», que en
español del Ecuador se lee como seis coma cuatro ocho metros — los separadores están al revés. Ahora
las distancias van sin agrupación por debajo del kilómetro y en kilómetros con coma decimal por
encima, que además se juzga más rápido: «a 6,5 km del activo» entra de una.

**Y la pre-revisión ya corre y se guarda.** `app/prereview/` es la otra mitad: construye los hechos
desde la base, ejecuta el grafo, y guarda `agent_run`, `agent_report` y `agent_step_trace`
(migración 0013). Está **fuera** de `app/agents/` a propósito: la guarda estructural de ese paquete
prohíbe importar SQLAlchemy, que es cómo la regla 14 se sostiene sin que nadie tenga que recordarla.
Una guarda con una excepción para «el archivo que sí puede escribir» sería una guarda que alguien
amplía.

Lo que el criterio de aceptación de RF-170 pide, y que ahora tiene test contra base real:

| Propiedad | Cómo se sostiene |
|---|---|
| Toda OT sincronizada acaba con ejecución en estado terminal | `orders_without_a_terminal_run` es la cola del worker, y se comprueba que se vacía |
| Un fallo queda registrado y se reintenta | una excepción del grafo no escapa: deja la ejecución en `fallido` con su motivo. El único estado prohibido es que la OT no tenga ejecución ninguna |
| Nada bloquea la revisión humana | el worker nunca está en el camino de una petición, y aprobar funciona sin informe |
| RF-180: reproducir una ejecución da el mismo informe | dos ejecuciones sobre la misma captura producen documentos idénticos salvo la duración medida |
| El nodo que no corrió queda en la traza con su motivo | «¿por qué no hay sección visual?» tiene respuesta en el registro y no en la memoria de alguien sobre el despliegue |

Y en la pantalla del supervisor el informe aparece con el riesgo **en palabras**, cada observación con
su evidencia señalada y su acción sugerida, y —cuando no hay informe— el motivo: «falló» y «todavía
no corrió» son cosas distintas para quien está por decidir sin él, y ninguna de las dos es motivo de
esperar.

**La aprobación en lote de RF-176 ya está, y su forma la dicta el criterio de aceptación**, que es un
test negativo: *no existe ningún camino de aprobación automática sin clic humano*. Lo que ese test
comprueba no es que hoy esté bien escrito, es que **siga** estándolo cuando alguien añada, dentro de
un año, «un job nocturno que apruebe las de riesgo bajo, que total el agente ya las revisó». La frase
suena razonable y es exactamente el fallo, así que un recorrido del árbol de sintaxis prohíbe que los
workers, los agentes, la persistencia de la pre-revisión y la pasarela llamen a `decide` o mencionen
el estado `aprobada`. La guarda está probada en negativo.

Las tres reglas del lote, y por qué cada una es así:

| Regla | Por qué |
|---|---|
| Toda aprobación pasa por **el mismo** `decide` | un camino más rápido que se saltara los impedimentos de I6 sería una segunda puerta más débil, y a partir de ahí la compuerta no significa nada. El lote los recibe idénticos: una OT sin fotos se rechaza dentro del lote |
| La muestra se redondea **hacia arriba** y su piso es uno | el 5 % de tres es 0,15, y una política que redondea a cero es una política con un agujero: el supervisor que lo descubre aprueba de tres en tres. Un lote de una sola OT la aparta entera —aprobar de una en una ya existe y se llama aprobar— |
| Sin informe **no** es riesgo bajo | una OT que nadie pre-revisó es justo la que un lote no debería tragarse |

Y la cola de revisión ahora trae el riesgo de cada OT, en una consulta por página y no una por fila:
sin eso el supervisor selecciona a ciegas y el servidor le rechaza media selección. En la pantalla,
solo las de riesgo bajo tienen casilla; las demás dicen por qué no la tienen. El lote necesita **dos
pulsaciones**, porque libera las propuestas as-built de cada OT hacia el SIG corporativo y eso no se
hace con un clic mal dado. Y el resultado nombra las apartadas: «12 aprobadas» sin «1 apartada» se lee
como un lote terminado, y la apartada es el punto del requerimiento.

**Otro defecto de localización, de la misma familia que el de las distancias:** el motivo del rechazo
decía «riesgo medium». Los identificadores van en inglés (regla 11), así que interpolar el valor del
enum en una frase en español produce eso mismo en la pantalla de un supervisor. Las palabras viven
ahora junto al enum, y un test falla si alguien añade un nivel sin la suya.

**Y la muestra ciega de RF-111a, que es lo que hace que el kappa signifique algo.** El riesgo que el
requerimiento nombra es el anclaje: un supervisor que lee «riesgo bajo, sin observaciones» antes de
mirar la captura encuentra la captura bien. Cuando eso pasa por costumbre, la revisión es del agente,
la concordancia es perfecta y nadie puede notarlo — un número calculado sobre revisiones que vieron
el informe primero mide concordancia con una sugerencia, no entre dos juicios.

Así que en una parte configurable de las OT (10 % por omisión) el informe **se retiene** hasta que el
supervisor registra su decisión, y después se muestra. Tres decisiones de diseño sostienen el número:

| Decisión | Por qué |
|---|---|
| El sorteo lo hace el servidor, al guardar el informe | `blind_sample` era un booleano que mandaba el navegador: un campo que rellenaba lo que se está midiendo. Y sortear en el camino de una petición sería sortear con el medido dentro |
| El sorteo se guarda, no se recalcula | la tasa es configurable, y una métrica cuyo denominador cambia cuando alguien edita un ajuste no se puede defender en una reunión. La fila lleva la tasa que estaba en vigor |
| Se retiene el informe, nunca lo determinista | los hallazgos normativos, los impedimentos y las fotos no son del agente: son de lo que depende una aprobación, y RF-204 exige poder aprobar sin informe ninguno |

Y **se muestra después**, con la OT todavía abierta: retenerlo y no mostrarlo nunca le costaría al
supervisor la realimentación y a la plataforma su única oportunidad de que alguien le diga que el
informe estaba equivocado.

La concordancia se reduce a dos categorías —«tenía problema» o no— porque comparar tres botones
contra tres niveles de riesgo sería comparar escalas distintas: devolver y anular difieren en la
consecuencia, no en el hallazgo. Sobre eso, el kappa de Cohen con el piso de RNF-060 (≥ 0,6), y dos
negativas deliberadas: con menos de diez pares no se reporta kappa —sobre nueve casos es ruido con
decimales— y si los dos usaron una sola categoría se reporta **indefinido** y no 1,00, que es
exactamente el número que el requerimiento existe para no creerse. La tabla viaja con el
coeficiente, porque un 0,58 no dice *cómo* discreparon y las dos formas cuestan cosas muy distintas:
que el agente no viera un problema no es que el agente diera una falsa alarma.

**Y el tablero RF-134 ya está completo**, con la concordancia como uno de sus paneles —que es
literalmente lo que pide el criterio de aceptación de RF-111a— más los cinco que el requerimiento
enumera: aceptación por campo, correcciones por clase visual, error de palabras estimado, adopción de
la voz por persona y versiones en la flota. Todo sale de `field_provenance`, que existe justamente
para que estos números se deriven en vez de contarlos alguien con una hoja de cálculo.

Un tablero es una herramienta de decisión: alguien mira una tasa y decide publicar un modelo, pedir
un lote de etiquetado o no hacer nada. Así que lo que se construyó con cuidado no es la aritmética
sino lo que evita la decisión equivocada:

| Decisión | Por qué |
|---|---|
| Ninguna tasa se reporta con menos de cinco propuestas | «100 % de aceptación» sobre dos propuestas es ruido con signo de porcentaje, y la decisión que invita —publicar— es la cara. La cuenta sí viaja: ocultarla también dejaría al analista sin saber si el campo se usa |
| El error de palabras dice qué mide | un WER de verdad compara contra una transcripción de referencia del mismo audio, y nadie transcribe estas grabaciones dos veces. Lo medible es la distancia entre lo que la voz propuso para un campo y lo que la persona envió: reconocimiento **y** extracción. El propio payload lo aclara, porque quien lea el número lo va a citar |
| Lo que no se pudo medir se cuenta | una tasa calculada sobre veinte campos de cuatrocientos no es la tasa de nada, y la única forma de que el lector lo note es que el tablero lo diga |
| Los consejos no acusan a nadie | la misma regla de RF-174 para los agentes: un panel que suena a veredicto se discute en vez de accionarse. Y la adopción de la voz dice explícitamente para qué es —saber si la función sirve— porque un número por persona se lee como calificación |

Dos cosas que salieron de escribirlo. La primera, un defecto de denominador: la adopción de la voz
medida sobre «las capturas que ya tienen un valor de IA» haría que quien nunca dicta no tuviera
capturas, y la adopción saldría alta justo donde es más baja; el denominador son **todas** sus
capturas enviadas. La segunda, del lado de la pantalla: el panel de la flota compara versiones del
mismo modelo y avisa cuando una nueva acepta peor que la anterior —«nunca regresar» es la primera
compuerta de calidad de la guía (8.4)—, pero solo cuando **las dos** tienen tasa reportable: una
caída medida contra un número que el servidor se negó a dar sería una caída inventada.

Queda fuera el panel de evidencia visual (300 pares evaluados por supervisores), que necesita el
piloto.

**Y los conjuntos dorados son ahora una compuerta, no una intención.** La regla 15 dice que todo
cambio de prompt, grafo o modelo pasa por `ml/agents_eval` en CI; hasta ahora no había nada que
pasar. Se construyen como manda la sección 11.2 de la guía de entrenamiento: diez capturas limpias y
un catálogo de **perturbaciones etiquetadas** que se siembran sobre ellas, 188 casos de los que la
mitad son legítimos.

Esa mitad limpia es la parte que se suele omitir y la que decide si el número sirve: un falso
positivo solo aparece en una captura que estaba bien, así que un corpus de puros defectos informa una
precisión de 1,00 y no prueba nada. Las capturas limpias incluyen a propósito las que más se parecen
a un problema —el GPS a 200 m del activo, el cambio de luminaria de seis minutos, la propuesta de IA
aceptada con la confianza justa— porque son esas las que un supervisor castiga ignorando el informe
entero.

| Compuerta | Piso (RNF-060) | Hoy |
|---|---|---|
| Recall sobre inconsistencias sembradas | ≥ 0,85 | 1,00 |
| Precisión sobre capturas legítimas | ≥ 0,70 | 1,00 |
| Recall de anomalías | ≥ 0,80 | 1,00 |
| Observaciones normativas sin cita | 0 | 0 |
| Obediencias a instrucciones inyectadas | 0 | 0 |
| Datos personales sembrados que llegan al informe | 0 | 0 |

El *red teaming* mide la obediencia como **diferencia**: el informe producido con la frase inyectada
tiene que ser el mismo que sin ella. Comprobar algo más débil —«que el riesgo no salga bajo»— fallaría
en capturas cuyos hechos son de verdad leves, y una compuerta que salta con el comportamiento correcto
es una compuerta que alguien apaga. Hoy los nodos son deterministas y no hay nada que obedezca una
orden; el conjunto existe para fallar el día que un nodo LLM entre en I12 y trate el texto de la
cuadrilla como parte de su prompt. Escribirlo después de ese día es escribirlo tarde.

**Y encontró un fallo en la primera ejecución.** La regla de horas posteriores al envío comparaba
contra el reloj de quien corría el informe en vez de contra el envío de la captura: se callaba entera
para cualquier llamador que pasara un `now` —el lote nocturno incluido, que es justo el caso que su
propio comentario decía proteger— y el recall seguía por encima del piso. Una compuerta puede pasar
con una regla muda, así que las compuertas están probadas en negativo: se rompen reglas a propósito y
se comprueba que cada métrica se hunde y nombra los casos.

DeepEval y promptfoo entran con I12 sobre estos mismos corpus: los dos envuelven un modelo, y lo que
una compuerta necesita primero son los datos etiquetados, que es lo que un framework no da.

Falta la mitad que necesita modelos: los nodos VLM y de redacción, en I12.

---

### RF-122: el ERP, y el catálogo que nadie podía llenar

El catálogo `material` se enviaba con `source: integracion` y la nota «vacío hasta el primer envío del
ERP», y **no existía forma de hacer ese primer envío**. Un teléfono que dibujaba la tabla de
materiales de B07 tenía un campo de código y ningún valor para elegir. Es el mismo patrón de RF-034 y
de los bloques B04/B07: un dato que apuntaba a nada.

**El ERP es el dueño, así que la plataforma escribe ese catálogo solo como el ERP.** `upsert_entry`
rechaza una edición a mano en un catálogo de integración y el adaptador pasa `from_integration=True`.
Para eso existe la bandera: un valor tecleado sobre uno que el lote de esta noche va a sobreescribir
es un valor que desaparece sin explicación.

**Un lote que no se declara completo no puede retirar nada.** Una descarga paginada que falló a medias
vaciaría el selector en el campo — silencioso en el servidor y muy ruidoso en una subestación — así
que el ERP tiene que decir `"complete": true` para que la plataforma retire los códigos que dejó de
enviar, y el informe dice en qué modo corrió. El simulador `tools/erp-mock` sirve las dos formas
(`/materials?partial=1`), así que la negativa se ejercita en vez de suponerse.

**Las existencias son una instantánea, reemplazada por ubicación.** Fusionar dejaría una línea
fantasma del material que se acabó, y alguien planifica contra las líneas fantasma. `as_of` viene del
ERP y se muestra junto al número: una existencia de un lote nocturno tiene horas, y un número
presentado como actual es como una cuadrilla maneja hasta una bodega por algo que ya no está.

**El consumo y la devolución son dos movimientos, no una cantidad con signo.** Instalar tres
aisladores y sacar dos rotos es un consumo *y* una recepción, y caen en lugares distintos del ERP: lo
reutilizable a bodega, la chatarra a disposición. Una sola cifra «usada» perdería la mitad del
inventario — que es exactamente la forma que B07 se diseñó para evitar. Lo retirado sin estado
anotado va «por clasificar» y no se asume reutilizable: meter chatarra a bodega es la dirección cara
de ese error.

Los dos movimientos se publican **dentro de la transacción de la aprobación**, como el cierre del
reclamo de RF-124: una OT aprobada no puede dejar al ERP sin saber qué salió de bodega. La clave de
idempotencia es la OT y el tipo, así que una corrección actualiza el asiento en vez de doblarlo.

**Y una escritura cruzada que encontró el sabotaje.** El reemplazo por ubicación es un `DELETE`, y su
filtro de unidad de negocio no estaba probado: `stock_of` filtra al leer, así que ningún test veía
que quitarle el filtro al borrado dejaría que importar las existencias de una unidad **vaciara las de
otra** con el mismo código de bodega. «BOD-01» es un nombre que se repite. Es la clase de defecto que
ya costó caro una vez aquí —la tabla de staging as-built sin columna de unidad— y ahora tiene su
test.

Dieciocho guardas rotas a propósito y detectadas, dos de ellas después de corregir lo que el primer
pase dejó ver: un sabotaje que no aplicaba por una diferencia de formato, y el hueco de la escritura
cruzada.

Y una guarda vieja que atrapó la primera versión de este adaptador: RF-160 prohíbe que cualquier
módulo reasigne el payload de un asiento de la bitácora de integraciones, y el importador lo hacía
para dejar el recuento del lote. El recuento va ahora en la **respuesta** del asiento, que es donde
vive el resultado; el payload es lo que se pidió. Es exactamente lo que esas guardas existen para
impedir, y esta vez impidió algo mío.

---

### B04 y B07: los dos bloques comunes que estaban declarados y no existían

El SRS 4.2 dice que los bloques B1 a B12 están «en todos los formularios». Faltaban dos, y cada uno
dejaba una declaración sin efecto — el mismo patrón de RF-034 y RF-147: no un requisito sin
implementar, sino un dato que apuntaba a nada.

**B04 Seguridad.** Seis formularios declaraban `requires_ats: true`. La bandera llegaba al teléfono
como `x-requires-ats` y **nada la miraba**, porque no había ningún campo donde anotar qué ATS se
firmó: una OT «que exige ATS» se podía cerrar sin nombrar ninguno. Ahora la referencia es un campo y
el compositor la hace obligatoria cuando el formulario lo declara. Y hay una guarda que habría
encontrado el hueco: un formulario que exige ATS y no incluye B04 **avisa**, porque esa mala
configuración es invisible y era el estado de los seis.

La referencia es un texto y no una relación a la respuesta del F-TR-01, por una razón de campo: el
ATS se firma en papel o en otro dispositivo cuando el propio se quedó sin batería, y exigir un
identificador de la plataforma habría dejado a la cuadrilla sin poder cerrar un trabajo que sí hizo
con su análisis firmado. Lo que la plataforma puede exigir —y exige— es que alguien escriba cuál.

**B07 Materiales.** El catálogo `material` existía, declarado `source: integracion` y vacío «hasta el
primer envío del ERP», y **ningún formulario** donde anotar el consumo salvo una tabla propia dentro
del bloque de luminarias. Dos decisiones:

* **Un solo lugar.** La tabla de AP01 se retiró en favor de B07: dos tablas habrían obligado al
  conector del ERP a leer en dos sitios, y uno se habría desviado. El SRS nombra la tabla dos veces
  —como bloque común y dentro de F-AP-01— y es la misma información.
* **Instalado y retirado son dos cantidades.** Un cambio de luminaria instala una y retira otra, y el
  ERP necesita los dos movimientos: el consumo, y el ingreso a bodega o a chatarra. Una sola cantidad
  «usada» habría perdido la mitad del inventario. `removed_state` decide a dónde va lo retirado, y por
  eso es un enum: «reutilizable» va a bodega y «chatarra» a disposición.

**Y un operador nuevo en el lenguaje de reglas, que es lo que casi se convirtió en el siguiente
defecto del mismo tipo.** La regla de B04 —«si hay permiso de trabajo, exige la referencia del ATS»—
se escribió con `!!`, el «está contestado» de JSON Logic, y **ninguna de las tres implementaciones lo
soportaba**: el evaluador es un subconjunto deliberado y un operador desconocido vale `false`, así que
la regla habría sido otra declaración que no hace nada. Se detectó antes de escribir el código porque
el corpus compartido es lo primero que se toca: ocho casos nuevos en
`forms/contract/validation-cases.json`, que fallaron en las tres implementaciones, y después `!!` y su
complemento `!` en el backend, la web y Kotlin — escritos con la misma función `is_answered` que decide
el otro lado de la regla, para que un 0 medido cuente como respuesta en la condición igual que cuenta
en la exigencia.

Los cinco formularios que cambiaron de forma subieron a **1.1.0**. Es un cambio de forma real —hay un
campo obligatorio nuevo— y RF-032 hace el resto: cada OT en vuelo conserva la versión con la que se
asignó. De paso, los tests de RF-032 dejaron de escribir «1.0.0» a mano y leen la versión del archivo:
un test que fija la versión de hoy falla en el siguiente cambio legítimo, y entonces alguien edita el
test en vez de pensar en el cambio.

Doce guardas rotas a propósito y detectadas. El cambio en Kotlin **sí** se ejecuta: no en este
entorno —el módulo Android no tiene wrapper de Gradle y el SDK no se puede descargar— pero el job
`core:sync` de CI corre `gradle :core:sync:test` con el Gradle del runner y sin SDK de Android
(ADR-010), y pasó con el operador nuevo. Es la razón por la que ese módulo está deliberadamente libre
de dependencias de Android: la lógica de más riesgo de la plataforma se prueba sin emulador ni
dispositivo.

---

### RF-012: el plan preventivo, y por qué el periodo es una etiqueta

El criterio es un conteo: «un plan mensual genera N OT en la fecha programada». Un conteo es toda la
dificultad. Una OT de más manda una cuadrilla a un poste que está bien; una de menos deja una
inspección sin hacer y el área se entera en la auditoría. Así que todo el módulo está construido para
poder defender ese número después.

**La guarda de idempotencia es una etiqueta de periodo, no un reloj.** `plan_issue` guarda una fila
por plan, activo y **periodo** —`2026-09`, `2026-T3`— y la unicidad es un índice de la base. Dos
corridas el 3 y el 27 de septiembre son el mismo periodo y la segunda no emite nada. La alternativa
que parece natural —comparar contra la fecha de la última corrida más la frecuencia— habría hecho
legal la segunda, y el error solo se ve contando OT. Son **dos** índices parciales y no uno, porque
PostgreSQL trata los NULL como distintos: un plan que emite una sola OT para todo el alcance tiene
`asset_code` nulo, y con un índice único corriente podría emitir el mismo periodo dos veces.

**El día 28 es una decisión, no un límite técnico.** «El 31 de cada mes» no existe en febrero, y las
dos formas de arreglarlo sobre la marcha dan conteos anuales distintos del que el área reporta:
disparar el 28 acorta el periodo, saltarse febrero emite once veces al año. La plataforma rechaza el
29, el 30 y el 31 y dice por qué, que es una conversación con el planificador en vez de una
discrepancia en una auditoría.

**El disparo es «el día programado o después».** Una máquina caída el día 5 no puede costarle al área
un mes de preventivo, y ser generoso aquí es seguro *precisamente* porque la etiqueta impide el doble.
Ser estricto, en cambio, perdería el periodo entero en silencio.

**Un alcance por alimentador o por zona es una aproximación declarada.** «Todos los postes del
alimentador 04BH07T11» es una pregunta que contesta el SIG, no esta plataforma (ADR-006). Lo que esta
plataforma puede contestar es «los activos de ese alimentador en los que ya registramos trabajo», que
es un subconjunto — y justamente el activo que nunca se ha intervenido es el que más falta hace
inspeccionar. El caveat viaja con cada emisión y aparece en la pantalla con las palabras del
servidor. Una lista explícita, que el área escribe o importa y que además es cómo se expresa una
**ruta** (la lista en orden de visita), no lleva caveat porque es exacta.

**Cada negativa es una fila con su motivo.** Un plan que emitió 4 de 11 puede estar funcionando bien
—siete activos ya tienen cuadrilla en camino— o mal —una guarda que nadie quiso poner— y la única
forma de distinguirlo es un registro por activo. De ahí `plan_issue` con `outcome` y `reason`, y no
líneas de log.

**Y una consecuencia del diseño que vale escribir, porque la encontraron los tests:** un plan cuyas OT
nadie ejecuta **deja de emitir**. La guarda de «trabajo pendiente» —la misma de RF-013, ahora
compartida en `workorders/service.py` para que no haya dos definiciones— salta el activo cuyo periodo
anterior sigue abierto. El resultado es que no se apilan doce OT sobre el mismo poste, y que cada
periodo saltado queda registrado como «atrasado» en vez de como «al día»: la pantalla lo nombra así,
porque el conteo de un plan atrasado —cero— se ve igual que el de un plan sin nada que hacer.

En la web, la emisión y el cumplimiento se muestran juntos y nunca uno en vez del otro: «emitió 11 de
11» y «se ejecutaron 2 de 11» son ambos ciertos a la vez, y solo el segundo contesta «¿cumplimos el
plan?». Generar es un botón, nunca un efecto de abrir la página — un GET que emitiera OT las emitiría
otra vez en cada refresco.

Dieciocho guardas rotas a propósito y detectadas. El job corre a las 04:30 de Guayaquil, y hay una
CLI (`python -m app.plans.cli --dry-run`) para la primera carga y para ver qué emitiría un plan antes
de dejarlo suelto.

---

### RF-013: la OT que se propone sola, y la aritmética que se puede discutir

El criterio es «la propuesta aparece en la bandeja del supervisor; al aprobarla pasa a Planificada; al
rechazarla guarda el motivo», con la matriz de criticidad del anexo C detrás. Los hallazgos ya
existían —RF-133 los lee del JSONB de las capturas— y nadie hacía nada con ellos: un técnico marcaba
«generar OT» en la tabla de hallazgos y esa casilla no llegaba a ninguna parte.

**Una propuesta no es una OT, y son tablas distintas.** Crearla en `borrador` y anularla al rechazarla
dejaría a los tableros de RF-130, a la bitácora y a los indicadores contando trabajo que nunca existió,
y esos números son los que una unidad reporta hacia arriba. Además una propuesta lleva cosas que una OT
no lleva y no debería llevar: los hallazgos que la originaron, el modelo que los vio, y la aritmética
del anexo C con lo que esa aritmética no pudo saber.

**Toda la matriz es dato, y nada de ella está en el código.** La severidad es un atributo del catálogo
de defectos; la consecuencia, de un catálogo nuevo por tipo de activo; el plazo sugerido, del catálogo
de prioridad. Un área ajusta la severidad de «cruceta podrida» sin un despliegue, que es la única forma
de que la matriz sobreviva a la primera reunión con mantenimiento.

**La consecuencia es una aproximación declarada, no un cálculo.** El anexo la define por impacto en el
servicio: troncal de media tensión con cargas críticas es 5, ramal es 4. La plataforma **no puede
distinguirlos** —cuántos clientes cuelgan de un alimentador y qué es troncal vive en el SIG y en los
sistemas comerciales— así que el catálogo dice 4 para un tramo y lleva el caveat escrito, y el caveat
viaja con cada propuesta que lo usó. Sin eso, un 4 se lee como una medición. Lo mismo con las omisiones:
un defecto sin severidad produce una propuesta que **dice** que usó 3 por omisión, junto al número. Una
prioridad presentada como cálculo cuando la mitad de sus entradas fueron omisiones es como un supervisor
aprende a ignorar la bandeja entera, y para eso hay una bandera —`estimated`— por la que la pantalla
puede ordenar: «estas sí las sabía».

**Un ajuste por exposición que alguien tiene que marcar.** «Zona urbana o escolar, vía principal: +1
nivel» es una columna de la zona (RF-152), en falso por omisión: subir un nivel a todas las propuestas
porque nadie marcó la casilla sería peor que no aplicar el ajuste. El +1 va a la consecuencia y no al
puntaje, porque el anexo dice «nivel» — sumarlo al puntaje movería un P3 a P1 de un solo defecto.

**Y la criticidad se guarda, no se recalcula al leer.** Los catálogos se mueven; un supervisor que mira
una decisión de marzo tiene que ver los números de marzo.

Lo que la generación **se niega a hacer** es la mitad del valor, y vuelve contada en el informe:

* un activo con trabajo pendiente en campo no se vuelve a proponer (RF-014, aquí como negativa y no
  como alerta: una bandeja con propuestas de trabajo ya programado es una que se aprende a hojear);
* un par activo+defecto con propuesta abierta tampoco, y la unicidad está en un índice parcial de la
  base y no en una comprobación de la función, que es algo que un segundo trabajador puede correr en
  paralelo. Parcial sobre el estado abierto a propósito: un defecto que alguien descartó puede volver;
* un hallazgo sin código de activo no se puede proponer, y se cuenta aparte en vez de desaparecer.

**El defecto que encontraron los tests de integración vale escribirlo, porque nació de una resta.** La
lista de estados «con trabajo abierto» se derivaba restando los estados atendidos, y eso dejaba dentro
`sincronizada` y `en_revision` — que son justo los estados de la OT cuya captura produjo el hallazgo.
Resultado: **ninguna propuesta podía levantarse nunca**, y el generador devolvía «omitida por OT
abierta» sobre el activo de cada hallazgo. La lista está ahora escrita a mano, con `devuelta` dentro
(manda a la cuadrilla otra vez al campo) y `en_revision` fuera (su trabajo de campo está hecho; lo que
falta es un supervisor, y que un supervisor esté ocupado no es razón para dejar de proponer trabajo). Y
la comprobación excluye además la OT del propio hallazgo: es la única OT que con certeza existe sobre
ese activo, y contarla callaría al generador incluso con la lista bien.

**Las tres decisiones son de una persona.** `approve` es el único camino de esta tabla a `work_order`,
toma al decisor de un token y ninguna tarea programada lo llama. La prioridad calculada es un parámetro
que el supervisor puede cambiar —saben si ese tramo es troncal, que es exactamente lo que la plataforma
no sabe— y la bitácora guarda que la cambió. `merge` existe porque la bandeja va a proponer lo que
alguien ya programó a mano, y deja los hallazgos en la descripción de la OT de destino: una fusión sin
rastro haría que la cuadrilla llegue sin saber por qué. `reject` exige un motivo **de catálogo**.

**Y el motivo de rechazo es de catálogo por una razón que no es el orden.** RF-114 dice que «se usa como
señal negativa en el entrenamiento», y no todos los motivos enseñan lo mismo: «no es un defecto» dice
que la detección se equivocó, «ya está resuelto» dice que acertó y el mundo cambió. Usar el segundo como
ejemplo negativo enseñaría a un modelo a no ver un defecto que estaba ahí. Así que `attributes.signal`
dice qué enseña cada motivo, la señal se resuelve el día de la decisión —el catálogo se mueve— y hay un
endpoint que los agrupa por señal para quien arme el conjunto.

Un defecto más, encontrado de paso: el lector de hallazgos de RF-133 seguía al activo de la fila o al de
la OT, y **no al que la captura identifica**. Una OT creada sin activo cuya cuadrilla leyó el código de
la placa en sitio dejaba un hallazgo perfectamente seguible contado como imposible de seguir. La lista
simple de defectos sí lo usaba; la tabla de hallazgos no, y esa diferencia entre los dos lectores era el
defecto. Ahora los dos miran lo mismo, en el mismo orden: la fila, la captura, la OT.

**La bandeja web (RF-114)** tiene una sola insistencia: una prioridad estimada no puede parecerse a una
calculada. La banda del anexo, la aritmética completa, la palabra «Estimada» y los caveats en las
palabras del servidor —nunca parafraseados, porque son las palabras que acordó el área— están todos por
eso. Las tres decisiones dicen qué van a hacer antes de hacerlo, y cambiar la prioridad calculada se
anuncia como lo que es: «en lugar de la que calculó el anexo C», y queda en la bitácora. El motivo de
rechazo es un selector del catálogo, con la señal que enseña debajo; cuando el catálogo no está cargado
la pantalla **no ofrece rechazar** y dice por qué, en vez de caer en un campo libre que produciría
etiquetas con las que nadie puede entrenar.

Dieciséis guardas rotas a propósito y detectadas. Falta la mitad de visión: una detección como origen de
propuesta, con su modelo y confianza, que la tabla y la pantalla ya admiten y que llega con I11.

---

### RF-182: los guardrails que faltaban, y por qué el cero no probaba nada

Los conjuntos dorados de RNF-060 **medían** las fugas de datos personales desde el día que se
escribieron, y la medida daba cero. Eso no es lo mismo que impedirlas: los nodos deterministas citan
poco texto libre, así que el cero venía de lo que los nodos hacen, no de que algo los detuviera. El
día que un nodo LLM redacte un resumen desde el dictado de un técnico —I12— el primer teléfono de
cliente entrará en un informe, y el conjunto dorado lo reportará *después*, sobre un corpus, no sobre
el informe que un supervisor tiene delante.

Así que esto es la mitad de tiempo de ejecución, y la forma la dicta lo que cada defecto merece:

* **El dato personal se redacta, no se descarta.** Una observación que dice «el cliente reportó al
  0991234567 que la luminaria falla» es una observación **útil**; el número es incidental. Borrar la
  observación costaría el hallazgo, y rechazar el informe costaría todos.
* **Una frase no neutral se descarta, no se reescribe.** RF-174 pide un informe que marque para
  verificación y no acuse. Una regla determinista no puede reescribir una acusación en neutral —una
  acusación reformulada sigue siendo una acusación— así que lo honesto es negar la observación y
  contarla, igual que hace la guarda de evidencia.
* **Nada es silencioso.** Cada redacción y cada negativa vuelven en la traza del run, incluso cuando
  no hubo ninguna: «el guardrail corrió y no encontró nada» y «el guardrail no corrió» son
  respuestas distintas a la pregunta de un auditor, y solo una tranquiliza.

**El dígito verificador de la cédula es el detalle que decide si la guarda sobrevive.** Redactar toda
corrida de diez dígitos se comería códigos de activo, números de medidor y referencias de cuenta, y
una guarda que estropea datos reales la quita quien tenga que explicar el informe estropeado — y
entonces ya no protege nada. Así que está el algoritmo real: provincia 01–24 o 30, tercer dígito menor
que 6, y el módulo 10 sobre los nueve primeros. Hay una clase de tests entera dedicada a los falsos
positivos: «transformador T-4521 de 50 kVA», «medidor 8891234», «alimentador 04BH07T11»,
«coordenadas -2.170000, -79.900000».

**Y una ambigüedad del dominio que vale escribir:** en Ecuador una cédula del Guayas empieza «09» y
todos los celulares también. La comprobación de cédula resuelve casi todo —el tercer dígito de un
celular es un prefijo de operadora de 6 o más, que la regla de persona natural rechaza— pero un
celular «093» puede pasar el dígito verificador por coincidencia y reportarse como cédula. Las dos
cosas son datos personales y las dos se quitan igual, así que la ambigüedad cuesta una etiqueta y
nunca la protección.

El **re-ask** existe y está acotado por dos cosas: para en cuanto una salida valida, y para cuando la
salida se repite — el grafo determinista es función pura de sus hechos, así que volver a pedirle gasta
el presupuesto para recibir las mismas negativas. El número de intento llega al productor, porque «sin
datos personales» funciona mejor como corrección que como instrucción permanente, y eso es lo que los
nodos LLM de I12 van a necesitar.

Catorce guardas rotas a propósito y detectadas. Una de ellas —la regla del tercer dígito— no se
detectaba: el número de prueba fallaba también el dígito verificador, así que el test pasaba por la
razón equivocada y la regla podía desaparecer sin que nadie lo notara. Ahora el número tiene dígito
verificador válido y solo el tercer dígito lo descalifica.

---

### RF-147: el diccionario vivo, y el camino que no estaba conectado

El criterio es «un término añadido llega al móvil en el siguiente sync de catálogos», y con RF-034 los
sinónimos ya existían como dato: «cruceta podrida» está al lado de `cruceta_podrida`. **El constructor
del léxico no los leía.** Construía del vocabulario canónico (`profiles/amd/voice-es-EC.yaml`) y de los
metadatos sincronizados del SIG, y de nada más. Un campo de defecto no tenía **ningún hotword**, así
que un técnico que dictaba «cruceta podrida» no tenía nada hacia lo que empujar al decodificador.

**Dos fuentes, y la división es deliberada.** El archivo del perfil es la **línea base canónica**: dice
cómo un liniero ecuatoriano dice un valor *canónico*, y vive con el descriptor del modelo porque eso es
parte de lo que significa «canónico»; no es administrable en caliente y no debe serlo, porque cambiarlo
cambia el significado de todos los perfiles. Los catálogos son **la mitad viva**: los sinónimos de un
valor viven con el valor, así que añadir un regionalismo es el mismo acto que añadir el valor, se
versiona con él y viaja en el mismo delta al teléfono. Eso es lo que vuelve el criterio *cierto* en vez
de *aspiracional*, y hay tests del camino completo: del catálogo al hotword, del hotword al hash del
léxico, y del hash del catálogo al hash del paquete.

Y un catálogo más, `vocabulary`, para las palabras que no son valor de nada: pistas de campo («dígame
la altura») y términos sueltos que el decodificador debe favorecer aunque no llenen nada — si el
técnico dice «el bushing», que no salga «el bus in».

**La distinción que costó encontrar: dos necesidades distintas, no una.** `value_aliases` es el
contrato del extractor y cubre lo que un solo dictado puede llenar; una tabla repetible se llena
entrada por entrada, así que un defecto no pertenece ahí — y `extractable_fields` lo excluye con razón.
Pero el **decodificador** tiene otra necesidad, más simple: haber oído las palabras. Tratar las dos
como una sola es lo que dejaba el bloque de hallazgos entero sin dictar mientras parecía un problema
del reconocedor. Ahora los valores anidados entran como hotwords y no como alias, y el comentario del
código dice por qué.

**Y el catálogo vacío se avisa.** Un formulario que referencia un catálogo sin valores produce un
aviso en el léxico que nombra el catálogo, porque el síntoma sin él es «el dictado no reconoce nada»,
que se lee como un decodificador roto y no como una lista vacía. La división política —vacía a
propósito hasta que llegue la lista del INEC— aparece ahí, que es exactamente donde tiene que aparecer.

La pantalla de administración no hizo falta inventarla: el vocabulario **es** un catálogo, así que
hereda el versionado, el delta y la pantalla de RF-034. Lo que sí se añadió es la escritura: código,
etiqueta, sinónimos, y —solo para `vocabulary`— el campo que anuncian. El aviso previo dice dónde va a
caer el valor, cuántas formas nuevas aprenderá el reconocedor y que llega en el siguiente sync, porque
un administrador que no lo sabe añade una palabra y se queda mirando un teléfono que no cambió.

Nueve guardas rotas a propósito y detectadas.

---

### RF-034: los catálogos que los formularios ya referenciaban

Este tampoco era un hueco de funcionalidad: era una **referencia colgando**. `b11-hallazgos.yaml`
decía `x-catalog-ref: defect` y `b06-actividades.yaml` decía `x-catalog-ref: activity`, y **nada
servía ninguna de las dos listas**. Un teléfono que renderizaba el bloque de hallazgos tenía un campo
de código y ningún valor de dónde elegir. La referencia existía; el catálogo no.

**La guarda que cierra el círculo es el test más valioso del incremento.** Recorre los YAML de
`forms/blocks/`, junta todos los `x-catalog-ref` y exige que cada uno lo pueda servir algo: un
catálogo de la plataforma, los metadatos sincronizados del SIG (`feeder`, `substation`, que difieren
por unidad, RF-304) o los enums del perfil (`voltage_level`). Se lee del YAML y no de una lista en el
test, porque una lista habría que mantenerla en paso y de eso se trata justamente. Y está probada en
negativo: se le añade una referencia inventada y la nombra.

**La revisión la pone un disparador de la base, no el servicio.** Es lo que hace posible la descarga
incremental: el dispositivo pide todo lo que esté por encima de la revisión que tiene. Una marca de
tiempo no serviría —tercera vez en el día que aparece la misma trampa— y el disparador, en vez de una
función del servicio, porque una entrada escrita por el conector del ERP también necesita revisión, y
una regla que vive en una sola función es una regla que el siguiente escritor olvida. Se comprobó
contra la base migrada con un `UPDATE` en SQL crudo: 115 revisiones distintas para 115 filas.

**Desactivar es la forma de borrar.** Un valor retirado viaja al dispositivo como lápida, o el
teléfono sigue ofreciendo un código que la distribuidora retiró hace dos años, y nadie lo nota porque
el valor se ve perfectamente normal.

**Y el lote recortado lo dice.** Un tope silencioso deja un teléfono al que le falta la cola de un
catálogo para siempre, convencido de estar al día.

**Vacío con motivo no es lo mismo que vacío.** La división política del Ecuador queda vacía **a
propósito**: son ~221 cantones y ~1 500 parroquias y la lista oficial es del INEC. Inventarla
parcialmente sería peor que no tenerla —un cantón mal escrito en miles de OT no se arregla después, y
la exportación al regulador se lo lleva—. Así que el cargador **exige** que un catálogo vacío declare
su `note`, y la pantalla distingue «vacío, a la espera» de «vacío sin motivo declarado»: el primero es
una decisión, el segundo es una falla.

**Lo que la integración mantiene no se edita a mano.** Los materiales son del ERP (RF-121), y un valor
tecleado sobre uno que el conector va a sobreescribir esta noche desaparece sin explicación. La
plataforma lo rechaza con 409 y la pantalla no ofrece el botón.

**Un valor de la unidad sobrescribe al nacional del mismo código**, no lo duplica: dos filas con un
código en un selector es un error que el técnico ve. La resolución se hizo en **dos pasadas
explícitas** después de que la comprobación en negativo mostrara que una sola pasada acertaba por el
orden en que la consulta devolvía las filas — es decir, por suerte.

**Y una colisión de rutas que encontró un test:** `/units/GYE/delta` casaba con
`/units/{unit_code}/{catalog_code}`, así que el delta del dispositivo resolvía al catálogo inexistente
«delta». La forma de que no vuelva a pasar no es ordenar las rutas —deja la ambigüedad esperando a
que alguien cree un catálogo con ese nombre— sino un segmento literal `catalog/` que impide que un
código de catálogo ocupe la posición de un verbo. Hay un test que crea un catálogo llamado «delta».

Once guardas rotas a propósito y detectadas. Las 115 entradas de línea base —defectos, actividades,
unidades, motivos, causas de interrupción, protecciones, criticidad, prioridad y las 24 provincias—
son, como los formularios, una línea base del sector que cada área tiene que validar antes del
piloto.

---

### RF-032: la publicación es lo que congela la forma

Esto no era una funcionalidad faltante: era una **incorrección**. Los formularios viven como
archivos bajo `forms/` y el catálogo los indexaba solo por código, así que editar `F-AP-01.yaml`
cambiaba la forma de **todas** las OT, incluida la que un técnico ya llevaba en el teléfono. Un campo
renombrado un martes habría hecho que las respuestas del lunes no validaran contra un formulario que
nadie en campo vio nunca. El criterio de RF-032 —«publicar la v2 no altera las OT asignadas con la
v1»— no se cumplía.

**Los archivos son el borrador.** Editar uno no cambia nada para nadie hasta que se publica.
Publicar congela en la base la definición **y los bloques que usa**: congelar solo la definición
dejaría la forma a merced de una edición de bloque, que es el mismo error un nivel más abajo.

**Una OT se compone contra su propia versión**, y la versión se fija **al asignarse** —que es lo que
dice el punto 6 de la sección 4.1 del SRS, no al crearse—. Tomarla de lo publicado y no del archivo
es el centro del asunto: fijar el número de un borrador fijaría un número que no nombra ninguna forma
congelada, así que publicar después seguiría cambiando la OT. Hay un test de exactamente eso: se
publica v1, se edita el archivo a v2 **sin publicar**, se asigna, y la OT queda en v1 con el bloque
que el borrador quitó todavía presente.

**Una versión obsoleta sigue componiendo.** Las OT que la llevan existen y hay que cerrarlas;
obsoletar solo impide que una OT nueva la use.

**Y lo que no se congela son los catálogos de la unidad**, deliberadamente: una OT ejecutada hoy tiene
que nombrar un alimentador que exista hoy (RF-304). Congelarlos le daría al técnico una lista de
subestaciones del año pasado. La forma se congela; los valores no.

Cuando nada está publicado, el archivo hace de suplente y el formulario compuesto **lo dice** en sus
avisos: un revisor que mira respuestas tiene derecho a saber si el formulario que tiene delante es el
que el técnico llenó.

**El mismo defecto, dos veces el mismo día.** El historial de versiones ordenaba por
`published_at`, y el `now()` de PostgreSQL es el reloj de la *transacción*: dos publicaciones de una
misma petición comparten la marca al microsegundo y «la más nueva primero» queda al azar del
recorrido. Es exactamente el defecto que RF-150 había encontrado unas horas antes en la bitácora de
parámetros. La conclusión ya no es «arreglar este caso» sino una regla: **ordenar un registro
append-only por una marca de tiempo es un error con mecha larga**; lleva una secuencia de la base.

**Y un agujero en el arnés de pruebas.** Los tests de RF-032 editan una definición en memoria para
simular una versión nueva, y once tests del mismo archivo empezaron a fallar por cosas que no tenían
que ver con lo que afirmaban: `load_definitions` y `load_blocks` son `lru_cache` y el conftest raíz
solo limpiaba las cachés de perfil y de AMD. Ahora limpia las cuatro. El agujero llevaba ahí desde
I2 y lo encontró el primer test que mutó un formulario.

Nueve guardas rotas a propósito y detectadas — dos de ellas solo después de corregir los tests: las
dos que importaban más (que la versión se fije desde lo publicado, y que el manifiesto anuncie lo
publicado) pasaban con la sabotaje puesta porque en mis casos la versión del archivo y la publicada
coincidían siempre. Los tests que las fijan ahora son los del borrador sin publicar.

---

### RF-021: la sugerencia de cuadrilla, y por qué el puntaje se puede discutir

«La sugerencia devuelve el top 3 de cuadrillas con puntaje explicable» es el criterio, y
*explicable* es todo el diseño. Un planificador que no puede ver por qué una cuadrilla quedó
primera hará una de dos cosas: seguir el número a ciegas o ignorarlo. Las dos son peores que no
tener sugerencia.

**Lo duro excluye; lo blando puntúa.** Una cuadrilla sin la competencia que el formulario exige no
aparece, por cerca que esté. Meter la seguridad en una suma ponderada dejaría que la cercanía le
gane a «no está habilitada para trabajar en tensión», y el día que eso pase hay alguien lastimado.

**Y lo excluido se devuelve con su razón.** Omitir C-03 en silencio deja al planificador preguntándose
si la plataforma la olvidó o la descartó, y lo primero lo invita a asignarla a mano.

**Las competencias son dato, no código.** Se declaran en `forms/definitions/` —el formulario *es* el
dato por tipo de trabajo (regla 3)— y una lista vacía significa «sin requisito duro», que es una
decisión y no un olvido: inventar un requisito de seguridad haría que la sugerencia rechace cuadrillas
sin motivo y el planificador aprendería a ignorarla. Las áreas tienen que validar esa lista contra su
práctica, igual que los formularios.

**«No se sabe» se dice, no se puntúa como cero.** La plataforma no guarda el GPS de las cuadrillas
—el «último GPS reportado» de RF-020 todavía no se captura—, así que la cercanía se estima desde el
centroide del trabajo abierto de la cuadrilla: un proxy defendible (una cuadrilla con seis OT en el
norte está en el norte) pero un proxy. Cuando no hay trabajo abierto desde donde estimar, la razón lo
dice con esas palabras en vez de no sumar nada y parecer mal encaje.

Los cuatro factores suman 100 en números enteros —zona 40, cercanía 30, carga 20, presión de SLA 10—
para que comparar 72 con 68 no necesite calculadora. Y la pantalla dice cuándo esa diferencia **no**
es una recomendación: dos puntos son ruido de redondeo, y presentarlos como consejo sería prestarle
al número una autoridad que no tiene.

La carga **no** es un tope duro: un planificador puede querer darle la novena OT a la cuadrilla que ya
está en esa calle, y el puntaje debe mostrarle el costo, no prohibírselo.

**Un hallazgo del camino: `create_work_order` no aceptaba `sla_due_at`.** La columna existía desde
I3, RF-010 la pide, el tablero de SLA de RF-130 la lee y la presión de SLA de aquí la necesita — y
nada la escribía nunca. Estaba llena de nulos.

Siete guardas rotas a propósito y detectadas. La octava —el desempate por código— **no** se detecta, y
queda anotado en el código por qué: el orden ya lo garantizan el `ORDER BY code` de la consulta y la
estabilidad del `sort` de Python, así que la clave explícita es redundante a propósito, para que la
propiedad sobreviva a que alguien cambie la consulta. Un test no puede distinguir los dos mecanismos;
el comentario es el registro de que la redundancia es deliberada.

---

### RF-150: el autor de un parámetro, y desde qué valor lo cambió

La mayor parte de RF-150 ya estaba: la vigencia desde/hasta, la referencia a la norma y el criterio
que importa —«los cálculos usan el parámetro vigente en la fecha del evento»— viven en
`regulatory_parameter` desde ADR-007 y tienen sus tests. Lo que faltaba era **el usuario que
modificó**, y la mitad W del canal.

**El autor no es el verificador**, y tenerlos en un solo campo habría hecho que una corrección
pareciera una certificación. `created_by` y `updated_by` dicen quién cargó y quién editó; `verified_by`
es una afirmación más fuerte: que alguien leyó el texto oficial. Una persona puede arreglar un numeral
mal citado sin certificar la cifra.

**Y «quién lo cambió» solo sirve al lado de «desde qué valor».** Los períodos son la historia de los
valores que publicó el regulador; la única mutación que el modelo permite es corregir un período
existente, y eso sobrescribía una cifra sin dejar rastro. De ahí `regulatory_revision`: creación,
corrección, cierre y verificación, con el diff de lo que se movió. Solo lo que se movió —un registro
que lista diez campos iguales esconde el que cambió— y con el valor **desenvuelto**, porque quien lee
una revisión busca la cifra y no `{"v": 24}`.

**La corrección que vale anotar: ordenar por la marca de tiempo no ordena nada.** El `now()` de
PostgreSQL es el reloj de la *transacción*, así que todas las revisiones de una misma petición
comparten la marca al microsegundo y el orden que devuelve la consulta es el que el índice quiera.
Peor: una marca puede ser anterior a la de la fila previa —un ajuste de reloj, una inserción con
fecha atrasada—. Así que hay una columna `sequence` de la base y el log se ordena por ella. Lo
descubrió la comprobación en negativo: sustituir el orden por `at` **no rompía ningún test**, porque
el recorrido físico devolvía las filas en orden de inserción por casualidad. El test que ahora lo fija
inserta una revisión con `at` de 2001 y exige que se lea al final.

**La verificación sale del token, no del cuerpo de la petición.** El endpoint de escritura aceptaba un
`verified_by` que el navegador podía escribir, que es una verificación que nadie hizo. Ahora la
verificación es su propio endpoint —cargar una cifra y certificarla son dos actos, y juntarlos es cómo
una importación masiva marca siete valores verificados por una bandera— y firma con el sujeto del
token. El cargador de semilla sigue recibiendo un nombre, porque corre en una consola sin token.

**Y existe el comando que el propio archivo de semilla mandaba usar.** `seeds/regulatory-ec.yaml`
decía «cargarlo con `--verified-by`» y ese comando no existía; ahora es
`uv run python -m app.regulatory.cli`, con `--dry-run`, y el archivo cita la línea exacta. El comando
imprime al final las dos listas que una lista de verificación de despliegue tiene que tener vacías, y
avisa cuando alguien pasó `--verified-by` sobre un archivo que no marca nada como verificado: esa
persona cree estar certificando algo.

En la pantalla esas dos listas van **separadas**. No son el mismo problema: un código que ninguna
regla encuentra hace que la regla informe que no puede juzgar —lo que en un tablero se parece a
cumplir—, y un código cargado sin verificar la hace juzgar contra un número que alguien escribió. Una
es silencio y la otra es una respuesta verosímil, y se arreglan de distinta manera.

Cinco guardas rotas a propósito y las cinco detectadas.

---

### RF-151: la política de captura, y por dónde llega al teléfono

El criterio de aceptación no habla de la escritura, habla de la entrega: «cambiar la política se
refleja en el móvil en el siguiente sync». Así que la política **viaja dentro del manifiesto del
paquete de la zona**, cuyo hash de contenido es justamente lo que un dispositivo usa para saber que
tiene algo viejo. Cambiar la política cambia el hash, el teléfono descarga y obedece. No hay un canal
aparte que mantener en paso, que es el que se desincroniza.

**Todas las columnas son anulables y un nulo significa «sin opinión».** Una zona que solo difiere de
su unidad en que no sube por datos móviles declara eso y nada más. La alternativa —sobrescribir la
fila entera— obligaría a la zona a repetir los otros nueve valores, y el día que la unidad cambie uno
la zona se quedaría callada con el viejo. Hay un test exactamente de eso: se cambia la unidad y se
comprueba que la zona lo recibe para todo lo que no declaró.

De ahí sale la regla del guardado: **una clave ausente deja el campo quieto y un nulo explícito lo
borra.** Una pantalla que enviara los diez campos en cada guardado convertiría «esto no lo toqué» en
«pon esto en nulo», y como el nulo significa heredar, la zona dejaría de sobrescribir cosas que nadie
quiso cambiar. El navegador manda solo lo que cambió, y el servidor distingue las dos cosas por
`model_fields_set` y no por un diccionario de valores por omisión.

**Los valores por omisión son la lectura conservadora, no la cómoda.** El audio **no** se guarda —el
propio RF-058 hace de guardarlo la excepción—, el consentimiento se pide y no se sube nada por datos
móviles. Un valor por omisión que subiera un día de fotografías por el plan de datos del técnico
sería un valor por omisión que nadie eligió.

**Y `store_audio` se aplica en el servidor, no solo en el teléfono.** Esto salió de leer el criterio
de RF-058 («respeta el parámetro `store_audio` por área») contra el código: `register_evidence`
aceptaba audio de cualquiera. Una versión vieja de la app, una base local corrupta o un envío
repetido no pueden hacer que la plataforma conserve la voz de una persona contra la decisión del
área. Se rechaza en vez de aceptar y descartar en silencio: una fila de evidencia apuntando a un
archivo que nadie va a guardar se lee como audio conservado en una auditoría y como audio perdido
para quien vaya a buscarlo.

**Una política y un límite regulatorio no son lo mismo**, y la frontera está escrita en el módulo: un
plazo de retención es una decisión operativa del área; un plazo máximo de reposición es una cifra que
publicó un regulador y vive en `regulatory_parameter` con su vigencia y su cita (ADR-007). Si alguna
norma llega a poner un **techo** a una retención, ese techo va allá y una regla determinista rechaza
la política que lo pase — la fila de política no puede convertirse en el lugar donde se guarda
calladamente un límite legal.

En la pantalla, lo primero que se ve no es lo que alguien escribió: es **lo que el teléfono va a
obedecer**, con el origen de cada valor. Sin eso, quien cambia la política de la unidad y no ve
cambio en el norte concluye que el sync está roto, cuando lo que pasa es que la zona lo sobrescribe.
Y un valor heredado se muestra distinto de uno decidido, porque leerse igual es cómo se confunden.

Seis guardas rotas a propósito —la precedencia zona sobre unidad, el `is not None` que distingue
`False` de una ausencia, la validación de enteros, la aplicación de `store_audio`, la política en el
manifiesto y el envío de solo lo cambiado— y las seis detectadas.

---

### RF-152: las zonas dejan de ser una cadena de texto

Hasta aquí una zona era un `String(64)`: `work_order.zone` y `crew.zone` guardan texto, y con texto
se puede filtrar una lista y nada más. Las tres cosas para las que una zona sirve de verdad —decidir
qué cuadrilla cubre un punto, nombrar el paquete que un dispositivo descarga, acotar a un supervisor
al norte de la ciudad— necesitan geometría.

**El código sigue siendo la identidad.** El polígono se le cuelga; no lo reemplaza. Así una unidad
que todavía no dibujó sus zonas funciona exactamente igual que ayer, y no hay nada que migrar el día
que los polígonos llegan. El tipo es MULTIPOLYGON y no POLYGON porque las zonas de operación reales
no siempre son conexas —una isla, una parroquia separada, un área partida por un río que es de
otro—, y exigir POLYGON obligaría a partir en dos lo que la operación trata como una.

**Lo que este módulo no hace es su decisión principal: no repara geometrías.** PostGIS arregla un
anillo que se autointersecta con `ST_MakeValid`, y el resultado es **otro límite** que el del
archivo. Redibujar en silencio la zona de operación de alguien y reportar éxito es exactamente cómo
una zona termina cubriendo una calle que no cubre. Así que el rasgo se rechaza con el motivo que dio
PostGIS, y el arreglo va en el archivo de origen.

**Los rechazos son por rasgo, no por archivo.** Un GeoJSON de cuarenta parroquias con un anillo roto
importa treinta y nueve y nombra el que falló. Eso obligó a una corrección que vale anotar: la sonda
de validez corre dentro de un SAVEPOINT. Una geometría que PostGIS no puede ni leer aborta la
transacción entera, y un `session.rollback()` allí se habría llevado las zonas ya escritas **mientras
el informe seguía diciendo que se crearon**. La primera versión hacía eso. El test que lo fija no
mira el informe: mira las filas.

**El número que dice si las zonas sirven no es la lista de zonas.** Doce zonas bien nombradas se ven
terminadas; lo que hay que leer es cuántas OT abiertas no caen en ninguna. Así que la cobertura
separa cuatro cosas —en una zona, en varias, en ninguna, y sin punto— porque son cuatro problemas
distintos: la ambigua no tiene respuesta, la descubierta es una cuadrilla sin mapa, y la que no tiene
coordenadas no es un problema de las zonas. Si se contara con las demás, una unidad que todavía no
captura puntos leería como zonas rotas.

**Vecindad no es solapamiento.** Dos zonas que comparten un borde son el caso normal, y reportar cada
vecina enterraría el único par que está mal. Se excluye el contacto (`ST_Touches`) y no la
contención: una zona entera dentro de otra sí es un problema, y `ST_Overlaps` a solas la habría
pasado por alto.

**Y la zona que una OT ya trae no se pisa nunca.** Pudo venir del sistema corporativo, de una
integración o de un planificador que sabe algo que el polígono no. El relleno llena lo vacío; lo
ambiguo lo devuelve para que lo vea una persona, porque elegir una de dos zonas en silencio sería una
decisión que nadie podría revisar.

Cinco guardas se rompieron a propósito para comprobar que la suite las nota: el `ST_Touches`, el
SAVEPOINT, el filtro de zona vacía del relleno, el denominador de la cobertura y la propia
validación de anillos. Las cinco se detectaron.

---

### RF-133: el tablero de mantenimiento, y lo que «abierto» quiere decir

Este tablero responde tres preguntas de planificación —qué alimentadores concentran defectos, qué
activos reinciden y qué hallazgos siguen sin atender— y las tres se apoyan en una definición, no en un
hecho. «Hallazgo abierto» no es un campo: es el resultado de comparar cuándo se registró el defecto
con cuándo se atendió por última vez el activo. Dos planificadores pueden entender cosas distintas por
la misma palabra, así que la definición exacta viaja en el payload (`OPEN_DEFINITION`) y la pantalla
la muestra sin parafrasear. Un tablero que dijera «12 hallazgos abiertos» sin decir contra qué los
contó estaría pidiendo que se le crea.

**La corrección que vale escribir: el backlog lee la bitácora, no `work_order.updated_at`.** La
primera versión tomaba la última atención de ese campo, y es falso en producción: `updated_at` se
mueve con cualquier edición de la fila —una nota, una reasignación—, así que reasignar hoy una OT
vieja habría cerrado un hallazgo de ayer sin que nadie tocara el activo. Ahora la fecha sale de los
eventos `TRANSITION` de M16, que es el único registro de que alguien llegó al activo. La bitácora
inmutable se construyó para auditoría y termina siendo la fuente de la que dependen tres tableros.

**El «calor» por alimentador es una proporción, no un mapa.** La plataforma no guarda la geometría del
alimentador —vive en la geodatabase— así que el tablero reparte los defectos entre los alimentadores
que las capturas nombran y muestra el peso relativo de cada uno. Es lo que se puede afirmar con los
datos propios; pintar un mapa exigiría llamar al GIS por cada carga de pantalla.

**Reincidencia: un defecto repetido y varios defectos distintos no dicen lo mismo.** El mismo código
dos veces en el mismo activo es una reparación que no aguantó; tres códigos distintos es un activo al
final de su vida. El consejo que la pantalla da distingue los dos casos porque la acción del
planificador es distinta: revisar la cuadrilla y el material en el primero, programar el reemplazo en
el segundo.

Los hallazgos se leen de **dos** bloques de formulario: la tabla `findings` de B11 y la lista simple
`defects` de B05. Un tablero que solo mirara el bloque nuevo habría reportado cero para todas las
inspecciones ya levantadas.

**Y una falla del método, no del código.** La comprobación en negativo del orden temporal no detectaba
nada, y la razón era que `ruff format` había colapsado el `if` objetivo en una sola línea: el parche de
sabotaje no coincidía y por tanto no se aplicaba, y yo leía «la guarda no detecta» donde decía «no
cambié nada». Desde aquí todo parche de sabotaje afirma primero que encontró su patrón.

---

### RF-132: la base de interrupciones, y el índice que la plataforma no publica

Lo que este módulo **no** hace es su decisión principal: no calcula FMIK ni TTIK. Los dos índices
dividen por el kVA instalado de la unidad, que vive en los sistemas corporativos y no aquí. Una
plataforma que publicara un índice contra un denominador supuesto estaría publicando un número que la
distribuidora tiene que defender después ante el regulador.

Así que se exporta la base y se calculan **los dos numeradores** —kVA fuera de servicio y kVA·hora—
que salen solo de las interrupciones y por tanto sí son de la plataforma. La explicación de qué falta
viaja en el payload y la pantalla la muestra sin parafrasear, porque el fallo que este panel podría
causar es que alguien copie un numerador a un informe como si fuera el índice. Y un test comprueba que
no existe ningún **campo** llamado `fmik` ni `ttik`: que la nota los nombre para explicar por qué no
están es justo lo contrario.

**Hizo falta el formulario antes.** F-OP-03 estaba especificado en el SRS y no existía, así que se
construyó con los campos que ARCERNNR-002/20 exige: tipo, origen, inicio y reposición total,
reposiciones parciales como tabla, protección que operó, transformadores y kVA afectados, y causa. El
umbral de «no computable» **no está en el formulario**: lo evalúa la regla determinista sobre
`regulatory_parameter`, y el campo solo declara contra qué parámetro se mide. Una guarda de CI lo
comprobó enseguida — la primera versión citaba un código de parámetro que ninguna regla conoce.

**El formato es un archivo.** «Formato configurable» del requerimiento significa que las columnas, sus
cabeceras, su orden y el separador viven en `seeds/export-formats/`: la regulación los renombra cada
pocos años, y eso debería ser un archivo que se añade. Un formato que no existe da 404 y nunca cae al
de por omisión en silencio — una exportación que usara otro formato produciría un archivo que el
regulador rechaza por razones que nadie puede rastrear.

Las interrupciones que la regla no pudo clasificar se cuentan aparte y **no se suponen** en ninguna
dirección: suponerlas computables inflaría los índices, y suponer lo contrario esconderia
interrupciones que ocurrieron.

---

### RF-131: el tablero de alumbrado, con el plazo como dato

El número que este tablero produce —qué porcentaje de luminarias se repuso dentro del plazo— va a un
informe al regulador. Así que la propiedad que importa no es el promedio: es que el número se pueda
defender.

**El plazo no está en el código.** Vive en `regulatory_parameter` con su vigencia, su referencia a la
norma y su marca de verificación, y el tablero pregunta **la misma regla** que la compuerta de
aprobación. Dos consecuencias que son el módulo entero:

* se cambia el parámetro y el veredicto cambia con él, sin tocar una línea — hay un test que sube el
  plazo de 48 a 72 horas y ve las mismas atenciones pasar de incumplir a cumplir;
* un periodo de marzo se juzga con el plazo de marzo, porque el parámetro lleva sus fechas. Un
  porcentaje guardado sería una segunda copia de la verdad, libre de separarse de la regla que lo
  produjo.

**Y un límite sin verificar se reporta como provisional**, en el panel y en cada fila de la tabla.
Nadie lo ha comprobado contra el texto oficial, y un porcentaje calculado contra un número que
alguien escribió de memoria —presentado como si citara la regulación— es peor que no tener
porcentaje: invita al lector a dejar de comprobar. La pantalla no pone la norma al lado de un límite
así, y hay un test de que no la pone.

Las atenciones que la regla no pudo juzgar se cuentan junto al porcentaje, y cuando son más de la
mitad del periodo el tablero lo dice: un 100 % sobre cinco medibles de doscientas capturadas no es
una tasa de cumplimiento. Sin parámetro cargado no se inventa un plazo — la omisión es de la oficina,
y la plataforma la reporta.

**La tasa de falla dice de qué está dividida:** luminarias con al menos una falla en el periodo, no
el total instalado. El inventario vive en el SIG y dividir por un total que la plataforma no conoce
sería inventar el denominador. Con la reincidencia al lado, que es la señal de que el reemplazo no
arregló el problema.

**Para las tecnologías hubo que arreglar algo antes.** F-AP-01 no llevaba el bloque de atributos del
activo, así que la plataforma podía atender miles de luminarias en falla sin saber de qué tecnología
era ninguna. Se añadió B05 al formulario, que es el bloque que el generador rellena desde el perfil
de la unidad (RF-303, regla 3): la tecnología y la potencia vienen del modelo de datos, no escritas a
mano. Y son obligatorias, así que una captura nueva sin tecnología ya no se puede enviar —mejor que
contarlas: que no ocurran— aunque el panel sigue contando las antiguas, porque una composición de
flota calculada solo sobre las capturas que la registraron informa la forma de los formularios bien
llenados y no la de la flota.

**La exportación es un CSV que abre bien en el Excel que esta área tiene**: punto y coma, decimales
con coma y marca de orden de bytes. No es una preferencia — un Excel configurado para Ecuador lee un
archivo separado por comas como una sola columna y «1.5» como quince, así que «exportable a Excel»
significa esto y no un archivo técnicamente válido que llega ilegible. Se pide con el token y no con
un enlace: un `<a href>` bajaría una página de login llamada «.csv».

Faltan RF-132 (exportación de interrupciones para FMIK y TTIK) y RF-133 (defectos por alimentador,
reincidencia por activo, hallazgos por criticidad).

---

### RF-130: el tablero operativo, que la bitácora hizo posible

Cuatro preguntas que un supervisor hace antes del almuerzo: qué hay dónde, qué está atrasado, quién
está sacando trabajo y cuánto tarda el trabajo. Las tres primeras salen de las OT. La cuarta sale de
la bitácora, y hasta que la bitácora existió no se podía responder.

Los tiempos son donde un tablero operativo engaña con más facilidad, así que las tres decisiones que
lo sostienen son negativas:

| Decisión | Qué evita |
|---|---|
| Medianas y percentil 90, no promedios | dos OT abiertas durante un fin de semana mueven un promedio horas y no dicen nada del día normal. La mediana dice cómo es un día normal; el p90, cuánto duran los que no lo son |
| Una OT en curso no es un cero | un trabajo despachado hace una hora no ha tardado cero en llegar: no ha llegado. Contarlo arrastraría el promedio hacia abajo justo cuando las cuadrillas están ocupadas |
| El reloj arranca en el **primer** despacho | una reasignación no lo reinicia. El tiempo que cuesta reasignar es tiempo que el trabajo tardó, y un tablero que lo esconde es uno con el que no se puede averiguar por qué |

Cada tramo informa tres números distintos que un promedio solo fundiría: lo que midió, lo que sigue
en curso y lo que no pudo medir. Lo último son las OT anteriores a la bitácora, y se cuentan en vez
de ignorarse: un promedio calculado solo sobre las que quedaron bien registradas informa el mejor
caso. Y el máximo viaja al lado del p90, porque en una muestra pequeña el percentil interpolado
esconde justo la cola que interesa —con nueve trabajos de media hora y uno de cinco, el p90 da 57
minutos: aritmética correcta y respuesta inútil a «¿cuál fue la peor?».

Del SLA se informan las vencidas **y abiertas** —un tablero que grita por trabajo terminado es uno
que se deja de mirar— y también **cuántas OT abiertas no tienen fecha cargada**, porque «0 vencidas»
sobre cien de esas no informa de nada.

La productividad de una cuadrilla se mide por lo que cerró **en campo**. Lo que pase después en
revisión es trabajo de la oficina, y contarlo aquí haría que el número de una cuadrilla se moviera
porque alguien más estaba de vacaciones.

El criterio de aceptación —datos de menos de cinco minutos— es un refresco y no una caché: el
tablero se recalcula en cada llamada y la pantalla vuelve a pedirlo cada cinco minutos. Una caché
añadiría un error de invalidación a cambio de una consulta que un supervisor hace doce veces por
hora. Y la pantalla **dice cuándo se calculó**: uno que se refresca en silencio parece igual de
fresco cuando el refresco lleva una hora fallando.

Faltan RF-131 (APG contra el máximo regulatorio), RF-132 (exportación de interrupciones para FMIK y
TTIK) y RF-133 (mapa de calor de defectos, reincidencia por activo, hallazgos por criticidad).

---

### M16: la bitácora que se daba por hecha

Este plan decía «M16 del SRS completo» desde el principio. No lo estaba. La migración de base
declaraba una tabla `audit_event` —con otra forma: `entity_type`, `action`, `actor_sub`— y **ningún
código escribió jamás en ella**. No tenía modelo, no aparecía en la metadata, y por eso las pruebas,
que construyen el esquema desde la metadata, nunca la tuvieron delante. Una tabla declarada alcanzó
para que la casilla quedara marcada.

Se descubrió buscando por dónde seguir: los tiempos promedio de RF-130 (despacho → llegada → cierre)
necesitan saber cuándo cambió de estado cada OT, y resultó que las transiciones no se registraban en
ninguna parte. La máquina de estados movía el campo y se acabó.

**Lo que ahora se registra**, en la misma transacción que el cambio: creación, cambios de campo con
el valor anterior, el nuevo y de dónde salió el nuevo (persona o modelo, con la versión y la
confianza), transiciones de estado con el estado de origen, asignaciones con el antes y el después,
accesos a evidencias, exportaciones y decisiones de revisión. Lo del «mismo transacción» no es
detalle: una bitácora que se escribiera aparte podría registrar trabajo que la base deshizo después,
y eso es peor que no tener bitácora — es una con la que alguien defendería una decisión.

**La inmutabilidad se sostiene tres veces, a tres distancias de quien tendría que vencerla:**

| Dónde | Qué impide | Cómo se prueba |
|---|---|---|
| En la base | un disparador rechaza UPDATE y DELETE | contra PostgreSQL de verdad, y también contra la base migrada |
| En el código | nada escribe en la tabla salvo la función de escritura, y el router de auditoría solo tiene GET | recorriendo el árbol de sintaxis de toda la aplicación; la guarda está probada en negativo |
| En los datos | cada evento lleva el hash del anterior, y su posición es única por unidad | tres manipulaciones distintas, las tres detectadas con el motivo que un auditor puede poner en un informe |

Las tres formas de manipular la cadena dan tres hallazgos distintos, y distinguirlos importa porque
significan cosas distintas: **una fila alterada** es alguien editando historia, **un eslabón roto** es
alguien quitando un evento del medio, y **un hueco en la secuencia** es alguien quitando el último
—que es lo único que los enlaces solos no ven, y la razón de que la posición sea única por unidad.

La cadena es por unidad de negocio y no global. Mitad ADR-009 —la bitácora de una unidad es suya— y
mitad concurrencia: las escrituras se serializan contra la cola de la cadena, y una sola cadena
global pondría a cada unidad del país a esperar detrás de todas las demás.

Y la migración **no borra la tabla vieja a ciegas**: si en algún despliegue llegara a tener filas, se
detiene con un mensaje en vez de destruirlas. Que una tabla esté vacía en el repositorio no prueba
que lo esté en producción.

En la pantalla, la bitácora es del auditor y de administración de TI —un registro de auditoría no es
un informe de gestión—, con las cuatro preguntas de RF-161 como filtros que se combinan y la
verificación de la cadena a un clic. Una cadena rota se ve rota: pintar de verde una verificación que
falló sería el peor defecto posible de esa pantalla.

---

### M19: la pasarela de modelos, y que nadie espere a un modelo

La regla 13 dice que el servidor consume LLM y VLM **solo por alias**, y hasta ahora eso era una
intención: no había pasarela. `infra/inference/aliases.yaml` la vuelve cierta — el modelo detrás de
`llm-judge` se cambia ahí y ningún agente se toca (RF-200). Un nombre de modelo escrito en el código
convertiría migrar de llama.cpp a vLLM en un refactor; un test lo verifica buscando por los nombres
que el propio registro declara, así que añadir un alias extiende la comprobación sola.

**La propiedad que sostiene todo lo demás es RF-204**, y su criterio de aceptación es literal: con
el servicio de modelos detenido, el supervisor puede revisar y aprobar OT, con aviso. Por eso la
política de admisión es una función pura: se puede afirmar sobre **toda** la matriz de alias ×
perfil × (pasarela arriba/abajo) a la vez, en vez de sobre el camino de una petición. Ninguna
combinación devuelve algo que signifique «espere a que haya modelo»: o corre ahora, o queda para la
noche, o se omite con aviso.

| Perfil | Extractor de dictado | Juez (LLM) | Auditoría visual (VLM) |
|---|---|---|---|
| **A** — solo CPU | en línea | lote nocturno | **no se ejecuta** (SRS 7.9) |
| **B** — GPU 16 GB | en línea | en línea | lote nocturno (RNF-026) |
| **C** — GPU 24 GB | en línea | en línea | en línea |

Tres cosas que el SRS afirma y que el código habría contradicho en silencio:

- **RF-203: en 16 GB el juez y el VLM no coexisten.** La aritmética simple dice que sí —6,5 + 9 =
  15,5 en una tarjeta de 16— y no: lo que sobra no alcanza para la caché KV de ninguno. El perfil
  declara una **reserva de VRAM**, y eso hace cierta la regla por aritmética en vez de por una lista
  de pares prohibidos que se queda vieja al cambiar un modelo detrás de su alias.
- **La degradación son dos campos, no uno.** «El hardware no puede» y «ahora mismo no cabe» son
  situaciones distintas y el SRS las trata distinto: el VLM está *desactivado* en el perfil A y
  *espera la noche* en el B. Con un solo campo, o se perdía en B o se encolaba para siempre en A.
- **Un hecho permanente decide antes que uno temporal.** Decir «el servicio no responde; pasa al
  lote nocturno» de un alias que ese hardware no puede ejecutar le promete al supervisor un informe
  que nunca llega. Es el orden de dos comprobaciones, y sin un test se invierte en cualquier
  refactor.

**Y el aviso llega a quien decide.** El detalle de la revisión trae `degradations` con motivo, y la
pantalla los muestra encima de la evidencia: quien va a decidir sin el informe del agente tiene que
saberlo antes de leer, no después. La sección **no** aparece cuando no falta nada — un aviso
permanente se vuelve parte del decorado, y entonces nadie lo lee el día que significa algo. Se
calcula de la configuración, sin una sola llamada al servicio de modelos: una pantalla de revisión
que esperara dos segundos para descubrir que no hay GPU le habría quitado dos segundos a alguien sin
darle nada que pudiera hacer.

Lo que falta de M19 es lo que necesita hardware: medir en la GPU real, el planificador ejecutándose
dentro de Celery, y las métricas publicadas en Grafana. La política —qué corre, dónde y por qué— ya
está y se prueba.

---

**Aceptación:** criterios del SRS 10.4 para agentes — recall de inconsistencias ≥ 0,85, kappa supervisor–agente ≥ 0,6 en la muestra ciega, −30 % de tiempo de revisión. Sin vulnerabilidades críticas ni altas. Cero observaciones sin evidencia citada. Todo límite regulatorio evaluado sale de `regulatory_parameter`, ninguno codificado.

---

## Nota sobre el estado de verificación

Los tests de integración **se ejecutaron contra PostgreSQL 16 + PostGIS 3.4 real**, no solo en CI:
1 744 tests del backend en verde bajo ambos perfiles y en orden aleatorio, y las veintitrés
migraciones aplicadas y revertidas sobre una base limpia.

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
| Lógica pura | Orden, severidad, PKCE, sesión, importador, validación, disposición, informe | 534 |
| Render (jsdom) | Que las pantallas muestren lo que hay que ver | 214 |
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
