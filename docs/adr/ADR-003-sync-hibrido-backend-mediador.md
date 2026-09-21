# ADR-003 — Sync híbrido: el móvil habla solo con nuestro backend

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-09-21 |
| Decide | Stack de mapa y sincronización del cliente Android |

## Contexto

La app móvil es Android nativo en Kotlin (R3 del SRS) y debe funcionar completamente offline (R5).
Hay dos formas de llegar a los datos de ArcGIS desde el teléfono:

1. **ArcGIS Maps SDK for Kotlin.** Sincroniza con feature services de ArcGIS Enterprise 10.2.2 o
   posterior, así que 10.8.1 califica. Trae mobile geodatabase, áreas offline, adjuntos y registros
   relacionados: es lo que usa Field Maps. Pero es propietario y **exige licencia Esri de nivel
   Standard por dispositivo** para editar y sincronizar offline, lo que choca con la política de
   licencias del SRS (sección 0.7) y añade costo por técnico.
2. **Implementar el sync ArcGIS nosotros mismos**, en el móvil, con MapLibre para el mapa.
   Open source, pero pone la pieza de mayor riesgo técnico del proyecto dentro del cliente, donde
   depurar y corregir es más lento y cada arreglo exige una nueva versión del APK.

## Decisión

Un tercer camino: **el móvil no conoce ArcGIS**.

- El **móvil** habla únicamente con nuestra API. Usa MapLibre Native + PMTiles para el mapa y
  Room + SQLCipher como fuente de verdad local. Su contrato de sync es el del SRS (RF-101 a RF-106):
  outbox idempotente, delta sync, subida por prioridad y resumible.
- El **backend** es el único que habla ArcGIS: mantiene la réplica de bajada
  (`createReplica` / `synchronizeReplica`), sincroniza metadatos, construye los paquetes offline por
  zona y gestiona el staging de subida.

## Consecuencias

**A favor:**

- El móvil queda 100 % open source y sin licencia Esri por dispositivo.
- Toda la complejidad y el riesgo de ArcGIS se concentran en un servicio del backend, donde se
  corrige y se despliega sin pasar por la tienda de aplicaciones.
- El contrato móvil↔backend es estable: migrar a Utility Network o incluso a otro GIS no obliga a
  tocar la app.
- Un solo punto que hablar ArcGIS simplifica auditoría, límites de tasa y caché.

**En contra:**

- El backend es indispensable para preparar datos; el móvil no puede sincronizar con el GIS por su
  cuenta. Aceptable: el móvil ya depende del backend para OT, formularios y modelos.
- Hay que construir el constructor de paquetes offline, que el SDK de Esri habría dado hecho. Es el
  costo real de esta decisión y está presupuestado en I4.
- Perdemos funciones listas del SDK (mobile geodatabase, edición de relacionados). Se reemplazan con
  el motor de formularios propio, que de todos modos hacía falta por la IA on-device.

## Alternativas descartadas

Ambas están arriba, en Contexto. La primera se descarta por licencia y costo por dispositivo; la
segunda, por concentrar el mayor riesgo del proyecto en el componente más difícil de corregir.
