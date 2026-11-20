"""Pruebas de métricas de recuperación sin llamadas a Gemini."""

import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest
from langchain_core.documents import Document

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_2 import evaluar_recuperacion
from src.GATE_2.indexar_corpus import dividir_corpus


def test_evaluador_se_ejecuta_como_script_fuera_de_la_raiz(
    tmp_path: Path,
) -> None:
    script = ROOT_DIR / "src" / "GATE_2" / "evaluar_recuperacion.py"
    resultado = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert "--k K" in resultado.stdout


def test_metricas_precision_recall_y_f1_para_un_top_k() -> None:
    recuperados = ["doc2", "doc0", "doc4"]
    relevantes = {"doc0"}

    precision = evaluar_recuperacion.precision_at_k(recuperados, relevantes)
    recall = evaluar_recuperacion.recall_at_k(recuperados, relevantes)

    assert precision == pytest.approx(1 / 3)
    assert recall == 1.0
    assert evaluar_recuperacion.f1(precision, recall) == pytest.approx(0.5)


def test_metricas_manejan_listas_vacias_y_casos_sin_relevantes() -> None:
    assert evaluar_recuperacion.precision_at_k([], {"doc0"}) == 0.0
    assert evaluar_recuperacion.recall_at_k(["doc0"], set()) is None
    assert evaluar_recuperacion.f1(0.0, None) is None
    assert evaluar_recuperacion.promediar([0.0, None, 1.0]) == 0.5
    assert evaluar_recuperacion.promediar([None]) == 0.0


def test_tradeoff_de_k_coincide_con_el_ranking_de_ejemplo() -> None:
    ranked = ["doc2", "doc4", "doc0", "doc1", "doc3"]
    relevantes = {"doc0"}
    esperados = [
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (1 / 3, 1.0, 0.5),
        (0.25, 1.0, 0.4),
        (0.2, 1.0, 1 / 3),
    ]

    for k, (precision_esperada, recall_esperado, f1_esperado) in enumerate(
        esperados,
        start=1,
    ):
        top_k = ranked[:k]
        precision = evaluar_recuperacion.precision_at_k(top_k, relevantes)
        recall = evaluar_recuperacion.recall_at_k(top_k, relevantes)

        assert precision == pytest.approx(precision_esperada)
        assert recall == pytest.approx(recall_esperado)
        assert evaluar_recuperacion.f1(precision, recall) == pytest.approx(
            f1_esperado
        )


def test_etiquetas_de_evaluacion_corresponden_a_ids_del_corpus() -> None:
    ids_corpus = {
        f"{chunk.metadata['source']}::chunk-{chunk.metadata['chunk_index']}"
        for chunk in dividir_corpus()
    }

    assert len(evaluar_recuperacion.CASOS_EVALUACION) == 10
    assert all(
        caso["ids_relevantes"] <= ids_corpus
        for caso in evaluar_recuperacion.CASOS_EVALUACION
    )


def test_evaluar_recuperacion_limita_k_y_ignora_recall_no_definido() -> None:
    retriever = Mock(
        invoke=Mock(
            return_value=[
                Document(page_content="A", id="doc0"),
                Document(page_content="B", id="doc1"),
            ]
        )
    )
    casos = [
        {"pregunta": "respondible", "ids_relevantes": {"doc0"}},
        {"pregunta": "sin respuesta", "ids_relevantes": set()},
    ]

    resultados, precision_promedio, recall_promedio, f1_promedio = (
        evaluar_recuperacion.evaluar_recuperacion(retriever, casos, k=1)
    )

    assert resultados[0]["precision"] == 1.0
    assert resultados[0]["recall"] == 1.0
    assert resultados[0]["f1"] == 1.0
    assert resultados[1]["recall"] is None
    assert resultados[1]["f1"] is None
    assert precision_promedio == 0.5
    assert recall_promedio == 1.0
    assert f1_promedio == 1.0
    assert retriever.invoke.call_count == 2


def test_evaluar_recuperacion_rechaza_documentos_sin_id_explicito() -> None:
    retriever = Mock(
        invoke=Mock(return_value=[Document(page_content="Sin ID")])
    )

    with pytest.raises(ValueError, match="ID explícito"):
        evaluar_recuperacion.evaluar_recuperacion(
            retriever,
            [{"pregunta": "consulta", "ids_relevantes": {"doc0"}}],
        )


@pytest.mark.parametrize("k", [0, -1, True])
def test_evaluar_recuperacion_rechaza_k_invalido(k: int) -> None:
    with pytest.raises(ValueError, match="entero positivo"):
        evaluar_recuperacion.evaluar_recuperacion(Mock(), [], k=k)


def test_guardar_resultado_agrega_jsonl_sin_reemplazar_corridas(
    tmp_path: Path,
) -> None:
    archivo = tmp_path / "evaluacion.jsonl"
    resultados = [
        {"pregunta": "consulta", "precision": 0.5, "recall": 1.0, "f1": 0.67}
    ]

    for _ in range(2):
        evaluar_recuperacion.guardar_resultado(
            resultados,
            0.5,
            1.0,
            3,
            archivo,
        )

    registros = [
        json.loads(linea)
        for linea in archivo.read_text(encoding="utf-8").splitlines()
    ]
    assert len(registros) == 2
    assert registros[0]["k"] == 3
    assert registros[0]["resultados"] == resultados
    assert registros[0]["f1_promedio"] == pytest.approx(0.67)
