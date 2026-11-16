# Bloque 26: recuperación semántica y respuestas con citas

Este bloque conecta el índice persistido del Bloque 24 con una consulta RAG:
busca los chunks más cercanos a la pregunta, los presenta como contexto
numerado y pide al modelo responder solo con ese contexto y citar las fuentes.

## Ejecutar el flujo

Desde la raíz del proyecto:

```console
python -m src.GATE_1.recuperacion_citas
```

`src/GATE_1/recuperacion_citas.py` indexa el corpus del proyecto con sus
metadatos `source` y luego ejecuta dos preguntas de demostración. La búsqueda
usa `k=3` por defecto. `formatear_contexto` numera cada chunk como `[1]`, `[2]`,
etc. y conserva el mapa entre número y ruta fuente; `construir_prompt` limita la
respuesta al contexto e indica que el modelo admita cuando no alcance para
responder. `validar_citas` rechaza referencias a números que no se recuperaron
y exige citas cuando hay contexto, salvo que la respuesta sea una abstención.

La indexación y las búsquedas generan embeddings con Gemini; las respuestas
llaman al modelo configurado en `modeloIA`. Configura `GEMINI_API_KEY` en `.env`
antes de ejecutar. La ejecución puede consumir cuota. Las citas son referencias
propuestas por el modelo: comprueba cada afirmación contra el chunk y la fuente,
porque validar que el número exista no prueba que la afirmación sea correcta.

## Pruebas sin API

Desde la raíz:

```console
python -m pytest tests/test_recuperacion_citas.py -q
```

Las pruebas usan documentos, recuperador y modelo simulados. Comprueban la
numeración del contexto, el prompt, las fuentes, las abstenciones, el rechazo de
citas inexistentes y el flujo de dos preguntas sin llamar a Gemini.

## Problemas frecuentes

- **No hay resultados:** confirma que `vectorstore/` corresponde al índice del
  proyecto y que la indexación terminó correctamente.
- **Un chunk no tiene `source`:** reindexa con
  `src/GATE_1/indexar_corpus.py`, que agrega los metadatos de fuente.
- **Cita un número que no aparece en el contexto:** el validador detiene la
  respuesta; inspecciona el prompt y la salida del modelo antes de aceptarla.
- **El modelo no encuentra respuesta:** una abstención es esperable cuando los
  chunks recuperados no contienen información suficiente. Revisa primero la
  recuperación y luego el `k`; agregar resultados irrelevantes no garantiza
  una respuesta mejor.

La guía de preparación y persistencia del índice está en
[Bloque 24](bloque-24-indexacion-corpus-rag.md). Para medir si el recuperador
trae los chunks pertinentes, continúa con
[Bloque 27](bloque-27-evaluacion-recuperacion.md).
