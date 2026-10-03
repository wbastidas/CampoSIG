# ADR-007 — Sin RAG normativo en v1

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-09-21 |
| Decide | Si la plataforma incluye recuperación semántica sobre normativa (M18 del SRS) |
| Sustituye a | [ADR-005](ADR-005-vector-store-rag.md) |
| Afecta a | SRS M18 y RF-190 a RF-193; nodo de normativa de M17 |

## Contexto

El SRS especificaba M18: base de conocimiento con embeddings `bge-m3`, índice vectorial, ingesta
segmentada por artículo y numeral, búsqueda híbrida con reranker, y un asistente que responde preguntas
normativas con citas. ADR-005 discutía dónde alojar los vectores.

El cliente cuestionó la premisa: *¿por qué necesito RAG?* Es la pregunta correcta, y al examinarla la
respuesta es que **para v1 no se necesita**.

El razonamiento completo está en la sección 6.3 del addendum. En resumen: el RAG cubría dos necesidades
distintas que se habían confundido en una.

| Necesidad | ¿RAG? | Solución elegida |
|---|---|---|
| **Hacer cumplir** un límite regulatorio (plazo de reposición de APG, umbral de interrupción no computable, resistencia de tierra admisible) | Mal ajuste. Un LLM puede leer mal una tabla y el error es silencioso | `regulatory_parameter` con vigencia y referencia a la norma, evaluado por reglas deterministas |
| **Consultar** dónde lo dice la norma o el manual | Caso legítimo | Búsqueda de texto completo de PostgreSQL con enlace al numeral y la página |

La observación decisiva: **la validación normativa que el sistema necesita es aritmética, no semántica.**
"¿Se repuso dentro del plazo?" es una resta contra un parámetro. El propio SRS ya lo había resuelto en su
sección 1.4, al exigir que los valores regulatorios se parametricen en `regulatory_parameter` con
vigencia y referencia en lugar de codificarse.

## Decisión

**M18 queda fuera de v1.** En su lugar:

1. **`regulatory_parameter`** — valores regulatorios con vigencia y referencia a la norma. Ya estaba
   previsto en el SRS; ahora es la única fuente de verdad normativa del sistema.
2. **Reglas deterministas** en el nodo de normativa de los agentes (M17). La guía de entrenamiento ya lo
   recomienda como primer paso: *"convertir los patrones fallidos en reglas deterministas antes de tocar
   el prompt o el modelo"*.
3. **Repositorio documental con búsqueda de texto completo**, con enlace al numeral y la página exactos.
   Sin embeddings ni vector store.

M17 se mantiene íntegro en lo demás: coherencia entre voz, campos y fotos, evidencia visual, anomalías y
consolidación del `AgentReport`. Solo su nodo de normativa cambia de recuperación semántica a reglas.

## Consecuencias

**A favor:**

- Elimina de v1: vector store, modelo de embeddings, pipeline de ingesta y segmentación, conjunto dorado
  de 100–200 preguntas por área, métricas RAGAS en CI y reindexación en cada cambio de norma.
- Cierra la decisión pendiente sobre el almacén de vectores, y con ella el riesgo R-N5.
- La validación normativa pasa a ser **auditable**: un parámetro con vigencia y una regla se pueden
  mostrar a un auditor. Una respuesta de LLM, no.
- Reduce el riesgo asimétrico de una respuesta equivocada con aire de autoridad sobre normativa de
  seguridad eléctrica.

**En contra:**

- No hay asistente conversacional de procedimientos en v1. Se acepta: además de costoso, requería
  conexión, y el técnico necesita la norma justamente cuando está en el poste, sin red.
- La búsqueda de texto completo no entiende sinónimos ni paráfrasis. Se mitiga parcialmente con el léxico
  técnico que ya se construye para el ASR (RF-331), que da sinónimos del dominio gratis.

**Fuera de v1, no descartado.** Se reconsidera después del piloto con una señal medida en el propio
sistema: cuántas consultas normativas abiertas hacen realmente supervisores y técnicos, y cuántas no
quedan resueltas por la búsqueda de texto completo. Instrumentar esa medición cuesta poco y es el dato
que hoy no existe; construir M18 sin él sería decidir a ciegas.
