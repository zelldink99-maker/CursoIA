"""Pruebas locales de las herramientas del Bloque 30, sin llamadas a la API."""

from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_1.decision_personalizacion import (
    CLAVES_RESPUESTAS,
    estimar_costo_de_etiquetar,
    generar_esqueleto_decision,
    main,
    obtener_estadisticas_tuning,
    recomendar_estrategia,
)


def test_estimacion_de_etiquetado_y_revision() -> None:
    horas_base, costo_base = estimar_costo_de_etiquetar(500, 4, 20)
    horas_revision, costo_revision = estimar_costo_de_etiquetar(500 * 0.20, 2, 20)

    assert (round(horas_base, 2), round(costo_base, 2)) == (33.33, 666.67)
    assert (round(horas_revision, 2), round(costo_revision, 2)) == (3.33, 66.67)
    assert round(horas_base + horas_revision, 2) == 36.67
    assert round(costo_base + costo_revision, 2) == 733.33


@pytest.mark.parametrize("valor", [-1, float("inf"), float("nan")])
def test_estimacion_rechaza_valores_invalidos(valor: float) -> None:
    with pytest.raises(ValueError):
        estimar_costo_de_etiquetar(valor, 5, 25)


def test_recomendacion_conserva_empates_y_reconoce_ganador_claro() -> None:
    caso_empate = dict.fromkeys(CLAVES_RESPUESTAS, False)
    caso_empate["problema_de_formato_o_tono"] = True
    caso_empate["dataset_grande_y_de_calidad"] = True
    puntos_empate, ganadoras_empate = recomendar_estrategia(caso_empate)

    assert puntos_empate == {"RAG": 0, "Fine-tuning completo": 3, "PEFT": 3}
    assert ganadoras_empate == ["Fine-tuning completo", "PEFT"]

    caso_rag = dict.fromkeys(CLAVES_RESPUESTAS, False)
    caso_rag["informacion_cambia_seguido"] = True
    caso_rag["problema_de_formato_o_tono"] = True
    caso_rag["presupuesto_limitado_o_iterar_rapido"] = True
    assert recomendar_estrategia(caso_rag) == (
        {"RAG": 5, "Fine-tuning completo": 1, "PEFT": 3},
        ["RAG"],
    )


def test_recomendacion_exige_booleanos_reales_y_claves_completas() -> None:
    respuestas = dict.fromkeys(CLAVES_RESPUESTAS, False)
    respuestas["problema_de_formato_o_tono"] = "si"
    with pytest.raises(TypeError, match="True o False"):
        recomendar_estrategia(respuestas)

    with pytest.raises(ValueError, match="Faltan respuestas"):
        recomendar_estrategia({})


def test_esqueleto_muestra_empate_y_cuatro_secciones() -> None:
    documento = generar_esqueleto_decision(
        "El clasificador no siempre respeta el formato.",
        {"RAG": 0, "Fine-tuning completo": 3, "PEFT": 3},
        ["Fine-tuning completo", "PEFT"],
    )

    assert documento.count("## ") == 4
    assert "**Empate entre: Fine-tuning completo, PEFT**" in documento
    assert "## 4. Qué necesitarías para ejecutarla" in documento


def test_main_imprime_y_guarda_el_ejemplo_completo(tmp_path, capsys) -> None:
    destino = tmp_path / "decision_personalizacion.md"

    assert main(destino) == 0

    salida = capsys.readouterr().out
    documento = destino.read_text(encoding="utf-8")
    assert "PASO 1: el método corre sobre un caso de ejemplo" in salida
    assert "candidatas: ['Fine-tuning completo', 'PEFT']" in salida
    assert "PASO 2: " in salida
    assert "Elijo PEFT." in salida
    assert "[COMPLETAR:" not in documento
    assert salida.endswith(documento + "\n")


def test_main_no_sobrescribe_un_documento_existente(tmp_path, capsys) -> None:
    destino = tmp_path / "decision_personalizacion.md"
    destino.write_text("decisión propia", encoding="utf-8")

    assert main(destino) == 1
    assert capsys.readouterr().out == (
        f"Error: {destino} ya existe; no se sobrescribió.\n"
    )
    assert destino.read_text(encoding="utf-8") == "decisión propia"


def test_consulta_estadisticas_informa_datos_ausentes_sin_fallar_silenciosamente() -> (
    None
):
    client = Mock()
    client.tunings.get.return_value = SimpleNamespace(tuning_data_stats=None)

    with pytest.raises(RuntimeError, match="todavía no tiene estadísticas"):
        obtener_estadisticas_tuning(client, "jobs/ejemplo")
    client.tunings.get.assert_called_once_with(name="jobs/ejemplo")


def test_consulta_estadisticas_devuelve_las_estadisticas_supervisadas() -> None:
    stats = SimpleNamespace(tuning_dataset_example_count=7)
    client = Mock()
    client.tunings.get.return_value = SimpleNamespace(
        tuning_data_stats=SimpleNamespace(supervised_tuning_data_stats=stats)
    )

    assert obtener_estadisticas_tuning(client, "jobs/ejemplo") is stats


def test_consulta_estadisticas_conserva_la_causa_del_error_del_sdk() -> None:
    client = Mock()
    from google.genai.errors import APIError

    error_sdk = APIError(500, {"message": "sin conexión"})
    client.tunings.get.side_effect = error_sdk
    with pytest.raises(RuntimeError, match="No se pudo consultar") as error:
        obtener_estadisticas_tuning(client, "jobs/ejemplo")

    assert error.value.__cause__ is error_sdk
