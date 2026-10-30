"""Pruebas de selección y preparación de revisiones cualitativas."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_1 import revisar_cualitativamente


def _resultados(cantidad: int) -> list[dict[str, object]]:
    return [
        {
            "consulta": f"Consulta {indice}",
            "referencia": f"Referencia {indice}",
            "respuesta": f"Respuesta {indice}",
            "precision": 0.5,
            "cobertura": 0.5,
            "f1": indice / cantidad,
        }
        for indice in range(cantidad)
    ]


@pytest.mark.parametrize(
    ("cantidad", "indices_esperados"),
    [
        (0, []),
        (1, [0]),
        (6, [0, 1, 2, 3, 4, 5]),
        (8, [0, 1, 2, 3, 4, 5, 6, 7]),
        (12, [0, 1, 2, 3, 4, 7, 8, 9, 10, 11]),
    ],
)
def test_seleccionar_muestra_sin_duplicar_casos(
    cantidad: int,
    indices_esperados: list[int],
) -> None:
    muestra = revisar_cualitativamente.seleccionar_muestra(_resultados(cantidad))

    assert [int(caso["consulta"].split()[-1]) for caso in muestra] == (
        indices_esperados
    )
    assert len({caso["consulta"] for caso in muestra}) == len(muestra)


def test_preparar_revision_incluye_campos_de_rubrica() -> None:
    muestra = revisar_cualitativamente.preparar_revision(_resultados(1))

    assert muestra[0]["correccion_factual"] == ""
    assert muestra[0]["completitud"] == ""
    assert muestra[0]["contradiccion"] == ""
    assert muestra[0]["justificacion"] == ""


def test_seleccionar_muestra_rechaza_resultado_sin_f1() -> None:
    with pytest.raises(ValueError, match="F1 numérico"):
        revisar_cualitativamente.seleccionar_muestra([{"consulta": "Consulta"}])


def test_preparar_revision_rechaza_campos_requeridos_ausentes() -> None:
    with pytest.raises(ValueError, match="consulta, referencia, respuesta"):
        revisar_cualitativamente.preparar_revision([{"f1": 0.5}])


def test_script_es_importable_fuera_de_la_raiz(tmp_path: Path) -> None:
    script = ROOT_DIR / "src" / "GATE_1" / "revisar_cualitativamente.py"
    codigo = (
        "import runpy; "
        f"runpy.run_path({str(script)!r}, run_name='import_check')"
    )

    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr


def test_main_carga_resultados_y_guarda_borrador(
    tmp_path: Path,
) -> None:
    entrada = tmp_path / "resultados.json"
    salida = tmp_path / "revision.json"
    entrada.write_text(json.dumps(_resultados(2)), encoding="utf-8")
    script = ROOT_DIR / "src" / "GATE_1" / "revisar_cualitativamente.py"

    resultado = subprocess.run(
        [
            sys.executable,
            str(script),
            "--entrada",
            str(entrada),
            "--salida",
            str(salida),
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr
    revision = json.loads(salida.read_text(encoding="utf-8"))
    assert len(revision) == 2
    assert all(caso["contradiccion"] == "" for caso in revision)


def test_main_no_sobrescribe_el_archivo_de_entrada(tmp_path: Path) -> None:
    entrada = tmp_path / "resultados.json"
    contenido = json.dumps(_resultados(1))
    entrada.write_text(contenido, encoding="utf-8")
    script = ROOT_DIR / "src" / "GATE_1" / "revisar_cualitativamente.py"

    resultado = subprocess.run(
        [
            sys.executable,
            str(script),
            "--entrada",
            str(entrada),
            "--salida",
            str(entrada),
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )

    assert resultado.returncode != 0
    assert "deben ser archivos distintos" in resultado.stderr
    assert entrada.read_text(encoding="utf-8") == contenido
