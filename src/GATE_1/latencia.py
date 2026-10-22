"""Mide la latencia de solicitudes a Gemini y estima el costo de la última."""

import math
import sys
import time
from numbers import Real
from typing import Any

# Estos módulos se importan desde el directorio GATE_1 al ejecutar este script.
from costo import (
    MODELO_TARIFADO,
    PRECIO_ENTRADA_POR_TOKEN,
    PRECIO_SALIDA_POR_TOKEN,
    calcular_costo,
)
from monolitico import GeminiError, armar_peticion, enviar_peticion

PRECIO_ENTRADA = PRECIO_ENTRADA_POR_TOKEN
PRECIO_SALIDA = PRECIO_SALIDA_POR_TOKEN
PREGUNTA_PREDETERMINADA = "Confirma en una frase corta que esta conexión funciona"
INSTRUCCION_SISTEMA = "Responde únicamente con una frase breve."


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
        if not isinstance(pregunta, str) or not pregunta.strip():
            raise ValueError("La pregunta no puede estar vacía.")
        if not isinstance(intentos, int) or isinstance(intentos, bool) or intentos <= 0:
            raise ValueError("El número de intentos debe ser mayor que cero.")
        for nombre, precio in (
            ("precio_entrada", precio_entrada),
            ("precio_salida", precio_salida),
        ):
            if (
                not isinstance(precio, Real)
                or isinstance(precio, bool)
                or not math.isfinite(precio)
                or precio < 0
            ):
                raise ValueError(f"{nombre} debe ser un número finito no negativo.")

        self.pregunta = pregunta
        self.intentos = intentos
        self.precio_entrada = precio_entrada
        self.precio_salida = precio_salida
        self.latencias: list[float] = []

    def medir_solicitudes(self) -> dict[str, Any]:
        """Envía las solicitudes configuradas, mide su duración y devuelve la última respuesta."""
        # Reinicia la medición para que una segunda ejecución no acumule tiempos anteriores.
        self.latencias.clear()
        respuesta_json: dict[str, Any] = {}

        for intento in range(1, self.intentos + 1):
            url, body = armar_peticion(self.pregunta, INSTRUCCION_SISTEMA)
            # perf_counter ofrece resolución adecuada para medir intervalos cortos.
            inicio = time.perf_counter()
            respuesta_json = enviar_peticion(url, body)
            duracion = time.perf_counter() - inicio
            self.latencias.append(duracion)
            print(f"Intento {intento}: {duracion:.2f} segundos")

        return respuesta_json

    def ejecutar(self) -> float:
        """Mide las solicitudes, muestra el promedio y estima el último costo."""
        respuesta_json = self.medir_solicitudes()
        # Se devuelve el promedio de todos los intentos y se cobra solo la última respuesta.
        latencia_promedio = sum(self.latencias) / len(self.latencias)
        print(f"Latencia promedio: {latencia_promedio:.2f} segundos")

        costo = calcular_costo(
            respuesta_json,
            self.precio_entrada,
            self.precio_salida,
        )
        print(f"Costo estimado de la última petición ({MODELO_TARIFADO}): ${costo:.8f} USD")
        return latencia_promedio


if __name__ == "__main__":
    try:
        Latencia().ejecutar()
    except (GeminiError, ValueError) as error:
        print(f"Error al medir la latencia: {error}", file=sys.stderr)
        raise SystemExit(1) from error
