import time
from costo import calcular_costo
from monolitico import armar_peticion, enviar_peticion
 
PRECIO_ENTRADA = 0.00000010  # el valor real de la página de precios
PRECIO_SALIDA = 0.00000030
pregunta = "Confirma en una frase corta que esta conexión funciona"
 
latencias = []
for i in range(4):
	url, body = armar_peticion(pregunta)
	inicio = time.perf_counter()
	respuesta_json = enviar_peticion(url, body)
	fin = time.perf_counter()
	latencias.append(fin - inicio)
	print(f"Intento {i + 1}: {latencias[-1]:.2f} segundos")
 
latencia_promedio = sum(latencias) / len(latencias)
print(f"Latencia promedio: {latencia_promedio:.2f} segundos")
 
costo = calcular_costo(respuesta_json, PRECIO_ENTRADA, PRECIO_SALIDA)
print(f"Costo de la última petición: {costo}")