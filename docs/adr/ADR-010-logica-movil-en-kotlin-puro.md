# ADR-010 — La lógica de riesgo del móvil vive en Kotlin puro, sin Android

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-09-21 |
| Decide | Dónde vive la lógica de sincronización offline y conflictos de la app |
| Se apoya en | [ADR-003](ADR-003-sync-hibrido-backend-mediador.md) |

## Contexto

El propio registro de riesgos de este proyecto marca el motor de sync como **el componente de
mayor riesgo técnico** (R-N6). Y con razón: un técnico puede pasar el día en una zona sin
señal, y todo lo que registró existe **únicamente en su teléfono** hasta que llega al
servidor. Un defecto ahí no produce un error visible: produce trabajo perdido.

Un módulo Android convencional pone esa lógica junto a Room, WorkManager y Compose. Eso la
vuelve comprobable solo con un dispositivo o un emulador, es decir: despacio, con dificultad,
y en la práctica poco.

## Decisión

La lógica de decisión del móvil vive en **`core:sync`, un módulo Kotlin/JVM sin una sola
dependencia de Android**. Contiene:

- el **outbox**: qué enviar a continuación, en qué orden, con qué presupuesto de transferencia;
- la **política de reintentos**: retroceso exponencial con tope y *jitter*;
- la **resolución de conflictos**: quién manda sobre qué cuando el dispositivo y el servidor
  discrepan;
- la **compuerta de liberación**: cuándo una OT puede dejar un dispositivo (RF-322).

Es estado inmutable con transiciones puras. El sync corre desde un *worker* que el sistema
puede matar en cualquier momento, así que cada cambio produce un estado nuevo que quien llama
persiste de forma atómica: no hay mutación a medio aplicar de la que recuperarse.

La capa Android —Room + SQLCipher, WorkManager, CameraX, MapLibre Native, Compose— **envuelve**
este módulo. No contiene decisiones.

## Consecuencias

**A favor:**

- La lógica más riesgosa del proyecto se prueba en la JVM, exhaustivamente, sin dispositivo ni
  servidor. Son 52 tests que corren en segundos, incluida una matriz completa de conflictos que
  verifica que **ninguna** combinación descarta lo capturado.
- Los tests corren en CI sin SDK de Android, que además es el único camino disponible mientras
  no haya una máquina con el SDK instalado.
- Las invariantes se pueden afirmar en negativo: rompiendo a propósito la promesa de no
  descartar datos, el test correspondiente falla. Verificado.
- El módulo no depende de la versión de Android ni de la del SDK, así que sobrevive a
  actualizaciones que sí obligan a tocar la capa de UI.

**En contra:**

- Dos módulos en lugar de uno, con una frontera que hay que respetar. La regla es simple: si
  toma una decisión, va en `core:sync`; si toca hardware, base local o pantalla, va en la capa
  Android.
- La integración entre ambos —que Room persista de verdad el estado que el outbox devuelve—
  necesita pruebas instrumentadas en dispositivo, que siguen siendo imprescindibles. Este ADR
  reduce lo que hay que probar en dispositivo, no lo elimina.
- `core:sync` no puede usar tipos de Android que serían cómodos (`Uri`, `Context`). Es el
  precio, y es bajo: usa cadenas y datos.

## Nota sobre el estado de verificación

En el entorno donde se construyó esto hay **JDK 21 y Gradle 8.14, pero no SDK de Android**. Por
tanto: `core:sync` está **compilado y con sus 52 tests ejecutados**; la capa Android está
especificada pero **no compilada**. Conviene tenerlo presente al revisar: lo que está probado
es la lógica, no la app.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Lógica en clases Android, probada con Robolectric | Robolectric simula el marco de trabajo pero es lento y no siempre fiel. Para la pieza de mayor riesgo del proyecto, conviene que sus pruebas no dependan de una simulación |
| Lógica solo en pruebas instrumentadas | Correctas y lentas. Nadie las ejecuta con la frecuencia que esta lógica merece, y una matriz de conflictos de 120 casos sería impracticable |
| Compartir la lógica con la web vía Kotlin Multiplatform | Atractivo y prematuro. La web no sincroniza offline, así que no hay nada que compartir todavía. `core:sync` no usa nada específico de JVM, de modo que la puerta queda abierta |
