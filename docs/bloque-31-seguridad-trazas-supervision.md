# Bloque 31: seguridad, trazas y supervisión humana

Este bloque integra seis prácticas para flujos RAG y prompts: callbacks
correlacionados, separación de roles, contexto recuperado como dato no
confiable, detección heurística de inyección, trazas por consulta, aprobación
humana antes de activar prompts y priorización de riesgos. El código vive en
[`src/GATE_2/seguridad_rag.py`](../src/GATE_2/seguridad_rag.py),
[`src/GATE_2/trazas_callbacks.py`](../src/GATE_2/trazas_callbacks.py),
[`src/GATE_2/privacidad_logs.py`](../src/GATE_2/privacidad_logs.py),
[`src/GATE_2/trazas_agente.py`](../src/GATE_2/trazas_agente.py) y
[`src/GATE_2/supervision_riesgos.py`](../src/GATE_2/supervision_riesgos.py).

## Alcance y límites

Ninguna de estas medidas es una solución completa por sí sola. La detección
busca frases conocidas en español e inglés; una instrucción nueva, codificada o
escrita de otra forma puede evadirla. También puede descartar un documento que
cite una frase sospechosa con fines legítimos. Usa defensa en profundidad,
revisión de resultados y monitoreo humano; no presentes el filtro como garantía
de seguridad.

## 1. Roles separados y contexto RAG no confiable

`recuperacion_citas.construir_prompt` construye un `SystemMessage` con las reglas
y un `HumanMessage` con la pregunta y el contexto. El contexto se encierra en
`<contexto>` y se escapan sus caracteres `<`, `>` y `&`, para que su contenido
no pueda cerrar la delimitación ni convertirse en una instrucción estructural.

Antes de construirlo, `filtrar_documentos_sospechosos` elimina documentos que
contengan patrones como «ignora las instrucciones anteriores», «nuevo sistema»
o «revela tu prompt». La lista está en `FRASES_SOSPECHOSAS`; mantenerla requiere
revisión y pruebas, y ampliarla no elimina falsos negativos ni positivos.

El filtro también se aplica en `registro_rag`, antes de enviar el contexto al
modelo. Si todos los documentos se descartan, el modelo recibe una indicación
de que no se recuperó contexto y las citas se validan con el conjunto vacío.

## 2. Callbacks y traza completa

`TrazaCallbacks` captura inicio y fin del retriever y del modelo. Cada evento
incluye un `trace_id`, los `run_id` de LangChain y su `parent_run_id`, para
relacionar los pasos de una consulta. Solo guarda longitudes y conteos: no
persiste pregunta, prompt, documentos ni respuesta.

```python
from src.GATE_2.recuperacion_citas import responder_con_citas
from src.GATE_2.trazas_callbacks import TrazaCallbacks

traza = TrazaCallbacks()
respuesta, fuentes = responder_con_citas(
    "¿Qué errores reintenta el cliente?",
    vectorstore,
    modelo,
    callbacks=[traza],
)
traza.guardar("trazas_callbacks.jsonl")
print(traza.trace_id, respuesta, fuentes)
```

El retriever y el modelo se ejecutan dentro de una misma cadena LangChain para
que sus callbacks compartan el identificador de ejecución padre. El archivo
JSONL de callbacks debe almacenarse y protegerse según la política de
observabilidad del proyecto.

## 3. Consultas RAG instrumentadas

El registro `src/GATE_2/registro_rag.py` asigna un `trace_id` nuevo por consulta
y emite eventos `consulta_recibida`, `documento_descartado_por_inyeccion`,
`contexto_filtrado` y `consumo_llm`. También conserva duración por etapa, los
tokens informados por el modelo y el costo estimado en USD cuando existen
metadatos completos:

```console
python -m src.GATE_2.registro_rag --pregunta "¿Qué errores reintenta el cliente?" --k 3
python -m src.GATE_2.registro_rag --demo-trazas
```

`--demo-trazas` usa datos locales y no consulta embeddings ni Gemini. Imprime
los tres pasos del ejemplo completo: una consulta con su respuesta y traza, dos
consultas con identificadores independientes, y el caso en que todo el contexto
recuperado se descarta y el sistema se abstiene. Los tokens, identificadores y
respuesta de la demostración son ilustrativos; para ejecutar una consulta RAG
real usa el comando `--pregunta`, que requiere credenciales.

