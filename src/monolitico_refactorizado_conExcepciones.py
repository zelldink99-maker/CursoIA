

import os
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
MODEL = "gemini-3.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
REQUEST_TIMEOUT = 30

load_dotenv(dotenv_path=ENV_PATH)


def _obtener_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "tu_llave_aqui":
        raise RuntimeError(f"Configura GEMINI_API_KEY con una clave real en {ENV_PATH}.")
    return api_key


def _extraer_texto(datos: object) -> str:
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
    try:
        datos = respuesta.json()
    except ValueError:
        datos = {}

    error = datos.get("error") if isinstance(datos, dict) else None
    mensaje = error.get("message") if isinstance(error, dict) else None
    if isinstance(mensaje, str) and mensaje:
        return mensaje
    return respuesta.text or "Respuesta vacía"


def obtener_dato_de_prueba(pregunta: str) -> str:
    """Envía una pregunta a Gemini y devuelve el texto generado."""
    api_key = _obtener_api_key()
    respuesta = requests.post(
        API_URL,
        headers={"x-goog-api-key": api_key},
        json={"contents": [{"parts": [{"text": pregunta}]}]},
        timeout=REQUEST_TIMEOUT,
    )

    if not respuesta.ok:
        raise RuntimeError(
            f"Error de Gemini ({respuesta.status_code}): {_mensaje_error(respuesta)}"
        )

    return _extraer_texto(respuesta.json())


if __name__ == "__main__":
    print(obtener_dato_de_prueba("¿Cual es la capital de Francia?"))