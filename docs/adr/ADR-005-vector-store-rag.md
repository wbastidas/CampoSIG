# ADR-005 — Vector store del RAG normativo

| Campo | Valor |
|---|---|
| Estado | Propuesta — pendiente de D1 |
| Fecha | 2026-09-21 |
| Decide | Dónde viven los embeddings del RAG normativo (M18 del SRS) |
| Depende de | ADR-002 |

## Contexto

El SRS resolvía el RAG con `pgvector` sobre PostgreSQL, reutilizando la misma base. ADR-002 movió la
plataforma a Oracle, así que `pgvector` ya no está disponible.

El tipo `VECTOR` y `VECTOR_DISTANCE` de Oracle existen a partir de **23ai**, y requieren
`COMPATIBLE ≥ 23.4`. En 19c no hay columnas ni índices vectoriales nativos: lo más que se puede hacer
es guardar los arreglos como JSON o BLOB y calcular distancias en la aplicación, lo que no escala
para búsqueda semántica.

## Decisión

Condicionada a la versión de Oracle (decisión pendiente **D1**):

| Si Oracle es… | Entonces |
|---|---|
| **23ai o superior** | **Oracle AI Vector Search** nativo: índices HNSW/IVF y búsqueda híbrida junto a Oracle Text. Una sola base, bajo el gobierno del DBA |
| **19c o 21c** | **Qdrant** (Apache 2.0) como sidecar en contenedor, solo para embeddings normativos. Los documentos, su versión y su vigencia siguen en Oracle |

En ambos casos:

- El modelo de embeddings es **bge-m3**, consumido por el alias `embed` de la pasarela de modelos
  (M19), igual que en el SRS.
- El acceso al vector store pasa por una interfaz (`KnowledgeIndex`) con dos implementaciones, para
  que cambiar de almacén no toque los agentes ni el asistente.
- La búsqueda léxica usa **Oracle Text** en las dos variantes; la híbrida combina ambos resultados.

## Consecuencias

Con 23ai, una sola base que respaldar y gobernar. Con Qdrant, un servicio más que operar, pero
liviano, con licencia permisiva y sin datos personales (solo texto normativo público o interno).

La interfaz `KnowledgeIndex` implica un poco de trabajo extra por adelantado y evita quedar atados a
la decisión: si la empresa migra a 23ai después, se cambia la implementación sin tocar M17 ni M18.

## Pendiente

**D1** — versión y edición exactas de Oracle. Hasta tenerla, se desarrolla contra Qdrant, que es el
escenario más restrictivo y el más probable en un entorno con ArcGIS 10.8.1.
