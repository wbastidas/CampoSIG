# ADR-011 — El dictado produce propuestas con gramática, nunca respuestas

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-09-21 |
| Decide | Cómo se convierte la voz del técnico en valores de formulario |
| Se apoya en | [ADR-004](ADR-004-capa-abstraccion-modelo-datos.md), [ADR-010](ADR-010-logica-movil-en-kotlin-puro.md) |

## Contexto

Llenar un formulario por voz es lo que más tiempo ahorra en campo y lo que más daño hace si
se equivoca. Un técnico con guantes, casco y una escalera no va a leer con cuidado cada campo
que la máquina rellenó; va a mirar que "se ve bien" y firmar. Así que el diseño no puede
apoyarse en que la persona revise: tiene que hacer que un valor equivocado **no llegue** a
parecer correcto.

Tres cosas fallan de verdad en este flujo, y ninguna es "el modelo entiende poco español":

1. **El modelo devuelve algo que no es JSON válido**, o JSON válido con un campo inventado.
2. **El modelo rellena un campo que el técnico no mencionó.** Es el fallo más caro, porque el
   valor inventado suele ser plausible.
3. **El decodificador escucha mal un código.** Un alimentador no es una palabra del español;
   nunca estuvo en los datos de entrenamiento de ningún ASR general.

## Decisión

### 1. La respuesta del extractor está restringida por una gramática GBNF generada

La gramática se genera del sub-esquema del formulario compuesto: tipos, enumeraciones como
alternativas literales de los valores canónicos, y nada más. `llama.cpp` la aplica durante el
muestreo, de modo que "100 % de validez JSON" deja de ser una métrica que se mide y pasa a ser
una propiedad del decodificador.

**Todos los campos están presentes y "no lo dijo" es `null`.** Una gramática sobre un conjunto
variable de miembros en orden arbitrario o se equivoca con las comas o es enorme; y, más
importante, sin un `null` la única respuesta gramatical es un valor inventado. Darle al modelo
la forma de callarse es la mitad del control del fallo 2.

Los arreglos y objetos anidados quedan fuera: una tabla repetible se llena una entrada a la
vez, cada una con su propio dictado.

### 2. Un código se resuelve contra el catálogo vigente, o no se propone

Para un campo cuyo valor **es** un código, el extractor no toma el token que sigue a la pista:
compara los caracteres dictados con el catálogo real de esa unidad de negocio, en tres
lecturas —la transcripción tal cual, la misma leída como nombres de letras y dígitos
("cero cuatro be hache…"), y una tercera con los sonidos que el español no distingue
colapsados, porque una *v* oída por una *b* es un artefacto de transcripción y no otro
alimentador—. Si nada coincide, **no se propone nada** y se reporta lo que se escuchó.

Ofrecer el fragmento "04" para el alimentador `04BH070T11` es exactamente el valor que se
confirma sin leer.

### 3. Una propuesta no es una respuesta hasta que una persona lo diga

El dictado escribe en `field_provenance` con `confirmed_by` vacío y **no toca**
`form_response.answers`. La compuerta de aprobación de I6 ya rechaza una respuesta con valores
de IA sin confirmar, así que un técnico que dicta y no revisa no puede enviar las suposiciones
de la máquina. Confirmar es el único camino de propuesta a respuesta, y guarda el par
propuesta/valor final: la tasa de aceptación es una métrica, no una meta.

### 4. El léxico se genera; nadie lo escribe

Las *hotwords*, los sinónimos y los catálogos de códigos salen de tres fuentes: el vocabulario
hablado canónico (`profiles/amd/voice-es-EC.yaml`), los metadatos sincronizados de la unidad de
negocio —que aportan las etiquetas propias de la distribuidora— y la **orden de trabajo
abierta**, cuyas palabras reciben el refuerzo más alto porque son las que se van a decir en el
próximo minuto (RF-331, RF-332).

### 5. Hay una línea base determinista, y corre sin pesos

`RuleBasedExtractor` empareja el léxico contra la transcripción normalizada y no propone nada
que no pueda señalar. Sirve para tres cosas: es el punto de comparación que cada versión de
modelo tiene que superar, es el respaldo sin conexión de un teléfono que todavía no bajó su
paquete de modelos, y es la lógica que se porta a Kotlin (ADR-010).

## Consecuencias

- El extractor puede cambiar de modelo sin cambiar el contrato: la gramática y el léxico son
  datos derivados del perfil y del formulario.
- Un catálogo volátil que no llegó en la última sincronización **degrada el dictado de ese
  campo y lo dice** (RF-304), en vez de proponer códigos viejos.
- La cobertura de campos por voz es deliberadamente menor que la teórica: un valor no propuesto
  cuesta una escritura manual; uno propuesto mal cuesta una captura equivocada.
- El normalizador es-EC tiene una consecuencia visible en campo: una serie de dígitos sueltos
  ("dos tres cinco") **no** se lee como cantidad. Es cómo se dicta un código, y leerla como 235
  sería una afirmación distinta.
