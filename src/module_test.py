# Path permite construir la ruta al archivo .env sin depender de la carpeta
# desde la que se ejecute este script.
from pathlib import Path

# os lee la clave de API de las variables cargadas; load_dotenv lee el .env.
import os
from dotenv import load_dotenv

# Importa las funciones que preparan la petición y la que la envía a Gemini.
from peticiones import create_headers, create_payload, make_request

# Obtiene la ruta raíz del proyecto y apunta al archivo .env.
env_path = Path(__file__).resolve().parents[1] / ".env"

# Carga las variables de ese archivo. override=True hace que sus valores
# prevalezcan sobre variables del mismo nombre que ya existan en el sistema.
load_dotenv(dotenv_path=env_path, override=True)

# Lee y elimina espacios extra al inicio y al final de la clave de API.
api_key = os.getenv("GEMINI_API_KEY", "").strip()

# Detiene el programa con un mensaje claro si falta la clave o si todavía
# contiene el valor de ejemplo de la plantilla.
if not api_key or api_key == "tu_llave_aqui":
    raise RuntimeError(f"Configura GEMINI_API_KEY con una clave real en {env_path}.")

# Define el endpoint del modelo y prepara los encabezados y el cuerpo JSON
# mediante las funciones del módulo peticiones.py.
result = make_request(
    url="https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent",
    headers=create_headers(api_key),
    payload=create_payload("Explícame cómo funciona la NBA en 20 palabras"),
)

# Muestra en la consola el texto devuelto por la API o el mensaje de error.
print(result)