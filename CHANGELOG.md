# Changelog

Los cambios importantes del proyecto se documentan en este archivo.

## Updates - 2026-11-23 — Integración final de Gate 2

Responsable: Igor Inostroza

### Añadido

- `test_gate2.py`: autochequeo integrado de pipeline, citas, privacidad de
  registros y pausa/reanudación de supervisión humana.
- `rubrica_gate2.py` y `tests/test_rubrica_gate2.py`: cálculo ponderado con
  validación de puntajes y criterios no compensables; la prueba también puede
  ejecutarse directamente con Python.
- `docs/checklist_gate2.md`: evidencia de las seis dimensiones, criterios
  obligatorios, corrida real y pendientes de entrega.

### Cambiado

- `src/GATE_2/registro_rag.py`: integra respuesta citada, fuentes, `trace_id`,
  latencias, tokens y costo estimado por consulta; los registros no guardan
  pregunta, respuesta ni documentos en texto crudo.
- `src/GATE_2/preflight_rag.py`: además de comprobar `.gitignore`, detecta
  directorios de índice vacíos.
- `src/GATE_2/supervision_riesgos.py`: asigna un punto concreto de supervisión
  humana a cada riesgo de nivel alto o crítico.
- `docs/decision_personalizacion.md`: aplica la comparación RAG, fine-tuning y
  PEFT al corpus y al servicio de este repositorio.
- README y guías de los Bloques 28, 31 y 32: documentan el costo registrado,
  privacidad, supervisión y checklist de entrega.
- Servicio de recuperación: se fijó `k=1` como valor por defecto tras evaluar
  diez preguntas del corpus; quedaron documentadas las métricas comparativas
  para `k=1`, `k=2` y `k=3`.
- Bloque 28: se documentó un objetivo operativo acordado de 30 s máximo por
  consulta; la medición real de 261.4 s aún no lo cumple.
- Bloque 22: se migró la memoria de conversación desde las clases obsoletas de
  LangChain a un `StateGraph` con `InMemorySaver`.
- `requirements.txt`: se actualizó el conector Gemini para usar el SDK 3.x
  compatible y una versión de `langchain-core` que satisface su requisito.
- `.gitignore`: excluye `.env` y variantes, conservando `.env.example`.
- `.gitignore`: excluye también el lote local `resultados_actividad_core.json`.
- `.env.example`: aclara que la clave configurada es de Gemini.

### Validación

- Suite completa: 195 pruebas pasaron; tras la migración de memoria y la
  actualización del SDK, queda un aviso upstream de Chroma por
  `asyncio.iscoroutinefunction` en Python 3.14.
- `compileall` compiló el código Python del proyecto y las entradas de Gate 2.
- `pip check` no encontró dependencias rotas y todos los requisitos declarados
  están instalados en rango.
- Preflight confirmó el índice persistido y la exclusión de secretos.
- Una consulta real completó con fuentes y sin persistir la pregunta cruda;
  registró 720 tokens y un costo estimado de USD 0.001878. La latencia total
  medida fue 261,407.46 ms.
- `revision_gate_2.py --omitir-api` confirmó el código y las dependencias, pero
  mantiene pendiente la actividad core del Bloque 17: hay 1 respuesta de 20
  en el archivo del lote actual y faltan las revisiones manuales requeridas.
- `requirements.txt` actualizado a `google-genai` 3.x, `langchain-google-genai`
  4.5.2 y `langchain-core` 1.8.4; `pip check` no detectó conflictos.
- Evaluación de recuperación del 23 de noviembre (10 preguntas): `k=1`
  precisión/recall/F1 **1.000/1.000/1.000**; `k=2` **0.500/1.000/0.667**.
- La regeneración de las respuestas del Bloque 17 guardó una respuesta antes de
  que la siguiente agotara tres reintentos de timeout; no se inventaron las
  respuestas restantes ni revisiones. La consulta RAG con
  `thinking_budget=0` también falló (504 con `gemini-3.5-flash`; 503 de alta
  demanda con `gemini-3.8-flash`). Una consulta adicional con el SDK actualizado
  agotó un timeout de 25 s; no se inventaron resultados ni revisiones.

## [No publicado] - 2026-11-19

### Añadido

- Bloque 32 consolidado en un único script para versionado y diff de prompts,
  supervisión humana con LangGraph y matriz de al menos cinco riesgos.
- Se agregó `src/GATE_2/unidad_completa_supervision.py`, que reproduce en consola los tres
  pasos: versiones y diff, interrupción/aprobación y matriz ordenada por puntaje.
- Se agregó `--demo-trazas` al módulo RAG para reproducir localmente, sin API,
  el flujo de dos consultas, el descarte por inyección y la separación de
  `trace_id` mostrada en las demostraciones del Bloque 31.
- El ejemplo generado de decisión de personalización se movió a
  `docs/decision_personalizacion.md`; el módulo escribe ese destino por defecto
  y conserva rutas explícitas como opción.
- Se agregó el documento generado a la sección de documentación adicional del
  README y se excluyó también su ruta dentro de `docs/`.
- Dependencia `langgraph>=1.2.11,<2` para ejecutar el punto de interrupción
  y reanudar aprobaciones o rechazos con booleanos.
