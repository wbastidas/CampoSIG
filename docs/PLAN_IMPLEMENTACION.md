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
957 tests del backend en verde bajo ambos perfiles y en orden aleatorio, y las trece
migraciones aplicadas y revertidas sobre una base limpia (28 tablas de la aplicación, más
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
| Lógica pura | Orden, severidad, PKCE, sesión, importador, validación, disposición, informe | 202 |
| Render (jsdom) | Que las pantallas muestren lo que hay que ver | 76 |
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
