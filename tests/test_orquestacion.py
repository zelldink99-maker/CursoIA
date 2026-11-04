"""Pruebas del enrutamiento de soporte sin llamadas al proveedor."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_1.enrutamiento import (  # noqa: E402
    construir_cadena,
    construir_cadena_con_enrutamiento,
    construir_cadena_queja_segura,
    construir_paso_clasificacion,
    procesar_mensaje_seguro,
)


@pytest.mark.parametrize(
    ("categoria", "nombre_ruta"),
    [
        ("queja", "queja"),
        ("sugerencia", "sugerencia"),
        ("pregunta", "pregunta"),
        ("categoria_inventada", "pregunta"),
    ],
)
def test_enrutamiento_elige_la_ruta_correcta(
    categoria: str, nombre_ruta: str
) -> None:
    clasificacion_falsa = MagicMock(return_value=categoria)
    rutas = {
        nombre: MagicMock(return_value=f"respuesta de {nombre}")
        for nombre in ("queja", "sugerencia", "pregunta")
    }
    rutas_runnable = {
        nombre: RunnableLambda(ruta)
        for nombre, ruta in rutas.items()
    }
    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=clasificacion_falsa,
        cadena_queja=rutas_runnable["queja"],
        cadena_sugerencia=rutas_runnable["sugerencia"],
        cadena_pregunta=rutas_runnable["pregunta"],
    )

    resultado = cadena.invoke({"mensaje": "mensaje de prueba"})

    assert resultado == f"respuesta de {nombre_ruta}"
    rutas[nombre_ruta].assert_called_once()
    entrada_ruta = rutas[nombre_ruta].call_args.args[0]
    assert entrada_ruta == {
        "mensaje": "mensaje de prueba",
        "categoria": categoria,
    }
    for nombre, ruta in rutas.items():
        if nombre != nombre_ruta:
            ruta.assert_not_called()


def test_paso_clasificacion_normaliza_el_resultado() -> None:
    modelo_falso = MagicMock(return_value=AIMessage(content=" Queja \n"))

    resultado = construir_paso_clasificacion(modelo_falso).invoke(
        {"mensaje": "algo salió mal"}
    )

    assert resultado == "queja"
    modelo_falso.assert_called_once()


def test_cadena_completa_clasifica_y_responde_por_la_ruta_correcta() -> None:
    modelo_falso = MagicMock(
        side_effect=[
            AIMessage(content=" Queja \n"),
            AIMessage(content="respuesta empática"),
        ]
    )

    resultado = construir_cadena(modelo_falso).invoke(
        {"mensaje": "La app se cierra al subir una foto."}
    )

    assert resultado == "respuesta empática"
    assert modelo_falso.call_count == 2
    assert "La app se cierra al subir una foto." in (
        modelo_falso.call_args_list[0].args[0].to_string()
    )
    prompt_respuesta = modelo_falso.call_args_list[1].args[0].to_string()
    assert "empatía" in prompt_respuesta
    assert "La app se cierra al subir una foto." in prompt_respuesta


def test_cadena_queja_usa_fallback_ante_fallo_de_la_ruta() -> None:
    def fallar_a_proposito(_: object) -> None:
        raise ConnectionError("Error de red simulado")

    cadena_rota = RunnableLambda(fallar_a_proposito)
    cadena_segura = construir_cadena_queja_segura(cadena_rota)

    resultado = cadena_segura.invoke({"mensaje": "esto no funciona"})

    assert "equipo" in resultado.lower()


@pytest.mark.parametrize("categoria", ["queja", "sugerencia", "pregunta"])
def test_cada_ruta_usa_fallback_ante_una_excepcion(categoria: str) -> None:
    def fallar_a_proposito(_: object) -> None:
        raise ConnectionError("Error de red simulado")

    ruta_rota = RunnableLambda(fallar_a_proposito)
    rutas = {
        nombre: MagicMock(return_value=f"respuesta de {nombre}")
        for nombre in ("queja", "sugerencia", "pregunta")
    }
    rutas[categoria] = ruta_rota
    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=MagicMock(return_value=categoria),
        cadena_queja=rutas["queja"],
        cadena_sugerencia=rutas["sugerencia"],
        cadena_pregunta=rutas["pregunta"],
    )

    resultado = cadena.invoke({"mensaje": "mensaje de prueba"})

    assert "equipo" in resultado.lower()


def test_procesar_mensaje_seguro_registra_y_no_propaga_fallo_de_clasificacion(
    caplog: pytest.LogCaptureFixture,
) -> None:
    clasificacion_falsa = MagicMock(
        side_effect=ConnectionError("Error de red simulado")
    )
    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=clasificacion_falsa,
    )

    with caplog.at_level("ERROR"):
        resultado = procesar_mensaje_seguro(cadena, "mensaje de prueba")

    assert "no pudimos procesar" in resultado.lower()
    assert "Error procesando mensaje" in caplog.text
    assert "Error de red simulado" in caplog.text
