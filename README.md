# SIGEC-Campo

Plataforma de gestión de trabajos de campo para una distribuidora eléctrica ecuatoriana, inspirada en
ArcGIS Field Maps e integrada con ArcGIS Enterprise 10.8.1 + ArcFM sobre ArcSDE en Oracle 11g R2.

- **Web** (React + TypeScript) para planificadores, supervisores, editores GIS y administradores.
- **Android nativo** (Kotlin/Compose) para técnicos y cuadrillas, con operación completamente offline
  e IA on-device: dictado por voz que llena formularios y análisis de fotografías de la red.
- **Backend** Python (FastAPI) sobre PostgreSQL + PostGIS, con capa de agentes de validación.

## Qué la distingue

| | |
|---|---|
| **Independiente del modelo de datos** | Los tipos de activo, catálogos y formularios se derivan de los metadatos del GIS. Cambiar de Unidad de Negocio o de distribuidora es configuración, no programación |
| **Offline de verdad** | Voz, visión, formularios, mapa y cierre de orden funcionan en modo avión. La sincronización es diferida y resumible |
| **Sin ataduras de proveedor** | El móvil no lleva un solo componente propietario: Kotlin nativo, MapLibre, ONNX Runtime y `llama.cpp`, todo con licencia permisiva |
| **La IA propone, el humano dispone** | Todo valor generado por IA se guarda con origen, versión de modelo y confianza, y requiere confirmación |
| **El GIS no se pone en riesgo** | Los cambios de red se proponen y un editor los aplica en ArcFM, donde corren los auto-actualizadores y el trace |

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/SRS.md`](docs/SRS.md) | Especificación de requerimientos (ISO/IEC/IEEE 29148) |
| [`docs/ADDENDUM-01-ArcGIS-FieldMaps-Oracle.md`](docs/ADDENDUM-01-ArcGIS-FieldMaps-Oracle.md) | Análisis de Field Maps, arquitectura de integración con ArcGIS 10.8.1, abstracción del modelo de datos. **Corrige el SRS donde discrepen** |
| [`docs/PLAN_IMPLEMENTACION.md`](docs/PLAN_IMPLEMENTACION.md) | Incrementos I0–I12 con entregables y criterios de aceptación |
| [`docs/adr/`](docs/adr/) | Decisiones de arquitectura |
| [`docs/GUIA_ENTRENAMIENTO_MODELOS.md`](docs/GUIA_ENTRENAMIENTO_MODELOS.md) | Entrenamiento de modelos y aprendizaje continuo |
| [`docs/modelo-datos-cnel/`](docs/modelo-datos-cnel/) | Referencia de la geodatabase eléctrica de CNEL EP |

## Estado

En definición. El código arranca con el incremento I0; ver [`docs/PLAN_IMPLEMENTACION.md`](docs/PLAN_IMPLEMENTACION.md).

Antes de escribir código conviene leer [`CLAUDE.md`](CLAUDE.md), en particular las reglas 4, 5 y 6:
no filtrar nombres del modelo de datos al código, no escribir campos de conectividad, y mantener el
móvil ajeno a ArcGIS.
