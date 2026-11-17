# Bloque 29: RAG, fine-tuning, PEFT y soft-prompting

Este bloque distingue cuatro técnicas de personalización y practica cómo
preparar y validar datos para tuning sin enviar trabajos a la API. El problema
del ejercicio es la consistencia del comportamiento y el formato, no la falta
de información.

## Requisitos del entorno

El proyecto requiere Python 3.10 o superior. Activa el entorno virtual y
actualiza las dependencias desde la raíz:

```console
python -m pip install -r requirements.txt
```

La dependencia directa `google-genai` expone los tipos de tuning; `python-dotenv`
lee la configuración local. Copia `.env.example` como `.env` si todavía no lo
hiciste y define `GEMINI_API_KEY` allí. No escribas la clave en el código ni la
incluyas en Git.

Comprueba el entorno sin llamar a la API:

```console
python -m src.GATE_1.verificar_entorno
```

El verificador confirma Python, el paquete, los tipos de tuning disponibles y
la presencia de la variable, pero nunca imprime su valor. Si informa que falta
el SDK o `python-dotenv`, activa el entorno virtual y vuelve a instalar los
requisitos. Si no encuentra `GEMINI_API_KEY`, revisa el `.env` de la raíz.

## Las cuatro técnicas

| Técnica | Qué cambia | Cuándo conviene |
| --- | --- | --- |
| **RAG** | Recupera información externa pertinente para cada consulta, sin actualizar parámetros del modelo. | Hechos nuevos o cambiantes, documentos internos, políticas vigentes y respuestas que deben citar fuentes. |
| **Fine-tuning completo** | Actualiza los parámetros del modelo a partir de ejemplos de entrada y salida. | Cambios profundos de comportamiento con datos y presupuesto suficientes para entrenar y mantener el modelo completo. |
| **PEFT (adapters)** | Congela el modelo base y entrena un conjunto pequeño de parámetros adicionales. | Estilo, formato o clasificación consistentes con menos datos y presupuesto que el tuning completo, o varias personalizaciones pequeñas del mismo modelo base. |
| **Soft-prompting** | Aprende vectores continuos que se anteponen a la entrada, en lugar de modificar pesos del modelo. | Casos muy acotados con acceso a pesos abiertos e infraestructura para entrenar; aquí se estudia como concepto, no se implementa. |

RAG suele ser el primer recurso cuando el problema es información que cambia:
actualizar los documentos implica reindexarlos, no entrenar el modelo. El tuning
es para enseñar patrones de respuesta y no es una buena forma de almacenar
hechos que deben recordarse literalmente. RAG y PEFT pueden combinarse:
recuperar condiciones vigentes para cada consulta y usar un modelo afinado para
mantener un formato o tono consistente.

El SDK de Gemini expone `TuningMode.TUNING_MODE_FULL` y
`TuningMode.TUNING_MODE_PEFT_ADAPTER`, además de tamaños de adapter. Estos tipos
son detalles de la API y su disponibilidad puede depender del modelo, la cuenta
y la versión instalada; `verificar_entorno` hace una comprobación local. Un
`adapter_size` mayor permite más capacidad entrenable y puede aumentar costo y
riesgo de sobreajuste; no es una garantía de mejor resultado. Los campos
`epoch_count`, `learning_rate_multiplier` y `batch_size` tampoco son
intercambiables: revisa las descripciones del SDK para tu modelo y versión.

Puedes inspeccionar los campos y sus descripciones en la versión instalada sin
enviar un trabajo:

```python
from google.genai import types

for campo in ("epoch_count", "learning_rate_multiplier", "batch_size"):
    try:
        descripcion = types.CreateTuningJobConfig.model_fields[campo].description
        print(campo, "->", descripcion)
    except KeyError:
        print(campo, "-> este campo no existe en tu versión del SDK")
```

`batch_size` o una tasa de aprendizaje que no corresponda al tipo de modelo
pueden no aplicar. La documentación embebida en el SDK y la disponibilidad
vigente del modelo son más confiables que copiar parámetros de otra versión.

### Caso para decidir

Una aseguradora necesita resúmenes con estructura y estilo fijo a partir de
unos 3.000 ejemplos aprobados, y además cada resumen debe citar condiciones de
póliza que cambian trimestralmente. Una combinación razonable es RAG para las
condiciones vigentes y PEFT para el estilo/formato. Fine-tuning completo puede
ser innecesariamente caro cuando PEFT aborda el comportamiento requerido; el
soft-prompting no es una opción de la API gestionada de este curso.

## Laboratorio: preparar un dataset

La tarea de ejemplo clasifica tickets de soporte en una categoría y una acción
sugerida. El dataset tiene doce casos, repartidos entre devolución, cobro, envío
y promoción.

Desde la raíz, ejecuta:

```console
python -m src.GATE_1.dataset_tuning
```

El script construye doce `types.TuningExample` y muestra los mismos tres pasos
que el laboratorio: balance de categorías, validación del dataset correcto y
una copia deliberadamente rota para comprobar que se detecta el JSON inválido.
La salida original debe indicar `12 ejemplos, 0 problemas encontrados`; la
prueba rota debe mostrar un problema en el ejemplo 3. Todo sucede localmente:
no requiere la clave ni llama a la API. Las pruebas correspondientes también
son locales:

