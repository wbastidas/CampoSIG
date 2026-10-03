# ADR-006 — PostgreSQL en servidor aparte; Oracle 11g R2 dedicado a la geodatabase

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-09-21 |
| Decide | Motor y ubicación de la base de datos operativa de la plataforma |
| Sustituye a | [ADR-002](ADR-002-oracle-esquema-separado.md) |
| Confirma | SRS sección 7.2 (PostgreSQL 16 + PostGIS), que ADR-002 había corregido por error |

## Contexto

ADR-002 movió la base operativa a Oracle para aprovechar licencias, DBA y respaldos existentes. Al
conocerse las características reales del motor, esa decisión dejó de sostenerse:

- El motor es **Oracle 11g R2** y **no tiene la opción Spatial** contratada.
- El **Soporte Extendido de 11.2.0.4 terminó en diciembre de 2020**. Desde entonces está en Sustaining
  Support: sin parches de seguridad nuevos.
- **11g R2 no tiene soporte JSON alguno.** El tipo `JSON` nativo llega en 21c y la validación `IS JSON`
  en 12c. Las respuestas de formulario son JSON por diseño (regla 0.4 del SRS): en 11g R2 quedarían como
  `CLOB` sin poder indexarse ni consultarse por campo, que es precisamente lo que el sistema necesita
  hacer con ellas.
- **`python-oracledb` en modo *thin* exige Oracle Database 12.1 o posterior.** Para 11.2 hace falta modo
  *thick* con librerías de Oracle Instant Client dentro de cada contenedor.
- Sin Spatial, `SDO_GEOMETRY` no está garantizado. (Existe **Oracle Locator**, incluido de serie, que sí
  lo provee; pero depender de ello añade una verificación y una discusión de licenciamiento que la
  arquitectura no necesita tener.)

El cliente ofreció explícitamente provisionar otra base en un servidor aparte si hacía falta.

## Decisión

Se separan los dos papeles, que nunca debieron confundirse:

**Oracle 11g R2 queda dedicado a la geodatabase ArcSDE.** Sigue haciendo exactamente lo que ya hace. La
plataforma:

- **no crea ni un objeto** en ese motor;
- **no se conecta por SQL**, así que no necesita driver Oracle ni Instant Client;
- lo consume **solo a través de los feature services de ArcGIS 10.8.1** (ADR-001 y ADR-003).

**La plataforma vive en PostgreSQL 16 + PostGIS, en un servidor aparte.** OT, formularios, respuestas,
evidencias, colas de sync, caché de red, staging as-built, auditoría y parámetros regulatorios.

## Consecuencias

**A favor:**

- Se recupera el stack del SRS sin desviaciones: PostGIS para lo espacial, **JSONB con índices GIN** para
  las respuestas de formulario, y Martin vuelve a estar disponible para las teselas vivas de la web.
- **No se amplía la superficie expuesta de un motor sin parches de seguridad.** Es el beneficio más
  importante y el menos visible: cada tabla nueva en 11g R2 habría sido deuda de seguridad.
- El backend queda sin dependencias nativas: `httpx` para ArcGIS, `psycopg` para PostgreSQL. Contenedores
  limpios y reproducibles.
- **Desacopla el proyecto de la migración del GIS.** Cuando la distribuidora migre la geodatabase a 19c
  o a lo que exija ArcGIS Pro, la plataforma no se entera: su contrato es el feature service.
- El equipo de base de datos de la distribuidora no adquiere trabajo nuevo sobre su Oracle de producción.

**En contra:**

- Un servidor y un motor más que operar, respaldar y monitorear. Es el costo real de esta decisión, y el
  cliente ya lo aceptó al ofrecer el servidor.
- El DBA de Oracle no cubre PostgreSQL. Hay que definir quién lo administra (decisión **D10**).
- Dos motores que correlacionar al depurar un problema de datos. Se mitiga con el `proposal_id` y el
  `GLOBALID` que ya viajan en cada propuesta as-built (addendum 5.3), que dan la traza de punta a punta.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Esquema propio en el Oracle 11g R2 existente | Sin JSON útil, sin garantía de tipo espacial, con driver en modo *thick*, y añadiendo datos a un motor sin parches de seguridad desde 2020 |
| Oracle 11g R2 con geometría en texto y JSON en `CLOB` | Técnicamente posible y funcionalmente pobre: sin consultas espaciales ni por campo de formulario, habría que subir a la aplicación trabajo que la base debe hacer |
| Pedir que se actualice Oracle a 19c para alojar la plataforma | Es una migración de la geodatabase corporativa: alcance, riesgo y plazo desproporcionados frente a provisionar un PostgreSQL. Vale la pena por otras razones (R-N7), pero no debe bloquear este proyecto |
| SQLite o DuckDB en el servidor | No sostienen concurrencia de varios planificadores ni el volumen de evidencias previsto |
