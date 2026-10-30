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


def contar_coincidencias(
    tokens_referencia: list[str],
    tokens_respuesta: list[str],
) -> int:
    """Cuenta coincidencias entre tokens sin ignorar sus repeticiones."""
    if isinstance(tokens_referencia, str):
        raise TypeError("tokens_referencia debe ser una lista de tokens, no str")
    if isinstance(tokens_respuesta, str):
        raise TypeError("tokens_respuesta debe ser una lista de tokens, no str")

    # Counter conserva cuántas veces aparece cada token; & toma el mínimo
    # de ambos conteos para no premiar repeticiones que no están en la referencia.
    interseccion = Counter(tokens_referencia) & Counter(tokens_respuesta)
    return sum(interseccion.values())


def calcular_precision_cobertura_f1(
    tokens_referencia: list[str],
    tokens_respuesta: list[str],
) -> dict[str, float]:
    """Calcula precisión, cobertura y F1 a partir de dos listas de tokens."""
    coincidencias = contar_coincidencias(tokens_referencia, tokens_respuesta)

    if not tokens_respuesta or not tokens_referencia:
        return {"precision": 0.0, "cobertura": 0.0, "f1": 0.0}

    # La precisión usa como total la respuesta generada; la cobertura, la referencia.
    precision = coincidencias / len(tokens_respuesta)
    cobertura = coincidencias / len(tokens_referencia)
    if precision + cobertura == 0:
        f1 = 0.0
    else:
        # Media armónica: combina ambas métricas y baja si una de ellas es baja.
        f1 = 2 * precision * cobertura / (precision + cobertura)

    return {"precision": precision, "cobertura": cobertura, "f1": f1}


def calcular_metricas(texto_referencia: str, texto_respuesta: str) -> dict[str, float]:
    """Limpia y tokeniza ambos textos antes de calcular sus métricas."""
    return calcular_precision_cobertura_f1(
        procesar_texto(texto_referencia),
        procesar_texto(texto_respuesta),
    )
