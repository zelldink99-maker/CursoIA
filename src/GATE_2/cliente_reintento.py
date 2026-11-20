"""Reintenta operaciones que fallan por condiciones transitorias."""

import math
import random
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def con_reintento(
    funcion: Callable[[], T],
    intentos: int = 3,
    espera_base: float = 2,
    espera_maxima: float = 30,
) -> T:
    """Ejecuta una operación con backoff exponencial y jitter ante TimeoutError."""
    if not callable(funcion):
        raise ValueError("La operación debe ser invocable.")
    if not isinstance(intentos, int) or isinstance(intentos, bool) or intentos <= 0:
        raise ValueError("El número de intentos debe ser un entero mayor que cero.")
    for nombre, espera in (
        ("espera_base", espera_base),
        ("espera_maxima", espera_maxima),
    ):
        if (
            not isinstance(espera, (int, float))
            or isinstance(espera, bool)
            or not math.isfinite(espera)
            or espera < 0
        ):
            raise ValueError(f"{nombre} debe ser un número finito no negativo.")

    espera_actual = min(float(espera_base), float(espera_maxima))
    for intento in range(1, intentos + 1):
        try:
            return funcion()
        except TimeoutError:
            # Propaga el último fallo para que la capa pública lo pueda traducir.
            if intento == intentos:
                raise

            # El jitter evita que varios clientes vuelvan a intentar a la vez.
            jitter = random.uniform(0, espera_actual * 0.1)
            espera = min(espera_actual + jitter, float(espera_maxima))
            print(
                f"[!] Intento {intento} de {intentos} falló. "
                f"Reintentando en {espera:.1f}s..."
            )
            time.sleep(espera)
            # Duplica el tiempo de espera sin superar el máximo configurado.
            espera_actual = min(espera_actual * 2, float(espera_maxima))

    raise RuntimeError("El flujo de reintentos terminó inesperadamente.")
