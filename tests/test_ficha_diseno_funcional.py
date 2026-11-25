import csv
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ficha_datos import RUTA, cargar
from presupuesto.presupuesto_alcance import funcionalidades, recortar
from verificar_ficha_completa import (
    verificar_completa,
    verificar_criterios,
    verificar_plan,
    verificar_revision,
)


REVISION_VALIDA = """\
# Revision del alcance
Revisor: Persona revisora
Fecha: 2026-11-25

- Hallazgo 1: La prueba de latencia necesita conservar su conjunto de datos.
  Decisión: aceptado. Cambio: se documentó el conjunto de prueba.

- Hallazgo 2: El hito final deja tiempo para las pruebas.
  Decisión: rechazado. Motivo: las nueve horas cubren el plan de pruebas.
"""


def test_ficha_cubre_requerimientos_y_plan():
    ficha = cargar(ROOT_DIR / RUTA)

    errores, avisos = verificar_criterios(ficha)
    assert errores == []
    assert avisos == []
    assert verificar_plan(ficha) == []
    assert len(ficha["criterios"]) == 11
    assert len(ficha["hitos"]) == 6


def test_revision_valida_y_plantilla_pendiente():
    ficha_texto = (ROOT_DIR / RUTA).read_text(encoding="utf-8")
    errores, _ = verificar_completa(ficha_texto, REVISION_VALIDA)
    assert errores == []

    revision_actual = (ROOT_DIR / "docs/revision_alcance.md").read_text(
        encoding="utf-8"
    )
    errores, _ = verificar_completa(ficha_texto, revision_actual)
    assert errores == []

    errores = verificar_revision(
        "Revisor: PENDIENTE\nFecha: PENDIENTE\n"
    )
    assert any("hallazgos" in error for error in errores)
    assert any("revisor" in error for error in errores)
    assert any("fecha" in error for error in errores)


def test_presupuesto_incluye_mvp_y_contenedor_sin_exceder_tope():
    dentro, _, usado = recortar(funcionalidades)
    ids_dentro = {item["id"] for item in dentro}

    assert {"RF-01", "RF-02", "RF-03", "RF-04", "RF-05"} <= ids_dentro
    assert "RNF-04" in ids_dentro
    assert usado <= 15


def test_archivo_de_prueba_reproduce_los_conteos_de_aceptacion():
    ruta = ROOT_DIR / "data/ventas_prueba.csv"
    with ruta.open(encoding="utf-8", newline="") as archivo:
        filas = list(csv.DictReader(archivo))

    filas_completas = [fila for fila in filas if fila["importe"]]
    filas_unicas = {}
    for fila in filas_completas:
        clave = (fila["pedido_id"], fila["fecha"])
        filas_unicas.setdefault(clave, fila)
    ventas = sum(
        float(fila["importe"])
        for fila in filas_unicas.values()
        if fila["fecha"].startswith("2026-11")
    )

    assert len(filas) == 4
    assert len(filas_completas) == 3
    assert len(filas_completas) - len(filas_unicas) == 1
    assert len(filas_unicas) == 2
    assert ventas == 300
    assert sum(not fila["importe"] for fila in filas) == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main(["-v", str(Path(__file__).resolve())]))
