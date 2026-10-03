# Formularios como datos

Los formularios no se programan: se **componen** de bloques reutilizables y se versionan
(SRS regla 0.4 y sección 4.1). Un formulario codificado en una pantalla es un defecto.

```
forms/
├── blocks/        # bloques reutilizables: B1-B12 del SRS 4.2, más los específicos
└── definitions/   # un formulario por tipo de trabajo, que lista sus bloques en orden
```

## Cómo encaja con el generador desde metadatos

Dos orígenes distintos que se combinan en el mismo formulario:

| Origen | Qué aporta | Quién lo mantiene |
|---|---|---|
| **Bloques** (aquí) | Lo que no depende del modelo de datos: cabecera, tiempos, seguridad, actividades, evidencias, cierre | Administrador funcional |
| **Generador** (`app/forms/generator.py`) | Las secciones que describen un activo, derivadas de los dominios y campos reales del GIS | Se genera y un humano aprueba |

Un bloque con `source: asset_metadata` se rellena desde el generador en tiempo de composición,
así que el bloque "Estado encontrado" de una inspección de estructura ofrece exactamente los
valores del dominio de esa Unidad de Negocio, sin que nadie los copie a mano.

## Reglas

1. Un bloque no menciona jamás un nombre de clase o campo real: usa claves canónicas del AMD.
2. Cada campo declara `x-voice` (si el dictado puede llenarlo) y, cuando aplica,
   `x-vision-source` (si una foto puede proponerlo).
3. Los valores de catálogo nunca se embeben: se referencian con `x-catalog-ref`.
4. Un formulario publicado es inmutable. Un cambio es una versión nueva, porque una OT se
   ejecuta con la versión vigente al asignarse (SRS 4.1.6).
