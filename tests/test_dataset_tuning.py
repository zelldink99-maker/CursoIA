"""Pruebas locales del dataset de tuning, sin llamadas a la API."""

from pathlib import Path
import sys

from google.genai import types

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_2.dataset_tuning import (
    EJEMPLOS_RAW,
    chequear_balance,
    construir_ejemplos,
    validar_dataset,
)


def test_dataset_de_ejemplo_se_construye_valido_y_con_balance_conocido() -> None:
    examples = construir_ejemplos(EJEMPLOS_RAW)

    assert len(examples) == 12
    assert validar_dataset(examples) == []
    assert chequear_balance(EJEMPLOS_RAW) == {
        "devolucion": 3,
        "cobro": 3,
        "envio": 3,
        "promocion": 3,
    }


def test_validador_reporta_todos_los_problemas_del_dataset() -> None:
    base = construir_ejemplos(EJEMPLOS_RAW)
    examples = base + [
        types.TuningExample(text_input="", output='{"categoria": "red"}'),
        types.TuningExample(text_input=EJEMPLOS_RAW[0][0], output="no es json"),
    ]

    assert validar_dataset(examples) == [
        "ejemplo 12: text_input vacio",
        'ejemplo 12: output no tiene la clave "accion_sugerida"',
        "ejemplo 13: text_input duplicado",
        "ejemplo 13: output no es JSON valido",
    ]


def test_validador_detecta_salida_json_que_no_es_objeto() -> None:
    example = types.TuningExample(text_input="entrada", output="[]")

    assert validar_dataset([example]) == [
        "ejemplo 0: output no es un objeto JSON"
    ]


def test_main_imprime_los_tres_pasos_y_demuestra_el_error(capsys) -> None:
    from src.GATE_2.dataset_tuning import main

    assert main() == 0
    salida = capsys.readouterr().out
    assert "PASO 1: balance de MI dataset" in salida
    assert "devolucion: 3" in salida
    assert "cobro: 3" in salida
    assert "envio: 3" in salida
    assert "promocion: 3" in salida
    assert "PASO 2: validacion de MI dataset" in salida
    assert "12 ejemplos, 0 problemas encontrados" in salida
    assert "PASO 3: rompo un ejemplo a proposito" in salida
    assert "12 ejemplos, 1 problemas encontrados" in salida
    assert "ejemplo 3: output no es JSON valido" in salida
