# Plan de implementación por incrementos — SIGEC-Campo

| Campo | Valor |
|---|---|
| Código | PLAN-SIGEC-001 |
| Versión | 1.0 |
| Fecha | 21 de septiembre de 2026 |
| Base | `SRS.md` v1.1 · `ADDENDUM-01-ArcGIS-FieldMaps-Oracle.md` v1.0 · `GUIA_ENTRENAMIENTO_MODELOS.md` v1.1 |
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
| **I0** | Fundaciones y Oracle | 2 sem | — | 📋 D1 |
| **I1** | Prueba de concepto ArcGIS 10.8.1 | 3 sem | I0 | 🔴 📋 D2 D5 D7 |
| **I2** | Capa de abstracción del modelo de datos | 4 sem | I1 | 🔴 |
| **I3** | Núcleo de OT, planificadores y asignación | 5 sem | I2 | 🟢 📋 D3 |
| **I4** | Móvil offline: mapa, base cifrada y sync | 6 sem | I3 | 🔴 🟢 |
| **I5** | Motor de formularios y evidencias | 5 sem | I4 | 🟢 |
| **I6** | Revisión web y staging as-built | 4 sem | I5 | 🟢 📋 D4 |
| **I7** | Voz → formulario | 6 sem | I5 | 🟢 |
| **I8** | Integraciones corporativas | 4 sem | I3 | 📋 D3 |
| **I9** | **Piloto 1** | 8 sem | I6, I7, I8 | 🟢 📋 D6 |
| **I10** | MLOps y paquetes de modelos | 4 sem (‖ I9) | I7 | — |
| **I11** | Visión on-device | 6 sem | I9, I10 | 🟢 |
| **I12** | Agentes, RAG y endurecimiento | 8 sem | I11 | 🟢 |

Duración de referencia: **11 a 14 meses**. Equipo del SRS 10.2, con dos ajustes: el frontend web pasa a tiempo completo (el diseñador de perfiles y la bandeja GIS son trabajo de web sustancial) y se requiere **un enlace formal con el equipo GIS** desde I1, no como consulta ocasional.

---

## I0 — Fundaciones y Oracle · 2 semanas

**Objetivo:** el equipo puede levantar todo el entorno con un comando y el CI protege las reglas desde el primer commit.

| Entregable | Detalle |
|---|---|
| Monorepo | Estructura del SRS 10.1, con los módulos nuevos del addendum 7.2 |
| Docker Compose de desarrollo | Oracle Free, Redis, SeaweedFS, Keycloak con realm de prueba, backend, web, `llama.cpp` con Qwen2.5-1.5B tras la pasarela de modelos |
| Esquema Oracle base | Esquema `SIGEC` separado del SDE, migraciones Alembic con `oracledb` *thin*, `SDO_GEOMETRY` probado con un ida y vuelta |
| CI | Lint, tests, verificación de licencias, `THIRD_PARTY_LICENSES.md` automático, **prueba de fuga de modelo de datos** (RF-305) desde el día uno |
| Autenticación | Keycloak con OIDC y el flujo de login corporativo (RF-001), federación LDAP/AD documentada aunque se conecte después |
| ADR | Los cinco ADR del addendum versionados en el repo |

**Aceptación:** un desarrollador nuevo clona, ejecuta un comando y tiene el entorno corriendo con login funcional. El CI rechaza un commit que introduzca el literal `PuestoTransfDistribucion` en `backend/app/`.

**Decisión necesaria:** D1 (versión y edición de Oracle). Sin ella se asume 19c y el vector store se resuelve con Qdrant.

---

## I1 — Prueba de concepto ArcGIS 10.8.1 · 3 semanas 🔴

**Objetivo:** convertir los supuestos del addendum sección 5 en hechos medidos. Este incremento puede cambiar la arquitectura; por eso va antes que todo lo demás.

Se trabaja **sobre una copia** de la geodatabase, nunca sobre producción.

