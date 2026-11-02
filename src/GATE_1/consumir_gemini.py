"""Interfaz compatible de consulta delegada en el cliente principal."""

import sys
from pathlib import Path
from typing import Any

if __package__:
    from . import cliente, monolitico
else:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.GATE_1 import cliente, monolitico


def _extraer_texto(datos: Any) -> str:
    """Conserva el helper anterior usando la validación compartida."""
    return monolitico.extraer_texto(datos)


def obtener_dato_de_prueba(pregunta: str) -> str:
    """Conserva la interfaz previa y consulta mediante el cliente principal."""
    return cliente.consultar_modelo(pregunta)


def _main() -> int:
    """Delega la ejecución de consola al único flujo principal."""
    return cliente.main()


if __name__ == "__main__":
    raise SystemExit(_main())
