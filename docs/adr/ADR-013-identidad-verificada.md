# ADR-013 — La identidad viene del token, nunca del cuerpo de la petición

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-09-22 |
| Decide | Cómo la plataforma sabe quién está llamando y qué puede hacer |
| Se apoya en | [ADR-009](ADR-009-multi-tenencia-unidades-negocio.md) |

## Contexto

Hasta esta decisión, la plataforma tenía un problema que no se veía mirando el código de cada
endpoint por separado: **toda identidad se autodeclaraba**.

- El `reviewer_sub` de una aprobación llegaba en el cuerpo de la misma petición que registraba
  esa aprobación.
- El `confirmed_by` de un valor propuesto por IA era quien el llamante dijera.
- El `requested_by` de un reintento de integración, igual.

Cada uno de esos campos es una columna de auditoría, y todos valían exactamente lo que valiera
la afirmación del llamante. Es decir: nada. El rastro que la regla 0.5 del SRS exige —ningún
valor de IA es definitivo sin confirmación humana— era una cadena de texto que cualquiera podía
escribir. Y los endpoints estaban **abiertos**: no había ni una comprobación de token en toda
la API, aunque el `pyproject.toml` ya arrastrara `python-jose` y el realm de Keycloak estuviera
definido desde I0.

## Decisión

### 1. La identidad se construye desde un token verificado y de nada más

`app/auth/tokens.py` verifica firma contra las claves publicadas por el emisor, emisor,
audiencia y caducidad. Cuatro cosas se rechazan explícitamente porque cada una es una forma
concreta de entrar:

| Rechazo | Por qué |
|---|---|
| Token firmado por otra clave | Es lo que impide que cualquiera emita sus propios tokens |
| Token **sin** caducidad | Un token que no caduca es una contraseña en un encabezado |
| Token para otra audiencia | El token del cliente web no es un token para esta API; aceptarlo convierte una confusión de clientes en un fallo de autorización |
| `kid` desconocido | Con **un** refresco de claves, y con piso de tiempo: un flujo de tokens forjados no debe convertirse en un flujo de peticiones al proveedor de identidad |

Los campos de identidad desaparecieron del cuerpo de las peticiones. No se ignoran: **no
existen**, para que nadie los vuelva a leer por costumbre.

### 2. El ámbito por unidad de negocio se comprueba en la puerta del router

`unit_scope` es una dependencia del router, no de cada handler. Un endpoint nuevo no puede
olvidarla, y ADR-009 se cumple antes de que el handler corra en vez de en algún sitio dentro de
él.

Responder que la unidad está fuera de ámbito —y no si existe— es deliberado: un 404 para las
inexistentes y un 403 para las ajenas permitiría enumerar las unidades de negocio de la empresa
preguntando una por una.

### 3. Una guarda en CI de que ninguna ruta quede abierta

El fallo que importa no es escribir mal un chequeo: es **olvidarlo**. Se añade un endpoint, se
prueba lo que hace, se mezcla, y queda abierto.

`test_rf001_every_route_is_guarded.py` recorre todas las rutas y exige que cada una resuelva una
dependencia de identidad, con una lista de excepciones corta y justificada una por una.

Y tiene **prueba en negativo**, por una razón que vale contar: la primera versión de esa guarda
recorría `app.routes` buscando `APIRoute`. Esta versión de FastAPI difiere la inclusión de
routers, así que encontraba **cero** rutas y pasaba sin mirar nada. Una guarda que pasa porque no
inspeccionó nada es peor que no tener guarda: da confianza y no la merece.

### 4. La escotilla de desarrollo es explícita y ruidosa

Sin un Keycloak corriendo, la API entera sería imposible de probar a mano o de demostrar. Con una
escotilla silenciosa, un despliegue podría salir con la autenticación apagada y nadie lo notaría.
Así que el encabezado `X-SIGEC-Dev-Identity` requiere `SIGEC_ALLOW_DEV_IDENTITY=1` **y** un
entorno de desarrollo, y un token presente siempre gana sobre él — presentar las dos cosas no es
una forma de esquivar la verificación.

### 5. El agente arcpy sigue con su clave

Un proceso desatendido en una máquina Windows no hace un flujo interactivo de OIDC (ADR-008). El
agente se autentica con su clave de registro, verificada en `app/api/gis.py`, y la guarda lo
declara como mecanismo aparte en vez de como excepción.

## Consecuencias

- La web manda el token en un solo sitio (`api/session.ts`), y el token **no se persiste**:
  vive en memoria mientras dure la pestaña. `localStorage` sobreviviría a un portátil cerrado en
  una sala de control de subestación, que es exactamente donde no debería sobrevivir.
- El nivel de revisor (`reviewer_level`) sigue viniendo del cuerpo: es una propiedad de *qué
  clase de revisión* se está haciendo, no de quién la hace. Los roles decidirán si eso se
  restringe cuando la muestra ciega de I12 esté en marcha.
- Falta el flujo de login de la web contra Keycloak (PKCE) y la renovación silenciosa. La
  costura ya está: `setAccessToken` y `onTokenExpired`.
