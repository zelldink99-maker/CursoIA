# Bloque 27: evaluación de la recuperación RAG

Esta guía mide si el vector store trae los chunks pertinentes, primero con
métricas aisladas y luego contra el índice del proyecto. No evalúa la calidad de
la respuesta generada: una recuperación correcta no garantiza que el modelo
use bien el contexto.

## Métricas

- **Precisión@k**: IDs relevantes recuperados dividido por la cantidad de
  resultados que devolvió el recuperador. Si no devuelve resultados, vale `0.0`.
- **Recall@k (exhaustividad)**: IDs relevantes recuperados dividido por el total
  de IDs relevantes etiquetados. Si el caso no tiene ninguno, devuelve `None`
  porque no hay nada que recuperar.
- **F1**: media armónica de precisión y recall. Devuelve `None` si el recall no
  está definido y `0.0` si ambas métricas son cero.

Al variar `k`, el recall no puede bajar y la precisión puede bajar al añadir
resultados irrelevantes. Etiqueta los chunks relevantes leyendo el corpus antes
de consultar el recuperador; no ajustes las etiquetas para mejorar el número.

## Evaluación real del índice del proyecto

`src/GATE_1/evaluar_recuperacion.py` trae diez preguntas sobre las cinco fuentes
incluidas en `indexar_corpus.py`. El corpus actual genera IDs como
`src/GATE_1/cliente.py::chunk-0`; esos IDs se asignan explícitamente al indexar
y son parte de las etiquetas. Revisa las etiquetas si cambias el corpus o los
parámetros de chunking. Amplía el conjunto con preguntas que representen las
zonas difíciles de tus propios documentos.

Indexa el corpus si todavía no existe y ejecuta desde la raíz:

```console
python -m src.GATE_1.indexar_corpus
python -m src.GATE_1.evaluar_recuperacion --k 3
```

La indexación y cada búsqueda calculan embeddings con Gemini; hace falta
`GEMINI_API_KEY` y las llamadas pueden consumir cuota. El script imprime una
línea por pregunta y los promedios; los casos sin chunks relevantes muestran
`n/a` para recall y no entran en los promedios de recall ni F1. Cada ejecución
se agrega, sin sobrescribir, a `resultados_evaluacion.jsonl`, incluyendo fecha,
`k`, parámetros de chunking, métricas por pregunta y promedios de precisión,
recall y F1. El archivo local está excluido de Git.

Prueba el trade-off con un `k` mayor y compara ambas corridas:

```console
python -m src.GATE_1.evaluar_recuperacion --k 5
```

Los valores absolutos dependen del índice y del servicio. Para que las métricas
tengan sentido, conserva las mismas preguntas y etiquetas entre corridas y
verifica primero los casos individuales con recall bajo.

## Pruebas sin API

Desde la raíz:

```console
python -m pytest tests/test_evaluacion_recuperacion.py -q
```

Las pruebas verifican precisión, recall, F1, casos vacíos, promedios, IDs
explícitos y persistencia de varias corridas. Usan recuperadores simulados, no
llaman a Gemini ni al vector store persistido.

## Problemas frecuentes

- **Precisión y recall en cero:** confirma que `vectorstore/` corresponde al
  índice recién creado y que las etiquetas coinciden con sus IDs. El indexador
  usa `source::chunk-N`, no `doc0`, `doc1`, etc.
- **Error por ID explícito faltante:** reindexa con el indexador del proyecto;
  no evalúes comparando texto del chunk contra una etiqueta.
- **Recall `n/a`:** el conjunto tiene un caso sin chunks relevantes. Es válido
  para una pregunta que el corpus no responde; se excluye del promedio de recall.
- **Recall bajo en una pregunta:** el chunk etiquetado no apareció en el top-k.
  Inspecciona la pregunta, el chunk y los parámetros de chunking antes de subir
  `k` a ciegas.
