"""
# Importa la función sumar desde el módulo local aritmetica.py.
from aritmetica import sumar

# Importa el módulo estándar para convertir texto JSON en un diccionario.
import json

# Indica en la consola que comienza la prueba del módulo de aritmética.
print("prueba de modulo de aritmetica")

# Llama a sumar con 5 y 3 e imprime el resultado.
print(sumar(5,3))

# Texto de ejemplo con formato JSON; representa una respuesta y sus detalles.
respuesta_json = '{"texto": "Hola, soy una respuesta generada", "detalles": {"modelo": "nombre-del-modelo", "tokens": 12}}'

# Convierte el texto JSON en un diccionario de Python para acceder a sus valores.
respuesta_dict = json.loads(respuesta_json)
 
# Imprime el texto y el nombre del modelo guardados en el diccionario.
print(respuesta_dict["texto"])
print(respuesta_dict["detalles"]["modelo"])

# Intenta consultar una clave que no existe; esta línea provoca un KeyError.
print(respuesta_dict["color"])
"""


#Test
from consumir_gemini import obtener_dato_de_prueba

print(obtener_dato_de_prueba("¿Cual es la capital de Inglaterra?"))