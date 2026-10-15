# json prepara el cuerpo que se enviará a la API y requests realiza
# la comunicación HTTP.
import json
import requests


# Convierte el prompt en la estructura JSON que espera el endpoint de Gemini.
def create_payload(prompt):
    return json.dumps({
    "contents": [
        {
        "parts": [
            {
            "text": prompt
            }
        ]
        }
    ]
    })

# Crea los encabezados HTTP, incluyendo la clave y el tipo de contenido JSON.
def create_headers(api_key):
    return {
        'x-goog-api-key': api_key,
        'Content-Type': 'application/json'
    }

# Envía una solicitud POST con la URL, los encabezados y el cuerpo recibidos.
# Devuelve el texto de la respuesta o un mensaje si ocurre una excepción.
def make_request(url, headers, payload):
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.text
    except Exception as e:
        return f"Error: {e}"