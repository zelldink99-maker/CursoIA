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
python src\latencia.py
```

La clase `Latencia`, definida en `src/latencia.py`, realiza cuatro solicitudes
con la pregunta de prueba predeterminada. Informa el tiempo de cada solicitud,
el promedio y una estimación del costo de la última respuesta. Las tarifas por
token están definidas en el módulo y deben revisarse frente a los precios
actuales del proveedor.

También puedes configurar la prueba desde Python:

```python
from src.latencia import Latencia

prueba = Latencia(
    pregunta="¿Cuál es la capital de Escocia?",
    intentos=2,
)
promedio = prueba.ejecutar()
```

La petición y la medición solo se ejecutan al llamar `ejecutar()` o al lanzar
el módulo directamente; importar `Latencia` no realiza llamadas a la API.

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
