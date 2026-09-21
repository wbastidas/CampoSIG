# `app.voice` — voz → formulario (I7)

Convierte lo que dictó el técnico en **propuestas** de campo. Nunca en respuestas: eso lo
decide una persona (ADR-011, SRS regla 0.5).

## Qué hay aquí

| Módulo | Qué hace | Necesita modelos |
|---|---|---|
| `normalizer.py` | Transcripción es-EC → texto canónico: números, unidades, decimales, fechas, códigos deletreados | No |
| `lexicon.py` | Genera *hotwords*, sinónimos y catálogos de códigos del perfil, los metadatos de la unidad y la OT abierta (RF-331, RF-332) | No |
| `grammar.py` | Gramática GBNF del sub-esquema del formulario, para que la respuesta sea JSON válido por construcción | No |
| `extractor.py` | `RuleBasedExtractor` (línea base determinista) y el *payload* para la pasarela de modelos | No |
| `service.py` | Persiste cada propuesta como valor de IA sin confirmar, y confirma o descarta | No |

Nada de esto carga un modelo. El ASR (sherpa-onnx) y el extractor LLM (`llama.cpp` +
Qwen2.5-1.5B) viven en el teléfono y detrás de la pasarela (M19); este paquete es lo que los
rodea, y es la parte que se puede probar entera sin un solo peso en disco.

## El flujo

```
audio ──► ASR (teléfono) ──► transcripción
                                  │
                                  ▼
                          normalizer.normalize()
                                  │
              ┌───────────────────┴───────────────────┐
              ▼                                       ▼
   RuleBasedExtractor.extract()          build_extraction_request()
   (sin pesos, offline, línea base)      (gramática GBNF → pasarela)
              └───────────────────┬───────────────────┘
                                  ▼
                  service.propose_from_dictation()
                       → field_provenance sin confirmar
                                  │
                        una persona revisa
                                  ▼
                          service.confirm()
                       → form_response.answers
```

## Lo que no hace, a propósito

- **No rellena prosa.** Un campo narrativo se llena con la transcripción, no con una
  inferencia.
- **No convierte unidades.** "cincuenta kilovoltios" ofrecido para un campo en kVA se rechaza:
  es otra magnitud, no un detalle de transcripción.
- **No propone un código parcial.** O coincide con el catálogo vigente de la unidad, o el campo
  queda vacío y se reporta lo que se escuchó.
- **No lee dígitos sueltos como cantidad.** "dos tres cinco" es un código dictado carácter a
  carácter; leerlo como 235 sería otra afirmación.

## Probar

```bash
cd backend
uv run pytest tests/unit/test_rf331_normalizer.py tests/unit/test_rf331_lexicon.py \
              tests/unit/test_rf332_grammar.py tests/unit/test_rf140_extraction.py
uv run pytest tests/integration/test_rf140_voice_flow.py   # necesita PostGIS
```

`tests/support/gbnf.py` es un intérprete mínimo de GBNF: la gramática se prueba por **lo que
acepta y lo que rechaza**, no comparando cadenas.

## Pendiente de I7

Todo lo que necesita hardware o audio real: elección entre la Ruta T (Zipformer con
*hotwords*) y la Ruta W (Whisper small con léxico), el paquete de modelos del teléfono,
`tools/bench-app` y el informe de línea base sobre 2–3 h de audio.
