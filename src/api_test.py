# os permite leer variables de entorno; requests envía la petición HTTP;
# json crea el cuerpo JSON; load_dotenv carga variables desde el archivo .env.
import os
import requests
import json
from dotenv import load_dotenv

# Carga las variables del archivo .env encontrado en el directorio actual
# o en sus directorios superiores.
load_dotenv()

# Dirección del endpoint de Gemini y modelo al que se enviará la solicitud.
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"

# Construye el cuerpo JSON requerido por la API, con el texto de la consulta.
payload = json.dumps({
  "contents": [
    {
      "parts": [
        {
          "text": "Explicame como funciona la NBA en 20 palabras"
        }
      ]
    }
  ]
})

# Configura la clave de autenticación y declara que el cuerpo está en JSON.
headers = {
  'x-goog-api-key': os.getenv("GEMINI_API_KEY"),
  'Content-Type': 'application/json'
}

# Envía una solicitud POST e imprime el texto devuelto por el servidor.
# El bloque except captura errores que ocurran al enviar la petición.
try:
    response = requests.request("POST", url, headers=headers, data=payload)
    print(response.text)

except Exception as e:
    print(f"Error: {e}")

# Este mensaje se imprime al final incluso si la petición falló;
# por sí solo no confirma que la llamada haya sido exitosa.
print("API request completed successfully.")