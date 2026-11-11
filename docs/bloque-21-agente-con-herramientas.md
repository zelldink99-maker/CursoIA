# Bloque 21: agente con herramientas y traza de decisión

## Chain y agente resuelven problemas distintos

En una chain, el código fija los pasos y el orden: el modelo produce contenido
dentro de ese recorrido. `RunnableBranch` permite elegir entre rutas conocidas,
pero esas rutas y condiciones siguen definidas por el programa.

En un agente, el modelo decide durante la ejecución si responde directamente
o llama a una de las herramientas disponibles. Si una observación revela que
hace falta otra acción, puede volver a llamar al modelo y elegir otra
herramienta. Por eso el número de pasos, la latencia y el costo varían según la
consulta.

Conviene usar una chain si el recorrido es estable, el tiempo debe ser
predecible o las alternativas se pueden enumerar. Un agente es útil cuando la
entrada determina qué herramienta hace falta y en qué orden. Esa flexibilidad
también requiere validar las herramientas y revisar las acciones seleccionadas.

## Ciclo de acción y observación

El ciclo básico consiste en que el modelo elige una herramienta y sus
argumentos, el programa ejecuta la llamada, y su resultado vuelve al modelo
como observación. El ciclo termina cuando el agente produce una respuesta.
Cada decisión del modelo puede requerir otra llamada y sumar latencia o costo.

La traza de LangChain permite revisar las herramientas, los argumentos y las
observaciones. No es una transcripción de razonamiento privado: para verificar
el comportamiento de la aplicación, comprueba las acciones observables y sus
resultados.

## Herramientas de este proyecto

`src/GATE_1/agente_con_herramientas.py` integra un agente para el dominio de
soporte y operación del proyecto:

- `buscar_en_documentacion(consulta)` devuelve las políticas documentadas de
  reintentos, costos y metadatos de tokens.
- `calcular_costo_tokens(tokens_entrada, tokens_salida,
  tokens_pensamiento=0)` delega el cálculo en `src/GATE_1/costo.py` y usa las
  tarifas configuradas allí. Los contadores inválidos se devuelven como una
  observación explicativa en vez de dejar que la herramienta interrumpa al
  agente.

El docstring de cada herramienta describe para qué consulta sirve. Esa
descripción y las anotaciones de tipo forman parte de la información que se
entrega al modelo para que elija una herramienta y prepare argumentos.

El ejecutor usa `create_tool_calling_agent` y `AgentExecutor`, reserva
`agent_scratchpad` para los mensajes de herramienta y devuelve
`intermediate_steps` en el resultado. Limita la ejecución a cinco iteraciones
para reducir el riesgo de un ciclo prolongado.

## Ejecutar y revisar la traza

Instala el proyecto desde la raíz para obtener también `langchain-classic`,
que contiene `AgentExecutor` y `create_tool_calling_agent` en LangChain 1.x:

```console
python -m pip install -r requirements.txt
```

Configura `GEMINI_API_KEY` en `.env` y ejecuta:

```console
python -m src.GATE_1.agente_con_herramientas
```

El ejemplo combina una consulta de política con un cálculo de costo. `verbose`
muestra las invocaciones de herramientas en consola. `intermediate_steps`
permite inspeccionar cada acción y observación desde el código. Si el agente
resuelve una pregunta general sin herramientas, esa lista queda vacía.

Para comprobar cada herramienta manualmente desde la raíz, el ejecutor devuelve
también el rastro programático:

```python
from src.GATE_1.agente_con_herramientas import construir_ejecutor_agente
from src.GATE_1.configuracion import crear_chat_modelo

agente = construir_ejecutor_agente(
    crear_chat_modelo(),
    verbose=True,
)

for entrada in (
    "¿Cuántos reintentos hace el cliente?",
    "¿Cuánto cuesta una respuesta con 1000 tokens de entrada y 200 de salida?",
):
    resultado = agente.invoke({"entrada": entrada})
    print(resultado["output"])
    for accion, observacion in resultado["intermediate_steps"]:
        print(accion.tool, accion.tool_input, "->", observacion)
```

No uses solo la respuesta final como prueba de que se escogió la herramienta
correcta: verifica `accion.tool` y la observación. Como la selección depende
del modelo, las pruebas automáticas usan respuestas simuladas y no hacen
llamadas de API:

```console
python -m pytest tests/test_agente_con_herramientas.py -q
```

El conjunto cubre el contenido de ambas herramientas, el registro de una
acción en `intermediate_steps` y la respuesta directa sin herramientas.

## Problemas frecuentes

- **`ModuleNotFoundError: langchain_classic`:** instala las dependencias con
  `python -m pip install -r requirements.txt`.
- **Error de clave al crear o invocar el modelo:** comprueba que `.env` contenga
  una clave vigente y que se cargue desde la raíz del proyecto.
- **El agente no elige la herramienta esperada:** revisa que su docstring
  describa la pregunta que debe activar y comprueba la traza, no solo el texto
  final.
- **`intermediate_steps` está vacío:** el agente decidió responder sin una
  herramienta; puede ser lo correcto para una pregunta general.
- **Se alcanza el máximo de iteraciones:** el ejecutor corta a las cinco
  iteraciones; revisa descripciones ambiguas o herramientas que compiten por
  las mismas consultas.
