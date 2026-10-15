# os permite leer la clave guardada en las variables de entorno.
import os

# requests envía la solicitud HTTP a la API de Gemini.
import requests

# load_dotenv carga en el entorno las variables definidas en el archivo .env.
from dotenv import load_dotenv
  
# Busca y carga las variables del archivo .env.
load_dotenv()
  
# Envía una pregunta a Gemini y devuelve el texto generado.
def obtener_dato_de_prueba(pregunta):
     # Obtiene la clave de API configurada como GEMINI_API_KEY.
     api_key = os.getenv("GEMINI_API_KEY")

     # Indica qué modelo de Gemini se utilizará.
     modelo = "gemini-3.5-flash"

     # Construye la URL del endpoint e incluye la clave para autenticar la llamada.
     url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"

     # Organiza la pregunta en el formato que espera la API.
     body = {
     	"contents": [
         	{"parts": [{"text": pregunta}]}
     	]
     }

     # Envía la pregunta como una solicitud POST con el cuerpo en formato JSON.
     respuesta = requests.post(url, json=body)

     # Convierte la respuesta JSON recibida en un diccionario de Python.
     datos = respuesta.json()

     # Extrae y devuelve el texto de la primera respuesta generada por Gemini.
     return datos["candidates"][0]["content"]["parts"][0]["text"]

# Ejecuta la función con una pregunta de prueba e imprime el texto generado.
print(obtener_dato_de_prueba("Confirma en una frase corta que esta conexion funciona"))