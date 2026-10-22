# Plantilla de repositorio base — Especialización en Desarrollo con IA Generativa (Accenture)

Esta es la estructura base del proyecto para la Especialización en Desarrollo
con IA Generativa. Se irá ampliando bloque a bloque hasta llegar a la
aplicación completa del Gate 3. En este repositorio se practica el envío de
preguntas a la API de Gemini, la medición de latencia y la estimación del costo
de los tokens de una respuesta.

## Cómo empezar

Estos pasos se completan de forma progresiva durante la Unidad U1.2:

1. Descarga el archivo comprimido del proyecto desde la plataforma y
   descomprímelo. Inicializa el control de versiones en esa carpeta y, si aún
   no lo hiciste, registra un commit inicial con la estructura base.
2. Crea y activa un entorno virtual de Python:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Instala las dependencias del proyecto:

   ```powershell
   python -m pip install -r requirements.txt
   ```

   Las dependencias directas están registradas en `requirements.txt`.
4. Copia `.env.example` a un archivo llamado `.env` y configura
   `GEMINI_API_KEY` con tu clave real de API. No compartas ni subas `.env`;
   este archivo está excluido por `.gitignore`.

## Requisitos

- Python 3.9 o superior.
- Una clave de API de Gemini.

## Medir latencia y costo

Desde la raíz del repositorio ejecuta:

```powershell
python src\GATE_1\latencia.py
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
`python src\GATE_1\monolitico.py`, el ejemplo imprime la respuesta y esos tres
contadores. El programa informa un error explícito si la API no incluye
metadatos de tokens válidos.

El módulo `src/GATE_1/costo.py` calcula el costo a partir del uso reportado y
los precios oficiales de Gemini 3.8 Flash. La tarifa utilizada y sus condiciones
están documentadas en [la decisión de arquitectura](docs/decision-arquitectura.md#precios-oficiales-y-cálculo-de-costo).

## Revisar GATE_1

Desde la raíz del repositorio ejecuta el verificador:

```powershell
python src\GATE_1\revision_gate_1.py
```

Describe los módulos `api_test`, `consumir_gemini`, `costo`, `latencia`,
`main`, `module_test`, `monolitico` y `peticiones`; valida sintaxis,
dependencias, imports y credenciales, y ejecuta pruebas locales simuladas.
También comprueba por defecto la disponibilidad de Gemini con una petición
real. Configura `GEMINI_API_KEY` en `.env` antes de ejecutarlo. La clave no se
imprime; la prueba real puede generar un costo mínimo de API.
Para actuar ante saturación, cuota o límites de tokens, consulta la
[guía de contingencia y cambio de modelo](docs/decision-arquitectura.md#contingencia-disponibilidad-y-límites-de-tokens).

Para omitir la prueba de red y dejar el check de disponibilidad pendiente:

```powershell
python src\GATE_1\revision_gate_1.py --omitir-api
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

El módulo `prompts/banco.py` contiene un banco de pruebas para evaluar respuestas
JSON de Gemini. Cada prompt define una instrucción, un ejemplo de usuario y,
opcionalmente, un esquema de respuesta. El programa ejecuta cada prompt tres
veces (15 solicitudes para los cinco ejemplos), cuenta las respuestas JSON
válidas que incluyen las claves requeridas y guarda el resumen en
`prompts/registro_resultados.json`.

Desde la raíz del repositorio ejecútalo con:

```powershell
python prompts\banco.py
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
