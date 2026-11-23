"""Calcula el promedio ponderado y aplica los criterios no compensables."""

from __future__ import annotations

from math import isclose, isfinite
from collections.abc import Mapping

DIMENSIONES = {
    "pipeline_funcional": 0.25,
    "recuperacion_citacion": 0.15,
    "costo_latencia": 0.10,
    "personalizacion": 0.15,
    "observabilidad": 0.15,
    "seguridad_gobernanza": 0.20,
}


def promedio_ponderado(
    puntajes: Mapping[str, int | float],
    pesos: Mapping[str, float] = DIMENSIONES,
) -> float:
    """Calcula el promedio tras validar dimensiones, pesos y puntajes."""
    dimensiones = set(DIMENSIONES)
    if set(puntajes) != dimensiones or set(pesos) != dimensiones:
        raise ValueError("Los puntajes deben cubrir exactamente las seis dimensiones.")
    if any(
        isinstance(peso, bool)
        or not isinstance(peso, (int, float))
        or not isfinite(peso)
        or peso < 0
        for peso in pesos.values()
    ):
        raise ValueError("Cada peso debe ser un número finito no negativo.")
    if not isclose(sum(pesos.values()), 1.0):
        raise ValueError("Los pesos deben sumar exactamente 1.0.")
    if any(
        isinstance(puntaje, bool)
        or not isinstance(puntaje, (int, float))
        or not isfinite(puntaje)
        or not 0 <= puntaje <= 100
        for puntaje in puntajes.values()
    ):
        raise ValueError("Cada puntaje debe ser un número entre 0 y 100.")
    return sum(puntajes[dimension] * peso for dimension, peso in pesos.items())


def evaluar_gate(
    puntajes: Mapping[str, int | float],
    no_compensables_ok: bool,
    umbral: int | float = 80,
    pesos: Mapping[str, float] = DIMENSIONES,
) -> tuple[float, bool]:
    """Aprueba solo si alcanza el umbral y todos los no compensables pasan."""
    if type(no_compensables_ok) is not bool:
        raise TypeError("no_compensables_ok debe ser True o False.")
    if (
        isinstance(umbral, bool)
        or not isinstance(umbral, (int, float))
        or not isfinite(umbral)
        or not 0 <= umbral <= 100
    ):
        raise ValueError("El umbral debe ser un número entre 0 y 100.")

    promedio = promedio_ponderado(puntajes, pesos)
    return promedio, promedio >= umbral and no_compensables_ok


def main() -> int:
    """Muestra los tres casos de referencia de la rúbrica del Gate 2."""
    puntajes = {
        "pipeline_funcional": 95,
        "recuperacion_citacion": 90,
        "costo_latencia": 85,
        "personalizacion": 88,
        "observabilidad": 92,
        "seguridad_gobernanza": 80,
    }
    print(f"suma de pesos: {sum(DIMENSIONES.values()):.1f}")

    for numero, no_compensables_ok, valores in (
        (1, False, puntajes),
        (2, True, puntajes),
        (3, True, {clave: valor - 15 for clave, valor in puntajes.items()}),
    ):
        promedio, aprueba = evaluar_gate(valores, no_compensables_ok)
        print(
            f"caso {numero}: promedio {promedio:.1f}, "
            f"no compensables OK? {no_compensables_ok} -> aprueba? {aprueba}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
