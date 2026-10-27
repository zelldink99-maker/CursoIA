"""Calcula el costo de uso de una respuesta de la API."""

import math
from numbers import Real
from typing import TypedDict


class MetadatosUso(TypedDict):
    """Contadores de tokens incluidos en la respuesta de la API."""

    promptTokenCount: int
    candidatesTokenCount: int
    totalTokenCount: int


class MetadatosUsoConPensamiento(MetadatosUso, total=False):
    """Incluye los tokens de pensamiento cuando Gemini los reporta aparte."""

    thoughtsTokenCount: int


class DatosRespuesta(TypedDict):
    """Parte de la respuesta necesaria para calcular el costo."""

    usageMetadata: MetadatosUsoConPensamiento


MODELO_TARIFADO = "gemini-3.8-flash"
PRECIO_ENTRADA_USD_POR_MILLON = 0.75
PRECIO_SALIDA_USD_POR_MILLON = 3.75
PRECIO_ENTRADA_POR_TOKEN = PRECIO_ENTRADA_USD_POR_MILLON / 1_000_000
PRECIO_SALIDA_POR_TOKEN = PRECIO_SALIDA_USD_POR_MILLON / 1_000_000


def calcular_costo(
    datos: DatosRespuesta,
    precio_entrada: float = PRECIO_ENTRADA_POR_TOKEN,
    precio_salida: float = PRECIO_SALIDA_POR_TOKEN,
) -> float:
    """Estima el costo con precios USD/token; incluye tokens de pensamiento."""
    if not isinstance(datos, dict):
        raise ValueError("La respuesta debe ser un objeto con metadatos de uso.")
    uso = datos.get("usageMetadata")
    if not isinstance(uso, dict):
        raise ValueError("La respuesta no contiene metadatos de uso válidos.")

    tokens_entrada = uso.get("promptTokenCount")
    tokens_salida = uso.get("candidatesTokenCount")
    tokens_pensamiento = uso.get("thoughtsTokenCount", 0)
    if any(
        not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 0
        for tokens in (tokens_entrada, tokens_salida, tokens_pensamiento)
    ):
        raise ValueError("Los contadores de tokens deben ser enteros no negativos.")

    precios = (precio_entrada, precio_salida)
    if any(
        not isinstance(precio, Real)
        or isinstance(precio, bool)
        or not math.isfinite(precio)
        or precio < 0
        for precio in precios
    ):
        raise ValueError(
            "Los precios por token deben ser números finitos no negativos."
        )

    return (
        tokens_entrada * precio_entrada
        + (tokens_salida + tokens_pensamiento) * precio_salida
    )
