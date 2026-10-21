"""Calcula el costo de uso de una respuesta de la API."""

from typing import TypedDict


class MetadatosUso(TypedDict):
    """Contadores de tokens incluidos en la respuesta de la API."""

    promptTokenCount: int
    candidatesTokenCount: int
    totalTokenCount: int


class DatosRespuesta(TypedDict):
    """Parte de la respuesta necesaria para calcular el costo."""

    usageMetadata: MetadatosUso


def calcular_costo(
    datos: DatosRespuesta,
    precio_entrada: float,
    precio_salida: float,
) -> float:
    """Calcula el costo usando el precio por token de entrada y de salida."""
    # 1. Obtiene los metadatos con el consumo de tokens.
    uso = datos["usageMetadata"]

    # 2. Separa los tokens enviados a la API de los tokens generados.
    tokens_entrada = uso["promptTokenCount"]
    tokens_salida = uso["candidatesTokenCount"]

    # 3. Multiplica cada consumo por su tarifa correspondiente.
    costo_entrada = tokens_entrada * precio_entrada
    costo_salida = tokens_salida * precio_salida

    # 4. Suma ambos importes y devuelve el costo total.
    return costo_entrada + costo_salida


if __name__ == "__main__":
    # Ejemplo de respuesta con 850 tokens de entrada y 320 de salida.
    datos_ejemplo: DatosRespuesta = {
        "usageMetadata": {
            "promptTokenCount": 850,
            "candidatesTokenCount": 320,
            "totalTokenCount": 1170,
        }
    }

    # Las tarifas están expresadas en costo por token.
    costo = calcular_costo(datos_ejemplo, 0.00000010, 0.00000040)
    print(costo)