```console
python -m pytest tests/test_dataset_tuning.py -q
```

La construcción usa los tipos reales del SDK:

```python
from src.GATE_1.dataset_tuning import EJEMPLOS_RAW, construir_ejemplos

examples = construir_ejemplos(EJEMPLOS_RAW)
```

Para tu actividad, reemplaza `EJEMPLOS_RAW` en una copia de trabajo con una
tarea de tu proyecto, no con hechos que deban consultarse mediante RAG. Incluye
al menos diez entradas variadas y salidas exactas. Ajusta la clave de balance
si tu tarea clasifica por otro campo; el formato debe reflejar exactamente lo
que quieres que el modelo produzca.

Antes de enviar datos a entrenar, confirma:

- el dataset contiene al menos diez casos representativos y no variaciones
  mínimas de un único ejemplo;
- la distribución entre categorías no tiene un desbalance extremo;
- `validar_dataset(examples)` devuelve una lista vacía;
- probaste el validador con una entrada vacía, duplicada, con JSON inválido o
  con una clave faltante.

Las pruebas incluyen un dataset roto deliberadamente para demostrar que el
validador informa todos los problemas detectables en vez de detenerse en el
primero.

## Diagnosticar errores de llamadas futuras

Los siguientes casos solo corresponden a scripts que sí consulten la API. Una
función mínima puede orientar los errores habituales sin ocultar el mensaje
original:

```python
def explicar_error(error: Exception) -> str:
    mensaje = str(error)
    if "API key" in mensaje or "401" in mensaje or "403" in mensaje:
        return "Problema de autenticación: revisa GEMINI_API_KEY en .env."
    if "429" in mensaje or "RESOURCE_EXHAUSTED" in mensaje:
        return "Cuota agotada: espera unos minutos y vuelve a intentar."
    if "Connection" in mensaje or "timed out" in mensaje:
        return "Problema de conexión: revisa internet y vuelve a intentar."
    return "Error inesperado: " + mensaje
```

No uses este diagnóstico como sustituto de revisar el error real: la
autenticación, la cuota y la conectividad son causas distintas y requieren
acciones diferentes.

## Enviar y consultar un trabajo de tuning

El trabajo de tuning es asíncrono: `client.tunings.tune(...)` devuelve un
trabajo, y `client.tunings.get(name=...)` consulta su estado. Preparar y
validar los ejemplos no envía nada. No ejecutes el envío como parte de las
pruebas locales: la disponibilidad depende de la cuenta y el modelo, y puede
generar costo.

Este es el contorno del código que se ejecutaría **solo** si se decide enviar un
trabajo con acceso habilitado y una cuenta configurada:

```python
from google import genai
from google.genai import types

client = genai.Client()
dataset = types.TuningDataset(examples=examples)
config = types.CreateTuningJobConfig(
    tuning_mode=types.TuningMode.TUNING_MODE_PEFT_ADAPTER,
    adapter_size=types.AdapterSize.ADAPTER_SIZE_FOUR,
    epoch_count=5,
    tuned_model_display_name="clasificador-errores-cliente",
)

# Esta llamada crea un trabajo remoto y puede generar costo.
trabajo = client.tunings.tune(
    base_model="models/gemini-2.0-flash",
    training_dataset=dataset,
    config=config,
)
print(trabajo.name, trabajo.state)
```

Confirma en la documentación vigente que el modelo y los parámetros son
compatibles antes de enviarlo. Para seguir el trabajo, consulta el mismo nombre
de trabajo; no vuelvas a llamar a `tune`, porque eso crea otro:

```python
import time

estados_finales = {
    types.JobState.JOB_STATE_SUCCEEDED,
    types.JobState.JOB_STATE_FAILED,
    types.JobState.JOB_STATE_CANCELLED,
    types.JobState.JOB_STATE_PARTIALLY_SUCCEEDED,
    types.JobState.JOB_STATE_EXPIRED,
}

while True:
    trabajo = client.tunings.get(name=trabajo.name)
    print(f"estado actual: {trabajo.state}")
    if trabajo.state in estados_finales:
        break
    time.sleep(30)
```

Usa una pausa entre consultas: consultar continuamente no acelera el
entrenamiento y genera llamadas innecesarias. Revisa el estado terminal antes
de usar el modelo resultante.

## Errores frecuentes

- **`ModuleNotFoundError` al importar `google.genai`:** activa el entorno
  virtual e instala dependencias con `python -m pip install -r requirements.txt`.
- **No aparecen `TuningMode` o `AdapterSize`:** actualiza `google-genai` y vuelve
  a ejecutar `python -m src.GATE_1.verificar_entorno`.
- **Salida marcada como JSON inválido:** JSON exige comillas dobles; una cadena
  con comillas simples puede ser un literal de Python, pero no JSON.
- **Campo desconocido o `ValidationError`:** consulta
  `types.CreateTuningJobConfig.model_fields.keys()` en la versión instalada y
  usa, por ejemplo, `epoch_count`, no `epochs`.
- **Clave inválida o cuota agotada al llamar a la API:** verifica `.env`, el
  acceso de la cuenta y la cuota. No cambies el dataset si la causa es de
  autenticación o disponibilidad.
- **La clasificación favorece una sola categoría:** revisa el conteo antes de
  entrenar y agrega ejemplos variados a las categorías menos representadas.
