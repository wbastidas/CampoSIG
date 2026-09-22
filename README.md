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

Construido y ejecutado: I0, I2, I3, I5, I6, I7 y la parte de I11 que no necesita modelos, más el
despliegue a cuadrillas. El detalle por incremento está en
[`docs/PLAN_IMPLEMENTACION.md`](docs/PLAN_IMPLEMENTACION.md).

| Módulo | Qué es | Pruebas |
|---|---|---|
| `backend/app/model_profile/` | La única parte del código que conoce nombres reales, a través del perfil (ADR-004) | |
| `backend/app/forms/` | Formularios generados de los metadatos y compuestos de bloques; nunca codificados | |
| `backend/app/workorders/`, `sync/`, `dispatch/` | OT, contrato de sincronización y tablero de despliegue | |
| `backend/app/responses/`, `review/`, `gis_gateway/` | Captura, evidencias, revisión y *staging* as-built hacia el GIS | |
| [`backend/app/voice/`](backend/app/voice/README.md) | Voz → formulario: normalizador es-EC, léxico, gramática GBNF | |
| [`backend/app/vision/`](backend/app/vision/README.md) | Taxonomía, prellenado y comparador antes/después | |
| `backend/app/regulatory/` | Parámetros con vigencia y reglas de cumplimiento deterministas (ADR-007) | |
| `backend/app/integrations/` | Outbox transaccional y adaptadores de OT y call center (ADR-012) | |
| `backend/app/auth/` | Identidad verificada contra Keycloak; ninguna ruta abierta (ADR-013) | |
| `android/core/sync/` | Motor de sincronización offline, Kotlin puro sin Android (ADR-010) | 52 |
| `gis-agent/` | Agente arcpy, Python 2.7, el único que toca el GIS (ADR-008) | 44 |
| `web/src/features/` | Asignación gráfica, tablero de despliegue, integraciones y revisión | 85 |

El backend suma **622 tests** que corren contra PostgreSQL 16 + PostGIS real y **bajo los dos
perfiles de modelo de datos**, que es la forma de comprobar que la independencia del modelo no es
una aspiración. Las integraciones se prueban **contra los simuladores de verdad**, levantados
dentro del propio test.

Lo que todavía no se ha ejecutado: la app Android (falta el SDK), el agente contra un ArcMap real
(falta la máquina) y los modelos de voz y visión (faltan los pesos y las fotos del piloto).

Y una advertencia que no es técnica: los valores de `seeds/regulatory-ec.yaml` están marcados
**sin verificar** a propósito. Son la estructura y la referencia a la norma, no la cifra
confirmada. Antes del piloto hay que abrir las resoluciones vigentes y cargarlos con el nombre de
quien las leyó.

Antes de escribir código conviene leer [`CLAUDE.md`](CLAUDE.md), en particular las reglas 4, 5 y 6:
no filtrar nombres del modelo de datos al código, no escribir campos de conectividad, y mantener el
móvil ajeno a ArcGIS.
