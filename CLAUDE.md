# CLAUDE.md — SIGEC-Campo

## Contexto
Plataforma de trabajos de campo para una distribuidora eléctrica ecuatoriana (CNEL EP), inspirada en
ArcGIS Field Maps: backend Python (FastAPI) sobre **PostgreSQL 16 + PostGIS**, web React + TypeScript,
y app Android (Kotlin/Compose) offline con IA on-device (voz→formulario y visión). Integrada con
**ArcGIS Enterprise 10.8.1 + ArcFM** sobre geodatabase ArcSDE en **Oracle 11g R2**.

**El Oracle es solo del GIS.** La plataforma no crea objetos ahí, no se conecta por SQL y no lleva
driver Oracle: consume la geodatabase únicamente por los feature services REST de ArcGIS (ADR-006).

## Documentos fuente (leer antes de programar, en este orden)
1. `docs/SRS.md` — requerimientos (IDs RF-xxx / RNF-xxx). Fuente de verdad general.
2. `docs/ADDENDUM-01-ArcGIS-FieldMaps-Oracle.md` — **corrige y extiende el SRS**. Donde discrepen, manda el addendum.
3. `docs/PLAN_IMPLEMENTACION.md` — incrementos I0–I12. Reemplaza la sección 10.2 del SRS.
4. `docs/adr/` — decisiones de arquitectura vigentes.
5. `docs/GUIA_ENTRENAMIENTO_MODELOS.md` — entrenamiento y MLOps (carpeta `ml/`).
6. `docs/modelo-datos-cnel/` — geodatabase eléctrica de CNEL EP. **Referencia, no destino de código**: sus nombres solo pueden aparecer en `profiles/`.

## Reglas de trabajo
1. Construir por incrementos en el orden de `PLAN_IMPLEMENTACION.md`; no avanzar sin cumplir la Definition of Done.
2. Referenciar el ID de requerimiento en commits, PR y nombres de tests (`test_rf_322_reasignacion_sin_perdida`).
3. Los formularios son datos (JSON Schema + UI Schema en `forms/`), nunca pantallas codificadas. Y se **generan** del perfil de modelo de datos, no se escriben a mano.
4. **Ningún nombre de clase, campo o dominio del modelo CNEL fuera de `profiles/`.** Todo pasa por `model_profile/resolver.py`. Verificado en CI (RF-305).
5. La plataforma **nunca escribe** campos de conectividad de la red geométrica (`ANCILLARYROLE`, `*CIRCUITSOURCEGUID`, `ENABLED`, `ELECTRICTRACEWEIGHT`). Los cambios de red van a staging (ADR-001).
6. El móvil **no conoce ArcGIS**: habla solo con nuestra API (ADR-003). **Prohibido cualquier artefacto `com.esri.*` en el APK** — nada de ArcGIS Maps SDK for Kotlin ni licencias Esri por dispositivo. Verificado en CI.
7. La plataforma **no habla SQL con Oracle**. Nada de `oracledb`, `cx_Oracle` ni Instant Client en el backend (ADR-006).
8. Todo valor de IA se guarda con origen, versión de modelo y confianza, y requiere confirmación humana.
9. Offline primero: probar los flujos móviles en modo avión.
10. Licencias permitidas: MIT, BSD, Apache 2.0, MPL 2.0, LGPL dinámica. Prohibido AGPL/GPL en código propio o en el APK (incluye Ultralytics YOLO). Cero componentes propietarios en el móvil.
11. Código e identificadores en inglés; textos de UI en **español de Ecuador** (i18n), con `es-419` como respaldo. Sin español peninsular.
12. La IA en el móvil se usa detrás de interfaces (`SpeechRecognizer`, `FormExtractor`, `ObjectDetector`, `Summarizer`).
13. En el servidor, los LLM y VLM se consumen solo a través de la pasarela compatible con OpenAI (M19), por alias (`llm-judge`, `vlm-audit`, `asr-server`).
14. Los agentes (LangGraph, M17) solo leen datos mediante herramientas MCP y escriben únicamente su `AgentReport`. Nunca aprueban, cierran ni integran.
15. Todo cambio de prompt, grafo o modelo pasa por las pruebas de `ml/agents_eval` (DeepEval, promptfoo) en CI.
16. **Sin RAG en v1** (ADR-007). Los límites regulatorios viven en `regulatory_parameter` con vigencia y referencia a la norma, y los evalúan reglas deterministas — nunca un LLM, nunca codificados.
17. La IA del servidor debe funcionar en los perfiles A (CPU), B (16 GB) y C (24 GB); lo que no quepa pasa a lote nocturno (RF-204).

## Comandos (completar en I0)
- Entorno de desarrollo: `docker compose -f infra/docker-compose/dev.yml up -d`
- Backend: `cd backend && uv sync && uv run pytest && uv run ruff check .`
- Tests con perfil alterno: `cd backend && SIGEC_PROFILE=alt-synthetic uv run pytest`
- Web: `cd web && pnpm i && pnpm test && pnpm lint && pnpm e2e`
- Android: `cd android && ./gradlew test lint assembleDebug`
- ML: `cd ml && dvc repro`

## Primera tarea
Incremento **I0** de `PLAN_IMPLEMENTACION.md`: monorepo, Docker Compose de desarrollo con PostgreSQL 16
+ PostGIS, Redis, SeaweedFS, Keycloak, `llama.cpp` tras la pasarela de modelos, `tools/arcgis-mock` y
`tools/legacy-ot-mock`; migraciones Alembic con PostGIS y JSONB; y CI con lint, tests y las tres
verificaciones obligatorias: fuga de modelo de datos (RF-305), artefactos `com.esri.*` y licencias.

Antes de I0 hace falta responder **D10** (servidor y administración de PostgreSQL): addendum 10.2.
