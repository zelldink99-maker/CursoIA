# os permite leer variables de entorno; requests envía la petición HTTP;
# json crea el cuerpo JSON; load_dotenv carga variables desde el archivo .env.
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Lee la configuración desde la raíz, aunque el script se ejecute desde otra carpeta.
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# Endpoint del modelo que recibe la solicitud de generación de contenido.
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"


def main() -> int:
    """Envía una pregunta a Gemini e informa si la solicitud tuvo éxito."""
    # No se intenta llamar a la API si falta una credencial real.
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "tu_llave_aqui":
        print(f"Error: configura GEMINI_API_KEY en {PROJECT_ROOT / '.env'}.")
        return 1

    # El contenido enviado debe coincidir con el formato esperado por Gemini.
    payload = {
        "contents": [
            {"parts": [{"text": "Explícame cómo funciona la NBA en 20 palabras"}]}
        ]
    }
    # La clave va en un encabezado para no exponerla en la URL.
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"Error al consultar Gemini: {error}")
        return 1

    # El estado HTTP ya fue validado; se puede mostrar el cuerpo de la respuesta.
    print(response.text)
    print("La API respondió correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())