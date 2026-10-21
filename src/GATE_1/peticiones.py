"""Construye y envía solicitudes HTTP a la API de Gemini."""

# json serializa el cuerpo y requests realiza la comunicación HTTP.
import json
import requests


def create_payload(prompt):
    """Serializa el prompt con la estructura de contenido que espera Gemini."""
    return json.dumps(
        {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }
    )


def create_headers(api_key):
    """Crea los encabezados de autenticación y formato para la petición."""
    return {
        'x-goog-api-key': api_key,
        'Content-Type': 'application/json'
    }


def make_request(url, headers, payload):
    """Envía el cuerpo JSON; devuelve el texto o un mensaje de error HTTP."""
    try:
        # El timeout impide que una conexión detenida bloquee el programa indefinidamente.
        response = requests.request(
            "POST", url, headers=headers, data=payload, timeout=30
        )
        # Convierte las respuestas HTTP 4xx/5xx en excepciones de requests.
        response.raise_for_status()
        return response.text
    except requests.RequestException as error:
        return f"Error: {error}"