Cada línea de `registros_latencia_costo.jsonl` incluye longitudes, conteos,
tiempos, uso y costo estimado por tokens, pero omite la pregunta, la respuesta
y el contexto en texto crudo. Si faltan metadatos, tokens y costo quedan en
`null`.
Las consultas reales requieren credenciales y pueden consumir cuota. Las
pruebas enfocadas son locales y no llaman a Gemini:

```console
python -m pytest tests/test_seguridad_rag.py tests/test_recuperacion_citas.py tests/test_trazas_callbacks.py tests/test_registro_rag.py -q
python -m pytest tests/test_privacidad_logs.py tests/test_trazas_agente.py -q
```

Los registros antiguos de RAG y del agente pueden contener datos sin redactar:
no se reescriben retroactivamente. Revísalos según la política de datos antes
de compartirlos. Las trazas nuevas del agente conservan la información
operativa, pero `privacidad_logs.redactar_pii` reemplaza correos y teléfonos
reconocidos por marcadores antes de guardarlos. Es una heurística: no detecta
todas las clases ni formatos de datos personales, así que limita el acceso a
los archivos y revisa los registros antes de compartirlos.

## 4. Versionado de prompts e interrupción humana

`VersionadorPrompts` calcula una huella SHA-256 de 12 caracteres y registra las
propuestas en `prompts/versiones_prompt.jsonl`. Una propuesta queda pendiente:
el flujo no la activa hasta que una persona llama explícitamente a `aprobar` y
después a `activar`. Si se rechaza, la versión activa anterior se conserva.
El historial permite reanudar el estado después de reiniciar Python.

```python
from src.GATE_2.supervision_riesgos import VersionadorPrompts

versionador = VersionadorPrompts()
huella = versionador.proponer(
    "Responde solo con el contexto citado.",
    "aprobar la nueva versión antes de producción",
)
print("interrupción pendiente:", versionador.interrupcion_pendiente)

# Pausa aquí y solicita revisión a una persona antes de reanudar:
versionador.aprobar(huella)
versionador.activar(huella)
```

Para rechazar, usa `versionador.rechazar(huella)` en vez de aprobar. El archivo
de auditoría contiene el texto completo de cada prompt para poder restaurarlo;
está excluido de Git. No incluyas secretos ni datos personales en los prompts y
protege el archivo en disco.

## 5. Matriz de riesgos: probabilidad por impacto

`puntuar_riesgo(probabilidad, impacto)` acepta enteros de 1 a 5 y calcula su
producto. Los niveles son: bajo (<4), medio (4-8), alto (9-14) y crítico (15+).
`ordenar_riesgos` presenta primero los puntajes mayores. Todo riesgo alto o
crítico marca `requiere_supervision_humana=True` y especifica su acción de
revisión en `punto_supervision`.

```console
python -m src.GATE_2.supervision_riesgos
python -m pytest tests/test_supervision_riesgos.py -q
```

La matriz de ejemplo puntúa por separado inyección de prompt (16), filtración
de PII en logs (15), sesgo por dataset desbalanceado (9), obsolescencia de
embeddings (8) y contexto desactualizado por chunks no reindexados (6). Revisa
probabilidad e impacto con evidencia del sistema real; estos números son solo
un ejemplo educativo.

## 6. Renombre del paquete

El paquete del proyecto se llama ahora `src/GATE_2`; imports, comandos y
documentación usan el nombre actualizado. Ejecuta las pruebas del bloque y el
verificador local desde la raíz:

```console
python -m pytest tests/test_supervision_riesgos.py tests/test_seguridad_rag.py tests/test_trazas_callbacks.py -q
python src/GATE_2/revision_gate_2.py --omitir-api
```

El vector store persistente existente puede conservar fuentes con rutas
anteriores al paquete actual. El registro y la evaluación migran esas rutas e
IDs sin una llamada de embeddings solo cuando el contenido, el nombre de
archivo y el índice del chunk coinciden exactamente con el corpus actual; los
vectores existentes se conservan. Si no se puede demostrar esa coincidencia,
el flujo informa el error y solicita reindexar. La reindexación completa
calcula embeddings con Gemini, requiere credenciales y puede consumir cuota.
Los archivos de historial y otros datos locales no se migran automáticamente.
