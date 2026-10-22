"""Ejecuta una demostración aritmética y consulta de ejemplo a Gemini."""

import sys

# Los imports relativos permiten ejecutar el módulo desde la raíz con python -m.
from aritmetica import sumar
from consumir_gemini import obtener_dato_de_prueba


def main() -> int:
    """Muestra la suma 5 + 3 y la respuesta de Gemini."""
    # Esta demostración combina una función local con una consulta remota.
    try:
        print(f"5 + 3 = {sumar(5, 3)}")
        print(obtener_dato_de_prueba("¿Cuál es la capital de Inglaterra?"))
    except (RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    # Evita ejecutar la demostración al importar este módulo desde otro archivo.
    raise SystemExit(main())
