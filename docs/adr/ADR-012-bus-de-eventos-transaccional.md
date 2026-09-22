# ADR-012 — Los intercambios con sistemas corporativos van por un outbox transaccional

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-09-22 |
| Decide | Cómo la plataforma le cuenta a los sistemas corporativos lo que pasó |
| Se apoya en | [ADR-009](ADR-009-multi-tenencia-unidades-negocio.md) |

## Contexto

Hay un fallo concreto que esta decisión existe para impedir, y conviene escribirlo tal como
ocurre en campo:

> Una cuadrilla repone la luminaria. El supervisor aprueba el trabajo. Todos consideran el
> caso cerrado. Y el reclamo del cliente **sigue abierto** en el call center, porque cerrarlo
> era un efecto secundario que nadie garantizó: la llamada HTTP falló, o el proceso se reinició
> entre la aprobación y el envío, o el otro sistema estaba en mantenimiento.

La forma habitual de escribir eso es llamar a la API del otro sistema dentro de la operación de
negocio. Tiene dos consecuencias, y ninguna es aceptable:

1. Si la llamada falla, o la aprobación falla con ella —y entonces una integración caída
   impide trabajar— o se ignora el error, y el reclamo queda abierto para siempre.
2. Si la llamada tarda, la transacción de base de datos la espera, con los bloqueos tomados.

## Decisión

Cada intercambio es **una fila antes de ser una petición**. La aprobación escribe el evento de
salida en `integration_event` **dentro de su propia transacción**, junto con el cambio de estado
que lo causó. Nada de red en esa transacción. La entrega ocurre después, y puede fallar todas
las veces que quiera.

De ahí se siguen cuatro cosas:

- **El evento no se puede perder.** Si la aprobación se guardó, el evento existe. Si la
  transacción se revierte, no existe ninguno de los dos. No hay un estado intermedio en el que
  el trabajo esté aprobado y el reclamo no tenga quien lo cierre.
- **Idempotencia por clave**, no por intento. La clave de un estado incluye el estado
  (`estado:OT-77:aprobada`), así que cada transición se reporta una vez y una operación de
  negocio reintentada no le cuenta dos veces lo mismo al otro sistema.
- **Los reintentos terminan.** Retroceso exponencial acotado y, al agotarse, el evento queda
  `fallido` y **espera a una persona** en la pantalla de integraciones (RF-125). Un conector que
  lleva seis horas rechazando llamadas necesita que alguien lo mire, no un bucle más apretado.
- **Un 4xx no se reintenta.** Significa que la petición está mal; mandarla cuatro veces más solo
  añade cuatro entradas al registro de errores de otra persona.

### La bitácora es el registro, no un log

`integration_event` guarda el payload tal como se envió o tal como llegó. Cuando una importación
resulta haber estado mal, la única forma de saber qué mandó el otro sistema es haberlo
guardado. Un evento descartado se marca descartado con motivo y autor; no se borra, porque la
pregunta "por qué esto nunca se envió" tiene que seguir teniendo respuesta.

## Consecuencias

- Hace falta algo que entregue: por ahora se invoca desde la API y desde los tests; en I9 pasa a
  un *worker* periódico. El diseño no cambia — el outbox ya está escrito.
- La entrega es **eventual**. Un reclamo se cierra segundos o minutos después de la aprobación,
  no en el mismo instante. Es el precio de no perder ninguno, y es el correcto.
- La pantalla de integraciones deja de ser un informe y pasa a ser una herramienta: el botón de
  reintentar reencola de verdad, y reinicia el contador de intentos, porque quien lo presiona
  normalmente acaba de arreglar algo.
- Cada conector está acotado a la unidad de negocio, como todo lo demás (ADR-009).
