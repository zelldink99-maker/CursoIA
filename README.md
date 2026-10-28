# Curso IA - Tareas / Gate 1

Proyecto de laboratorio para trabajar con la API de Gemini, validación de prompts, cálculo de costos y manejo robusto de errores en consultas con IA.

## Descripción general

Este repositorio funciona como base práctica para integrar modelos generativos con Python, evaluar respuestas estructuradas, medir latencia y estimar el coste de cada operación. Está pensado para aprender de forma modular: cada archivo resuelve un bloque del flujo con Gemini y facilita ver cómo se valida, se prueba y se documenta una solución real.

Incluye:
- consultas directas a Gemini;
- validación de campos, respuestas y errores HTTP;
- reintentos por errores transitorios;
- estimación del costo por uso de tokens;
- pruebas de salida estructurada con prompts JSON;
- limpieza, tokenización y comparación de texto para evaluar resultados.

## Objetivos del proyecto

- entender cómo autenticar y consumir la API de Gemini desde Python;
- validar la pregunta, la respuesta y los metadatos del proveedor;
- manejar errores de conexión, timeout, autenticación y respuestas inválidas;
- medir tiempos de respuesta y estimar costos por operación;
- evaluar la consistencia y calidad de las salidas del modelo;
- revisar el proyecto con una validación automatizada del Gate 1.

## Requisitos

- Python 3.10 o superior.
- Variable de entorno `GEMINI_API_KEY` con una clave válida.
- Conexión a Internet para ejecutar consultas reales.
- Entorno virtual recomendado para aislar dependencias.

## Estructura del proyecto

```text
.
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── docs/
│   ├── decision-arquitectura.md
│   ├── IA.jpg
│   └── registro_resultados.txt
├── prompts/
│   ├── banco.py
│   └── registro_resultados.json
├── src/
│   └── GATE_1/
│       ├── api_test.py
│       ├── aritmetica.py
│       ├── cliente.py
│       ├── cliente_reintento.py
│       ├── consumir_gemini.py
│       ├── costo.py
│       ├── evaluar_salidas.py
│       ├── latencia.py
│       ├── main.py
│       ├── module_test.py
│       ├── monolitico.py
│       ├── peticiones.py
│       ├── pipeline_texto.py
│       ├── revision_gate_1.py
│       ├── test.py
│       └── ...
├── tests/
│   ├── test_cliente.py
│   └── test_pipeline_texto.py
├── venv/
└── .pytest_cache/
```

## Configuración inicial

1. Clona o descarga el repositorio.
2. Crea un entorno virtual desde la raíz:

```bash
python -m venv .venv
```

3. Activa el entorno:

- Linux/macOS:

```bash
source .venv/bin/activate
```

- Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```

4. Instala las dependencias:

```bash
python -m pip install -r requirements.txt
```

5. Genera tu archivo local de entorno:

```bash
cp .env.example .env
```

En PowerShell:

```powershell
Copy-Item .env.example .env
```

6. Edita `.env` y reemplaza `tu_llave_aqui` por tu clave real:

```env
GEMINI_API_KEY=tu_clave_real
```

> El archivo `.env` no debe compartirse ni subirse al repositorio. Ya está excluido en `.gitignore`.

## Ejecución rápida

### 1. Demostración simple

```bash
python src/GATE_1/main.py
```

Ejecuta una suma local y una consulta de ejemplo a Gemini.

### 2. Consulta directa a la API

```bash
python src/GATE_1/consumir_gemini.py
```

### 3. Cliente modular con reintentos y costos

```bash
python src/GATE_1/cliente.py
```

### 4. Ensayo con varias consultas

```bash
python -c "from src.GATE_1.cliente import ejecutar_ensayo; raise SystemExit(ejecutar_ensayo())"
```

Este comando ejecuta varias consultas y muestra el costo acumulado de la sesión y los reintentos si la API responde con errores transitorios.

### 5. Banco de prompts

```bash
python prompts/banco.py
```

El banco valida respuestas JSON estructuradas y guarda un resumen en `prompts/registro_resultados.json`.

## Modelo y costos

El proyecto usa el modelo `gemini-3.8-flash` y estima el coste de cada operación usando los metadatos reales de uso reportados por Gemini (`usageMetadata`).

El cálculo de costo está en:

- [src/GATE_1/costo.py](src/GATE_1/costo.py)
- [docs/decision-arquitectura.md](docs/decision-arquitectura.md)

La estimación se basa en precios oficiales y sirve como medida local de la operación; no reemplaza la facturación exacta del proveedor.

## Pipeline de texto y evaluación de salidas

Además de la consulta a Gemini, el proyecto incluye herramientas para tratamiento y comparación de texto:

- [src/GATE_1/pipeline_texto.py](src/GATE_1/pipeline_texto.py): limpia texto, elimina puntuación y espacios extra, tokeniza y cuenta frecuencias.
- [src/GATE_1/evaluar_salidas.py](src/GATE_1/evaluar_salidas.py): compara la salida del modelo con una referencia usando métricas de texto crudo y texto normalizado.

### Validación del pipeline

```bash
python -m pytest tests/test_pipeline_texto.py -q
```

Esto valida limpieza, tokenización, conteo de frecuencias y comparación de coincidencias sin llamadas reales a la API.

## Validación del proyecto

### Pruebas unitarias del cliente

```bash
python -m pytest tests/test_cliente.py -v
```

Estas pruebas simulan la API y validan:
- clasificación de errores HTTP;
- reintentos con backoff exponencial;
- costo por operación y acumulado de sesión;
- manejo de errores de autenticación;
- criterios de validación de entradas y salidas.

### Revisión general del Gate 1

```bash
python src/GATE_1/revision_gate_1.py --omitir-api
```

Este verificador valida:
- sintaxis de los módulos;
- importaciones del paquete;
- dependencias e instalación del entorno;
- configuración de credenciales;
- pruebas simuladas sin llamadas reales a la API;
- nuevos módulos agregados al proyecto.

También puedes ejecutar la revisión completa con autenticación real:

```bash
python src/GATE_1/revision_gate_1.py
```

## Módulos clave

- [src/GATE_1/monolitico.py](src/GATE_1/monolitico.py): cliente base para armar y enviar peticiones a Gemini.
- [src/GATE_1/cliente_reintento.py](src/GATE_1/cliente_reintento.py): reintentos con backoff y jitter.
- [src/GATE_1/cliente.py](src/GATE_1/cliente.py): interfaz principal con costo por operación y manejo de errores.
- [src/GATE_1/consumir_gemini.py](src/GATE_1/consumir_gemini.py): cliente robusto con validación de respuestas y configuración.
- [src/GATE_1/latencia.py](src/GATE_1/latencia.py): mide tiempos y calcula promedio y costo.
- [prompts/banco.py](prompts/banco.py): banco de prompts estructurados y automatizados.

## Documentación adicional

- [docs/decision-arquitectura.md](docs/decision-arquitectura.md): decisiones de diseño, modelo elegido y cálculo de costos.
- [docs/registro_resultados.txt](docs/registro_resultados.txt): registro de resultados de pruebas y evaluaciones.

## Notas importantes

- Los módulos de `src/GATE_1` se ejecutan mejor desde la raíz del repositorio.
- Si `GEMINI_API_KEY` está vacía o conserva el valor de ejemplo, la ejecución falla explícitamente para evitar llamadas no autorizadas.
- Los errores 401 y 403 se consideran permanentes; no se reintentan.
- Los errores 429, 5xx, timeout y de conexión se manejan con reintentos controlados.
- El costo mostrado es una estimación local de la sesión actual y no reemplaza la facturación real del proveedor.

## Roadmap

- ampliar casos de uso con más prompts y escenarios reales;
- añadir pruebas de integración para evaluación de salidas;
- encapsular más flujo de negocio en módulos reutilizables;
- integrar comparadores semánticos y métricas más avanzadas.

## Conclusión

Este repositorio sirve como punto de partida para aprender a integrar un modelo generativo, validar sus respuestas y estimar el costo operativo de cada interacción. La intención es formar una base sólida para luego pasar a proyectos más complejos de IA aplicada al desarrollo y a la evaluación de software.
