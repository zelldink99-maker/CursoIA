# Plantilla de repositorio base — Especialización en Desarrollo con IA Generativa (Accenture)

<p align="center">
  <img src="docs/IA.jpg" alt="Inteligencia artificial aplicada al desarrollo" width="800">
</p>

Esta es la estructura base del proyecto para la Especialización en Desarrollo
con IA Generativa. Se irá ampliando bloque a bloque hasta llegar a la
aplicación completa del Gate 3. En este repositorio se practica el envío de
preguntas a la API de Gemini, la medición de latencia y la estimación del costo
de los tokens de una respuesta.

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
> en el Python del sistema. Este proyecto necesita `python-dotenv` (declarado
> en `requirements.txt`), y la instalación debe hacerse con el entorno virtual
> activado mediante `python -m pip install -r requirements.txt`. Esto también
> evita el error `externally-managed-environment` de distribuciones Linux que
> aplican PEP 668.

## Requisitos

- Python 3.10 o superior.
- Una clave de API de Gemini.

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
con los tokens de entrada, salida y el total. Al ejecutar
`python src/GATE_1/monolitico.py`, el ejemplo imprime la respuesta y esos tres
contadores. El programa informa un error explícito si la API no incluye
metadatos de tokens válidos.

El módulo `src/GATE_1/costo.py` calcula el costo a partir del uso reportado y
los precios oficiales de Gemini 3.8 Flash. La tarifa utilizada y sus condiciones
están documentadas en [la decisión de arquitectura](docs/decision-arquitectura.md#precios-oficiales-y-cálculo-de-costo).

## Revisar GATE_1

Desde la raíz del repositorio ejecuta el verificador:

```console
python src/GATE_1/revision_gate_1.py
```

Describe los módulos `api_test`, `consumir_gemini`, `costo`, `latencia`,
`main`, `module_test`, `monolitico` y `peticiones`; valida sintaxis,
dependencias, imports y credenciales, y ejecuta pruebas locales simuladas.
También comprueba por defecto la disponibilidad de Gemini con una petición
real. Configura `GEMINI_API_KEY` en `.env` antes de ejecutarlo. La clave no se
imprime; la prueba real puede generar un costo mínimo de API.
Si Gemini no responde, revisa primero el estado HTTP antes de cambiar el
modelo:

- **503 o servicio ocupado:** suele ser saturación temporal. Espera unos
  minutos y vuelve a probar; si persiste, prueba un modelo alternativo.
- **429 o cuota agotada:** revisa los límites y la cuota del proyecto en Google
  AI Studio; cambiar de modelo no garantiza resolverlo.
- **400, modelo no disponible o error de autenticación:** comprueba el nombre
  del modelo, la clave y que el modelo esté habilitado para tu proyecto.

Este proyecto usa actualmente `gemini-3.8-flash`; no usa `gemini-3.5-flash`.
Como alternativas oficiales puedes evaluar `gemini-3.6-flash` para tareas
generales, o `gemini-3.5-flash-lite` y `gemini-3.1-flash-lite` para cargas de
mayor volumen. La disponibilidad, capacidades y precios dependen del modelo,
la cuenta y la fecha; confirma los datos vigentes en la
[lista oficial de modelos](https://ai.google.dev/gemini-api/docs/models) y la
[tabla oficial de precios](https://ai.google.dev/gemini-api/docs/pricing).

El proyecto no cambia de modelo automáticamente. Si decides cambiarlo, actualiza
el identificador en `monolitico.py`, `consumir_gemini.py`, `api_test.py` y
`module_test.py`; actualiza también el modelo y los precios de `costo.py` y las
comprobaciones de `revision_gate_1.py`. Ejecuta primero las pruebas locales con
`--omitir-api` y luego verifica el modelo elegido con una petición real. Para
más detalle sobre cuota, límites de tokens y cambio manual, consulta la
[guía de contingencia y cambio de modelo](docs/decision-arquitectura.md#contingencia-disponibilidad-y-límites-de-tokens).

Para omitir la prueba de red y dejar el check de disponibilidad pendiente:

```console
python src/GATE_1/revision_gate_1.py --omitir-api
```

### Manejo de errores y excepciones

Los clientes de Gemini validan la configuración y las entradas antes de enviar
solicitudes. `consumir_gemini.py` comunica errores de conexión, tiempo de espera,
HTTP, JSON y formato de respuesta mediante excepciones explícitas; `monolitico.py`
usa excepciones específicas derivadas de `GeminiError`. Los scripts de ejecución
(`main.py`, `latencia.py` y `prompts/banco.py`) muestran los errores esperables
al usuario y finalizan con un código distinto de cero.

Las operaciones locales también validan los casos inválidos: `dividir` genera
`ZeroDivisionError` si el divisor es cero, `calcular_costo` genera `ValueError`
si faltan los metadatos o los valores son inválidos, y `Latencia` rechaza una
pregunta, cantidad de intentos o tarifa incorrecta. El banco de prompts valida
el tipo y los campos de cada ejemplo; los JSON no válidos se informan y no se
cuentan como respuestas exitosas. `peticiones.py` devuelve un mensaje explícito
cuando falla la solicitud HTTP, y `module_test.py` propaga ese fallo como código
de salida 1.

`aritmetica.py` y `test.py` no realizan operaciones de red o de archivos; el
primero expone la división por cero como excepción y el segundo solo imprime un
saludo, por lo que no requieren manejo adicional de errores de ejecución.

## Banco de prompts estructurados

El módulo `prompts/banco.py` contiene tres ejemplos para evaluar respuestas
JSON de Gemini. Cada prompt define una instrucción, un ejemplo de usuario y un
esquema de respuesta. El programa ejecuta cada prompt tres veces (9 solicitudes
en total), cuenta las respuestas JSON válidas que incluyen las claves
requeridas y marca el resultado como consistente solo si los tres intentos
producen respuestas JSON válidas e idénticas. Guarda los intentos y ese estado
en `prompts/registro_resultados.json`.

Desde la raíz del repositorio ejecútalo con:

```console
python prompts/banco.py
```

Este comando realiza solicitudes reales a Gemini y puede generar costos de API.
El verificador de GATE_1 también comprueba la sintaxis y la preparación local
del banco de prompts sin enviar solicitudes de red.

## Estructura de carpetas

- `src/`: código fuente, incluyendo la consulta a Gemini, la estimación de
  costos y la medición de latencia.
- `prompts/`: banco de prompts estructurados y resultados agregados de sus
  ejecuciones.
- `docs/`: documentación técnica, diagramas y decisiones de arquitectura.
- `tests/`: pruebas del código; se incorporarán conforme el proyecto lo
  requiera.
- `requirements.txt`: dependencias de Python necesarias para reconstruir el
  entorno.
- `.env.example`: plantilla de variables de entorno sin credenciales reales.
- `.gitignore`: indica a Git qué archivos y carpetas excluir, como el entorno
  virtual y `.env`.

## Reglas que se mantienen durante todo el programa

- Ningún secreto (contraseña, llave de API o token) debe escribirse
  directamente en el código ni en archivos que se suban al repositorio.
- Cada proyecto debe tener su propio entorno virtual; no se comparten
  dependencias entre proyectos distintos.
- Todo el trabajo que se entrega en el programa vive en un repositorio de GitHub.
