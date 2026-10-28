"""Limpieza, tokenización y vectorización básica de texto."""

import re
from collections import Counter


def limpiar_texto(texto: str) -> str:
    """Normaliza el texto a minúsculas y elimina puntuación y espacios extra."""
    if not isinstance(texto, str):
        tipo = type(texto).__name__
        raise TypeError(f"limpiar_texto espera str, no {tipo}")

    texto = texto.lower()
    texto = re.sub(r"[^\w\s]", "", texto)
    return re.sub(r"\s+", " ", texto).strip()


def tokenizar(texto_limpio: str) -> list[str]:
    """Convierte texto limpio en una lista de tokens separados por espacios."""
    return texto_limpio.split()


def procesar_texto(texto: str) -> list[str]:
    """Limpia y tokeniza un texto en una sola operación."""
    return tokenizar(limpiar_texto(texto))


def vectorizar(tokens: list[str]) -> Counter[str]:
    """Cuenta cuántas veces aparece cada token."""
    return Counter(tokens)
