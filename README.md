# Plantilla de repositorio base — Especialización en Desarrollo con IA Generativa (Accenture)

<p align="center">
  <img src="docs/IA.jpg" alt="Inteligencia artificial aplicada al desarrollo" width="800">
</p>

Esta es la estructura base del proyecto para la Especialización en Desarrollo
con IA Generativa. Se irá ampliando bloque a bloque hasta llegar a la
aplicación completa del Gate 3. En este repositorio se practica el envío de
preguntas a la API de Gemini, la medición de latencia, la estimación del costo
de los tokens de una respuesta y la validación local de módulos auxiliares del
proyecto.

## Ficha de diseño funcional — Bloques 33 y 34

El proyecto propio está documentado en
[docs/ficha_diseno_funcional.md](docs/ficha_diseno_funcional.md). La ficha
describe los requerimientos del asistente de revisión de datos post-ETL, sus
criterios de aceptación y el plan de construcción por hitos.
El conjunto pequeño y reproducible para comprobar los reportes está en
[data/ventas_prueba.csv](data/ventas_prueba.csv).
Sus registros de ventas corresponden a noviembre de 2026.

El diagrama de arquitectura se encuentra en
[docs/diagrama_arquitectura.png](docs/diagrama_arquitectura.png). Para
regenerarlo desde la raíz:

```console
python scripts/generar_diagrama_arquitectura.py
```

Para comprobar la estructura inicial de la ficha:

```console
python verificar_ficha.py
```

Los scripts `ficha_datos.py` y `resumen_ficha.py` leen la ficha y muestran la
cobertura de criterios, requerimientos y horas planificadas. Para verificar
las cinco secciones y el registro de revisión cruzada:

```console
python resumen_ficha.py
python verificar_ficha_completa.py
```

La verificación integral comprueba el formato y la coherencia del registro en
`docs/revision_alcance.md`, incluida la identificación del revisor, la fecha,
los hallazgos y sus decisiones.

El presupuesto ilustrativo puede ajustarse y ejecutarse desde la raíz:

```console
python presupuesto/presupuesto_alcance.py
```

## Cómo empezar

Después de clonar el repositorio o descomprimir el proyecto, abre una terminal
en la carpeta raíz. Usa Python 3.10 o superior y crea un entorno virtual para
instalar las dependencias sin modificar la instalación global de Python.

### Linux

En Debian o Ubuntu, si la creación del entorno virtual falla porque no está
instalado el módulo `venv`, instálalo con `sudo apt install python3-venv`.
Luego ejecuta:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

En otras distribuciones, instala el paquete de `venv` correspondiente a tu
versión de Python si fuera necesario.

### macOS

