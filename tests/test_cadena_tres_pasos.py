"""Pruebas de la chain LangChain sin llamadas al proveedor."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_1.cadena_tres_pasos import construir_cadena


def test_cadena_conecta_tres_pasos_y_devuelve_texto_plano() -> None:
    modelo_falso = MagicMock(
        side_effect=[
            AIMessage(content="idea uno\nidea dos\nidea tres"),
            AIMessage(content="explicación sencilla"),
            AIMessage(content="- viñeta uno\n- viñeta dos"),
        ]
    )
    cadena = construir_cadena(modelo_falso)

    resultado = cadena.invoke({"texto": "Texto técnico de prueba"})

    assert modelo_falso.call_count == 3
    assert resultado == "- viñeta uno\n- viñeta dos"
    assert isinstance(resultado, str)
    assert "Texto técnico de prueba" in modelo_falso.call_args_list[0].args[0].to_string()
    assert "idea uno" in modelo_falso.call_args_list[1].args[0].to_string()
    assert "explicación sencilla" in (
        modelo_falso.call_args_list[2].args[0].to_string()
    )


def test_cadena_falla_antes_de_invocar_modelo_si_falta_texto() -> None:
    modelo_falso = MagicMock()
    cadena = construir_cadena(modelo_falso)

    try:
        cadena.invoke({})
    except KeyError as error:
        assert "texto" in str(error)
    else:
        raise AssertionError("Se esperaba KeyError para la variable texto faltante")

    modelo_falso.assert_not_called()
