# Doble de prueba de arcpy

Implementación mínima de la superficie de `arcpy` que usa `gis-agent`, para que sus
tests corran en CI sin ArcMap ni licencia de ArcGIS Desktop (ADR-008, incremento I1).

**No es un emulador de ArcGIS.** Solo reproduce los comportamientos de los que depende
el diseño del agente, incluidos los que fallan:

| Comportamiento real | Reproducido |
|---|---|
| `da.InsertCursor` falla en clases de la red geométrica con `SystemError` (H13) | Sí — es el que obliga al patrón staging + `Append` |
| `Append_management` sí funciona sobre clases de la red | Sí |
| `da.Editor` exige sesión de edición para clases de red | Sí |
| Conectividad, trace, auto-actualizadores de ArcFM | **No.** Eso solo se verifica en la máquina real, en I1 |

La verificación de verdad es el agente corriendo contra la geodatabase real. Este doble
sirve para que los errores de lógica se atrapen antes de llegar ahí.
