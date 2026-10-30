"""Pruebas del evaluador por lotes sin llamadas de red."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_1 import evaluar_metricas


def test_evaluar_metricas_se_puede_importar_fuera_de_la_raiz(
    tmp_path: Path,
) -> None:
    script = ROOT_DIR / "src" / "GATE_1" / "evaluar_metricas.py"
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


def test_evaluar_casos_guarda_respuestas_y_metricas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archivo = tmp_path / "resultados.json"
    monkeypatch.setattr(
        evaluar_metricas,
        "consultar_modelo",
        Mock(return_value="Python es interpretado."),
    )

    resultados = evaluar_metricas.evaluar_casos(
        (("¿Qué es Python?", "Python es interpretado."),),
        archivo,
    )

    assert resultados[0]["respuesta"] == "Python es interpretado."
    assert resultados[0]["precision"] == 1.0
    assert resultados[0]["cobertura"] == 1.0
    assert resultados[0]["f1"] == 1.0
    assert json.loads(archivo.read_text(encoding="utf-8")) == resultados


def test_evaluar_casos_conserva_resultados_si_falla_una_consulta(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archivo = tmp_path / "resultados.json"

    def consultar(consulta: str) -> str:
        if consulta == "segunda":
            raise RuntimeError("fallo simulado")
        return "respuesta guardada"

    monkeypatch.setattr(evaluar_metricas, "consultar_modelo", consultar)

    with pytest.raises(RuntimeError, match="fallo simulado"):
        evaluar_metricas.evaluar_casos(
            (("primera", "referencia"), ("segunda", "referencia")),
            archivo,
        )

    contenido = json.loads(archivo.read_text(encoding="utf-8"))
    assert len(contenido) == 1
    assert contenido[0]["respuesta"] == "respuesta guardada"


def test_resumir_metricas_devuelve_ceros_si_no_hay_resultados() -> None:
    assert evaluar_metricas.resumir_metricas([]) == {
        "precision_promedio": 0.0,
        "cobertura_promedio": 0.0,
        "f1_promedio": 0.0,
    }