| Entregable | Detalle |
|---|---|
| Inventario de habilitación | Qué clases del modelo tienen Global IDs, archiving y versionado; qué falta y qué cuesta habilitarlo (riesgo R-N2, decisión D5) |
| Feature services publicados | Publicación con sync habilitado desde la copia, con versionado tradicional en el feature dataset `Electrico` |
| Cliente ArcGIS mínimo | `rest_client.py` + `replica.py`: token de Portal, `query`, `createReplica`, `synchronizeReplica` |
| **Informe de medición** | Tiempo y tamaño de `createReplica` por zona y por alimentador; tiempo de sync incremental; comportamiento con las clases de `Electrico_RedGeom`; qué pasa exactamente al intentar editar conectividad |
| `tools/arcgis-mock` | Simulador de feature service 10.8.1 para el CI, con los mismos rechazos que el real |
| Verificación de las hipótesis H1–H7 | Cada hallazgo del addendum 5.1 confirmado, corregido o refutado, con evidencia |
| Ruta de aplicación en ArcFM | Ensayo del flujo: lote de propuestas → editor aplica en ArcMap/ArcFM → auto-actualizadores y trace corren. Medición del tiempo por elemento (alimenta R-N3) |

**Aceptación:** existe un informe firmado con el equipo GIS que responde: ¿se puede sincronizar?, ¿a qué costo?, ¿qué clases sí y cuáles no?, ¿cuánto tarda un editor en aplicar un lote de 50 elementos? Si alguna respuesta invalida el diseño, se revisa el addendum **antes** de I2.

**Decisiones necesarias:** D2, D5, D7.

> **Punto de no retorno.** Si aquí se descubre que la geodatabase no puede habilitarse para sync, el plan cambia a un modelo de exportación periódica (ETL a la caché Oracle, sin réplica). El resto de los incrementos sobrevive; solo cambia `arcgis_connector`.

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
| Acta PDF | WeasyPrint con fotos, firmas, resumen y QR de verificación (RF-115) |
| `staging_asbuilt` | RF-342: propuestas con `proposal_id`, `GLOBALID` de origen, OT, y resultado de aplicación |
| **Bandeja de revisión GIS** | RF-343: agrupación por zona y alimentador, antes/después, aprobación por lotes, rol de editor GIS |
| Exportación para ArcFM | RF-344: lote aprobado como GeoJSON/CSV de trabajo, con instrucciones por elemento |
| Controles de calidad del SIG | RF-350 y RF-351: reglas sobre el AMD → trabajos de verificación en campo |

**Aceptación:** una OT con un poste nuevo recorre todo el camino: captura offline → sync → revisión del supervisor → staging → bandeja GIS → lote exportado → editor lo aplica en ArcFM → el elemento existe en la geodatabase con su conectividad correcta. Se mide el tiempo del ciclo completo (insumo de R-N3).

**Decisión necesaria:** D4.

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

---

## I12 — Agentes, RAG y endurecimiento · 8 semanas 🟢

**Objetivo:** el supervisor revisa con ayuda, y la plataforma queda lista para producción.

| Entregable | Detalle |
|---|---|
| Pasarela de modelos y planificador de GPU | M19: alias lógicos, colas día/noche, degradación a lote nocturno según perfil |
| Base de conocimiento y RAG | M18 con el vector store de ADR-005; ingesta normativa segmentada por numeral |
| Grafo de pre-revisión | M17: coherencia, catálogos y normativa, evidencia visual, anomalías, consolidador. Reglas deterministas primero |
| Informe en la revisión | RF-111 con observaciones enlazadas a su evidencia, y RF-111a (muestra ciega) |
| Evaluación en CI | Conjuntos dorados, DeepEval, RAGAS, promptfoo, *red teaming* |
| Endurecimiento | Pentest, rendimiento, evaluación de impacto LOPDP, documentación de operación, despliegue escalonado |

**Aceptación:** criterios del SRS 10.4 para agentes — recall de inconsistencias ≥ 0,85, kappa supervisor–agente ≥ 0,6 en la muestra ciega, −30 % de tiempo de revisión. Sin vulnerabilidades críticas ni altas. Cero observaciones sin evidencia citada.

---

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

1. **Responder D1** (versión y edición de Oracle) — desbloquea I0 y cierra ADR-005.
2. **Agendar con el equipo GIS** la copia de la geodatabase y la ventana para I1 — es el camino crítico real.
3. **Arrancar I0**, que no depende de nadie más: monorepo, Docker Compose, esquema Oracle, CI con la prueba de fuga de modelo de datos y los cinco ADR.
4. Con I0 corriendo, **lanzar I1** y tratar su informe como puerta: si invalida una hipótesis, se corrige el addendum antes de tocar I2.

Los seis tipos de activo del piloto (estructura de soporte, transformador de distribución, luminaria, seccionador fusible, tramo y punto de carga) y los seis formularios (F-TR-01, F-TR-02, F-OP-01, F-MT-01, F-AP-01, F-IC-03) son el alcance vertical de I2 a I7. Conviene no ampliarlo antes del piloto.
