import os
from pathlib import Path
import requests
from dotenv import load_dotenv


# Define las rutas y los valores compartidos por todas las funciones.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
MODEL = "gemini-3.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
REQUEST_TIMEOUT = 30

# Carga la clave del archivo .env; si no existe, se revisará la variable del sistema.
load_dotenv(dotenv_path=ENV_PATH)


def _obtener_api_key() -> str:
    """Lee la clave de API y falla con instrucciones si falta."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "tu_llave_aqui":
        raise RuntimeError(f"Configura GEMINI_API_KEY con una clave real en {ENV_PATH}.")
    return api_key


def _extraer_texto(datos: object) -> str:
    """Valida la estructura JSON de Gemini y devuelve el primer texto generado."""
    if not isinstance(datos, dict):
        raise RuntimeError("Gemini devolvió una respuesta con un formato inesperado.")

    try:
        texto = datos["candidates"][0]["content"]["parts"][0]["text"]
    except (IndexError, KeyError, TypeError) as error:
        raise RuntimeError("Gemini no devolvió texto en su respuesta.") from error

    if not isinstance(texto, str):
        raise RuntimeError("Gemini devolvió un texto con un formato inesperado.")
    return texto


def _mensaje_error(respuesta: requests.Response) -> str:
    """Obtiene el mensaje de error JSON o, si no existe, el texto HTTP."""
    try:
        datos = respuesta.json()
    except ValueError:
        datos = {}

    error = datos.get("error") if isinstance(datos, dict) else None
    mensaje = error.get("message") if isinstance(error, dict) else None
    if isinstance(mensaje, str) and mensaje:
        return mensaje
    return respuesta.text or "Respuesta vacía"


def _obtener_mensaje_generado(respuesta: requests.Response) -> str:
    """Convierte la respuesta HTTP en texto y reporta errores de formato."""
    try:
        datos = respuesta.json()
    except ValueError as error:
        raise RuntimeError("Gemini devolvió una respuesta que no es JSON válido.") from error
    return _extraer_texto(datos)


def obtener_dato_de_prueba(pregunta: str) -> str:
    """Envía una pregunta a Gemini y devuelve el texto generado."""
    # Verifica la configuración antes de intentar usar la red.
    api_key = _obtener_api_key()
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("La pregunta debe ser un texto no vacío.")

    # Traduce los errores de red a mensajes claros sin ocultar la excepción original.
    try:
        respuesta = requests.post(
            API_URL,
            headers={"x-goog-api-key": api_key},
            json={"contents": [{"parts": [{"text": pregunta}]}]},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.Timeout as error:
        raise RuntimeError("La solicitud a Gemini superó el tiempo de espera.") from error
    except requests.ConnectionError as error:
        raise RuntimeError("No se pudo conectar con la API de Gemini.") from error
    except requests.RequestException as error:
        raise RuntimeError(f"No se pudo completar la solicitud a Gemini: {error}") from error

    # Convierte las respuestas HTTP fallidas en errores que incluyen el estado y el detalle.
    if not respuesta.ok:
        raise RuntimeError(
            f"Error de Gemini ({respuesta.status_code}): {_mensaje_error(respuesta)}"
        )

    # Valida el JSON recibido y extrae el texto generado.
    return _obtener_mensaje_generado(respuesta)


if __name__ == "__main__":
    # Muestra el resultado o informa errores esperables sin imprimir un traceback.
    try:
        print(obtener_dato_de_prueba("¿Cual es la capital de Escocia?"))
    except (RuntimeError, ValueError) as error:
        print(f"Error: {error}")