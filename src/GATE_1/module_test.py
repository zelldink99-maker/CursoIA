"""Demuestra el envío de una consulta usando las funciones de peticiones.py."""

# Path permite localizar el .env del proyecto desde cualquier directorio actual.
from pathlib import Path

import os
from dotenv import load_dotenv

# Importa las funciones que preparan la petición y la que la envía a Gemini.
from peticiones import create_headers, create_payload, make_request

# Obtiene la ruta raíz del proyecto y apunta al archivo .env.
env_path = Path(__file__).resolve().parents[2] / ".env"
# Mantiene el comportamiento del ejemplo: los valores del archivo prevalecen.
load_dotenv(dotenv_path=env_path, override=True)

def main() -> int:
    """Envía una pregunta de prueba con las funciones del módulo peticiones."""
    # Comprueba la configuración antes de construir o enviar la solicitud.
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "tu_llave_aqui":
        print(f"Error: configura GEMINI_API_KEY en {env_path}.")
        return 1

    # Reutiliza las funciones del módulo hermano para preparar y enviar la petición.
    result = make_request(
        url="https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
        headers=create_headers(api_key),
        payload=create_payload("Explícame cómo funciona la NBA en 20 palabras"),
    )

    # make_request devuelve un texto de error si falla una petición HTTP.
    print(result)
    return 1 if result.startswith("Error:") else 0


if __name__ == "__main__":
    raise SystemExit(main())