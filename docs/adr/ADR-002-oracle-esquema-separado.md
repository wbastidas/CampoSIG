# ADR-002 — La plataforma vive en Oracle, en un esquema separado del SDE

| Campo | Valor |
|---|---|
| Estado | **Sustituida por [ADR-006](ADR-006-postgresql-servidor-aparte.md)** |
| Fecha | 2026-09-21 |
| Decide | Motor y ubicación de la base de datos operativa |
| Corrige | SRS sección 7.2 (PostgreSQL 16 + PostGIS + pgvector) |

> **Nota de sustitución (2026-09-21).** Esta decisión se tomó asumiendo un Oracle moderno con la opción
> Spatial disponible. Al confirmarse que el motor es **Oracle 11g R2 sin Spatial**, sus dos premisas
> resultaron falsas: `SDO_GEOMETRY` no está garantizado y 11g R2 no tiene soporte JSON ni recibe parches
> de seguridad desde 2020. Se revierte en **ADR-006**. Se conserva este registro porque el razonamiento
> —aprovechar licencias, DBA y respaldos existentes— sigue siendo válido y es el que habría que retomar
> si la distribuidora migra la geodatabase a 19c o posterior.

## Contexto

El SRS especificaba PostgreSQL con PostGIS y pgvector. La distribuidora tiene Oracle, con DBA,
licencias, respaldos y procedimientos ya establecidos, y ese mismo Oracle aloja la geodatabase SDE
de ArcGIS. Operar un segundo motor añadiría carga sin beneficio proporcional.

## Decisión

La base operativa de la plataforma (OT, formularios, respuestas, evidencias, colas de sync, caché de
red, staging, auditoría) vive en **Oracle, en un esquema propio (`SIGEC`) separado del esquema SDE**.

- Lo geoespacial usa **`SDO_GEOMETRY`**. Oracle Spatial está incluido sin costo adicional en todas
  las ediciones desde 19c, así que no hay licencia extra que justificar.
- Acceso con SQLAlchemy 2.0 + `oracledb` en modo *thin* (sin cliente Oracle nativo), migraciones con
  Alembic.
- El esquema `SIGEC` **nunca** escribe en las tablas del SDE. Toda interacción con la geodatabase pasa
  por los feature services de ArcGIS (ADR-001 y ADR-003), no por SQL directo.

## Consecuencias

**A favor:** un solo motor que operar; aprovecha DBA, respaldos y monitoreo existentes; sin licencia
adicional para lo espacial.

**En contra:**

1. Se pierde `pgvector`. El RAG necesita otro almacén — ver ADR-005.
2. Se pierde Martin como generador de teselas vectoriales desde PostGIS. Se sustituye por
   `tippecanoe` → PMTiles (addendum 5.4).
3. JSONB de PostgreSQL se sustituye por JSON de Oracle. En 19c conviene validar el rendimiento de
   las respuestas de formulario; en 21c y superiores el tipo `JSON` nativo es mejor opción.
4. El entorno de desarrollo necesita Oracle Free en Docker, más pesado que PostgreSQL.

## Pendiente

Decisión **D1**: versión y edición exactas de Oracle. Determina el tipo JSON disponible, el
particionado y, sobre todo, si el vector store es nativo (23ai) o externo.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Oracle para GIS + PostgreSQL para la plataforma | Mantiene pgvector y PostGIS, pero obliga a operar dos motores y duplica respaldos, monitoreo y experiencia del DBA |
| Oracle sin Oracle Spatial, geometría como texto | Innecesario: Spatial no cuesta extra desde 19c, y perder consultas espaciales propias encarecería el conector y los paquetes offline |