- Bloque 31 con callbacks correlacionados para retriever y LLM, mitigación
  heurística de inyección en documentos RAG, trazas por consulta sin texto
  sensible, versionado de prompts con aprobación humana y matriz de riesgos.
- Se agregó `src/GATE_2/privacidad_logs.py` para redactar correos y teléfonos
  antes de persistir entradas, herramientas, observaciones y respuestas.
- Se excluyeron cachés, secretos, trazas, resultados locales, decisiones
  generadas y versiones de prompts en `.gitignore`; los resultados ya
  versionados se dejaron sin seguimiento para no subirlos nuevamente.
- Se agregaron módulos para filtros RAG, callbacks correlacionados y supervisión
  de riesgos bajo `src/GATE_2`.
- Pruebas locales para el filtro de documentos, roles del prompt, callbacks,
  persistencia de versiones, interrupción humana y puntajes de riesgo.
- Se agregó `tests/test_bloque32.py` para verificar la salida consolidada.

### Cambiado

- Renombrado el paquete del proyecto a `src/GATE_2`; se actualizaron imports,
  comandos, pruebas y documentación, incluido `revision_gate_2.py`.
- La normalización del paquete y sus rutas quedó aplicada de forma consistente
  en código, comandos, pruebas y documentación mantenida.
- Los registros RAG nuevos correlacionan eventos por `trace_id` y guardan la
  longitud de la pregunta, no la pregunta, el prompt ni el contexto recuperado.
- Las trazas del agente redactan correos y teléfonos detectables antes de
  persistir entradas, argumentos de herramientas, observaciones y respuestas.
- Los prompts RAG separan `SystemMessage` y `HumanMessage`, delimitan y escapan
  el contexto como dato no confiable y descartan documentos con patrones
  conocidos de inyección.
- La reindexación del corpus elimina fuentes de código obsoletas de la
  colección del proyecto y conserva entradas fuera de `src/`.
- Los flujos de registro y evaluación migran rutas e IDs obsoletos del índice
  al verificar una coincidencia exacta de contenido, sin recalcular embeddings.
- El índice persistente migra automáticamente las rutas del paquete anterior
  cuando los documentos coinciden exactamente; si no coinciden, solicita
  reindexación en vez de usar referencias ambiguas.
- La versión inicial y nueva del prompt de ejemplo muestran huellas abreviadas
  de 12 caracteres y el diff del Bloque 32.

### Seguridad

- El verificador `revision_gate_2.py` captura `KeyboardInterrupt` durante la
  carga de módulos y al salir del proceso, informa la cancelación y evita
  mostrar un traceback de Python.
- `prompts/versiones_prompt.jsonl` conserva el contenido de prompts para poder
  reanudar versiones; está excluido de Git y debe tratarse como dato sensible.
- El filtro de frases es una mitigación parcial: no detecta toda variante de
  inyección y no reemplaza la supervisión humana.
- La redacción de PII en trazas es heurística y no reemplaza controles de acceso,
  retención ni revisión humana.

### Validación

- Ejecutados 185 pruebas locales.
- `src/GATE_2/unidad_completa_supervision.py` mostró correctamente los tres pasos y el
  punto de supervisión aprobado.
- El verificador local renombrado se ejecutó con `--omitir-api`.
- Las pruebas completas no hicieron llamadas reales a Gemini.

## [No publicado] - 2026-11-16

### Añadido

- Réplica guiada del Bloque 25 con un corpus separado, colección Chroma propia,
  verificación de integridad, reintentos ante cuota 429 y guía de troubleshooting.
- Script RAG de reindexación, recuperación y respuestas con contexto y fuentes
  numeradas; incluye dos preguntas de demostración y pruebas con dobles locales.
- Guía propia del Bloque 26 para recuperación semántica, contexto numerado,
  citas, límites y pruebas sin API.
- Evaluación de recuperación RAG con precisión, recall y F1 por pregunta,
  etiquetas basadas en los IDs estables del corpus y registro acumulativo de
  resultados JSONL.
- Instrumentación de consultas RAG reales para medir embedding, búsqueda y
  generación y conservar los tokens reales reportados por el modelo;
  modo `--actividad-core` con comparación de `k` y resumen del archivo JSONL.
- Preflight local sin API para detectar un índice ausente o no excluido de Git.
- Guías de los Bloques 27 y 28 y pruebas locales para métricas, casos borde,
  persistencia de resultados y medición sin llamadas de red.
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

- Se definió `src/GATE_2/cliente.py` como flujo principal para consultar Gemini,
  con reintentos, validación de respuestas y registro de costos.
- `src/GATE_2/main.py` y `src/GATE_2/consumir_gemini.py` conservan sus interfaces
  por compatibilidad y delegan las consultas en el cliente principal.
- Se actualizó el gate para comprobar la delegación y la documentación para
  indicar el comando recomendado: `python -m src.GATE_2.cliente`.
- Validación: 25 pruebas pasaron y el gate local confirmó las comprobaciones del
  flujo. La API real se omitió; el gate aún reporta pendiente la actividad core
  (resultados y revisión manual incompletos).
