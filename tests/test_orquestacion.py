import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Permite importar `src` tanto desde pytest como al ejecutar este archivo.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.runnables import RunnableLambda  # noqa: E402

from src.GATE_1.enrutamiento import construir_cadena_queja_segura  # noqa: E402


def _simular_fallo_de_red(_: dict[str, str]) -> None:
    """Simula que la cadena del modelo falla al procesar el mensaje."""
    raise ConnectionError("Fallo de red simulado")


def test_cadena_queja_usa_fallback_ante_fallo_del_modelo() -> None:
    cadena_del_modelo = RunnableLambda(_simular_fallo_de_red)
    cadena_segura = construir_cadena_queja_segura(cadena_del_modelo)

    resultado = cadena_segura.invoke({"mensaje": "esto no funciona"})

    assert "equipo" in resultado.lower()


if __name__ == "__main__":
    # Ejecuta pytest en un proceso limpio para evitar problemas de imports/plugins.
    proceso = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(Path(__file__).resolve())],
        cwd=PROJECT_ROOT,
        check=False,
    )
    raise SystemExit(proceso.returncode)
