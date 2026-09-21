# ADR-001 — Los cambios de red llegan al GIS por staging y revisión en ArcFM

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-09-21 |
| Decide | Ruta de escritura de la plataforma hacia la geodatabase ArcGIS 10.8.1 |

## Contexto

El GIS corporativo es ArcGIS Enterprise 10.8.1 con ArcFM sobre geodatabase SDE en Oracle. El modelo
(`docs/modelo-datos-cnel/`) define la red geométrica `Electrico_RedGeom` con 20 clases participantes,
y la conectividad real se resuelve con `CIRCUITSOURCEGUID` / `PARENTCIRCUITSOURCEGUID`, campos que
mantienen los auto-actualizadores y el trace de ArcFM.

Hechos verificados (detalle en el addendum, sección 5.1):

- Field Maps y los clientes de sync tratan a los feature services con red geométrica como servicios
  simples: **las restricciones de la red se ignoran** al editar. Para llevarlos offline el feature
  dataset debe estar en versionado tradicional.
- La replicación de geodatabase de ArcGIS Pro **no soporta** redes geométricas (error 003131).
- Los **auto-actualizadores y la base de conocimientos de ArcFM no se ejecutan** al editar por REST.
- `PARENTCIRCUITSOURCEGUID` no se llena a mano; lo calcula el trace. Puede quedar huérfano.

Conclusión: la geodatabase puede leerse con seguridad y **no puede escribirse con seguridad** desde
una app de campo.

## Decisión

Las propuestas de cambio de red que produce el campo se materializan en un esquema de **staging**
propio de la plataforma. Un editor GIS las revisa por lotes y las aplica en ArcMap/ArcFM, donde sí
corren los auto-actualizadores, las reglas de conectividad y el trace.

Reglas derivadas:

1. La plataforma **nunca escribe** campos de conectividad (`ANCILLARYROLE`, `*CIRCUITSOURCEGUID`,
   `ENABLED`, `ELECTRICTRACEWEIGHT`), en ninguna ruta.
2. Toda geometría nueva, movida o borrada va a staging, sea cual sea la clase.
3. Toda clase que participe en `Electrico_RedGeom` va a staging.
4. La escritura directa a feature services queda disponible solo para clases fuera de la red
   geométrica y con cambios únicamente de atributos, **apagada por defecto** y habilitable por
   clase tras validación del equipo GIS (RF-345).
5. La ruta de cada clase se deriva de los metadatos del perfil, no de listas en el código.

## Consecuencias

**A favor:** integridad del GIS garantizada; ArcFM sigue siendo la autoridad de las reglas de red;
sobrevive bien a una migración futura a ArcGIS Pro y Utility Network.

**En contra:** introduce un paso humano y un rol nuevo (editor GIS con bandeja de revisión). Es un
posible cuello de botella — riesgo R-N3, mitigado con aprobación por lotes, agrupación por zona y
alimentador, prellenado con IA, y medición del tiempo de ciclo desde el piloto.

## Reparto de responsabilidades (precisado 2026-09-21)

La aplicación del lote **en ArcFM la ejecuta el equipo de la distribuidora**, que es quien conoce sus
auto-actualizadores, su base de conocimientos y sus procedimientos de edición.

Por tanto este proyecto **no construye** un complemento de ArcMap/ArcFM ni automatiza la edición dentro
de ArcFM. Su frontera es entregar el lote aprobado en un formato que el editor pueda consumir
directamente (GeoJSON y CSV de trabajo, con una fila por elemento, su acción, sus atributos y el enlace
a la OT, las fotos y las detecciones que lo sustentan), más la bandeja de revisión que produce ese lote.

Esto reduce el alcance de RF-344 a la exportación y el seguimiento del estado de cada propuesta, y
elimina del plan cualquier desarrollo sobre el SDK de ArcObjects.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Escritura directa a feature services versionados con reconcile/post | Produce datos válidos para la geodatabase e inválidos para ArcFM; omite los auto-actualizadores y deja la conectividad sin recalcular |
| Solo lectura, as-built exportado como reporte | No cierra el ciclo; el GIS quedaría permanentemente desactualizado respecto al campo |
| Híbrido por clase desde el inicio | Es el estado final deseable, pero habilitar rutas directas antes de medir el comportamiento real del GIS es prematuro. Se llega ahí por configuración (RF-345) |
