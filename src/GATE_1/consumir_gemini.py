"""Consulta la API de Gemini y valida sus respuestas."""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Mantiene la configuración independiente del directorio desde el que se ejecute.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
MODEL = "gemini-3.8-flash"
API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
)
REQUEST_TIMEOUT = 30

# Carga los valores locales, pero conserva prioridad para variables del sistema.
load_dotenv(dotenv_path=ENV_PATH)


def _obtener_api_key() -> str:
    """Devuelve la clave de API o indica cómo configurar una."""
    # Rechaza tanto la ausencia de clave como el marcador del archivo de ejemplo.
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "tu_llave_aqui":
        raise RuntimeError(
            f"Configura GEMINI_API_KEY con una clave válida en {ENV_PATH}."
        )
    return api_key


def _mensaje_error(respuesta: requests.Response) -> str:
    """Extrae el detalle del error HTTP, usando el cuerpo como alternativa."""
    # La API suele incluir el motivo dentro de un objeto JSON "error".
    try:
        datos = respuesta.json()
    except ValueError:
        datos = None

    if isinstance(datos, dict):
        error = datos.get("error")
        if isinstance(error, dict):
            mensaje = error.get("message")
            if isinstance(mensaje, str) and mensaje:
                return mensaje

    return respuesta.text.strip() or "La respuesta no incluyó detalles."


def _extraer_texto(datos: object) -> str:
    """Valida la estructura JSON de Gemini y concatena las partes de texto."""
    # Cada nivel se comprueba para convertir respuestas incompletas en errores claros.
    if not isinstance(datos, dict):
        raise RuntimeError("Gemini devolvió una respuesta con un formato inesperado.")

    candidatos = datos.get("candidates")
    if not isinstance(candidatos, list) or not candidatos:
        raise RuntimeError("Gemini no devolvió candidatos con contenido.")

    candidato = candidatos[0]
    if not isinstance(candidato, dict):
        raise RuntimeError("Gemini devolvió un candidato con un formato inesperado.")

    contenido = candidato.get("content")
    if not isinstance(contenido, dict):
        raise RuntimeError("Gemini no devolvió contenido en su respuesta.")

    partes = contenido.get("parts")
    if not isinstance(partes, list):
        raise RuntimeError("Gemini devolvió contenido con un formato inesperado.")

    textos = [
        parte["text"]
        for parte in partes
        if isinstance(parte, dict) and isinstance(parte.get("text"), str)
    ]
    if not textos:
        raise RuntimeError("Gemini no devolvió texto en su respuesta.")

    # Una respuesta puede dividirse en partes; se concatenan para devolverla completa.
    return "".join(textos)


def obtener_dato_de_prueba(pregunta: str) -> str:
    """Envía una pregunta a Gemini y devuelve el texto generado.

    Lanza ValueError para preguntas inválidas y RuntimeError para problemas de
    configuración, conexión, HTTP o formato de la respuesta.
    """
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("La pregunta debe ser un texto no vacío.")

    api_key = _obtener_api_key()

    # Envía la clave en un encabezado para no exponerla en la URL de la solicitud.
    try:
        respuesta = requests.post(
            API_URL,
            headers={"x-goog-api-key": api_key},
            json={"contents": [{"parts": [{"text": pregunta}]}]},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.Timeout as error:
        raise RuntimeError(
            "La solicitud a Gemini superó el tiempo de espera."
        ) from error
    except requests.ConnectionError as error:
        raise RuntimeError("No se pudo conectar con la API de Gemini.") from error
    except requests.RequestException as error:
        raise RuntimeError(
            f"No se pudo completar la solicitud a Gemini: {error}"
        ) from error

    if not respuesta.ok:
        raise RuntimeError(
            f"Error de Gemini ({respuesta.status_code}): {_mensaje_error(respuesta)}"
        )

    try:
        # Primero valida que el cuerpo HTTP sea JSON antes de recorrer su contenido.
        datos = respuesta.json()
    except ValueError as error:
        raise RuntimeError(
            "Gemini devolvió una respuesta que no es JSON válido."
        ) from error

    return _extraer_texto(datos)


def _main() -> int:
    """Ejecuta una consulta de ejemplo e informa fallos esperables al usuario."""
    try:
        print(obtener_dato_de_prueba("¿Cuál es la capital de Escocia?"))
    except (RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
