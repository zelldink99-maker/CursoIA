"""Punto de entrada compatible que delega en el cliente principal."""

import sys
from pathlib import Path

if __package__:
    from . import cliente
else:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.GATE_1 import cliente


def main() -> int:
    """Ejecuta la consulta con reintentos y registro de costos."""
    return cliente.main()


if __name__ == "__main__":
    raise SystemExit(main())
