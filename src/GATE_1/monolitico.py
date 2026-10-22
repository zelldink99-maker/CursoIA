import os
import sys
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

# La ruta absoluta permite cargar la configuración sin depender del directorio actual.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


class GeminiError(Exception):
    """Error base para los problemas al consultar Gemini."""


class ConfigurationError(GeminiError):
    """La configuración requerida para Gemini no es válida."""


class GeminiRequestError(GeminiError):
    """No se pudo completar una solicitud a Gemini."""


class GeminiTimeoutError(GeminiRequestError):
    """La solicitud a Gemini excedió el tiempo de espera."""


class GeminiConnectionError(GeminiRequestError):
    """No fue posible establecer conexión con Gemini."""


class GeminiHTTPError(GeminiRequestError):
    """Gemini respondió con un estado HTTP de error."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"Error HTTP {status_code} de Gemini: {message}")


class GeminiResponseError(GeminiError):
    """La respuesta de Gemini no tiene el formato esperado."""


def armar_peticion(
    pregunta_usuario: str, system_instruction: str
) -> tuple[str, dict[str, Any]]:
    """Construye el endpoint y el cuerpo de una consulta con instrucción del sistema."""
    if not isinstance(pregunta_usuario, str) or not pregunta_usuario.strip():
        raise ValueError("La pregunta debe ser un texto no vacío.")
    if not isinstance(system_instruction, str) or not system_instruction.strip():
        raise ValueError("La instrucción del sistema debe ser un texto no vacío.")

    modelo = "gemini-3.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": [{"text": pregunta_usuario}]}],
    }
    return url, body


def enviar_peticion(url, body):
    """Envía una consulta y convierte errores de red/HTTP en excepciones del cliente."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "tu_llave_aqui":
        raise ConfigurationError(
            f"Configura GEMINI_API_KEY en {PROJECT_ROOT / '.env'}."
        )

    try:
        # La autenticación viaja en un encabezado, no en la URL.
        respuesta = requests.post(
            url,
            headers={"x-goog-api-key": api_key},
            json=body,
            timeout=30,
        )
    except requests.Timeout as error:
        raise GeminiTimeoutError(
            "La solicitud a Gemini superó el tiempo de espera."
        ) from error
    except requests.ConnectionError as error:
        raise GeminiConnectionError(
            "No se pudo conectar con la API de Gemini."
        ) from error
    except requests.RequestException as error:
        raise GeminiRequestError(
            f"No se pudo completar la solicitud a Gemini: {error}"
        ) from error

    # Distingue errores de estado HTTP de los errores de conexión.
    try:
        respuesta.raise_for_status()
    except requests.HTTPError as error:
        detalle = _detalle_error_http(respuesta)
        raise GeminiHTTPError(
            respuesta.status_code, detalle
        ) from error

    try:
        datos = respuesta.json()
    except ValueError as error:
        raise GeminiResponseError(
            "Gemini devolvió una respuesta que no es JSON válido."
        ) from error

    if not isinstance(datos, dict):
        raise GeminiResponseError(
            "Gemini devolvió una respuesta con un formato inesperado."
        )
    return datos


def _detalle_error_http(respuesta: requests.Response) -> str:
    """Obtiene el mensaje de error proporcionado por Gemini, si existe."""
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


def extraer_texto(datos: Any) -> str:
    """Valida la respuesta y concatena las partes de texto del primer candidato."""
    if not isinstance(datos, dict):
        raise GeminiResponseError(
            "Gemini devolvió una respuesta con un formato inesperado."
        )

    candidatos = datos.get("candidates")
    if not isinstance(candidatos, list) or not candidatos:
        raise GeminiResponseError("Gemini no devolvió candidatos con contenido.")

    candidato = candidatos[0]
    if not isinstance(candidato, dict):
        raise GeminiResponseError("Gemini devolvió un candidato con formato inválido.")

    contenido = candidato.get("content")
    if not isinstance(contenido, dict):
        raise GeminiResponseError("Gemini no devolvió contenido en su respuesta.")

    partes = contenido.get("parts")
    if not isinstance(partes, list):
        raise GeminiResponseError(
            "Gemini devolvió contenido con un formato inesperado."
        )

    textos = [
        parte["text"]
        for parte in partes
        if isinstance(parte, dict) and isinstance(parte.get("text"), str)
    ]
    if not textos:
        raise GeminiResponseError("Gemini no devolvió texto en su respuesta.")

    return "".join(textos)


def extraer_metadatos_uso(datos: Any) -> dict[str, int]:
    """Devuelve los contadores de tokens de uso incluidos en la respuesta."""
    if not isinstance(datos, dict):
        raise GeminiResponseError(
            "Gemini devolvió una respuesta con un formato inesperado."
        )

    metadatos = datos.get("usageMetadata")
    if not isinstance(metadatos, dict):
        raise GeminiResponseError(
            "Gemini no devolvió metadatos de uso de tokens."
        )

    campos = ("promptTokenCount", "candidatesTokenCount", "totalTokenCount")
    if any(
        not isinstance(metadatos.get(campo), int)
        or isinstance(metadatos.get(campo), bool)
        or metadatos[campo] < 0
        for campo in campos
    ):
        raise GeminiResponseError(
            "Gemini devolvió metadatos de uso de tokens incompletos o inválidos."
        )

    return {campo: metadatos[campo] for campo in campos}


def obtener_dato_de_prueba(pregunta: str) -> str:
    """Valida una pregunta y devuelve la respuesta de texto de Gemini."""
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("La pregunta debe ser un texto no vacío.")

    system_instruction = (
        "Eres un asistente técnico. Responde siempre en un máximo de 3 oraciones."
    )
    url, body = armar_peticion(pregunta, system_instruction)
    datos = enviar_peticion(url, body)
    return extraer_texto(datos)


def main() -> int:
    """Ejecuta una consulta de ejemplo y devuelve un código de salida."""
    pregunta = "Explica qué es una API en términos simples."
    system_instruction = (
        "Eres un asistente técnico. Responde siempre en un máximo de 3 oraciones."
    )

    try:
        url, body = armar_peticion(pregunta, system_instruction)
        respuesta_json = enviar_peticion(url, body)
        texto = extraer_texto(respuesta_json)
        metadata = extraer_metadatos_uso(respuesta_json)
    except (GeminiError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(texto)
    print("Tokens de entrada:", metadata["promptTokenCount"])
    print("Tokens de salida:", metadata["candidatesTokenCount"])
    print("Total:", metadata["totalTokenCount"])
    return 0


if __name__ == "__main__":
    # La llamada queda protegida para que importar el módulo no realice peticiones.
    raise SystemExit(main())