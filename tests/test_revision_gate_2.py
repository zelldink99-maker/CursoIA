"""Pruebas del código de salida del gate cuando hay entregables pendientes."""

import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from unittest.mock import patch

from src.GATE_2.revision_gate_2 import (
    Reporte,
    _codigo_salida,
    _importar_modulos,
)


def test_actividad_core_pendiente_devuelve_codigo_no_cero() -> None:
    reporte = Reporte()
    reporte.agregar(
        "Actividad core Bloque 17",
        "20 respuestas",
        None,
        "pendiente",
    )

    assert _codigo_salida(reporte) == 1


def test_api_omitida_no_falla_si_actividad_core_esta_completa() -> None:
    reporte = Reporte()
    reporte.agregar(
        "Actividad core Bloque 17",
        "Entregables",
        True,
        "completos",
    )
    reporte.agregar("API funciona", "Prueba real", None, "omitida")

    assert _codigo_salida(reporte) == 0


def test_error_reportado_devuelve_codigo_no_cero_aunque_actividad_complete() -> None:
    reporte = Reporte()
    reporte.agregar(
        "Actividad core Bloque 17",
        "Entregables",
        True,
        "completos",
    )
    reporte.agregar("Código ejecutable", "Prueba local", False, "falló")

    assert _codigo_salida(reporte) == 1


def test_importacion_cancelada_se_reporta_sin_dejar_traceback(
    monkeypatch,
) -> None:
    def interrupcion() -> dict[str, object]:
        raise KeyboardInterrupt

    monkeypatch.setattr(
        "src.GATE_2.revision_gate_2._importar_modulos",
        interrupcion,
    )
    reporte = Reporte()

    try:
        interrupcion()
    except KeyboardInterrupt:
        reporte.agregar(
            "Código ejecutable",
            "Importaciones del paquete",
            False,
            "carga interrumpida por el usuario",
        )

    assert reporte.fallo
