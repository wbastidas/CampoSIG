# `app.vision` — visión on-device (I11)

Convierte lo que el modelo vio en **propuestas** de campo y en **hallazgos**. Nunca en
respuestas: eso lo decide una persona (ADR-011, SRS regla 0.5).

## Qué hay aquí

| Módulo | Qué hace | Necesita modelos |
|---|---|---|
| `taxonomy.py` | Taxonomía visual enlazada al AMD y validada contra él | No |
| `contracts.py` | `ObjectDetector`, `StateClassifier`, `Prediction`, `BoundingBox` | No |
| `prefill.py` | Predicciones → propuestas de campo vía `x-vision-source`, con umbral por clase | No |
| `comparator.py` | Antes/después: ¿la foto muestra el trabajo que se declara? | No |
| `service.py` | Guarda cada propuesta como valor de IA sin confirmar | No |

Los modelos —un detector D-FINE y un clasificador MobileNetV3, ambos ONNX int8— corren en el
teléfono. Nada aquí los invoca: la app programa contra las interfaces y el servidor contra
las predicciones. Por eso todo esto se prueba sin una sola imagen.

## Por qué la taxonomía vive en la capa canónica

Una clase visual apunta al **tipo canónico**, y de ahí el resolver llega al campo real de
cada unidad de negocio. Añadir una unidad de negocio cambia el perfil, no los pesos. El
cargador valida que cada valor que un clasificador puede proponer exista en la enumeración
canónica: un `fiberglass` que la enumeración nunca tuvo no es una predicción mala, es un
valor que no se puede guardar en ninguna parte, y el fallo aparecería meses después como un
rechazo inexplicable.

## Los datasets

`ml/datasets/registry.yaml` es la lista verificada, y `scripts/check_dataset_licenses.py` la
compuerta que corre en CI. La conclusión de la investigación está expresada como una
aserción, no como una nota al pie:

> Todos los datasets públicos de activos eléctricos que se encontraron son NonCommercial,
> copyleft, de acceso restringido o sin licencia declarada. **El modelo que se entrega se
> entrena con las fotografías de la propia distribuidora.**

Hay dos razones, y conviene no confundirlas:

1. **Licencia.** InsPLAD es CC BY-NC, STN PLAD es GPL-3.0, IDID es de acceso restringido,
   CPLID no declara licencia. Ninguno puede entrenar un modelo que se entrega a una empresa.
2. **Dominio.** Casi todo lo público es fotografía aérea de dron sobre líneas de
   transmisión. Lo nuestro es foto desde el suelo, con teléfono, en distribución urbana. Un
   modelo entrenado en el dominio equivocado no es peor: reconoce otra cosa.

De ahí que la app pida **encuadres guiados desde el primer día del piloto**, aunque el modelo
todavía no exista. Sin esas fotos no hay dataset, y sin dataset no hay visión.

## Lo que no hace, a propósito

- **No cierra nada.** El comparador produce una lectura con la evidencia detrás, para quien
  decide. Un modelo que cerrara órdenes de trabajo sería la peor idea de esta plataforma.
- **No interpreta una ausencia como un trabajo hecho.** Un hallazgo puede desaparecer porque
  la segunda foto se tomó desde más lejos. Solo un par declarado en la taxonomía confirma
  una resolución.
- **No confunde "no se analizó" con "no se vio nada".** Un teléfono sin paquete de modelos lo
  dice; un resultado vacío se leería como una fotografía limpia.

## Probar

```bash
cd backend
uv run pytest tests/unit/test_rf140_vision.py tests/unit/test_dataset_license_gate.py
uv run pytest tests/integration/test_rf140_vision_flow.py   # necesita PostGIS
```

## Pendiente de I11

Los modelos y los datos: curaduría del histórico con anonimización, entrenamiento del
detector y del clasificador, cuantización int8, `tools/bench-app` en los tres teléfonos de
referencia, y la UI de revisión con el recorte resaltado.
