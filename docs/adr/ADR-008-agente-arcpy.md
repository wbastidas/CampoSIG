# ADR-008 — Un agente arcpy es el único componente que toca la geodatabase

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-09-21 |
| Decide | Cómo lee y escribe la plataforma en la geodatabase ArcSDE |
| Refina a | [ADR-001](ADR-001-ruta-escritura-gis-staging-arcfm.md) y [ADR-003](ADR-003-sync-hibrido-backend-mediador.md) |

## Contexto

ADR-001 y ADR-003 asumían que toda la conversación con el GIS pasaría por los feature services REST de
ArcGIS 10.8.1, y que la aplicación del lote as-built la haría una persona en ArcMap/ArcFM. El cliente
indicó que la sincronización se haga **con Python y arcpy**, no con ArcObjects, y que él se ocupa de
ArcFM.

Eso obliga a mirar de frente cuatro hechos verificados sobre arcpy y las redes geométricas:

1. **Las redes geométricas son de solo lectura en ArcGIS Pro.** Para editarlas hay que usar ArcMap. Por
   tanto el arcpy utilizable es el de ArcMap 10.8.1, que corre sobre **Python 2.7.18 con NumPy 1.9.3**,
   no el arcpy de Pro (Python 3).
2. **`arcpy.da.InsertCursor` falla** al insertar en una clase que participa en una red geométrica: devuelve
   `SystemError('error return without exception set')`. El camino soportado es insertar en una clase
   **fuera** de la red y luego usar **`Append_management`**.
3. **`Append_management` sobre clases de red ha provocado estados inconsistentes** de la red lógica
   (referencias liberadas antes de `stopEditing`). Hay parches de Esri que lo previenen y que mejoran las
   herramientas de verificar, reparar y reconstruir conectividad.
4. **Los auto-actualizadores de ArcFM son ArcObjects/COM.** Desde Python solo se pueden *controlar* por
   COM (`Miner.Framework.Dispatch.MMAutoupdaterDispatch`, `mmAUMNoEvents`) — lo que confirma que con
   arcpy puro **no se disparan**. La práctica habitual del sector es incluso desactivarlos a propósito
   para actualizaciones masivas.

Hay además una consecuencia que no era evidente: **si arcpy está disponible, los feature services con
sync dejan de ser obligatorios para leer.** `arcpy.da.SearchCursor` lee directamente de ArcSDE, y
`arcpy.da.ListDomains` y `arcpy.Describe` dan metadatos más ricos que los que expone el servicio REST.
Eso elimina del camino crítico el prerrequisito más intrusivo del proyecto: habilitar Global IDs,
archiving y versionado sobre la geodatabase de producción (riesgo R-N2, decisión D5).

## Decisión

Se crea **`sigec-gis-agent`**: un proceso pequeño, en Python 2.7 con el arcpy de ArcMap 10.8.1, que corre
en una máquina Windows con ArcGIS Desktop licenciado, y que es **el único componente de todo el sistema
que toca la geodatabase**. Habla con el backend por HTTPS con token; el backend nunca habla con Oracle ni
con ArcSDE.

**Bajada (geodatabase → plataforma):**

| Qué | Cómo |
|---|---|
| Metadatos | `arcpy.da.ListDomains`, `arcpy.Describe` sobre subtipos y *relationship classes* → JSON → sube al backend. Alimenta el perfil de mapeo y los formularios (RF-302, RF-303) |
| Dominios volátiles por Unidad de Negocio | Los tres de `01_Dominios.md`, en cada corrida (RF-304) |
| Activos por zona | `arcpy.da.SearchCursor` con filtro espacial y por alimentador → GeoJSON → sube al backend |
| Incremental | Por los campos de fecha de modificación que el modelo ya tiene (categoría 🔧 Sistema). Si una clase no los tiene, extracción completa de esa clase |

**Subida (plataforma → geodatabase), por lotes aprobados:**

