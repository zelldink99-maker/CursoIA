"""Construye y valida localmente un dataset demostrativo para PEFT."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence

from google.genai import types

EjemploRaw = tuple[str, dict[str, str]]

EJEMPLOS_RAW: tuple[EjemploRaw, ...] = (
    (
        "Compré una chaqueta hace una semana y quiero devolverla.",
        {"categoria": "devolucion", "accion_sugerida": "indicar el proceso de devolución"},
    ),
    (
        "El talle no me quedó, ¿cómo inicio la devolución?",
        {"categoria": "devolucion", "accion_sugerida": "indicar el proceso de devolución"},
    ),
    (
        "Recibí el producto pero ya no lo necesito y quiero devolverlo.",
        {"categoria": "devolucion", "accion_sugerida": "indicar el proceso de devolución"},
    ),
    (
        "Me cobraron dos veces la misma compra con mi tarjeta.",
        {"categoria": "cobro", "accion_sugerida": "revisar los cargos duplicados"},
    ),
    (
        "El total de mi factura no coincide con el precio que vi al comprar.",
        {"categoria": "cobro", "accion_sugerida": "verificar el detalle del cobro"},
    ),
    (
        "Hay un cargo en mi cuenta que no reconozco.",
        {"categoria": "cobro", "accion_sugerida": "revisar los datos del cargo"},
    ),
    (
        "El pedido todavía no llegó y la fecha estimada ya pasó.",
        {"categoria": "envio", "accion_sugerida": "consultar el seguimiento del pedido"},
    ),
    (
        "¿Me pueden decir dónde está mi paquete?",
        {"categoria": "envio", "accion_sugerida": "compartir el estado del envío"},
    ),
    (
        "El seguimiento indica entregado, pero no recibí el paquete.",
        {"categoria": "envio", "accion_sugerida": "investigar la entrega del paquete"},
    ),
    (
        "El código promocional no se aplica al finalizar la compra.",
        {"categoria": "promocion", "accion_sugerida": "verificar las condiciones de la promoción"},
    ),
    (
        "¿La oferta de dos por uno sigue vigente esta semana?",
        {"categoria": "promocion", "accion_sugerida": "confirmar la vigencia de la promoción"},
    ),
    (
        "No veo reflejado el descuento que anunciaba la página.",
        {"categoria": "promocion", "accion_sugerida": "revisar el descuento anunciado"},
    ),
)


def construir_ejemplos(
    ejemplos_raw: Sequence[EjemploRaw],
) -> list[types.TuningExample]:
    """Convierte pares de entrada y salida a los tipos reales del SDK."""
    return [
        types.TuningExample(
            text_input=texto,
            output=json.dumps(salida, ensure_ascii=False),
        )
        for texto, salida in ejemplos_raw
    ]


def validar_dataset(
    examples: Sequence[types.TuningExample],
    claves_esperadas: tuple[str, ...] = ("categoria", "accion_sugerida"),
) -> list[str]:
    """Reporta entradas vacías o duplicadas y salidas JSON con esquema inválido."""
    problemas: list[str] = []
    vistos: set[str | None] = set()

    for indice, ejemplo in enumerate(examples):
        text_input = ejemplo.text_input
        output = ejemplo.output

        if not text_input or not text_input.strip():
            problemas.append(f"ejemplo {indice}: text_input vacio")
        if not output or not output.strip():
            problemas.append(f"ejemplo {indice}: output vacio")
            continue
        if text_input in vistos:
            problemas.append(f"ejemplo {indice}: text_input duplicado")
        vistos.add(text_input)

        try:
            salida = json.loads(output)
        except json.JSONDecodeError:
            problemas.append(f"ejemplo {indice}: output no es JSON valido")
            continue

        if not isinstance(salida, dict):
            problemas.append(f"ejemplo {indice}: output no es un objeto JSON")
            continue
        for clave in claves_esperadas:
            if clave not in salida:
                problemas.append(
                    f'ejemplo {indice}: output no tiene la clave "{clave}"'
                )

    return problemas


def chequear_balance(ejemplos_raw: Sequence[EjemploRaw]) -> Counter[str]:
    """Cuenta cuántos ejemplos hay por categoría."""
    return Counter(salida["categoria"] for _, salida in ejemplos_raw)


def main() -> int:
    """Muestra balance, validación y una prueba deliberadamente rota."""
    examples = construir_ejemplos(EJEMPLOS_RAW)

    # PASO 1: revisar el balance de categorías del dataset.
    print("=" * 70)
    print("PASO 1: balance de MI dataset")
    print("=" * 70)
    for categoria, cuenta in chequear_balance(EJEMPLOS_RAW).most_common():
        print(f"{categoria}: {cuenta}")

    # PASO 2: validar el dataset original, que debe estar limpio.
    print()
    print("=" * 70)
    print("PASO 2: validacion de MI dataset")
    print("=" * 70)
    problemas = validar_dataset(examples)
    print(f"{len(examples)} ejemplos, {len(problemas)} problemas encontrados")
    for problema in problemas:
        print(f" - {problema}")

    # PASO 3: romper una copia para comprobar que el validador detecta el error.
    print()
    print("=" * 70)
    print("PASO 3: rompo un ejemplo a proposito")
    print("=" * 70)
    examples_rotos = list(examples)
    examples_rotos[3] = types.TuningExample(
        text_input=examples[3].text_input,
        output="no es json",
    )
    problemas_rotos = validar_dataset(examples_rotos)
    print(
        f"{len(examples_rotos)} ejemplos, "
        f"{len(problemas_rotos)} problemas encontrados"
    )
    for problema in problemas_rotos:
        print(f" - {problema}")

    return 1 if problemas or not problemas_rotos else 0


if __name__ == "__main__":
    raise SystemExit(main())
