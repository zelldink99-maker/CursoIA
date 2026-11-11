# Bloque 25: réplica guiada de indexación y troubleshooting de vector stores

La réplica usa una política ficticia de devoluciones para comprobar el flujo de
chunking, validación local, embeddings, indexación y persistencia sobre un
corpus distinto al del Bloque 24. Su código está en
[`src/GATE_1/replica_corpus_ejemplo.py`](../src/GATE_1/replica_corpus_ejemplo.py);
no modifica la colección `curso_ia_corpus` ni la carpeta `vectorstore/`.

## Requisitos

- Python 3.10 o superior y un entorno virtual activo.
- Dependencias instaladas con `python -m pip install -r requirements.txt`.
  Incluyen `langchain-google-genai`, `langchain-text-splitters`,
  `langchain-chroma`, `chromadb` y `python-dotenv`.
- `GEMINI_API_KEY` definida en `.env` en la raíz del repositorio. El archivo
  `.env` está excluido de Git; no compartas ni publiques la clave.
- Permiso de escritura en la raíz del repositorio para crear
  `vectorstore_ejemplo/`, también excluida de Git.

## Ejecutar la réplica

Desde la raíz, corre:

```console
python -m src.GATE_1.replica_corpus_ejemplo
```

El programa divide cinco textos con `chunk_size=150` y `chunk_overlap=20`,
imprime los contenidos y comprueba que no hay chunks vacíos ni duplicados. En
este corpus, ningún texto se divide: el resultado es cinco chunks con longitudes
`106`, `103`, `99`, `85` y `97`, para un total de `490` caracteres, igual que
el corpus original. Estas comprobaciones ocurren antes de llamar a Gemini.

Luego carga la clave, usa `models/gemini-embedding-001` y guarda los vectores en
la ruta absoluta `vectorstore_ejemplo/`, bajo la colección explícita
`replica_corpus_ejemplo`. El script vuelve a abrir esa misma colección y espera
recuperar cinco chunks. La indexación llama a la API real y puede consumir
cuota. Los IDs estables evitan duplicar los cinco registros al volver a correr
la réplica.

Las pruebas locales no necesitan clave ni red:

```console
python -m pytest tests/test_replica_corpus_ejemplo.py -q
```

También puedes ejecutar el archivo de pruebas directamente; en ese modo
inicializa pytest por sí mismo:

```console
python tests/test_replica_corpus_ejemplo.py
```

## Guía de troubleshooting de vector stores

### Punto de partida recomendado

Usa la misma ruta absoluta y el mismo nombre de colección al indexar y al
consultar. Por ejemplo:

```python
import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

PERSIST_DIR = os.path.abspath("vectorstore")
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
vectorstore = Chroma(
    collection_name="corpus_ejemplo",
    embedding_function=embeddings,
    persist_directory=PERSIST_DIR,
)

print("Ruta del índice:", PERSIST_DIR)
print("Colección:", vectorstore._collection.name)
print("Chunks:", vectorstore._collection.count())
```

Una colección nueva muestra cero chunks; si el corpus ya fue indexado, mostrará
el total guardado.

### Instalación

- **`RuntimeError: Your system has an unsupported version of sqlite3. Chroma
  requires sqlite3 >= 3.35.0`:** la versión de SQLite disponible para Python es
  anterior a la requerida por Chroma. En Linux, puede instalarse
  `pysqlite3-binary` dentro del entorno. Antes de importar Chroma, reemplaza el
  módulo SQLite del proceso:

  ```python
  __import__("pysqlite3")
  import sys

  sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
  ```

- **`ModuleNotFoundError` para `langchain_chroma`,
  `langchain_text_splitters` o `langchain_google_genai`:** activa el entorno e
  instala las dependencias declaradas con
  `python -m pip install -r requirements.txt`.

### Autenticación y cuota

- **`ValidationError: ... API key required for Gemini Developer API`:** no se
  encontró `GEMINI_API_KEY` en el entorno. Confirma que `.env` está en la raíz
  y que `load_dotenv()` ocurre antes de crear los embeddings.
- **`API key not valid. Please pass a valid API key.`:** la clave existe, pero
  Gemini la rechazó. Verifica que no esté incompleta, vencida o asociada a otro
  proyecto.
- **`429 RESOURCE_EXHAUSTED`:** se alcanzó el límite de peticiones del modelo de
  embeddings. `con_reintentos` en la réplica vuelve a intentar hasta cuatro
  veces con esperas de 5, 10 y 20 segundos. Solo reintenta errores que contienen
  `429` o `RESOURCE_EXHAUSTED`; los demás errores se propagan. Si se agotan los
  intentos, espera y vuelve a ejecutar.

### Persistencia

- **El conteo de la colección recargada es cero:** compara la ruta absoluta que
  imprimen ambos scripts. Una ruta relativa se resuelve desde el directorio
  actual del proceso y puede apuntar a otra carpeta.
- **`PermissionError` al crear el vector store:** apunta a una carpeta del
  repositorio donde tengas permiso de escritura y verifica que exista la
  carpeta padre.

### Consistencia y nombre de colección

- **`InvalidArgumentError` por dimensiones distintas**, por ejemplo la
  colección espera 768 pero recibe 1536: los vectores se calcularon con modelos
  incompatibles. No fuerces la escritura; usa una carpeta/colección limpia y
  vuelve a indexar todo el corpus con un solo modelo. Conserva cualquier índice
  que necesites antes de retirarlo.
- **La búsqueda devuelve resultados irrelevantes:** confirma que los vectores
  de la colección fueron calculados con el mismo modelo. Cuando no puedas
  descartar una mezcla, crea un índice nuevo e indexa el corpus completo.
- **Error de validación del nombre:** Chroma admite entre 3 y 512 caracteres,
  letras, números, punto, guion y guion bajo; el nombre debe empezar y terminar
  con letra o número. Evita espacios y acentos; por ejemplo,
  `corpus_ejemplo`.
- **Colecciones fantasma o corpus mezclados:** no dejes el nombre por defecto
  `langchain`. Define un `collection_name` único y explícito para cada corpus,
  además de una ruta de persistencia coherente.
