# Catálogos operativos (RF-034)

Los formularios de `forms/` referencian estos catálogos con `x-catalog-ref`, y **nada los servía**:
un teléfono que renderizaba el bloque de hallazgos tenía un campo de código y ninguna lista de dónde
elegir. Estos archivos son la línea base.

## Qué es y qué no es cada catálogo

| Origen | Quién lo mantiene | Dónde vive |
|---|---|---|
| **Operativo** | La administración funcional, desde la web | Aquí, y en `catalog_entry` |
| **Integración** | El ERP u otro sistema corporativo (RF-121) | `catalog_entry`, escrito por el conector |
| **Del SIG** | La geodatabase de la unidad, por sincronización (RF-304) | El snapshot de metadatos, **no aquí** |
| **Del perfil** | El descriptor del modelo de activos (`profiles/amd/`) | El AMD, **no aquí** |

## Leer antes de usar

Estos valores son una **línea base construida desde la normativa ecuatoriana y la práctica del
sector**, igual que los formularios (SRS, sección 4, nota final). Cada área tiene que validarlos
contra sus formatos vigentes antes del piloto. Un código de defecto que nadie usa es ruido en un
selector; uno que falta obliga al técnico a escribir en el campo de observación, que es donde la
información va a morir.

Los catálogos que este repositorio **declara vacíos a propósito** llevan su `note` diciendo por qué.
La división política del Ecuador es el caso: son 24 provincias, ~221 cantones y ~1 500 parroquias, y
la lista oficial es del INEC. Inventarla parcialmente sería peor que no tenerla — un cantón mal
escrito en miles de OT no se arregla después.

## Cargar

```
cd backend
uv run python -m app.catalogs.cli --dry-run
uv run python -m app.catalogs.cli
```

Volver a cargar es idempotente: actualiza las etiquetas y los sinónimos, no duplica códigos, y **no
retira** nada que no esté en el archivo. Retirar un valor es un acto explícito, desde la web o con
`--retire-missing`, porque un archivo incompleto no debe poder vaciar un catálogo en producción.
