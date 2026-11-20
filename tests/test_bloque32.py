"""Prueba local de la unidad completa del Bloque 32."""

from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_2 import unidad_completa_supervision


def test_unidad_muestra_los_tres_pasos(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert unidad_completa_supervision.main() == 0
    salida = capsys.readouterr().out

    assert "PASO 1: versionado de mi prompt" in salida
    assert "0037a44f2a2 - version inicial" in salida
    assert "--- version_anterior" in salida
    assert "+++ version_nueva" in salida
    assert "PASO 2: punto de supervision" in salida
    assert "ba5b9a997ba3" in salida
    assert "version ba5b9a997ba3 activada" in salida
    assert "PASO 3: mi matriz de riesgos" in salida
    assert len(unidad_completa_supervision.MIS_RIESGOS) >= 5
    assert "CRITICO  (16)" in salida
    assert "[AL LIMITE]" in salida