1. Descarga del backend el lote de propuestas as-built aprobadas (RF-342, RF-343).
2. Escribe las filas en una **clase de staging fuera de la red geométrica**, con `da.InsertCursor`.
3. Dentro de un `arcpy.da.Editor` sobre la conexión SDE versionada, aplica con **`Append_management`**.
4. Ejecuta **verificar y reconstruir conectividad** en la extensión afectada.
5. Reporta al backend el resultado de **cada** propuesta: aplicada, rechazada o con error, con el mensaje.

**Invariantes del agente**, verificadas con tests:

- **Nunca escribe** campos de conectividad (`ANCILLARYROLE`, `*CIRCUITSOURCEGUID`, `ENABLED`,
  `ELECTRICTRACEWEIGHT`). Se mantiene la regla de ADR-001 sin excepción.
- **Nunca usa `InsertCursor` directo** sobre una clase de la red geométrica: siempre staging + `Append`.
- **Nunca desactiva los auto-actualizadores de ArcFM.** El agente no toca COM ni ArcObjects.
- **Escribe solo los campos del proceso** (decisión D11, resuelta): los que el perfil mapea, que por
  construcción son los que el formulario de campo produce. Los campos calculados por auto-actualizadores
  de ArcFM están **fuera de su alcance por decisión**, no por limitación: los recalcula ArcFM o un trace
  en el flujo del equipo GIS. Ver addendum 5.5.
- **Idempotente por `proposal_id`**: reprocesar un lote no duplica nada.
- Toda corrida deja bitácora con el detalle por propuesta.

## Consecuencias

**A favor:**

- **Saca del camino crítico la habilitación de Global IDs, archiving y versionado** sobre la geodatabase
  de producción. Era el riesgo R-N2 y la decisión D5; ahora son opcionales, no prerrequisitos.
- Metadatos más ricos que por REST: `ListDomains` y `Describe` dan subtipos y relaciones completos, que
  es justo lo que la capa de abstracción necesita (ADR-004).
- Una sola frontera con el GIS, y muy estrecha: el resto del sistema no sabe que ArcSDE existe.
- Automatiza la parte mecánica de la aplicación del lote sin tocar las reglas de negocio de ArcFM.
- El backend sigue en Python 3.12 y sin dependencias nativas: el agente está al otro lado de HTTPS.

**En contra, y conviene no minimizarlo:**

- **Python 2.7, fin de vida desde enero de 2020.** Es inevitable: es el único arcpy que edita redes
  geométricas. Se mitiga manteniendo el agente deliberadamente pequeño, sin dependencias fuera de la
  biblioteca estándar más `requests`, y sin exponerlo a internet: solo habla hacia el backend.
- **Una máquina Windows con ArcGIS Desktop licenciado.** Confirmado disponible en nivel **Advanced**
  (D2, resuelta), que cubre la edición de redes geométricas; el nivel Basic no la permite. Queda por
  definir qué máquina aloja el proceso desatendido.
- **Los auto-actualizadores de ArcFM siguen sin dispararse**, y eso quedó resuelto como límite de
  alcance: el agente escribe los campos del proceso y el resto no es su responsabilidad (D11). Eso
  convierte lo que era el riesgo R-N11 en una frontera documentada.
- Hay que verificar que la instalación tenga los parches de Esri para `Append` sobre redes geométricas, y
  reconstruir conectividad tras cada lote.
- Dos lenguajes y dos versiones de Python en el proyecto. Se acota con un contrato HTTP estrecho y
  versionado entre agente y backend.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| ArcObjects (.NET o COM) | Es lo único que dispararía los auto-actualizadores de ArcFM, pero el cliente lo descartó expresamente y además ataría el proyecto a un SDK propietario y a una tecnología en retirada |
| Solo feature services REST | Sigue siendo válido y se mantiene como opción, pero exige habilitar Global IDs, archiving y versionado en producción antes de poder leer nada. Con arcpy disponible, ese costo ya no se justifica como prerrequisito |
| arcpy de ArcGIS Pro (Python 3) | Las redes geométricas son de solo lectura en Pro. No puede aplicar los lotes |
| `InsertCursor` directo sobre las clases de red | Falla con `SystemError`. No es una opción |
| Agente en Python 3 llamando a arcpy 2.7 por subproceso | Añade una capa de serialización frágil para no ganar nada: el proceso que hace el trabajo sigue siendo Python 2.7 |