Comprueba que Python 3 esté disponible con `python3 --version`. Si no lo está,
instálalo desde [python.org](https://www.python.org/downloads/macos/) o con
Homebrew (`brew install python`). Después ejecuta:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

En todos los sistemas, edita `.env` y reemplaza `tu_llave_aqui` por tu clave
real de Gemini. Define también `modeloIA=gemini-3.8-flash` (o
`modeloIA=gemini-3.5-flash`) para seleccionar el modelo compartido por los
clientes del proyecto. No compartas ni subas ese archivo: `.gitignore` lo excluye.
Cuando termines de trabajar, puedes salir del entorno virtual con `deactivate`.

> **Importante:** no instales paquetes con `pip install dotenv` ni directamente
en el Python del sistema. Este proyecto necesita `python-dotenv` (declarado
en `requirements.txt`), y la instalación debe hacerse con el entorno virtual
activado mediante `python -m pip install -r requirements.txt`. Esto también
evita el error `externally-managed-environment` de distribuciones Linux que
aplican PEP 668.

## Requisitos

- Python 3.10 o superior.
- Una clave de API de Gemini.
- Conexión a internet para consultar la API real.

## Medir latencia y costo

Desde la raíz del repositorio ejecuta:

```console
python src/GATE_2/latencia.py
```

La clase `Latencia`, definida en `src/GATE_2/latencia.py`, realiza cuatro
solicitudes con la pregunta de prueba predeterminada. Informa el tiempo de cada
solicitud, el promedio y una estimación del costo de la última respuesta.
Todos los clientes leen el modelo de `modeloIA` en `.env`; el valor
predeterminado es `gemini-3.8-flash`. Ejecuta el archivo directamente como se
muestra; no uses `-m src.GATE_2.latencia`, ya que sus imports de módulos
hermanos no están configurados para la ejecución como módulo de paquete.

## Consultar tokens de una respuesta

La respuesta JSON de Gemini se conserva completa al volver de
`enviar_peticion`; además del contenido generado puede incluir `usageMetadata`
con los tokens de entrada, salida y total. `monolitico.py` proporciona el
transporte de bajo nivel usado por el cliente principal. Para consultar el
modelo en el flujo de producción, usa `src/GATE_2/cliente.py`, que aplica
reintentos y registra el costo con los metadatos de uso.

El módulo `src/GATE_2/costo.py` calcula el costo a partir del uso reportado y
los precios oficiales documentados para Gemini 3.8 Flash. Si seleccionas otro
modelo en `modeloIA`, verifica y actualiza primero sus tarifas: el estimador usa
las constantes actuales de 3.8 Flash. Consulta
[la decisión de arquitectura](docs/decision-arquitectura.md#precios-oficiales-y-cálculo-de-costo).
El modelo aceptado y el factory común de LangChain se prueban sin red con
`python -m pytest tests/test_configuracion.py -q`.

## Cliente modular: reintentos y costo por operación

El cliente `src/GATE_2/cliente.py` ofrece `consultar_modelo(pregunta)` como
interfaz única: valida y arma la solicitud, consulta Gemini, extrae el texto y
registra el costo estimado de cada respuesta exitosa. La instrucción del sistema
es opcional; si no se entrega, se usa una instrucción predeterminada no vacía,
tal como exige el constructor de solicitudes del proyecto.

El costo se calcula con los contadores reales de `usageMetadata` y las tarifas
configuradas en `costo.py`: tokens de entrada al precio de entrada, y tokens de
salida más los tokens de pensamiento (si Gemini los informa por separado) al
precio de salida. Durante el ensayo de diez consultas se imprime el total de
tokens reportado, el costo de esa operación y el acumulado. La ejecución de
una sola consulta muestra la respuesta y el costo acumulado al final. Si faltan
metadatos válidos, el cliente informa el error en vez de asignar un costo
inventado. `costo_total_sesion` guarda el acumulado en memoria mientras el
proceso está en ejecución; no se persiste en disco ni representa una factura.

`src/GATE_2/cliente_reintento.py` reintenta errores transitorios (429, 5xx,
timeout y conexión) hasta tres intentos totales por defecto. Entre intentos
aplica backoff exponencial con jitter y un techo de 30 segundos por espera. Los
mensajes de reintento indican el número de intento y la espera calculada. No
reintenta errores de autenticación (401/403) ni otros errores HTTP permanentes.
El envío conserva la clave en el encabezado y usa el timeout de 30 segundos de
`monolitico.py`.

### Flujo principal de producción: una consulta

Desde la raíz, ejecuta el único flujo principal de consulta. Llama una vez a
`consultar_modelo`, imprime la respuesta y el costo acumulado:

```console
python -m src.GATE_2.cliente
```

`src/GATE_2/main.py` se conserva como lanzador compatible y
`consumir_gemini.py` como interfaz de compatibilidad; ambos delegan en este
mismo cliente. Para nuevas ejecuciones, usa el comando anterior.

### Ensayo de diez consultas (evaluación, no producción)

Para ejecutar las diez preguntas de prueba (cada una puede generar costo), usa
desde la raíz:

```console
python -c "from src.GATE_2.cliente import ejecutar_ensayo; raise SystemExit(ejecutar_ensayo())"
```

El ensayo imprime la respuesta resumida y, debajo, los tokens reportados, el
costo de esa operación y el costo acumulado. Un fallo transitorio que agota
los tres intentos se registra como fallo y el ensayo continúa con la pregunta
siguiente. Un error permanente (por ejemplo, credenciales incorrectas o una
solicitud HTTP inválida) se informa y detiene el ensayo. En el peor caso, diez
preguntas podrían realizar hasta 30 solicitudes, además de las esperas entre
reintentos.

Los errores 401/403 se clasifican como problemas de credenciales y no se
reintentan. Los errores 429, 5xx, timeout y conexión se consideran transitorios;
al agotarse los intentos, `consultar_modelo` los comunica como
`ServicioNoDisponibleError` (subclase de `RuntimeError`). Los demás errores HTTP,
errores de configuración y respuestas inválidas se propagan con su tipo
específico.

Para comprobar la lógica interna del cliente sin llamadas de red, demoras ni
costo de API, ejecuta las pruebas unitarias con pytest:

```console
python -m pytest tests/test_cliente.py -v
```

También puedes ejecutar el archivo de pruebas directamente; prepara la ruta
del proyecto y lanza pytest automáticamente:

```console
python tests/test_cliente.py
```

La suite usa mocks para la API y el tiempo. Cubre clasificación HTTP, el camino
feliz, reintentos, agotamiento, validación y acumulación de costos y manejo de
errores del cliente. El paquete `pytest` está declarado en `requirements.txt`;
instala o actualiza el entorno con:

```console
python -m pip install -r requirements.txt
```

El verificador general local también ejecuta comprobaciones simuladas:

```console
python src/GATE_2/revision_gate_2.py --omitir-api
```

## Pipeline de texto y evaluación de salidas

Además de la consulta a Gemini, el proyecto incluye un flujo local para limpiar,
comparar y evaluar texto antes de interpretar la respuesta del modelo:

- `src/GATE_2/pipeline_texto.py`: limpia el texto, elimina puntuación y espacios
  extra, tokeniza, genera conteos por palabra y calcula coincidencias,
  precisión, cobertura y F1 sin perder las repeticiones.
- `src/GATE_2/evaluar_salidas.py`: compara la respuesta del modelo con una
  referencia usando métricas sobre texto crudo y texto normalizado.
- `src/GATE_2/evaluar_metricas.py`: evalúa varias respuestas reales, conserva
  respuesta y métricas en `resultados_metricas.json`, calcula promedios y
  muestra primero los casos con menor F1.
- `src/GATE_2/revisar_cualitativamente.py`: prepara una muestra de los F1 más
  bajos y más altos en `revision_manual.json`, lista para completar a mano
  con una rúbrica de corrección factual, completitud y contradicción.

La precisión mide qué proporción de las palabras generadas aparece en la
referencia; la cobertura mide qué proporción de la referencia aparece en la
respuesta. F1 combina ambas. La coincidencia cuenta repeticiones, pero sigue
siendo léxica: no reconoce sinónimos y puede puntuar alto una respuesta con un
número equivocado o una negación omitida. Por eso estas métricas ayudan a
priorizar revisiones, pero no determinan por sí solas si una respuesta es
correcta.

Para ejecutar el conjunto de tres consultas de ejemplo desde la raíz (cada
consulta puede generar costo de API):

```console
python -m src.GATE_2.evaluar_metricas
```

El archivo JSON se actualiza después de cada respuesta exitosa, de modo que
los resultados parciales se conservan si una consulta posterior falla. Para
generar los 20 resultados requeridos por la actividad core (20 consultas, que
pueden generar costo de API), ejecuta de forma explícita:

```console
python -m src.GATE_2.evaluar_metricas --actividad-core
```

Este modo guarda el lote en `resultados_actividad_core.json` para no sobrescribir
`resultados_metricas.json`; si una ejecución se interrumpe, volver a ejecutar
este modo reutiliza las respuestas ya guardadas y consulta únicamente las
pendientes. Después, prepara la muestra para revisar sin volver a llamar a la
API:

```console
python -m src.GATE_2.revisar_cualitativamente
```

El comando selecciona cinco casos con F1 más bajo y cinco con F1 más alto, y
guarda `revision_manual.json`. Lee cada respuesta junto a su referencia;
completa corrección factual y completitud (`sí`, `no` o `parcialmente`),
contradicción (`sí` o `no`) y una explicación en `nota`. No rellenes la rúbrica
automáticamente: requiere tu juicio manual.

Cada ejecución vuelve a generar `revision_manual.json` desde los resultados y
reemplaza el archivo anterior, incluidas las calificaciones manuales que
contuviera. Completa la revisión después de generar la plantilla.

Si todavía tienes menos de 20 resultados, el revisor igualmente prepara una
muestra parcial de los casos disponibles y advierte que la actividad sigue
incompleta. Puedes revisarlos mientras generas más respuestas; el gate no dará
por cumplido el mínimo hasta tener 20 resultados y 10 revisiones.

El revisor usa `resultados_actividad_core.json` si existe; si no, lee
`resultados_metricas.json`. Este último debe contener al menos 20 resultados
para cumplir la actividad core. Si tus resultados están en otro archivo,
indícalo con `--entrada ruta\al\archivo.json`.

Al terminar, actualiza las cuatro secciones de
[docs/limites_metrica.md](docs/limites_metrica.md) con los conteos, la fecha, el
criterio de selección y ejemplos concretos enlazados a consultas y F1 de tu
`revision_manual.json`. El gate devuelve un código de salida distinto de cero
mientras falten los resultados, las diez revisiones o los hallazgos
documentados. Omitir la comprobación real de API con `--omitir-api` no provoca
un fallo por sí solo.

Para probar las funciones sin conexión ni costo de API:

```console
python -m pytest tests/test_pipeline_texto.py -q
python -m pytest tests/test_evaluar_metricas.py -q
python -m pytest tests/test_revisar_cualitativamente.py -q
```

## LangChain: primera chain de tres pasos (Bloque 18)

El proyecto incluye `src/GATE_2/cadena_tres_pasos.py`, que transforma texto
técnico mediante tres etapas encadenadas:

1. Extrae tres puntos clave.
2. Los reescribe en lenguaje sencillo.
3. Los convierte en viñetas Markdown.

Cada etapa tiene su propio `PromptTemplate`, utiliza `StrOutputParser` para
pasar texto plano al siguiente paso y conecta los nombres de entrada con
`RunnableLambda`. `construir_cadena(modelo)` recibe el modelo desde afuera, lo
que permite probar todo el flujo con respuestas simuladas.

Instala las dependencias desde el entorno virtual:

```console
python -m pip install -r requirements.txt
```

Para ejecutar la chain real desde la raíz del proyecto:

```console
python -m src.GATE_2.cadena_tres_pasos
```

La ejecución requiere `GEMINI_API_KEY` en `.env` y realiza tres llamadas al
modelo, que pueden generar costo. Para probarla sin red ni credenciales:

```console
python -m pytest tests/test_cadena_tres_pasos.py -q
```

## LangChain: enrutamiento condicional (Bloque 19)

`src/GATE_2/enrutamiento.py` clasifica mensajes de soporte como `pregunta`,
`queja` o `sugerencia`, normaliza la clasificación y dirige el mensaje a un
prompt específico. La ruta de pregunta también es la ruta por defecto para
categorías desconocidas. `construir_cadena(modelo)` permite probar el flujo con
un modelo simulado; las funciones `construir_paso_clasificacion` y
`construir_cadena_con_enrutamiento` permiten probar clasificación y rutas por
separado.

Para ejecutar un ejemplo con Gemini desde la raíz del proyecto:

```console
python -m src.GATE_2.enrutamiento
```

Requiere `GEMINI_API_KEY` en `.env` y realiza dos llamadas al modelo (una para
clasificar y otra para responder), que pueden generar costo. Para comprobar
las tres rutas, la ruta por defecto, la normalización y el flujo completo sin
red ni credenciales:

```console
python -m pytest tests/test_orquestacion.py -q
```

El manejo de errores, el checklist completo y los casos de diagnóstico del
Bloque 20 están documentados en
[docs/bloque-20-manejo-errores-orquestacion.md](docs/bloque-20-manejo-errores-orquestacion.md).

## LangChain: primer agente con herramientas (Bloque 21)

`src/GATE_2/agente_con_herramientas.py` construye un agente de soporte con dos
herramientas: búsqueda de documentación del proyecto y estimación del costo
por tokens usando `src/GATE_2/costo.py`. A diferencia de la chain enrutada del
Bloque 19, el modelo decide si responde directamente o qué herramienta invocar.
El agente conserva las acciones y observaciones en `intermediate_steps`.

La guía conceptual, la ejecución, la revisión de la traza y los errores comunes
están en
[docs/bloque-21-agente-con-herramientas.md](docs/bloque-21-agente-con-herramientas.md).
El módulo requiere `langchain-classic` además de las dependencias del proyecto.
Instálalas con `python -m pip install -r requirements.txt`; configura
`GEMINI_API_KEY` en `.env` y ejecuta desde la raíz:

```console
python -m src.GATE_2.agente_con_herramientas
```

La ejecución usa Gemini y puede generar costos. Las pruebas usan un modelo
simulado y no requieren credenciales ni conexión:

```console
python -m pytest tests/test_agente_con_herramientas.py -q
```

## LangChain: herramienta estructurada y memoria (Bloque 22)

El agente también valida los argumentos del cálculo de tokens mediante un
`args_schema` de Pydantic 2, con descripciones por campo y el nombre explícito
`calcular_costo_tokens_gemini`. Un grafo de LangGraph con `InMemorySaver`
conserva contexto entre turnos y separa conversaciones por `session_id`,
traducido a `thread_id` para el checkpoint. Los historiales se mantienen en
memoria durante el proceso y no persisten al reiniciarlo;
`cerrar_sesion(session_id)` elimina el checkpoint de esa conversación.

El ejemplo ejecutable hace dos turnos en una sesión compartida, por lo que
requiere `GEMINI_API_KEY` y puede generar costos. Las pruebas del comando
anterior verifican la validación del esquema, la memoria y el aislamiento de
sesiones sin llamar a Gemini. Consulta la guía en
[docs/bloque-22-herramienta-estructurada-memoria.md](docs/bloque-22-herramienta-estructurada-memoria.md).

## LangChain: autonomía y revisión de trazas (Bloque 23)

El agente guarda las entradas, herramientas, argumentos, observaciones y
respuestas en `trazas_agente.jsonl`. Como sus herramientas actuales solo
consultan o calculan, no requieren aprobación humana; la guía documenta esos
niveles de riesgo, cómo revisar las trazas y qué hacer si el agente se desvía.

Consulta [docs/bloque-23-autonomia-y-trazas.md](docs/bloque-23-autonomia-y-trazas.md)
y ejecuta el analizador desde la raíz:

```console
python -c "from src.GATE_2.trazas_agente import marcar_repeticiones_sospechosas; marcar_repeticiones_sospechosas()"
```

Las pruebas del registro y el análisis no llaman a Gemini:

```console
python -m pytest tests/test_trazas_agente.py -q
```

## RAG: indexación del corpus y embeddings (Bloque 24)

`src/GATE_2/indexar_corpus.py` divide cinco documentos cortos del proyecto con
`RecursiveCharacterTextSplitter`, los vectoriza con `gemini-embedding-001` y
persiste los chunks en Chroma bajo `vectorstore/`. La carpeta generada está
excluida de Git. La indexación y la búsqueda semántica hacen llamadas reales a
Gemini; asegúrate de tener `GEMINI_API_KEY` en `.env`.

Instala las dependencias actualizadas y corre el indexador desde la raíz:

```console
python -m pip install -r requirements.txt
python -m src.GATE_2.indexar_corpus
```

El indexador informa el chunking y la indexación, lista los archivos creados
en `vectorstore/` y vuelve a conectarse para confirmar el total persistido
(cinco chunks en el corpus de ejemplo). La guía también incluye cómo reiniciar
Python y comprobar el total con `vectorstore._collection.count()` sin volver a
indexar.

La guía de chunking, persistencia, reconexión y solución de problemas está en
[docs/bloque-24-indexacion-corpus-rag.md](docs/bloque-24-indexacion-corpus-rag.md).
Las pruebas usan embeddings deterministas locales para verificar Chroma sin
llamadas a Gemini:

```console
python -m pytest tests/test_indexar_corpus.py -q
```

La réplica guiada del Bloque 25 usa una colección y carpeta diferentes para no
mezclarse con el corpus del proyecto. Su guía contiene los pasos, el resultado
esperado y el troubleshooting de instalaciones, clave, cuota, persistencia y
colecciones. Para ejecutarla con Gemini:

```console
python -m src.GATE_2.replica_corpus_ejemplo
```

La ejecución requiere una clave válida en `.env` y puede consumir cuota de la
API. Las comprobaciones automatizadas usan embeddings deterministas y no llaman
a Gemini:

```console
python -m pytest tests/test_replica_corpus_ejemplo.py -q
```

Consulta [docs/bloque-25-replica-corpus-ejemplo.md](docs/bloque-25-replica-corpus-ejemplo.md)
para los pasos detallados y la guía de troubleshooting de vector stores.

### Bloque 26: recuperar contexto y responder con citas

`src/GATE_2/recuperacion_citas.py` reindexa el corpus del proyecto con sus
metadatos, recupera los fragmentos pertinentes y consulta el modelo configurado
por `modeloIA`. El prompt limita la respuesta al contexto y solicita citas
numeradas; el script imprime las rutas fuente asociadas a cada número.

```console
python -m src.GATE_2.recuperacion_citas
python -m pytest tests/test_recuperacion_citas.py -q
```

La ejecución completa reindexa con Gemini Embeddings y hace dos búsquedas y dos
consultas al modelo, por lo que requiere una clave válida y puede consumir
cuota. Las pruebas usan dobles locales y no llaman a Gemini.
Consulta [la guía del Bloque 26](docs/bloque-26-recuperacion-rag.md) para el
flujo, la validación de citas y los problemas frecuentes.

### Evaluar recuperación y registrar latencia/costo (Bloques 27-28)

`src/GATE_2/evaluar_recuperacion.py` calcula precisión, recall y F1 por
pregunta para diez casos etiquetados sobre el corpus actual. La evaluación
consulta el índice real con embeddings de Gemini y agrega cada corrida a
`resultados_evaluacion.jsonl`, conservando `k`, chunking y resultados
individuales:

```console
python -m src.GATE_2.evaluar_recuperacion --k 1
python -m src.GATE_2.evaluar_recuperacion --k 2
python -m src.GATE_2.evaluar_recuperacion --k 3
python -m pytest tests/test_evaluacion_recuperacion.py -q
```

La medición actual del corpus (10 preguntas) favorece `k=1`; ese es también
el valor por defecto del servicio. Compara los valores explícitos cuando cambie
el corpus o sus etiquetas.

`src/GATE_2/registro_rag.py` mide embedding+búsqueda y generación, y guarda los
tokens reales de `usage_metadata` junto con el costo estimado en USD según las
tarifas configuradas. También devuelve la respuesta citada y las fuentes a la
consola, pero no las persiste en el registro. Cada consulta agrega una línea a
`registros_latencia_costo.jsonl`:

```console
python -m src.GATE_2.registro_rag --pregunta "¿Qué errores reintenta el cliente?"
python -m src.GATE_2.registro_rag --actividad-core
python -m pytest tests/test_registro_rag.py -q
python -m src.GATE_2.preflight_rag
```

`--actividad-core` imprime en consola las tres consultas, la comparación de
`input_tokens` para `k=1` y `k=2`, y el total de líneas guardadas. Ejecuta cinco
consultas reales y puede consumir cuota.

Ambos archivos de resultados quedan excluidos de Git. Las evaluaciones y el
registro real requieren credenciales de Gemini y pueden consumir cuota; las
pruebas enfocadas usan datos simulados sin red. Consulta las guías de
[evaluación de recuperación](docs/bloque-27-evaluacion-recuperacion.md) y
[latencia y costo RAG](docs/bloque-28-latencia-costo-rag.md) para etiquetas,
interpretación de resultados, comparación de `k` y solución de problemas.

## Gate 2: autochequeo integrado y rúbrica

El autochequeo de la raíz conecta el indexador Chroma, el servicio de
recuperación/citación, el registro de trazas y el grafo real de LangGraph. Las
cuatro pruebas usan embeddings y generación simulados, un índice temporal y no
requieren red ni credenciales:

```console
python -m pytest test_gate2.py -v
```

Con `-v`, pytest imprime el nombre de cada prueba. En esta versión son
`test_1_pipeline_indexa_recupera_y_responde_sin_excepciones`,
`test_2_respuesta_cita_una_fuente_recuperada`,
`test_3_registro_no_persiste_consulta_ni_pii` y
`test_4_supervision_pausa_y_reanuda_con_decision_humana`. El encabezado de
sesión, los datos de plataforma y el tiempo total dependen de la versión de
pytest, sus plugins y el equipo; por eso una salida de ejemplo puede no
coincidir carácter por carácter con la consola.

La respuesta usa citas numeradas (`[1]`) y el mapa `fuentes` asocia cada número
con el archivo recuperado. El registro JSONL contiene solo la longitud de la
pregunta, conteos, tiempos, tokens, costo estimado y `trace_id`; no persiste la
pregunta, la respuesta ni el contenido de documentos. Para comprobar la
integración con Gemini real, ejecuta una consulta individual:

```console
python -m src.GATE_2.registro_rag --pregunta "¿Qué errores reintenta el cliente?" --k 3
```

Esta llamada usa Gemini para el embedding y la generación, puede consumir cuota
y agrega un registro local. Si no hay clave válida, deja la comprobación real
como pendiente; no reemplaces tokens o costos ausentes con valores simulados.

La función `rubrica_gate2.py` valida los seis puntajes, calcula el promedio
ponderado y fuerza los cuatro criterios no compensables:

```console
python rubrica_gate2.py
```

Antes de entregar, sigue el [checklist verificable del Gate 2](docs/checklist_gate2.md).
Incluye el estado de las pruebas locales, las evidencias del corpus propio y
las comprobaciones que requieren la clave de API o una entrega Git.

### Personalización y dataset de tuning (Bloque 29)

El Bloque 29 compara RAG, fine-tuning completo, PEFT y soft-prompting, y
presenta un dataset de ejemplo para aprender un formato de clasificación
consistente. Comprueba los requisitos locales sin llamar a Gemini y ejecuta la
validación del dataset con:

```console
python -m src.GATE_2.verificar_entorno
python -m src.GATE_2.dataset_tuning
python -m pytest tests/test_dataset_tuning.py -q
```

La construcción, validación y revisión de balance son locales y no generan
costo. El envío de un trabajo de tuning es opcional, requiere acceso habilitado
y puede generar costo; no se ejecuta en este proyecto. La guía incluye el flujo
de trabajo, criterios de elección, ejercicio propio y errores frecuentes:
[docs/bloque-29-personalizacion-modelos.md](docs/bloque-29-personalizacion-modelos.md).

### Decisión de personalización (Bloque 30)

El Bloque 30 estima el costo humano del etiquetado, compara RAG, fine-tuning
completo y PEFT con un método que informa empates, y genera el esqueleto de la
decisión fundamentada para tu proyecto. Para mostrar en consola una decisión
de ejemplo completa y guardarla en `docs/decision_personalizacion.md`, ejecuta:

```console
python -m src.GATE_2.decision_personalizacion
```

La decisión documentada en este repositorio aplica el método al servicio RAG
propio: información cambiante, citas obligatorias y ausencia de un dataset de
entrenamiento grande favorecen RAG. El ejemplo de código no usa la API.
Ejecuta las pruebas locales sin credenciales ni llamadas de red:

```console
python -m pytest tests/test_decision_personalizacion.py -q
```

La consulta de estadísticas de un trabajo de tuning existente es opcional y no
inicia entrenamiento. La guía completa y los ejercicios están en
[docs/bloque-30-decision-personalizacion.md](docs/bloque-30-decision-personalizacion.md).

### Bloque 32: unidad completa de versionado, supervisión y riesgos

El Bloque 32 reúne en un solo archivo la actividad completa, sin llamadas a
Gemini. Ejecuta el versionado y diff del prompt, el punto de supervisión con
LangGraph y la matriz de cinco riesgos:

```console
python -m src.GATE_2.unidad_completa_supervision
```

La salida incluye huellas inicial y nueva, el diff, el punto pendiente,
la activación aprobada y los riesgos ordenados por puntaje.

El módulo está localizado en `src/GATE_2/unidad_completa_supervision.py` y se
ejecuta por el nombre del paquete. No requiere Gemini ni genera archivos.

La entrega detallada y el significado de cada salida están en
[docs/bloque-32-supervision-matriz.md](docs/bloque-32-supervision-matriz.md).

### Seguridad, trazas y supervisión humana (Bloque 31)

El Bloque 31 separa roles y delimita contexto no confiable en RAG, filtra
patrones conocidos de inyección, correlaciona callbacks y registra consultas
por `trace_id` sin guardar pregunta ni contexto. Las trazas del agente también
redactan correos y teléfonos detectables. Además, versiona prompts con
aprobación explícita antes de activarlos y ordena una matriz de riesgos por
probabilidad e impacto. Las defensas son heurísticas y no eliminan todos los
riesgos. Si el vector store conserva rutas del paquete anterior, el código
migra IDs y metadatos cuando el contenido coincide exactamente, sin recalcular
embeddings.

El modo `--demo-trazas` imprime en consola los tres pasos del ejemplo: pipeline
con respuesta, dos consultas con distintos `trace_id` y abstención cuando el
contexto recuperado es sospechoso. Es una salida ilustrativa local, no una
consulta real a Gemini.

```console
python -m src.GATE_2.registro_rag --pregunta "¿Qué errores reintenta el cliente?" --k 3
python -m src.GATE_2.registro_rag --demo-trazas
python -m src.GATE_2.supervision_riesgos
python -m pytest tests/test_seguridad_rag.py tests/test_trazas_callbacks.py tests/test_supervision_riesgos.py tests/test_privacidad_logs.py -q
```

Las consultas reales a RAG requieren credenciales y pueden consumir cuota; las
pruebas y la matriz de riesgos no llaman a servicios externos. La guía con el
flujo de aprobación, límites, ejemplo de callbacks y política de logs está en
[docs/bloque-31-seguridad-trazas-supervision.md](docs/bloque-31-seguridad-trazas-supervision.md).

## Verificaciones y revisión de GATE_2

Hay dos verificaciones distintas; una no sustituye a la otra.

### Autochequeo de los cuatro criterios no compensables

Ejecuta desde la raíz:

```console
python -m pytest test_gate2.py -v
```

Estas cuatro pruebas locales comprueban el pipeline de punta a punta con
servicios simulados, las citas, que el registro no persista la consulta ni el
correo de prueba, y que la supervisión humana pause y reanude el grafo. No
requieren Gemini ni validan por sí solas todas las dimensiones de la entrega.
La salida muestra los nombres actuales de las pruebas; el encabezado y la
duración dependen del entorno. Consulta la sección
[Gate 2: autochequeo integrado y rúbrica](#gate-2-autochequeo-integrado-y-rúbrica)
para los detalles.

### Verificador general del repositorio

`revision_gate_2.py` es un verificador más amplio de módulos y actividades del
proyecto. **No es el autochequeo de los cuatro criterios ni un resultado de
aprobación del Gate 2.** Desde la raíz, ejecútalo con:

```console
python src/GATE_2/revision_gate_2.py
```

Este verificador describe los módulos y el banco de prompts, valida sintaxis,
dependencias, imports y credenciales, y ejecuta comprobaciones locales
simuladas de otros componentes. Algunas actividades históricas requieren
resultados, revisión manual o hallazgos documentados; por eso puede terminar
con estado distinto de cero aunque `test_gate2.py` pase.

Para omitir las comprobaciones que llaman a la API:

```console
python src/GATE_2/revision_gate_2.py --omitir-api
```

`--omitir-api` evita las llamadas reales; no completa resultados faltantes ni
la revisión manual de esas actividades. En la verificación del 23 de noviembre
de 2026, el autochequeo de los cuatro criterios pasó, pero este verificador
general devolvió código 1 por resultados y revisiones manuales pendientes de
una actividad anterior. El estado vigente, las evidencias de Gate 2 y los
pendientes de latencia y entrega están en el
[checklist verificable del Gate 2](docs/checklist_gate2.md).

Si se cancela la carga o ejecución con Ctrl+C, el verificador informa la
cancelación y termina sin mostrar el traceback de Python.

## Decisión de arquitectura

Se puede consultar la explicación completa de la decisión de modelo, costes y
arquitectura en [docs/decision-arquitectura.md](docs/decision-arquitectura.md).

## Banco de prompts

El banco de prompts en `prompts/banco.py` prueba respuestas estructuradas en JSON
y guarda un resumen de resultados en `prompts/registro_resultados.json`.

Esto permite evaluar si el modelo devuelve exactamente los campos esperados y si
la respuesta es consistente entre varios intentos.

## Documentación adicional

- [docs/decision-arquitectura.md](docs/decision-arquitectura.md): decisiones de modelo, arquitectura y cálculo de costos.
- [docs/limites_metrica.md](docs/limites_metrica.md): límites conocidos de precisión, cobertura y F1, rúbrica y recomendación de revisión manual.
- [docs/decision_personalizacion.md](docs/decision_personalizacion.md): decisión de personalización aplicada al servicio RAG del proyecto.
- [docs/checklist_gate2.md](docs/checklist_gate2.md): checklist de evidencias, criterios no compensables y pendientes de entrega.
- [docs/registro_resultados.txt](docs/registro_resultados.txt): registro de resultados de pruebas y evaluaciones del proyecto.

## Notas importantes

- Los módulos de `src/GATE_2` están pensados para ejecutarse como scripts desde la raíz del proyecto.
- Si la variable `GEMINI_API_KEY` no existe o conserva el valor de ejemplo, la aplicación falla con un error explícito para evitar llamadas no autenticadas.
- En caso de 429, 5xx, timeout o problemas de conexión, el cliente modular reintenta automáticamente hasta un máximo configurado.
- Los errores de autenticación (401/403) se consideran permanentes y no se reintentan.
- El cálculo de costo es local y estimado; no representa una factura real.

## Siguientes pasos

- ampliar el repositorio con más casos de uso y módulos funcionales;
- añadir pruebas de integración para prompt engineering;
- encapsular la lógica de llamadas a la API para reutilizarla en otros proyectos;
- incorporar métricas más avanzadas de evaluación de salidas y calidad del texto.

## Changelog

El historial completo de cambios, incluyendo las actualizaciones recientes y
las entradas anteriores, está en [CHANGELOG.md](CHANGELOG.md).
