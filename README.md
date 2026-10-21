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
solicitud, el promedio y una estimación del costo de la última respuesta. Las
tarifas por token están definidas en el módulo y deben revisarse frente a los
precios actuales del proveedor. Ejecuta el archivo directamente como se muestra;
no uses `-m src.GATE_1.latencia`, ya que sus imports de módulos hermanos no
están configurados para la ejecución como módulo de paquete.

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

Para omitir la prueba de red y dejar el check de disponibilidad pendiente:

```powershell
python src\GATE_1\revision_gate_1.py --omitir-api
```

## Estructura de carpetas

- `src/`: código fuente, incluyendo la consulta a Gemini, la estimación de
  costos y la medición de latencia.
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
