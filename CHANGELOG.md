# Changelog

Los cambios importantes del proyecto se documentan en este archivo.

## [No publicado] - 2026-11-11

### Añadido

- Réplica guiada del Bloque 25 con un corpus separado, colección Chroma propia,
  verificación de integridad, reintentos ante cuota 429 y guía de troubleshooting.
- Selector central `modeloIA` en `.env`, con `gemini-3.8-flash` como valor
  predeterminado y `gemini-3.5-flash` como alternativa.
- Factory compartida para inicializar clientes LangChain con el modelo
  seleccionado.
- Documentación del ajuste del modelo y de la limitación actual de las tarifas
  del estimador de costos, que corresponden a Gemini 3.8 Flash.
- Ejecución directa de `tests/test_replica_corpus_ejemplo.py` mediante pytest.

### Corregido

- Eliminadas las referencias de modelo fijas de las inicializaciones LangChain,
  endpoints HTTP y scripts de prueba para que todos lean la configuración común.
- Agregada la raíz del proyecto a `sys.path` al ejecutar directamente la prueba
  de réplica, evitando `ModuleNotFoundError: No module named 'src'`.
- Corregida la comprobación del modelo en el verificador local del proyecto.

### Validación

- La ejecución directa de la prueba de réplica completó 6 pruebas.
- La suite completa completó 106 pruebas; permanecen advertencias de
  obsolescencia de dependencias.
- Las pruebas y verificaciones locales no requirieron llamadas reales a Gemini.

## Historial anterior

### Agregar indexación RAG con Chroma persistente (2026-11-09)

- Se agregó un corpus del proyecto de cinco fuentes y chunking recursivo con
  metadatos `source` y `chunk_index`.
- Se añadió la indexación con `gemini-embedding-001` y Chroma persistido en
  `vectorstore/`; los IDs estables evitan duplicados al reindexar y se limpian
  chunks obsoletos de las fuentes del corpus.
- Se declaró `langchain-chroma` y se excluyó el índice regenerable de Git.
- Se agregaron pruebas locales de persistencia y recarga usando embeddings
  deterministas sin conexión a Gemini, y documentación del Bloque 24.
- Validación: 95 pruebas pasaron y `pip check` no detectó dependencias rotas.
  También se confirmó la ejecución real del indexador: `vectorstore/` contiene
  los archivos de Chroma y una reconexión desde un proceso nuevo devuelve
  `count() == 5`.

### Corregir el historial del agente ante respuestas estructuradas de Gemini (2026-11-09)

- Se normaliza la respuesta final del agente antes de guardarla en la memoria:
  los bloques `type=text` de Gemini se concatenan como texto para que el
  siguiente turno pueda reconstruir el historial correctamente.
- El agente informa explícitamente si recibe un formato de salida no compatible,
  en lugar de fallar después al preparar los mensajes del historial.
- Se agregó una prueba de regresión local que simula la respuesta estructurada y
  verifica dos turnos en una misma sesión. Validación: `python -m pytest -q`
  completó con 87 pruebas pasadas; permanecen avisos de obsolescencia de las
  APIs de memoria de LangChain.

### Depurar y consolidar scripts redundantes en la raíz para dejar un único flujo principal de producción

- Se definió `src/GATE_1/cliente.py` como flujo principal para consultar Gemini,
  con reintentos, validación de respuestas y registro de costos.
- `src/GATE_1/main.py` y `src/GATE_1/consumir_gemini.py` conservan sus interfaces
  por compatibilidad y delegan las consultas en el cliente principal.
- Se actualizó el gate para comprobar la delegación y la documentación para
  indicar el comando recomendado: `python -m src.GATE_1.cliente`.
- Validación: 25 pruebas pasaron y el gate local confirmó las comprobaciones del
  flujo. La API real se omitió; el gate aún reporta pendiente la actividad core
  (resultados y revisión manual incompletos).
