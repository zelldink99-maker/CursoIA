# Checklist verificable de Gate 2

Verificación realizada el **23 de noviembre de 2026**. Los comandos se
ejecutan desde la raíz del repositorio con `venv` activo.

## Cuatro criterios no compensables

- [x] **Pipeline de punta a punta:** `python -m pytest test_gate2.py -v`
  indexa en Chroma temporal, recupera documentos y genera una respuesta
  simulada sin excepciones.
- [x] **Citas verificables:** el servicio valida que la respuesta cite números
  recuperados y entrega el mapa de número a fuente. La consulta real también
  citó `src/GATE_2/cliente.py`.
- [x] **Logs sin pregunta ni PII crudos:** la prueba escribe un correo y una
  pregunta de prueba y confirma que no aparecen en el JSONL. El registro real
  tampoco contiene la pregunta completa.
- [x] **Supervisión humana ejecutable:** la prueba del grafo real confirma
  `__interrupt__`, reanuda el mismo `thread_id` con `Command(resume=True)` y
  verifica que la decisión queda en el estado final.

Ejecuta estas cuatro comprobaciones sin llamar a Gemini:

```console
python -m pytest test_gate2.py -v
```

## Seis dimensiones de la rúbrica

- [x] **Pipeline RAG (25 %):** índice persistido de cinco chunks base; las
  pruebas verifican persistencia, recarga y actualización incremental sin
  duplicados.
- [x] **Recuperación y citación (15 %):** las citas se validan contra fuentes
  recuperadas. La comparación del **23 de noviembre de 2026**, con diez
  preguntas, obtuvo precisión/recall/F1 de **1.000/1.000/1.000** con `k=1`,
  **0.500/1.000/0.667** con `k=2`; la corrida del 16 de noviembre obtuvo
  **0.333/1.000/0.500** con `k=3`. El servicio ahora usa `k=1` por defecto.
  La muestra tiene un chunk relevante etiquetado por consulta; ampliar antes de
  generalizar a otros corpus.
- [!] **Costo, latencia y operación (10 %):** la consulta real del 23 de
  noviembre registró 274 tokens de entrada, 446 de salida y un costo estimado
  de **USD 0.001878**. Latencia medida: embedding+búsqueda **1,510.31 ms**,
  generación **259,897.14 ms**, total **261,407.46 ms**. Una prueba posterior
  con `thinking_budget=0` y salida limitada no obtuvo respuesta: Gemini devolvió
  504 con `gemini-3.5-flash` y 503 por alta demanda con `gemini-3.8-flash`.
  Una prueba adicional con el SDK actualizado agotó un timeout de 25 s.
  Se acordó un objetivo operativo de **30 s máximo total por consulta** (no es
  umbral oficial del curso). La medición válida disponible, **261.4 s**, lo
  excede; no hay una medición posterior exitosa y no se considera resuelto.
- [x] **Personalización (15 %):** [`decision_personalizacion.md`](decision_personalizacion.md)
  compara RAG, fine-tuning y PEFT sobre este corpus y justifica RAG por la
  actualización de fuentes y la necesidad de citar.
- [x] **Observabilidad (15 %):** eventos JSON estructurados, `trace_id`,
  duración por etapa, tokens y costo estimado; los registros omiten pregunta,
  respuesta y documentos crudos.
- [x] **Seguridad y gobernanza (20 %):** filtro de inyección antes de armar el
  contexto, versionado de prompts, pausa humana real y cinco riesgos. Cada
  riesgo alto/crítico tiene un `punto_supervision` concreto.

Los valores de precisión y latencia son evidencia, no umbrales de aprobación:
la rúbrica compartida no fija mínimos por dimensión. No se asigna aquí un
promedio propio de 0-100; debe basarse en la revisión honesta de las seis
dimensiones, no en los puntajes ilustrativos de `rubrica_gate2.py`.

## Comprobaciones manuales de entrega

- [x] **Entorno:** Python 3.14.7; `pytest`, `langchain-chroma`,
  `langchain-core` y `langgraph` importan en el entorno del proyecto.
- [x] **Secreto ignorado:** `git check-ignore .env` imprime `.env`. La clave
  está configurada y la consulta real terminó correctamente; nunca se imprime
  ni se incluye en el repositorio.
- [x] **Índice persistido:** `vectorstore/` contiene cinco registros con
  metadatos de fuente y archivos en disco. `python -m src.GATE_2.preflight_rag`
  confirma índice no vacío y regla de exclusión.
- [x] **Consulta real:** `python -m src.GATE_2.registro_rag --pregunta "¿Qué errores reintenta el cliente y cuántos intentos hace?" --k 3`
  completó recuperación y generación, citó fuentes y guardó consumo y latencia.
- [x] **Pruebas automatizadas:** la suite completa pasó: **195 pruebas**, sin
  fallos. Queda un aviso upstream de Chroma por `asyncio.iscoroutinefunction`
  en Python 3.14; Chroma 1.5.9 es la versión más reciente disponible.
- [!] **Verificador general heredado:** `python src/GATE_2/revision_gate_2.py --omitir-api`
  termina con código 1 porque `resultados_actividad_core.json` contiene solo
  1 de las 20 respuestas requeridas; el intento de generar la siguiente agotó
  tres timeouts de 30 s. `resultados_metricas.json` conserva sus 3 resultados
  heredados por separado y no se mezclan porque no corresponden al lote actual.
  Siguen faltando las 10
  revisiones manuales y sus límites documentados. Es un pendiente anterior a
  Gate 2; la opción
  `--omitir-api` también omite deliberadamente la API, aunque la consulta real
  de Gate 2 se ejecutó por separado y tuvo éxito.
- [ ] **Estado Git para entrega:** este trabajo deja cambios locales sin
  confirmar. Antes de entregar, revisa `git diff`, crea el commit de entrega y
  verifica que `git status` quede limpio. No se creó ni publicó un commit.

## Comandos de cierre

```console
python -m pytest test_gate2.py -v
python -m pytest -q
python -m src.GATE_2.preflight_rag
python rubrica_gate2.py
python src/GATE_2/revision_gate_2.py --omitir-api
git check-ignore .env
git status
git log -1
```
