# Bloque 22: herramienta estructurada y memoria de conversación

Este bloque amplía el agente del Bloque 21 en
`src/GATE_1/agente_con_herramientas.py`. El mismo agente conserva la invocación
directa y ahora admite una herramienta con esquema Pydantic y una capa de
historial por sesión.

## Argumentos validados con Pydantic

`ArgumentosCostoTokens` describe los tres campos de
`calcular_costo_tokens_gemini`:

- `tokens_entrada`: cantidad no negativa de tokens de entrada.
- `tokens_salida`: cantidad no negativa de tokens de salida.
- `tokens_pensamiento`: cantidad no negativa, opcional y con valor por defecto
  `0`.

El decorador asigna a la herramienta el nombre explícito
`calcular_costo_tokens_gemini`. Los tipos, descripciones, restricciones y valor
por defecto se exponen al modelo mediante `args_schema`. Pydantic valida los
argumentos antes de ejecutar la función; por ejemplo, un contador negativo
produce `ValidationError` en vez de calcular un costo.

La función sigue usando `calcular_costo` de `src/GATE_1/costo.py`, de modo que
las tarifas y el cálculo permanecen en una única implementación.

## Memoria por sesión

El prompt tiene dos espacios con propósitos distintos:

1. `chat_history` contiene mensajes anteriores y es opcional, para que el
   ejecutor del Bloque 21 siga admitiendo invocaciones directas.
2. `agent_scratchpad` contiene acciones y observaciones de la invocación actual.

`construir_agente_con_memoria(ejecutor)` envuelve el `AgentExecutor` con
`RunnableWithMessageHistory`. Cada llamada a la capa de memoria requiere:

```python
config = {"configurable": {"session_id": "cliente-123"}}
resultado = agente_con_memoria.invoke(
    {"entrada": "¿Cuánto cuesta con el doble de tokens de entrada?"},
    config,
)
```

`obtener_historial(session_id)` mantiene historiales separados en un diccionario
de `InMemoryChatMessageHistory`. Ese almacenamiento vive solo mientras el
proceso se ejecuta: no persiste al reiniciar. `cerrar_sesion(session_id)` libera
el historial de una conversación terminada y se puede llamar más de una vez.
Usa el mismo `session_id` para continuar una conversación y otro identificador
para una conversación independiente.

Antes de guardar el turno en la memoria, `construir_agente_con_memoria` adapta
la salida del ejecutor: conserva las cadenas y concatena los bloques
estructurados de tipo `text` del proveedor en una sola cadena. Esto evita que
una lista de bloques de Gemini se interprete como diccionarios de mensajes
cuando LangChain construye el prompt del siguiente turno. Si la salida no es
texto o contiene bloques no textuales, el adaptador informa explícitamente el
formato inesperado; no descarta esos datos silenciosamente.

La memoria conserva contexto conversacional; no sustituye los datos reales del
sistema. Cada turno vuelve a enviar el historial al modelo, por lo que las
conversaciones largas pueden aumentar latencia y costo.

En la versión de LangChain instalada, `RunnableWithMessageHistory` y
`InMemoryChatMessageHistory` emiten avisos de obsolescencia que recomiendan la
persistencia de LangGraph para código nuevo. Este bloque mantiene esas clases
porque enseña cómo envolver el `AgentExecutor` existente sin migrar la
arquitectura; el aviso no impide que la memoria funcione.

## Ejecutar y probar

La dependencia Pydantic 2 está declarada en `requirements.txt`; para actualizar
el entorno:

```console
python -m pip install -r requirements.txt
```

El ejemplo ejecutable de `src/GATE_1/agente_con_herramientas.py` hace dos turnos
con el mismo `session_id`, utiliza Gemini y puede generar costos. Configura
`GEMINI_API_KEY` en `.env`; desde la raíz puedes ejecutarlo como módulo:

```console
python -m src.GATE_1.agente_con_herramientas
```

Las pruebas locales no usan la API:

```console
python -m pytest tests/test_agente_con_herramientas.py -q
```

Comprueban el nombre y las descripciones del esquema, el rechazo de contadores
inválidos, el contexto entre dos turnos de una sesión y el aislamiento de dos
sesiones diferentes. También reproducen una respuesta de Gemini en bloques de
texto y comprueban que el siguiente turno recibe una cadena válida en su
historial. Para revisar el historial real, comprueba que la cantidad de mensajes
aumente después de cada turno y que una sesión nueva empiece vacía.

## Problemas frecuentes

- **`ValidationError: Field required`:** falta un argumento obligatorio o su
  nombre no coincide con el campo del esquema Pydantic.
- **Error de tipo o contador fuera de rango:** revisa el tipo y las restricciones
  `ge=0` declaradas en cada campo.
- **`TypeError: 'StructuredTool' object is not callable`:** invoca la herramienta
  decorada con `.invoke({...})`, no como una función Python normal.
- **Falta `session_id`:** pasa la configuración bajo
  `{"configurable": {"session_id": "..."}}` en cada llamada con memoria.
- **La segunda pregunta no recuerda la primera:** confirma que el prompt contiene
  `MessagesPlaceholder("chat_history", optional=True)` y que la capa usa
  `input_messages_key="entrada"` y `history_messages_key="chat_history"`.
- **`Message dict must contain 'role' and 'content' keys`:** algunas versiones
  del conector de Gemini devuelven el texto final como bloques estructurados.
  La capa de memoria convierte los bloques de texto en una cadena antes de
  guardarlos; actualiza el proyecto y vuelve a ejecutar los dos turnos con el
  mismo `session_id`.
- **Las sesiones parecen compartir contexto:** usa un `session_id` distinto por
  conversación y no reutilices identificadores entre usuarios.
- **El historial vuelve a cero después de reiniciar:** es el comportamiento
  esperado de `InMemoryChatMessageHistory`; para persistencia, reemplaza el
  proveedor de historial por un almacenamiento duradero.
- **Aparece `LangChainDeprecationWarning`:** la API del ejemplo sigue
  funcionando, pero LangChain recomienda LangGraph para implementaciones
  nuevas que necesiten persistencia. Es un aviso de migración, no el error que
  impedía iniciar el segundo turno.
