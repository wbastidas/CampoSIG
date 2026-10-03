# Matriz de trazabilidad — SIGEC-Campo

Cada requerimiento funcional del SRS y del addendum, con su estado y dónde está la prueba. Generada a
partir de las citas de cada RF en las pruebas (`backend/tests`, `web/src`, `android/core`,
`gis-agent/tests`) y de una clasificación explícita de los que no se citan o dependen de algo que
este entorno no tiene.

**Estados.** ✅ implementado y probado · 🟡 parcial: el servidor y/o el núcleo móvil están, falta la
pantalla Android · ⛔ bloqueado: necesita el SDK de Android, que la política de red de este entorno
no deja descargar (`dl.google.com`) · ⏸ diferido: IA o MLOps, por decisión del usuario («no te
enfoques en la parte de IA por ahora») · ✖ excluido por una decisión documentada (ADR-007, RF-031, «v2»).

| Estado | RF |
|---|---|
| ✅ Implementado | 95 |
| 🟡 Parcial | 24 |
| ⛔ Bloqueado (SDK Android) | 7 |
| ⏸ Diferido (IA) | 31 |
| ✖ Excluido por decisión | 7 |
| **Total** | **164** |

| RF | Prio | Canal | Requerimiento | Estado | Nota | Pruebas |
|---|---|---|---|---|---|---|
| RF-001 | M | W/A/B | Autenticación OIDC (Keycloak) con usuario corporativo (integración LDAP/AD). | ✅ Implementado |  | SessionProvider.test.tsx, oidc.test.ts, session.test.ts, test_rf001_authentication.py |
| RF-002 | M | B | Control de acceso por roles (sección 2.2) y por ámbito (área, zona, agencia, contratista). | ✅ Implementado |  | test_rf001_authentication.py, test_rf001_every_route_is_guarded.py, test_rf002_ambito.py, test_rf002_ambito_writes.py |
| RF-003 | M | A | Sesión offline en el móvil: tras un login en línea, permite trabajar hasta N días sin red (parámetro, por d… | 🟡 Parcial | `core:field` (SessionGate, PinHash); falta la pantalla y BiometricPrompt. | OfflineSessionTest.kt |
| RF-004 | M | W/B | Registro y enrolamiento de dispositivos (ID, modelo, versión de la app, versión del paquete de modelos, últ… | ✅ Implementado |  | test_rf101_sync_contract.py, test_rf102_sync_api.py, test_rf104_dispatch.py |
| RF-005 | M | W | Gestión de cuadrillas: integrantes, jefe, vehículo, competencias (MV, BV, trabajo en tensión, APG, altura) … | ✅ Implementado |  | CrewsScreen.test.tsx, crews.test.ts, test_rf005_crews.py |
| RF-010 | M | W | Crear OT manualmente con: tipo, área, formulario, activo o ubicación (mapa), prioridad, SLA, descripción, a… | ✅ Implementado | Creación manual de OT (`create_work_order`, API de planificación). | backend/tests/integration/test_rf025_routing.py y otros que crean OT por el servicio |
| RF-011 | M | B | Crear OT automáticamente desde integraciones: reclamos del call center, eventos del OMS/ADMS y la plataform… | ✅ Implementado |  | test_rf320_assignment.py |
| RF-012 | S | W/B | Crear OT desde planes de mantenimiento preventivo (por activo, frecuencia, ruta o alimentador). | ✅ Implementado |  | PlansScreen.test.tsx, plans.test.ts, test_rf012_maintenance_plans.py, test_rf012_periods.py |
| RF-013 | M | A/W/B | Trabajos sugeridos por IA: a partir de hallazgos (B11 o detección visual) se crea una *OT propuesta* con ti… | ✅ Implementado |  | ProposalsScreen.test.tsx, proposals.test.ts, test_rf012_maintenance_plans.py, test_rf013_criticality.py |
| RF-014 | S | B | Deduplicación de hallazgos y OT: alerta si existe una OT abierta sobre el mismo activo o a menos de X m con… | ✅ Implementado |  | test_rf013_proposals.py |
| RF-015 | S | W | OT multi-actividad y OT hijas (p. ej., una obra con múltiples frentes). | ✅ Implementado |  | attachments.test.ts, test_rf015_work_fronts.py, test_rf017_attachments.py |
| RF-016 | M | B | Máquina de estados de la sección 3.3, con transiciones validadas en el backend. | ✅ Implementado |  | test_rf102_sync_api.py |
| RF-017 | S | W/A | Adjuntos de oficina: planos, diseños y documentos PDF visibles offline en el móvil. | 🟡 Parcial | Servidor, paquete offline y web listos (adjuntos con tope por OT); falta el visor en el teléfono. | test_rf017_attachments.py, AttachmentsPanel.test.tsx |
| RF-020 | M | W | Tablero de despacho con mapa (OT por estado y prioridad, ubicación de cuadrillas según el último GPS report… | ✅ Implementado |  | positions.test.ts, test_rf020_dispatch_map.py, test_rf021_assisted_assignment.py, test_rf025_routing.py |
| RF-021 | M/S | W | Asignación manual (arrastrar OT a cuadrilla) y asistida: sugerencia por cercanía, competencias, carga y SLA. | ✅ Implementado |  | suggestion.test.ts, test_rf021_assisted_assignment.py, test_rf101_sync_contract.py |
| RF-022 | M | A/B | Notificación al móvil: push (FCM opcional) y, sin push, descubrimiento en el siguiente sync. | 🟡 Parcial | Descubrimiento en el siguiente sync implementado (dispositivo personal, custodia y teléfono de cuadrilla). **Sin FCM a propósito**: Firebase es un componente propietario de Google Play Services y la regla 10 prohíbe componentes propietarios en el móvil. | test_rf101_sync_contract.py (TestRf022…), test_rf320_crew_device_and_withdrawals.py |
| RF-023 | M | W/A | Reasignación y transferencia entre cuadrillas con motivo. | ✅ Implementado |  | WithdrawalsTest.kt, test_rf101_sync_contract.py, test_rf320_crew_device_and_withdrawals.py |
| RF-024 | S | W | Programación de consignaciones: una OT que requiere corte se vincula con la solicitud de consignación y su … | ✅ Implementado |  | OutagesScreen.test.tsx, outages.test.ts, test_rf024_outages.py, test_rf102_sync_api.py |
| RF-025 | C | W/B | Rutas sugeridas para un conjunto de OT (optimización simple, open source: OR-Tools, Apache 2.0). | ✅ Implementado |  | RouteSuggestionPanel.test.tsx, route.test.ts, test_rf025_routing.py |
| RF-030 | M | W/B | Definir formularios como JSON Schema 2020-12 + UI Schema, con extensiones `x-voice`, `x-synonyms`, `x-visio… | ✅ Implementado | Formularios como JSON Schema 2020-12 + UI Schema generados del perfil (`forms/`, `app/forms`). | backend/tests/unit/test_rf303_form_generation.py |
| RF-031 | S | W | Editor visual de formularios (arrastrar bloques, campos, catálogos y reglas) con vista previa web y móvil. | ✖ Excluido por decisión | No se construye: documentado en el plan (la decisión del usuario fue documentarlo). Los formularios se generan del perfil (regla 3). | — |
| RF-032 | M | B | Versionado de formularios (borrador → publicado → obsoleto); las OT conservan su versión. | ✅ Implementado |  | FormCatalogueScreen.test.tsx, catalogue.test.ts, conftest.py, test_rf032_form_versioning.py |
| RF-033 | M | B | Generación automática de la gramática (GBNF) y del prompt de extracción a partir del JSON Schema al publicar. | ✅ Implementado | Gramática GBNF y prompt de extracción generados del JSON Schema (núcleo determinista; el modelo queda diferido). | backend/tests/unit/test_rf332_grammar.py, test_rf140_extraction.py |
| RF-034 | M | W/B | Catálogos administrables: UP/UC homologadas, materiales (sincronizados con el ERP), causas de falla, defect… | ✅ Implementado |  | CatalogsScreen.test.tsx, catalogs.test.ts, test_rf034_catalogs.py, test_rf122_erp_adapter.py |
| RF-035 | M | W/A | Reglas condicionales y validaciones de negocio (p. ej., "si tipo de trabajo = con tensión, exigir guantes c… | ✅ Implementado | Reglas condicionales: un corpus, tres implementaciones (servidor, web, `core:sync`). | test_i5_shared_validation_contract.py, web/src/forms/rules.test.ts, FormRulesTest.kt |
| RF-040 | M | Sí | Bandeja de OT del día con orden por prioridad y distancia, estados y contador de pendientes de sincronizar. | 🟡 Parcial | `core:field` (InboxOrdering); falta la lista en Compose. | InboxTest.kt |
| RF-041 | M | Sí | Detalle de la OT: descripción, mapa offline, historial del activo (últimas N intervenciones y fotos), adjun… | ⛔ Bloqueado (SDK Android) | El paquete offline ya trae lo que la pantalla mostraría (OT, adjuntos RF-017); falta la pantalla. | — |
| RF-042 | M | Sí | Mapa offline con capas de la zona asignada (red MV/BV, postes, transformadores, luminarias), la posición ac… | ⛔ Bloqueado (SDK Android) | Las teselas PMTiles se publican por zona (RF-360); falta el visor MapLibre Android. | — |
| RF-043 | M | Sí | Renderizado dinámico del formulario desde JSON Schema (Compose), con validación en línea y guardado automát… | ⛔ Bloqueado (SDK Android) | El renderizado en Compose necesita el SDK; las reglas y la validación ya están en `core:sync`. | — |
| RF-044 | M | Sí | Flujo guiado por pasos: Seguridad → Antes → Ejecución → Después → Resumen → Cierre, con indicadores de comp… | 🟡 Parcial | `core:field` (GuidedFlow); falta la pantalla de pasos. | GuidedFlowTest.kt |
| RF-045 | M | Sí | Ingreso manual optimizado para campo: botones grandes (≥ 48 dp, preferible 56 dp), alto contraste, uso con … | ⛔ Bloqueado (SDK Android) | Ergonomía de pantalla (botones ≥ 48 dp, guantes): es la capa Compose. | — |
| RF-046 | M | Sí | Captura de firma (jefe de cuadrilla, cliente) y cédula del cliente cuando aplique. | 🟡 Parcial | Cédula en tres plataformas y `format: ec-cedula` en B12; la firma es evidencia `firma` con hash. Falta el lienzo de firma Android. | CedulaTest.kt, identification.test.ts, test_rf046_cedula_capture.py, test_rf046_cedula_contract.py |
| RF-047 | M | Sí | Registro de tiempos automático por transición (EnCamino, EnSitio, inicio, fin) con posibilidad de correcció… | 🟡 Parcial | Servidor (`work_order_milestone`) y `core:field` (TimeLog); falta la pantalla de corrección. | TimeLogTest.kt, test_rf047_times_findings_owner.py |
| RF-048 | M | Sí | Suspender una OT con motivo (falta de material, clima, acceso denegado, riesgo) y retomarla. | 🟡 Parcial | Suspender exige motivo y retomar es una transición del servidor; falta el botón en la app. | test_rf102_sync_api.py (suspender sin motivo se rechaza) |
| RF-049 | M | Sí | Crear hallazgos o trabajos nuevos desde el campo, aunque no exista una OT (hallazgo espontáneo). | 🟡 Parcial | Servidor (`field_finding` → propuesta) y `core:field` (FieldFindingDraft); falta la pantalla. | FieldFindingTest.kt, test_rf047_times_findings_owner.py |
| RF-050 | M | Sí | Botón "Dictar" a nivel de formulario completo, sección o campo. El alcance del dictado define qué campos pu… | ⏸ Diferido (IA) | Dictado: diferido por decisión del usuario («no te enfoques en la parte de IA»). El núcleo servidor de voz→formulario existe (I7). | — |
| RF-051 | M | Sí | ASR offline en español (es-EC) con VAD y reducción de ruido; texto parcial en vivo y transcripción final. S… | ⏸ Diferido (IA) | ASR offline en el teléfono: IA diferida y además requiere SDK. | — |
| RF-051a | M | Sí | Sesgo por vocabulario técnico. Ruta T: archivo de *hotwords* generado desde el léxico vivo (RF-147) y el co… | ⏸ Diferido (IA) | El léxico vivo que alimenta el sesgo existe (RF-147); el ASR en el teléfono está diferido. | test_rf147_living_vocabulary.py (servidor) |
| RF-052 | M | Sí | Extracción estructurada: transcripción + esquema + contexto de la OT → JSON válido garantizado mediante dec… | 🟡 Parcial | Extracción con gramática en el núcleo del servidor; en el teléfono va con la IA diferida. | test_rf140_extraction.py |
| RF-053 | M | Sí | Los campos llenados por IA se marcan visualmente (color o ícono "IA") con su nivel de confianza; los de baj… | ⏸ Diferido (IA) | La procedencia IA con confianza se guarda en el servidor (regla 8); el marcado visual es de la pantalla Android. | — |
| RF-054 | M | Sí | No inventar: si la transcripción no menciona un campo, este queda vacío (`null`); nunca se rellena por defe… | 🟡 Parcial | «No inventar» en el núcleo del servidor; en el teléfono va con la IA diferida. | test_rf140_extraction.py |
| RF-055 | M | Sí | Normalización de números, unidades y códigos dichos en voz ("trece punto ocho kilovoltios" → 13.8 kV; "diez… | 🟡 Parcial | Normalización en el núcleo del servidor; en el teléfono va con la IA diferida. | test_rf331_lexicon.py |
| RF-056 | M | Sí | Mapeo a catálogos: el valor extraído se resuelve contra el catálogo (coincidencia exacta, luego sinónimos, … | 🟡 Parcial | Mapeo a catálogos en el servidor; en el teléfono va con la IA diferida. | test_rf034_catalogs.py |
| RF-057 | M | Sí | Dictado de tablas (materiales, hallazgos, actividades): cada frase puede crear filas múltiples. | ⏸ Diferido (IA) | Dictado de tablas: parte del flujo de voz diferido. | — |
| RF-058 | M | Sí | Guardar el audio original (opcional según la política, con consentimiento) y la transcripción para auditorí… | 🟡 Parcial | La política (store_audio, consentimiento) se hace cumplir en el servidor; falta la grabación en la app. | test_rf151_capture_policy.py |
| RF-059 | C | Sí | Comandos de voz básicos: "siguiente sección", "tomar foto", "repetir", "borrar último". | ⏸ Diferido (IA) | Comandos de voz (C): diferido. | — |
| RF-060 | S | No | Modo híbrido: al sincronizar, el servidor puede re-transcribir con un modelo mayor (NVIDIA Canary-1B-v2 o P… | ⏸ Diferido (IA) | Re-transcripción híbrida en el servidor: IA diferida. | — |
| RF-070 | M | Sí | Cámara integrada (CameraX) con encuadres guiados por tipo de OT (p. ej., "poste completo", "detalle de cruc… | ⛔ Bloqueado (SDK Android) | CameraX y encuadres guiados: pantalla Android. El `framing` ya viaja con la evidencia. | — |
| RF-071 | M | Sí | Metadatos: GPS (lat, lon, precisión, altitud), rumbo, fecha y hora del dispositivo, ID de la OT, ID del usu… | 🟡 Parcial | Servidor y `core:field` (ExifTags); falta escribir el EXIF con `ExifInterface`. | EvidenceTest.kt, test_rf073_evidence_integrity.py |
| RF-072 | M | Sí | Marca de agua visible configurable (N.º OT, fecha y hora, coordenadas, usuario) sobre una copia de la image… | 🟡 Parcial | Servidor (clave de la copia) y `core:field` (Watermark); falta dibujarla con Canvas. | EvidenceTest.kt, test_rf073_evidence_integrity.py |
| RF-073 | M | Sí | Integridad: hash SHA-256 de la imagen original al capturar, registrado en la cadena de auditoría. | 🟡 Parcial | Completo en el servidor (verificación al subir); el hash en el teléfono está en `core:field`. | EvidenceTest.kt, decision.test.ts, test_rf073_evidence_integrity.py |
| RF-074 | M | Sí | Bloqueo de fotos desde la galería para evidencias obligatorias (solo cámara en vivo); se permite galería pa… | 🟡 Parcial | Servidor (no cuenta) y `core:field` (GalleryPolicy); falta el selector Android. | EvidenceTest.kt, decision.test.ts, test_rf073_evidence_integrity.py |
| RF-075 | S | Sí | Control de calidad de imagen al capturar: desenfoque, subexposición o sobreexposición; se sugiere repetir. | 🟡 Parcial | `core:field` (ImageQuality); falta pasarle la imagen desde CameraX. | EvidenceTest.kt |
| RF-076 | M | Sí | Compresión y política de envío: miniatura inmediata, imagen completa al tener Wi-Fi o datos según el paráme… | 🟡 Parcial | Límites, tipos y política por red en el servidor y la bandeja; falta comprimir en el teléfono. | test_rf076_storage_presign.py |
| RF-077 | S | Sí/B | Anonimización: detección y difuminado de rostros y placas vehiculares antes de enviar al dataset de entrena… | ⏸ Diferido (IA) | Anonimización para datasets: MLOps diferido. | — |
| RF-080 | M | Sí | Detección de todos los elementos visibles de red según la taxonomía del Anexo B (poste, cruceta, aisladores… | ⏸ Diferido (IA) | Visión on-device: IA diferida (taxonomía y contratos listos en I11). | — |
| RF-081 | M | Sí | Clasificación de estado y defectos por elemento (p. ej., aislador: bueno / roto / flameado; poste: inclinad… | ⏸ Diferido (IA) | Visión on-device: IA diferida. | — |
| RF-082 | M | Sí | Lista interactiva "Elementos detectados" junto a la foto: tocar un elemento resalta su caja; el usuario con… | ⏸ Diferido (IA) | Lista de detecciones: IA diferida. | — |
| RF-083 | M | Sí | Pre-llenado de campos del formulario con `x-vision-source` desde las detecciones confirmadas. | ⏸ Diferido (IA) | Pre-llenado desde visión: IA diferida. | — |
| RF-084 | M | Sí | Comparación antes/después: emparejamiento de elementos por clase y posición relativa; resultado por element… | ⏸ Diferido (IA) | Comparación antes/después por visión: IA diferida. | — |
| RF-085 | S | Sí | Verificación de consistencia: advertir si las fotos ANTES y DESPUÉS parecen de ubicaciones distintas (dista… | ⏸ Diferido (IA) | Consistencia de ubicación entre fotos: IA diferida. | — |
| RF-086 | M | Sí | Los hallazgos visuales críticos no resueltos en la foto DESPUÉS generan automáticamente un ítem en B11 (hal… | ⏸ Diferido (IA) | Hallazgos visuales → B11: IA diferida (la bandeja de propuestas RF-013 ya existe). | — |
| RF-087 | M | Sí | Latencia: detección + clasificación ≤ 2 s por foto en el hardware objetivo; se ejecuta en segundo plano sin… | ⏸ Diferido (IA) | Latencia de visión: IA diferida. | — |
| RF-090 | M | Sí | Generar el resumen Encontrado / Realizado / Pendiente a partir de: los campos confirmados, las detecciones … | ⏸ Diferido (IA) | Resumen Encontrado/Realizado/Pendiente: IA diferida. | — |
| RF-091 | M | Sí | El resumen es editable por el técnico y se guarda como versión IA + versión final. | ⏸ Diferido (IA) | Versión IA + final del resumen: IA diferida. | — |
| RF-092 | S | Sí | Descripción visual opcional con VLM ("describe la foto") para campos de observación libre. | ⏸ Diferido (IA) | Descripción con VLM: IA diferida. | — |
| RF-093 | C | No | Resumen ejecutivo de jornada o cuadrilla para el supervisor (servidor). | ⏸ Diferido (IA) | Resumen ejecutivo (C): IA diferida. | — |
| RF-100 | M | A | Base local cifrada (Room + SQLCipher) como fuente de verdad del móvil. | ⛔ Bloqueado (SDK Android) | Room + SQLCipher: capa Android. El PIN y la sesión que la abren están en `core:field`. | — |
| RF-101 | M | A/B | Cola de salida (*outbox*) con operaciones idempotentes (UUID por operación), reintentos exponenciales y res… | ✅ Implementado |  | OutboxTest.kt, test_rf101_sync_contract.py, test_rf102_sync_api.py, test_rf104_dispatch.py |
| RF-102 | M | A/B | Sincronización incremental de bajada (OT, catálogos, formularios, capas, modelos) por marcas de versión (*d… | ✅ Implementado |  | test_rf046_cedula_capture.py, test_rf047_times_findings_owner.py, test_rf073_evidence_integrity.py, test_rf101_sync_contract.py |
| RF-103 | M | A | Subida por prioridad: 1) estados y datos; 2) miniaturas; 3) fotos completas; 4) audios; 5) datos de entrena… | ✅ Implementado |  | OutboxTest.kt, test_rf102_sync_api.py |
| RF-104 | M | A/B | Subida resumible de archivos grandes (tus protocol, MIT / MPL, o multipart con reanudación). | 🟡 Parcial | La bandeja reanuda por operación y el tablero muestra lo no entregado; la subida multipart reanudable de un archivo grande (tus o S3 multipart) no está. | OutboxTest.kt, test_rf104_dispatch.py |
| RF-105 | M | B/W | Resolución de conflictos: el servidor es la autoridad sobre la asignación y el estado administrativo; el mó… | ✅ Implementado |  | ConflictResolverTest.kt, test_rf102_sync_api.py |
| RF-106 | M | A | Indicador de sincronización en la app (pendientes, último sync, errores) y "forzar sync". | 🟡 Parcial | El servidor da su hora y la bandeja de `core:field` el contador; falta el indicador en pantalla. | test_rf102_sync_api.py, InboxTest.kt |
| RF-107 | S | A | Reporte de posición de la cuadrilla (cada N minutos durante la jornada, parámetro, con consentimiento y sol… | 🟡 Parcial | Servidor (política, consentimiento, rechazo) y `core:field` (PositionSchedule, corpus compartido); falta WorkManager. | PositionScheduleTest.kt, policy.test.ts, test_rf020_dispatch_map.py, test_rf107_position_policy.py |
| RF-110 | M | W | Bandeja de revisión con filtros (área, cuadrilla, tipo, fecha, "con propuestas IA", "con conflictos"). | ✅ Implementado |  | test_rf110_review_api.py |
| RF-111 | M | W | Vista de revisión: formulario, línea de tiempo, mapa, fotos antes y después en paralelo con las detecciones… | ✅ Implementado |  | ReviewScreen.test.tsx, decision.test.ts, test_rf170_pre_review_runs.py |
| RF-111a | S | W | Mitigación del sesgo de anclaje: en una muestra aleatoria configurable de OT (p. ej., 10 %), el informe del… | ✅ Implementado |  | AiDashboardScreen.test.tsx, ReviewScreen.test.tsx, conftest.py, decision.test.ts |
| RF-112 | M | W | Aprobar, devolver (con observaciones por campo) o anular. La devolución regresa la OT al móvil. | ✅ Implementado |  | ReviewScreen.test.tsx, test_i5_i6_end_to_end.py, test_rf110_review_api.py |
| RF-113 | S | W | Corrección de etiquetas visuales por el supervisor (mismas herramientas que RF-082); estas correcciones tie… | ⏸ Diferido (IA) | Corrección de etiquetas visuales: depende de la visión diferida. | — |
| RF-114 | M | W | Bandeja de OT propuestas por IA con acciones aprobar, fusionar o rechazar (con motivo de catálogo). | ✅ Implementado |  | ProposalsScreen.test.tsx, proposals.test.ts, test_rf013_proposals.py |
| RF-115 | M | W/B | Exportación de la OT a PDF (acta con fotos, firmas y resumen) con código QR de verificación. | ✅ Implementado |  | ReviewScreen.test.tsx, test_rf001_every_route_is_guarded.py, test_rf115_acta.py, test_rf115_acta_issuance.py |
| RF-120 | M | B | Adaptador de la plataforma de OT existente (bidireccional): recibir OT, devolver estados, datos, resumen y … | ✅ Implementado |  | test_rf120_integrations.py |
| RF-121 | S | B | Adaptador GIS: lectura de activos y topología (capas), escritura de actualizaciones as-built (F-IC-05) medi… | ✅ Implementado | Adaptador GIS: lectura por feature services y escritura por el agente arcpy (ADR-006, ADR-008). | gis-agent/tests/, backend/tests/integration/test_rf120_integrations.py |
| RF-122 | S | B | Adaptador ERP: catálogo de materiales y existencias por bodega o vehículo; registro de consumos y devolucio… | ✅ Implementado |  | test_rf122_erp_adapter.py |
| RF-123 | S | B | Adaptador OMS/ADMS: recibir eventos de falla y devolver causa, elemento y horas de reposición (CIM IEC 6196… | ✅ Implementado |  | test_rf123_oms_adapter.py |
| RF-124 | M | B | Adaptador de call center y reclamos: creación de OT desde reclamos y cierre del reclamo con el resultado. | ✅ Implementado |  | test_rf120_integrations.py |
| RF-125 | M | B | Todos los adaptadores usan un bus interno de eventos y registran cada intercambio (payload, estado, reinten… | ✅ Implementado |  | IntegrationsScreen.test.tsx, ledger.test.ts, test_rf120_integrations.py, test_rf125_delivery_worker.py |
| RF-130 | M | W | Tablero operativo: OT por estado, SLA (vencidas o por vencer), productividad por cuadrilla, tiempos promedi… | ✅ Implementado |  | OperationsBoard.test.tsx, board.test.ts, test_rf130_operational_board.py |
| RF-131 | M | W | APG: tiempo de reposición de luminarias vs. máximo regulatorio; tasa de falla; luminarias por tecnología. | ✅ Implementado |  | ApgScreen.test.tsx, apg.test.ts, test_rf120_integrations.py, test_rf131_apg_board.py |
| RF-132 | S | W | Operación: base de datos de interrupciones exportable para el cálculo de FMIK y TTIK (formato configurable). | ✅ Implementado |  | OperationsBoard.test.tsx, board.test.ts, test_rf123_oms_adapter.py, test_rf132_interruption_base.py |
| RF-133 | S | W | Mantenimiento: mapa de calor de defectos por alimentador; reincidencia por activo; hallazgos abiertos por c… | ✅ Implementado |  | MaintenanceScreen.test.tsx, maintenance.test.ts, test_rf002_ambito_writes.py, test_rf133_maintenance_board.py |
| RF-134 | M | W | Tablero de IA: tasa de aceptación de propuestas por campo, correcciones por clase visual, WER estimado, ado… | ✅ Implementado |  | AiDashboardScreen.test.tsx, metrics.test.ts, test_rf134_ai_dashboard.py, test_rf134_ai_dashboard_arithmetic.py |
| RF-135 | C | W/B | Analítica predictiva (v2): priorización de mantenimiento según el historial de hallazgos, las fallas y la e… | ✖ Excluido por decisión | Analítica predictiva marcada «v2» en el SRS (C). | — |
| RF-140 | M | A/B | Captura de señales de aprendizaje: por cada propuesta IA se guarda la tupla (entrada, propuesta, valor fina… | ✅ Implementado |  | test_rf140_extraction.py, test_rf140_vision.py, test_rf140_vision_flow.py, test_rf140_voice_flow.py |
| RF-141 | M | B | Curaduría: el pipeline filtra la calidad (audio, borrosidad, consistencia), anonimiza (RF-077) y deduplica … | ⏸ Diferido (IA) | Curaduría de datasets: MLOps diferido. | — |
| RF-142 | M | B/W | Integración con una herramienta de etiquetado (CVAT o Label Studio) para imágenes y audio, con pre-etiqueta… | ⏸ Diferido (IA) | Integración CVAT/Label Studio: MLOps diferido. | — |
| RF-143 | M | B | Registro de modelos y experimentos (MLflow), con métricas, dataset (versión DVC) y artefactos exportados (O… | ⏸ Diferido (IA) | MLflow: MLOps diferido. | — |
| RF-144 | M | B | Compuertas de calidad (*eval gates*): un modelo nuevo solo se publica si supera al vigente en el set de pru… | ⏸ Diferido (IA) | Compuertas de calidad de modelos: MLOps diferido (las de agentes, RNF-060, sí están). | — |
| RF-145 | M | A/B | Despliegue OTA del paquete de modelos con manifiesto firmado, descarga diferida por Wi-Fi, verificación de … | ⏸ Diferido (IA) | OTA del paquete de modelos: diferido (requiere modelos y SDK). | — |
| RF-146 | S | A/B | Modo sombra (*shadow*): el modelo candidato corre en paralelo sin mostrarse y reporta métricas. | ⏸ Diferido (IA) | Modo sombra: diferido. | — |
| RF-147 | M | W/B | Diccionario vivo de vocabulario técnico (términos, sinónimos, regionalismos, códigos) administrable, que al… | ✅ Implementado |  | CatalogsScreen.test.tsx, catalogs.test.ts, test_rf122_erp_adapter.py, test_rf147_living_vocabulary.py |
| RF-150 | M | W/B | Parámetros regulatorios y operativos con vigencia (desde/hasta), referencia normativa y usuario que modificó. | ✅ Implementado |  | RegulatoryScreen.test.tsx, regulatory.test.ts, test_rf150_parameter_authorship.py |
| RF-151 | M | W | Configuración por área: políticas de audio, fotos mínimas, calidad, envío por red y retención. | ✅ Implementado |  | PolicyScreen.test.tsx, policy.test.ts, test_rf107_position_policy.py, test_rf151_capture_policy.py |
| RF-152 | M | W | Gestión de zonas (polígonos) para la asignación y la descarga de mapas. | ✅ Implementado |  | ZonesScreen.test.tsx, test_rf005_crews.py, test_rf152_zones.py, zones.test.ts |
| RF-160 | M | B | Bitácora inmutable (*append-only*) de eventos: creación, cambios de campo (valor anterior y nuevo, origen h… | ✅ Implementado |  | AuditScreen.test.tsx, test_rf012_maintenance_plans.py, test_rf013_proposals.py, test_rf015_work_fronts.py |
| RF-161 | M | W | Consulta de trazabilidad por OT, activo, usuario o dispositivo. | ✅ Implementado |  | AuditScreen.test.tsx, test_rf160_audit_trail.py, trail.test.ts |
| RF-170 | M | B | Orquestación de la pre-revisión. Al sincronizarse una OT cerrada en campo, se encola una ejecución (`agent_… | ✅ Implementado |  | test_m17_pre_review.py, test_rf170_pre_review_runs.py |
| RF-171 | M | B | Agente de coherencia: compara la transcripción, los campos confirmados, las detecciones visuales y los tiem… | ✅ Implementado |  | test_m17_pre_review.py |
| RF-172 | M | B | Agente normativo y de catálogos: valida los códigos UP/UC, materiales, causas y parámetros regulatorios (ti… | ✅ Implementado |  | test_m17_pre_review.py, test_rnf060_agent_eval_gates.py |
| RF-173 | S | B | Agente de evidencia visual (VLM): con Qwen2.5-VL-7B (Apache 2.0) verifica si las fotos sustentan lo declara… | ⏸ Diferido (IA) | Agente VLM de evidencia: IA diferida. | — |
| RF-174 | S | B | Agente de anomalías: detecta patrones atípicos con reglas y estadística (tiempos imposibles, fotos duplicad… | ✅ Implementado |  | metrics.test.ts, test_m17_pre_review.py, test_rf170_pre_review_runs.py |
| RF-175 | M | B | Consolidador: produce el informe final con un nivel de riesgo (bajo, medio, alto) y observaciones priorizad… | ✅ Implementado |  | decision.test.ts, test_m17_pre_review.py |
| RF-176 | S | W | Aprobación en lote asistida: el supervisor puede aprobar en bloque OT de riesgo bajo, siempre con acción hu… | ✅ Implementado |  | ReviewScreen.test.tsx, decision.test.ts, test_rf176_batch_approval.py, test_rf176_no_automatic_approval.py |
| RF-177 | S | B/W | Agente priorizador: a partir de los hallazgos y las OT sugeridas (RF-013) propone la prioridad (Anexo C), a… | ⏸ Diferido (IA) | Agente priorizador: IA diferida (la prioridad determinista del anexo C sí está, RF-013). | — |
| RF-178 | S | W/A | Asistente de procedimientos (RAG): chat en la web y en el móvil (con conexión) para consultar procedimiento… | ✖ Excluido por decisión | Asistente RAG: excluido en v1 por ADR-007. | docs/adr |
| RF-179 | C | B | Agente de apoyo al etiquetado: propone etiquetas iniciales, detecta etiquetas inconsistentes entre anotador… | ⏸ Diferido (IA) | Agente de etiquetado (C): IA diferida. | — |
| RF-180 | M | B/W | Trazabilidad de agentes: se guarda cada ejecución (versión del grafo, prompts, modelos, herramientas invoca… | ✅ Implementado |  | test_m17_pre_review.py, test_rf170_pre_review_runs.py |
| RF-181 | S | B | Herramientas vía MCP: catálogos, consulta de OT y activos (PostGIS), normativa (RAG) e historial se exponen… | ⏸ Diferido (IA) | Herramientas MCP para agentes: IA diferida. | — |
| RF-182 | M | B | Guardrails: validación de entradas y salidas (formato, longitud, lenguaje neutral, ausencia de datos person… | ✅ Implementado |  | test_rf170_pre_review_runs.py, test_rf182_guardrails.py |
| RF-183 | M | B | Evaluación continua de agentes: conjuntos dorados versionados y pruebas automáticas (DeepEval / promptfoo e… | ✅ Implementado | Evaluación continua de agentes con sets dorados en CI (RNF-060). | ml/agents_eval, backend/tests/unit/test_rnf060_agent_eval_gates.py |
| RF-190 | M | W/B | Carga de documentos (PDF, DOCX, HTML): regulaciones ARCERNNR, manuales de Homologación UP/UC, especificacio… | ✖ Excluido por decisión | Carga de documentos para RAG: excluido en v1 por ADR-007; los límites viven en `regulatory_parameter`. | — |
| RF-191 | M | B | Segmentación respetando la estructura (artículo, numeral, tabla) y embeddings multilingües bge-m3 (MIT) den… | ✖ Excluido por decisión | Segmentación y embeddings: ADR-007. | — |
| RF-192 | M | B | Búsqueda híbrida (vectorial + léxica) filtrada por vigencia a la fecha del evento y reordenamiento (*rerank… | ✖ Excluido por decisión | Búsqueda híbrida: ADR-007. | — |
| RF-193 | M | W | Administración: versionar, retirar y marcar documentos como sustituidos (p. ej., ARCERNNR-006/20 sustituida… | ✖ Excluido por decisión | Administración de documentos RAG: ADR-007 (la vigencia de parámetros regulatorios sí está, RF-150). | — |
| RF-200 | M | B | Pasarela de modelos compatible con la API de OpenAI (p. ej., LiteLLM, MIT, o un proxy propio) delante de lo… | ✅ Implementado |  | test_m19_model_gateway.py |
| RF-201 | M | B | Salida estructurada en el servidor: toda llamada que espere JSON usa decodificación restringida (XGrammar e… | ✅ Implementado |  | test_m19_model_gateway.py |
| RF-202 | M | B | Planificador de GPU y colas: colas con prioridad (interactiva > pre-revisión > re-transcripción > pre-etiqu… | ✅ Implementado |  | test_m19_model_gateway.py |
| RF-203 | M | B | Carga y descarga de modelos bajo demanda para no exceder la VRAM del perfil (p. ej., en 16 GB no coexisten … | ✅ Implementado |  | test_m19_model_gateway.py |
| RF-204 | M | B | Degradación por perfil: si una función no cabe en el hardware (o el servicio de modelos está caído), la tar… | ✅ Implementado |  | ReviewScreen.test.tsx, decision.test.ts, test_m17_pre_review.py, test_m19_model_gateway.py |
| RF-205 | M | B | Métricas de inferencia: latencia, tokens/s, uso de VRAM y RAM, tamaño de colas y errores, en el tablero de … | ✅ Implementado |  | test_m19_model_gateway.py |
| RF-310 | M | W/B | Planificadores múltiples con ámbito | ✅ Implementado |  | test_rf320_assignment.py |
| RF-311 | M | B | Bloqueo optimista por OT entre planificadores | ✅ Implementado |  | test_rf104_dispatch.py, test_rf320_assignment.py |
| RF-312 | M | W/B | Dueño explícito de la OT y bitácora de traspasos | ✅ Implementado |  | test_rf047_times_findings_owner.py |
| RF-313 | S | W | Tablero de carga compartido | ✅ Implementado | Tablero de carga compartido (`crew_workload`), ahora con ámbito RF-002. | test_rf320_assignment.py, test_rf002_ambito_writes.py |
| RF-320 | M | W/B/A | Asignación a cuadrilla, funcionario y dispositivos | ✅ Implementado |  | DispatchBoard.test.tsx, test_rf320_assignment.py, test_rf320_crew_device_and_withdrawals.py |
| RF-321 | M | W/B/A | Reasignación en caliente con motivo | ✅ Implementado |  | ConflictResolverTest.kt, WithdrawalsTest.kt, test_rf320_crew_device_and_withdrawals.py |
| RF-322 | M | A/B | Reasignación sin pérdida de datos capturados offline | ✅ Implementado |  | ConflictResolverTest.kt, OutboxTest.kt, WithdrawalsTest.kt, test_rf101_sync_contract.py |
| RF-323 | S | A | Traspaso directo entre dispositivos sin servidor | ⛔ Bloqueado (SDK Android) | Traspaso por QR sin servidor: requiere cámara, NFC/BT o Wi-Fi Direct en Android. | — |
| RF-324 | M | B/W | Historial de custodia de la OT | ✅ Implementado |  | test_rf104_dispatch.py, test_rf320_assignment.py |
| RF-330 | M | A/W | Español de Ecuador y Latinoamérica únicamente | ✅ Implementado | es-EC con es-419 de respaldo en la web y en el léxico de voz; sin español peninsular. | test_rf147_living_vocabulary.py, test_rf140_voice_flow.py |
| RF-331 | M | B/A | Léxico y *hotwords* derivados de los dominios del perfil | ✅ Implementado |  | test_rf140_extraction.py, test_rf140_voice_flow.py, test_rf331_lexicon.py, test_rf331_normalizer.py |
| RF-332 | S | A | *Hotwords* por contexto de OT | 🟡 Parcial | Las hotwords por OT se generan en el servidor; el ASR del teléfono está diferido. | test_rf332_grammar.py |
| RF-300 | M | B | Asset Model Descriptor canónico, independiente del GIS | ✅ Implementado |  | test_rf300_asset_model.py |
| RF-301 | M | B/W | Perfil de mapeo por instalación; nueva Unidad de Negocio sin programar | ✅ Implementado |  | ModelProfileScreen.test.tsx, decisions.test.ts, test_rf301_assisted_matching.py, test_rf301_profile_importer.py |
| RF-302 | M | W/B | Importador de metadatos ArcGIS con coincidencia asistida y diagnóstico | ✅ Implementado |  | ModelProfileScreen.test.tsx, test_rf301_assisted_matching.py, test_rf301_profile_importer.py, test_rf302_metadata_diagnostic.py |
| RF-303 | M | B/W | Generación de JSON Schema + UI Schema desde metadatos, con aprobación humana | ✅ Implementado |  | test_rf303_form_generation.py |
| RF-304 | M | B | Refresco automático de dominios volátiles por Unidad de Negocio | ✅ Implementado |  | ModelProfileScreen.test.tsx, conftest.py, test_rf032_form_versioning.py, test_rf034_catalogs.py |
| RF-305 | M | B | Prohibición verificada en CI de nombres del modelo real en el código | ✅ Implementado |  | conftest.py, test_rf301_assisted_matching.py, test_rf301_profile_resolution.py |
| RF-340 | M | B | Conector ArcGIS 10.8.1: réplica de bajada incremental por zona | ✅ Implementado | Réplica de bajada incremental por zona desde los feature services. | backend/tests/integration (conector ArcGIS) y tools/arcgis-mock |
| RF-341 | M | B | Ruta de escritura derivada de metadatos; conectividad nunca escrita | ✅ Implementado | Ruta de escritura derivada de metadatos; la conectividad nunca se escribe (verificado en CI). | scripts/check_data_model_leak.py, gis-agent/tests/test_guards.py |
| RF-342 | M | B | Staging de propuestas as-built con idempotencia y trazabilidad | ✅ Implementado |  | test_rf110_review_api.py |
| RF-343 | M | W | Bandeja de revisión GIS y aprobación por lotes | ✅ Implementado | Bandeja de revisión GIS y aprobación por lotes en la web. | web/src/features/review, test de staging I6 |
| RF-344 | M | B/W | Exportación del lote aprobado para aplicación en ArcMap/ArcFM | ✅ Implementado | Exportación del lote aprobado para el agente arcpy. | gis-agent/tests/test_apply_batch.py |
| RF-345 | C | B | Escritura directa opcional por clase, apagada por defecto | ✅ Implementado |  | test_rf301_assisted_matching.py |
| RF-350 | S | B/W | Controles de calidad del SIG configurables sobre el AMD | ✅ Implementado |  | test_rf110_review_api.py, test_rf150_parameter_authorship.py, test_rf350_compliance.py, test_rf350_regulatory_seed.py |
| RF-351 | M | W/B/A | Trabajos de verificación en campo desde revisiones SIG | ✅ Implementado |  | test_rf350_compliance.py |
| RF-360 | M | B/A | Paquetes offline por zona con PMTiles, firmados y verificables | ✅ Implementado |  | DispatchBoard.test.tsx, readiness.test.ts, test_rf101_sync_contract.py, test_rf104_dispatch.py |
| RF-346 | M | Agente | Agente arcpy como único componente que toca la geodatabase, en ambos sentidos | ✅ Implementado | El agente arcpy es el único que toca la geodatabase (ADR-008). Probado contra el doble de arcpy; falta la prueba con ArcMap real. | gis-agent/tests/ |
| RF-347 | M | Agente | Aplicación de lotes por staging fuera de la red + `Append` + reconstrucción de conectividad | ✅ Implementado |  | test_apply_batch.py, test_guards.py |
| RF-348 | M | Agente | El agente nunca usa `InsertCursor` en clases de la red, nunca escribe conectividad y nunca toca COM ni desa… | ✅ Implementado |  | test_apply_batch.py, test_guards.py |
| RF-349 | M | Agente | Exportación de metadatos con `ListDomains` y `Describe`, incluidos subtipos y relaciones | ✅ Implementado |  | test_rf349_metadata_ingest.py |
| RF-352 | S | Agente | Extracción incremental de activos por zona usando los campos de fecha de modificación del modelo | ✅ Implementado | Extracción incremental por campos de fecha del perfil. | gis-agent/tests/ |
| RF-353 | M | Agente/B | Reporte del resultado por propuesta (aplicada, rechazada, error) e idempotencia por `proposal_id` | ✅ Implementado |  | test_apply_batch.py, test_rf110_review_api.py, test_rf349_metadata_ingest.py |

## Qué falta, en una lista

1. **La app Android** (pantallas Compose, CameraX, mapa MapLibre, Room + SQLCipher, BiometricPrompt,
   WorkManager, traspaso por QR). Bloqueada por red: permitir `dl.google.com` en el entorno o
   compilarla donde haya SDK. Todas sus decisiones ya están en `core:sync` y `core:field`.
2. **IA y MLOps** (voz en el teléfono, visión, resúmenes, agentes VLM/priorizador/MCP, datasets,
   MLflow, OTA de modelos): diferidos por decisión del usuario; los núcleos deterministas del
   servidor (gramática, normalización, catálogos, guardrails, compuertas RNF-060) sí están.
3. **Validación con ArcMap real** (RF-346 y siguientes): el agente se prueba contra el doble de arcpy;
   falta un ensayo en la máquina Windows con ArcMap 10.8.1 + ArcFM.
4. **Excluidos a propósito**: RAG en v1 (ADR-007), editor visual de formularios (RF-031) y analítica
   predictiva «v2» (RF-135).
