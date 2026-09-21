# ADR-004 — Capa de abstracción del modelo de datos

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-09-21 |
| Decide | Cómo la plataforma deja de depender de un modelo de datos concreto |

## Contexto

Requerimiento explícito: la plataforma no debe depender de un solo modelo de datos. Instalarla en
otra Unidad de Negocio de CNEL, en otra distribuidora, o sobre un GIS distinto debe ser
configuración, no programación.

El modelo CNEL lo hace especialmente necesario: 47 clases, 196 dominios y 79 relaciones, con tres
dominios (`Codigo Alimentador`, `Numero Estacion`, `Subestacion`) que `01_Dominios.md` advierte
expresamente que **cambian por Unidad de Negocio** y no deben fijarse en código.

El SRS ya exige formularios como datos (regla 0.4). Esto va un nivel más abajo: el esquema de los
activos también es dato.

## Decisión

Tres artefactos y una regla dura.

1. **Asset Model Descriptor (AMD)** — vocabulario canónico interno, deliberadamente pequeño. Describe
   tipos de activo, sus atributos canónicos y **roles semánticos** (`business_key`,
   `network_grouping`, `voltage_level`), nunca nombres de campo.
2. **Perfil de mapeo** — traduce el AMD al modelo real de la instalación: capas, campos, dominios,
   relaciones, participación en la red geométrica y ruta de escritura. Un archivo por instalación;
   es lo único que cambia al migrar.
3. **Formularios derivados** — el JSON Schema + UI Schema se generan del AMD, el perfil y los
   metadatos del GIS, y el administrador funcional los ajusta y aprueba antes de publicar.

**Regla dura:** ningún nombre de clase, campo o dominio del modelo real aparece en el código fuente
del backend, la web o el móvil. Un único módulo (`model_profile/resolver.py`) resuelve nombres reales
en tiempo de ejecución. Se verifica en CI (RF-305).

## Consecuencias

**A favor:**

- Cambiar de Unidad de Negocio es editar un perfil.
- Los dominios volátiles se refrescan del GIS y nunca se empaquetan como constantes.
- Sinergia con la voz: el léxico y los *hotwords* del ASR se generan de los mismos dominios, así que
  el vocabulario se actualiza solo (RF-331).
- Sinergia con la calidad: las reglas de revisión SIG se escriben contra el AMD, así que valen para
  cualquier instalación.
- La ruta de escritura de cada clase se deriva de metadatos, sin listas de excepciones en el código
  (ADR-001).

**En contra:**

- Una indirección más que atravesar al depurar.
- Riesgo real de que el perfil se vuelva tan complejo que configurarlo cueste más que programar
  (R-N4). Mitigación: mantener el AMD pequeño, ofrecer coincidencia asistida en el importador, y
  vigilar la señal de alarma temprana que da el perfil alterno en CI.
- El generador de formularios propone, no decide: siempre hay revisión humana antes de publicar.

## Verificación

Dos pruebas, ambas en CI y ambas obligatorias en la Definition of Done:

1. **Prueba de fuga:** buscar identificadores del modelo real fuera de `profiles/`. Falla el build.
2. **Perfil alterno:** un segundo perfil sintético, con nombres y estructura deliberadamente
   distintos, debe pasar la misma suite de tests. Es la prueba real de que la abstracción funciona,
   no una declaración de intenciones.
