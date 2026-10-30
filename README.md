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
real de Gemini. No compartas ni subas ese archivo: `.gitignore` lo excluye.
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
python src/GATE_1/latencia.py
```

La clase `Latencia`, definida en `src/GATE_1/latencia.py`, realiza cuatro
solicitudes con la pregunta de prueba predeterminada. Informa el tiempo de cada
solicitud, el promedio y una estimación del costo de la última respuesta usando
el precio oficial vigente de Gemini 3.8 Flash. Ejecuta el archivo directamente
como se muestra; no uses `-m src.GATE_1.latencia`, ya que sus imports de módulos
hermanos no están configurados para la ejecución como módulo de paquete.

## Consultar tokens de una respuesta

La respuesta JSON de Gemini se conserva completa al volver de
`enviar_peticion`; además del contenido generado puede incluir `usageMetadata`
con los tokens de entrada, salida y total. Al ejecutar
`python src/GATE_1/monolitico.py`, el ejemplo imprime la respuesta y esos tres
contadores. El programa informa un error explícito si la API no incluye
metadatos de tokens válidos.

El módulo `src/GATE_1/costo.py` calcula el costo a partir del uso reportado y
los precios oficiales de Gemini 3.8 Flash. La tarifa utilizada y sus condiciones
están documentadas en [la decisión de arquitectura](docs/decision-arquitectura.md#precios-oficiales-y-cálculo-de-costo).

## Cliente modular: reintentos y costo por operación

El cliente `src/GATE_1/cliente.py` ofrece `consultar_modelo(pregunta)` como
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

`src/GATE_1/cliente_reintento.py` reintenta errores transitorios (429, 5xx,
timeout y conexión) hasta tres intentos totales por defecto. Entre intentos
aplica backoff exponencial con jitter y un techo de 30 segundos por espera. Los
mensajes de reintento indican el número de intento y la espera calculada. No
reintenta errores de autenticación (401/403) ni otros errores HTTP permanentes.
El envío conserva la clave en el encabezado y usa el timeout de 30 segundos de
`monolitico.py`.

### Una consulta

Desde la raíz, ejecuta una consulta real. El bloque `__main__` llama una sola
vez a `consultar_modelo`, imprime la respuesta y el costo acumulado:

```console
python -m src.GATE_1.cliente
```

También se puede ejecutar directamente el archivo:

```console
python src/GATE_1/cliente.py
```

### Ensayo de diez consultas

Para ejecutar las diez preguntas de prueba (cada una puede generar costo), usa
desde la raíz:

```console
python -c "from src.GATE_1.cliente import ejecutar_ensayo; raise SystemExit(ejecutar_ensayo())"
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
python src/GATE_1/revision_gate_1.py --omitir-api
```

## Pipeline de texto y evaluación de salidas

Además de la consulta a Gemini, el proyecto incluye un flujo local para limpiar,
comparar y evaluar texto antes de interpretar la respuesta del modelo:

- `src/GATE_1/pipeline_texto.py`: limpia el texto, elimina puntuación y espacios
  extra, tokeniza, genera conteos por palabra y calcula coincidencias,
  precisión, cobertura y F1 sin perder las repeticiones.
- `src/GATE_1/evaluar_salidas.py`: compara la respuesta del modelo con una
  referencia usando métricas sobre texto crudo y texto normalizado.
- `src/GATE_1/evaluar_metricas.py`: evalúa varias respuestas reales, conserva
  respuesta y métricas en `resultados_metricas.json`, calcula promedios y
  muestra primero los casos con menor F1.
- `src/GATE_1/revisar_cualitativamente.py`: prepara una muestra de los F1 más
  bajos y más altos en `revision_cualitativa.json`, lista para completar a mano
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
python -m src.GATE_1.evaluar_metricas
```

El archivo JSON se actualiza después de cada respuesta exitosa, de modo que
los resultados parciales se conservan si una consulta posterior falla. Para
preparar una muestra para revisar (sin volver a llamar a la API), primero
genera o conserva `resultados_metricas.json` y ejecuta:

```console
python -m src.GATE_1.revisar_cualitativamente
```

El comando selecciona hasta cinco casos con F1 más bajo y cinco con F1 más
alto; con menos de diez resultados reparte la muestra entre ambos extremos sin
duplicados. Edita `revision_cualitativa.json` y completa la corrección factual,
la completitud y la contradicción con `sí`, `no` o `parcialmente` según
corresponda, además de justificar cada decisión. La [documentación de límites
de la métrica](docs/limites_metrica.md) describe sus fallos conocidos y cuándo
conviene revisar manualmente.

Para probar las funciones sin conexión ni costo de API:

```console
python -m pytest tests/test_pipeline_texto.py -q
python -m pytest tests/test_evaluar_metricas.py -q
python -m pytest tests/test_revisar_cualitativamente.py -q
```

## Revisar GATE_1

Desde la raíz del repositorio ejecuta el verificador:

```console
python src/GATE_1/revision_gate_1.py
```

Describe los módulos de GATE_1 y el banco de prompts; valida sintaxis,
dependencias, imports y credenciales, y ejecuta pruebas locales simuladas,
incluidas las de clasificación de errores, reintentos, backoff, costo por
operación y validación de respuestas. También incorpora la revisión de
`pipeline_texto.py`, `evaluar_salidas.py`, `evaluar_metricas.py` y
`revisar_cualitativamente.py`.

Para ejecutar solo comprobaciones locales sin llamar a la API real:

```console
python src/GATE_1/revision_gate_1.py --omitir-api
```

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
- [docs/registro_resultados.txt](docs/registro_resultados.txt): registro de resultados de pruebas y evaluaciones del proyecto.

## Notas importantes

- Los módulos de `src/GATE_1` están pensados para ejecutarse como scripts desde la raíz del proyecto.
- Si la variable `GEMINI_API_KEY` no existe o conserva el valor de ejemplo, la aplicación falla con un error explícito para evitar llamadas no autenticadas.
- En caso de 429, 5xx, timeout o problemas de conexión, el cliente modular reintenta automáticamente hasta un máximo configurado.
- Los errores de autenticación (401/403) se consideran permanentes y no se reintentan.
- El cálculo de costo es local y estimado; no representa una factura real.

## Siguientes pasos

- ampliar el repositorio con más casos de uso y módulos funcionales;
- añadir pruebas de integración para prompt engineering;
- encapsular la lógica de llamadas a la API para reutilizarla en otros proyectos;
- incorporar métricas más avanzadas de evaluación de salidas y calidad del texto.
