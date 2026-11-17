"""Verifica los requisitos locales del laboratorio de tuning, sin usar la API."""

from __future__ import annotations

import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    """Comprueba Python, los paquetes requeridos y la presencia de la clave."""
    if sys.version_info < (3, 10):
        print("Se requiere Python 3.10 o superior.")
        return 1

    try:
        from dotenv import load_dotenv
    except ImportError:
        print(
            "Falta python-dotenv. Ejecuta: "
            "python -m pip install google-genai python-dotenv"
        )
        return 1

    load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

    try:
        version_sdk = version("google-genai")
    except PackageNotFoundError:
        print(
            "Falta google-genai. Ejecuta: "
            "python -m pip install google-genai python-dotenv"
        )
        return 1

    try:
        from google.genai import types

        types.TuningMode
        types.AdapterSize
    except (ImportError, AttributeError) as error:
        print(
            "El SDK instalado no expone los tipos de tuning requeridos: "
            f"{error}. Actualiza con: python -m pip install -U google-genai"
        )
        return 1

    print(f"google-genai instalado, versión {version_sdk}")
    if not os.environ.get("GEMINI_API_KEY"):
        print(
            'Falta GEMINI_API_KEY. Agrégala al archivo ".env" '
            "de la raíz del proyecto."
        )
        return 1

    print("GEMINI_API_KEY detectada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
