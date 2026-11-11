# Bloque 24: indexación del corpus y persistencia de embeddings

Este bloque prepara documentación del proyecto para recuperación semántica
(RAG): divide un corpus propio en chunks, calcula embeddings de Gemini y
persiste los vectores en Chroma local. La indexación hace llamadas reales a
Gemini; las pruebas automatizadas no las hacen.

## Flujo de indexación

`src/GATE_1/indexar_corpus.py` incluye cinco documentos breves del proyecto:
reintentos, cálculo de costos, agente y memoria, trazas, y pruebas locales.
`RecursiveCharacterTextSplitter` los divide en fragmentos de hasta 400
caracteres, con 60 caracteres de solapamiento para conservar contexto cuando
un documento necesita más de un chunk. Cada fragmento conserva el `source` y
recibe un `chunk_index`.

El modelo `models/gemini-embedding-001` convierte cada fragmento en un vector.
`langchain-chroma` guarda texto, metadatos y embeddings en `vectorstore/`, en
la colección `curso_ia_corpus`. La clave se carga desde `.env` en la raíz y se
valida antes de inicializar el modelo. Indexar usa la API real de embeddings y
puede generar consumo facturable.

Desde la raíz, instala las dependencias y ejecuta:

```console
python -m pip install -r requirements.txt
python -m src.GATE_1.indexar_corpus
```

Al ejecutar el indexador, la salida muestra tres pasos: división e
indexación de los cinco chunks, verificación de los archivos reales de
`vectorstore/` y reconexión al índice persistido para contar los chunks
recuperados. Una ejecución correcta termina con cinco chunks recuperados.
Confirma que la carpeta contiene archivos, por ejemplo `chroma.sqlite3`, y no
está vacía. `vectorstore/` está excluida de Git porque se puede regenerar desde
el código y el corpus.

## Reindexar y reconectar

Los IDs se generan de forma estable por fuente y posición. Volver a ejecutar
el indexador actualiza los registros existentes en vez de duplicarlos; también
elimina chunks antiguos de las fuentes indexadas que ya no están en el corpus.
La colección es exclusiva de este indexador, no la uses para otros datos.

Para comprobar la persistencia tras reiniciar Python, abre un proceso nuevo
desde la raíz del proyecto y reconecta con la colección existente. Este ejemplo
cuenta los registros almacenados sin volver a indexar los documentos ni llamar
a `from_documents`:

```python
from src.GATE_1.indexar_corpus import abrir_vectorstore, crear_embeddings

vectorstore = abrir_vectorstore(crear_embeddings())
print(vectorstore._collection.count())  # 5
```

El resultado esperado es `5`, igual al número de chunks indexados. Reconectar
no recalcula los embeddings de los documentos; inicializar el modelo no los
solicita. Para hacer una búsqueda semántica (que sí calcula el embedding de la
consulta):

```python
resultados = vectorstore.similarity_search(
    "¿Cuántas veces reintenta el cliente antes de fallar?",
    k=3,
)
for documento in resultados:
    print(documento.metadata["source"], documento.page_content)
```

La búsqueda vectorial usa la API de Gemini para calcular el embedding de la
consulta. Reabrir y contar el índice por sí solos no hacen esa llamada ni
vuelven a calcular los embeddings almacenados.

## Pruebas locales

Desde la raíz:

```console
python -m pytest tests/test_indexar_corpus.py -q
```

Las pruebas usan embeddings deterministas de juguete junto con Chroma local
para comprobar chunking, metadatos, persistencia, recarga, reindexación sin
duplicados y eliminación de chunks obsoletos. No requieren clave ni conexión a
Gemini; estos embeddings solo son para probar el almacenamiento y no deben
usarse para recuperación semántica real.

El verificador general también comprueba el chunking local, sin generar
embeddings:

```console
python src/GATE_1/revision_gate_1.py --omitir-api
```

## Problemas frecuentes

- **Falta `GEMINI_API_KEY`:** configura la variable en `.env` en la raíz del
  proyecto antes de indexar.
- **`ModuleNotFoundError` para `langchain_chroma` o `chromadb`:** activa el
  entorno virtual e instala `requirements.txt`.
- **Error 429 o de conexión:** la indexación llama al servicio de embeddings;
  espera si alcanzaste el límite o corrige la conexión y vuelve a correr el
  indexador.
- **La búsqueda devuelve cero resultados:** comprueba que la ruta de
  persistencia sea `vectorstore/` desde la raíz y que el indexador haya
  terminado correctamente.
- **SQLite demasiado antiguo en Linux:** algunas instalaciones de Python
  incluyen SQLite anterior a la versión que requiere Chroma. Actualiza el
  SQLite del entorno de Python siguiendo la documentación de Chroma para tu
  plataforma antes de aplicar parches de importación al proceso.
- **Diagnóstico por etapa:** la guía consolidada de instalación, cuota,
  persistencia y consistencia del índice está en
  [docs/bloque-25-replica-corpus-ejemplo.md](./bloque-25-replica-corpus-ejemplo.md).

## Alcance y límites

El índice contiene solamente los cinco textos de ejemplo incluidos en el
script; no indexa automáticamente todos los archivos del repositorio. Para
incorporar documentos nuevos, añádelos a `CORPUS_DOCUMENTOS` con un `source`
único y vuelve a ejecutar el indexador. RAG recupera contexto relevante, pero
no garantiza por sí solo que la respuesta generada sea correcta.
