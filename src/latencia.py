"""Mide la latencia de solicitudes a Gemini y estima el costo de la última."""

import time
from typing import Any
from costo import calcular_costo
from monolitico import armar_peticion, enviar_peticion

PRECIO_ENTRADA = 0.00000010
PRECIO_SALIDA = 0.00000030
PREGUNTA_PREDETERMINADA = "Confirma en una frase corta que esta conexión funciona"


class Latencia:
    """Agrupa la configuración y ejecución de una prueba de latencia."""

    def __init__(
        self,
        pregunta: str = PREGUNTA_PREDETERMINADA,
        intentos: int = 4,
        precio_entrada: float = PRECIO_ENTRADA,
        precio_salida: float = PRECIO_SALIDA,
    ) -> None:
        """Configura la pregunta, el número de solicitudes y sus tarifas."""
        if not pregunta.strip():
            raise ValueError("La pregunta no puede estar vacía.")
        if intentos <= 0:
            raise ValueError("El número de intentos debe ser mayor que cero.")

        self.pregunta = pregunta
        self.intentos = intentos
        self.precio_entrada = precio_entrada
        self.precio_salida = precio_salida
        self.latencias: list[float] = []

    def medir_solicitudes(self) -> dict[str, Any]:
        """Envía las solicitudes configuradas, mide su duración y devuelve la última respuesta."""
        self.latencias.clear()
        respuesta_json: dict[str, Any] = {}

        for intento in range(1, self.intentos + 1):
            url, body = armar_peticion(self.pregunta)
            inicio = time.perf_counter()
            respuesta_json = enviar_peticion(url, body)
            duracion = time.perf_counter() - inicio
            self.latencias.append(duracion)
            print(f"Intento {intento}: {duracion:.2f} segundos")

        return respuesta_json

    def ejecutar(self) -> float:
        """Mide las solicitudes, muestra el promedio y estima el último costo."""
        respuesta_json = self.medir_solicitudes()
        latencia_promedio = sum(self.latencias) / len(self.latencias)
        print(f"Latencia promedio: {latencia_promedio:.2f} segundos")

        costo = calcular_costo(
            respuesta_json,
            self.precio_entrada,
            self.precio_salida,
        )
        print(f"Costo de la última petición: {costo}")
        return latencia_promedio


if __name__ == "__main__":
    Latencia().ejecutar()
