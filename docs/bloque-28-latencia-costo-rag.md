# Bloque 28: latencia y costo del flujo RAG

Una consulta RAG tiene varias etapas: embedding de la pregunta, búsqueda local
en Chroma y generación de la respuesta. El registro del proyecto mide
embedding+búsqueda y generación por separado y guarda los tokens reales
informados por LangChain. Calcula el costo estimado en USD con la tarifa
configurada para el modelo; si faltan metadatos de uso, no inventa un costo.

Para esta entrega se acordó un objetivo operativo de **30 segundos máximo por
consulta completa**; no es un umbral oficial de la rúbrica. La medición real
anterior fue de **261.4 s** y, por tanto, no cumple ese objetivo. No se marcará
como resuelto hasta obtener una llamada real exitosa por debajo de 30 s.

## Registrar consultas reales

Desde la raíz, registra una consulta:

```console
python -m src.GATE_2.registro_rag --pregunta "¿Qué errores reintenta el cliente?"
```

El servicio usa `k=1` por defecto a partir de la comparación del corpus; puedes
pasar `--k` explícitamente para medir otro valor.

Para ver en consola el resumen de la actividad de la imagen, ejecuta el modo
core:

```console
python -m src.GATE_2.registro_rag --actividad-core
```

Este modo registra tres preguntas distintas con `k=1`, luego repite la primera
con `k=1` y `k=2`, imprime los `input_tokens` de la comparación y confirma el
número total de líneas del JSONL. Son cinco consultas de generación reales y
pueden consumir cuota. El modo normal sigue registrando una consulta para evitar
ese costo adicional accidental.

Se pueden enviar varias preguntas en una ejecución repitiendo `--pregunta`:

```console
python -m src.GATE_2.registro_rag --k 1 `
  --pregunta "¿Qué errores reintenta el cliente?" `
  --pregunta "¿Cómo se calcula el costo de Gemini?" `
  --pregunta "¿Qué guarda el sistema en las trazas?"
```

En Linux o macOS, reemplaza el acento grave de continuación por `\` o escribe
todo el comando en una línea. Cada pregunta llama al modelo y puede generar
costo de API; la recuperación también llama a Gemini para calcular el embedding.

Para comprobar cómo cambia la entrada al aumentar `k`, ejecuta la misma pregunta
con ambos valores:

```console
python -m src.GATE_2.registro_rag --pregunta "¿Qué errores reintenta el cliente?" --k 1
python -m src.GATE_2.registro_rag --pregunta "¿Qué errores reintenta el cliente?" --k 2
```

Cada ejecución agrega una línea JSON independiente a
`registros_latencia_costo.jsonl`; no reemplaza registros anteriores y el archivo
local está excluido de Git. El objeto contiene `timestamp`, `pregunta_len`,
`trace_id`, `k`, `tiempos_ms` (`embed_y_busqueda` y `generacion`),
`tiempo_total_ms`, `tokens`, `costo_estimado_usd` y eventos. No guarda la
pregunta, la respuesta ni el contenido de documentos en texto. Los tokens
vienen de `usage_metadata`; si el proveedor no informa uso, `tokens` y
`costo_estimado_usd` quedan en `null`.

Para revisar el historial guardado, lee cada línea como un objeto JSON:

```python
import json

with open("registros_latencia_costo.jsonl", encoding="utf-8") as archivo:
    for linea in archivo:
        registro = json.loads(linea)
        tokens = registro["tokens"]
        tokens_entrada = (
            tokens["input_tokens"] if tokens is not None else None
        )
        print(
            f"k={registro['k']}  input_tokens={tokens_entrada}  "
            f"costo_estimado_usd={registro['costo_estimado_usd']}  "
            f"total={registro['tiempo_total_ms']} ms  "
        )
```

El costo registrado es una estimación con la tarifa del modelo, no una factura;
verifica los precios vigentes en
[la decisión de arquitectura](decision-arquitectura.md#precios-oficiales-y-cálculo-de-costo).
El detalle de tokens es la fuente apropiada para comparar el consumo; los
tiempos de red varían entre corridas.

## Preflight local del checklist

Antes de gastar cuota, comprueba sin API que el índice exista, no esté vacío y
esté excluido de Git:

```console
python -m src.GATE_2.preflight_rag
```

El comando termina con estado `0` y muestra `Preflight OK` si ambas condiciones
se cumplen; si falta el índice o la regla de `.gitignore`, imprime cada
problema y termina con estado `1`. No indexa, no modifica archivos y no requiere
credenciales.

## Checklist de mantenimiento

Antes de comparar resultados, confirma que:

- el índice persistido existe, se creó con metadatos `source` e IDs explícitos
  y está excluido de Git;
- las etiquetas de evaluación se revisaron sin mirar las salidas del retriever;
- guardaste evaluaciones anteriores con sus valores de `k` y chunking;
- una consulta idéntica no cambió de forma inesperada y `k` mayor suele aportar
  al menos el mismo recall a cambio de más chunks de contexto;
- `tiempos_ms` contiene `embed_y_busqueda` y `generacion`, y
  `tiempo_total_ms` es su suma;
- comparaste varias preguntas antes de sacar conclusiones sobre costo o latencia.
- `tiempo_total_ms` de cada consulta real no excede el objetivo operativo de
  30,000 ms; si el proveedor devuelve error, esa corrida no cuenta como medida
  válida.

## Pruebas locales

Las pruebas usan dobles para embeddings, Chroma y modelo; no requieren clave,
red ni una llamada real:

```console
python -m pytest tests/test_registro_rag.py -q
python -m pytest tests/test_preflight_rag.py -q
```

## Problemas frecuentes

- **Falta `GEMINI_API_KEY`:** crea `.env` desde `.env.example` y define la clave
  antes de ejecutar el registro real.
- **El índice no tiene chunks:** indexa con
  `python -m src.GATE_2.indexar_corpus` antes de medir; el registro aborta antes
  de consultar el modelo para no generar una respuesta sin contexto.
- **No hay resultados o las citas no tienen fuente:** comprueba que el vector
  store sea el del proyecto y que sus documentos tengan metadatos `source`.
- **`tokens` aparece como `null`:** la respuesta no entregó `usage_metadata`;
  conserva también el costo como `null` y verifica la respuesta del proveedor.
- **El tiempo de generación es mayor que la búsqueda:** es normal; generación
  procesa el prompt y produce tokens, mientras que Chroma realiza la búsqueda
  localmente.
