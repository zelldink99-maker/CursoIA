"""Pruebas unitarias del cliente modular, sin llamadas a Gemini."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

# Hace importable el paquete src tanto con pytest como al ejecutar este archivo.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_1 import cliente, cliente_reintento, monolitico
from src.GATE_1.costo import (
    PRECIO_ENTRADA_POR_TOKEN,
    PRECIO_SALIDA_POR_TOKEN,
)


@pytest.fixture(autouse=True)
def reiniciar_costos() -> None:
    """Aísla el estado global de costos entre pruebas."""
    cliente.costo_total_sesion = 0.0
    cliente.costo_ultima_operacion = 0.0
    cliente.tokens_ultima_operacion = 0


def crear_respuesta_http(status_code: int, datos: dict[str, object]) -> Mock:
    """Prepara una respuesta HTTP simulada con el comportamiento de requests."""
    respuesta = Mock()
    respuesta.status_code = status_code
    respuesta.json.return_value = datos
    if status_code >= 400:
        respuesta.raise_for_status.side_effect = requests.HTTPError(
            f"HTTP {status_code}"
        )
    return respuesta


@pytest.mark.parametrize("status_code", [401, 403])
def test_cliente_clasifica_errores_de_autenticacion_sin_reintentar(
    status_code: int,
) -> None:
    """Los errores de credenciales deben propagarse como ValueError."""
    error_http = monolitico.GeminiHTTPError(status_code, "credencial inválida")

    with patch.object(monolitico, "enviar_peticion", side_effect=error_http) as enviar:
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            cliente._enviar_peticion_reintentable("https://example.invalid", {})

    enviar.assert_called_once()


@pytest.mark.parametrize("status_code", [429, 500, 503])
def test_cliente_clasifica_errores_transitorios_para_reintento(
    status_code: int,
) -> None:
    """Rate limit y errores 5xx deben convertirse en TimeoutError."""
    error_http = monolitico.GeminiHTTPError(status_code, "fallo transitorio")

    with patch.object(monolitico, "enviar_peticion", side_effect=error_http):
        with pytest.raises(TimeoutError, match="reintentar"):
            cliente._enviar_peticion_reintentable("https://example.invalid", {})


def test_enviar_peticion_devuelve_json_y_autentica_en_header() -> None:
    """El envío acepta JSON válido, mantiene la clave fuera de la URL."""
    datos = {"respuesta": "simulada"}
    respuesta = crear_respuesta_http(200, datos)
    with patch.dict("os.environ", {"GEMINI_API_KEY": "clave-de-prueba"}):
        with patch.object(monolitico.requests, "post", return_value=respuesta) as post:
            resultado = monolitico.enviar_peticion(
                "https://example.invalid/generateContent",
                {"contents": []},
            )

    assert resultado == datos
    assert "clave-de-prueba" not in post.call_args.args[0]
    assert post.call_args.kwargs["headers"]["x-goog-api-key"] == "clave-de-prueba"
    assert post.call_args.kwargs["timeout"] > 0


@pytest.mark.parametrize("status_code", [401, 403, 429, 500])
def test_enviar_peticion_conserva_codigo_http_en_error(status_code: int) -> None:
    """El transporte informa estados HTTP como GeminiHTTPError con su status."""
    respuesta = crear_respuesta_http(
        status_code,
        {"error": {"message": "error simulado"}},
    )
    with patch.dict("os.environ", {"GEMINI_API_KEY": "clave-de-prueba"}):
        with patch.object(monolitico.requests, "post", return_value=respuesta):
            with pytest.raises(monolitico.GeminiHTTPError) as error:
                monolitico.enviar_peticion(
                    "https://example.invalid/generateContent",
                    {"contents": []},
                )

    assert error.value.status_code == status_code


def test_con_reintento_reintenta_timeout_y_espera_una_vez() -> None:
    """Una falla transitoria se vuelve a intentar y no duerme realmente."""
    operacion = Mock(side_effect=[TimeoutError("simulado"), "ok"])

    with patch.object(cliente_reintento.time, "sleep") as dormir:
        with patch.object(cliente_reintento.random, "uniform", return_value=0.0):
            resultado = cliente_reintento.con_reintento(operacion)

    assert resultado == "ok"
    assert operacion.call_count == 2
    dormir.assert_called_once()


def test_con_reintento_no_reintenta_otras_excepciones() -> None:
    """Una excepción distinta a TimeoutError se propaga en el primer intento."""
    operacion = Mock(side_effect=ValueError("entrada inválida"))

    with patch.object(cliente_reintento.time, "sleep") as dormir:
        with pytest.raises(ValueError, match="entrada inválida"):
            cliente_reintento.con_reintento(operacion)

    operacion.assert_called_once()
    dormir.assert_not_called()


def test_con_reintento_agota_intentos_y_propaga_el_error_original() -> None:
    """Al alcanzar el máximo, con_reintento no oculta el TimeoutError."""
    error = TimeoutError("servicio no disponible")
    operacion = Mock(side_effect=error)

    with patch.object(cliente_reintento.time, "sleep"):
        with patch.object(cliente_reintento.random, "uniform", return_value=0.0):
            with pytest.raises(TimeoutError, match="servicio no disponible") as actual:
                cliente_reintento.con_reintento(operacion, intentos=3)

    assert actual.value is error
    assert operacion.call_count == 3


def test_registrar_costo_calcula_uso_y_acumula() -> None:
    """El costo por operación usa tokens reales y actualiza el acumulado."""
    respuesta = {
        "usageMetadata": {
            "promptTokenCount": 1000,
            "candidatesTokenCount": 100,
            "thoughtsTokenCount": 10,
            "totalTokenCount": 1110,
        }
    }

    costo = cliente.registrar_costo(respuesta)

    assert costo == pytest.approx(
        1000 * PRECIO_ENTRADA_POR_TOKEN + 110 * PRECIO_SALIDA_POR_TOKEN
    )
    assert cliente.costo_total_sesion == pytest.approx(costo)
    assert cliente.costo_ultima_operacion == pytest.approx(costo)
    assert cliente.tokens_ultima_operacion == 1110


def test_registrar_costo_rechaza_metadatos_ausentes_sin_acumular() -> None:
    """Una respuesta sin contadores válidos no puede generar costo ficticio."""
    with pytest.raises(monolitico.GeminiResponseError, match="metadatos de uso"):
        cliente.registrar_costo({})

    assert cliente.costo_total_sesion == 0.0


def test_consultar_modelo_convierte_timeout_y_no_cuenta_la_operacion() -> None:
    """El agotamiento de reintentos se expresa como ServicioNoDisponibleError."""
    with patch.object(cliente, "con_reintento", side_effect=TimeoutError("simulado")):
        with pytest.raises(cliente.ServicioNoDisponibleError, match="varios intentos"):
            cliente.consultar_modelo("pregunta de prueba")

    assert cliente.costo_total_sesion == 0.0


def test_consultar_modelo_no_convierte_value_error() -> None:
    """Errores permanentes de autenticación se propagan sin reintento."""
    with patch.object(cliente, "con_reintento", side_effect=ValueError("credencial")):
        with pytest.raises(ValueError, match="credencial"):
            cliente.consultar_modelo("pregunta de prueba")


def test_consultar_modelo_camino_feliz_devuelve_texto_y_registra_costo() -> None:
    """Una respuesta exitosa devuelve texto y suma su costo una sola vez."""
    datos = {
        "candidates": [
            {"content": {"parts": [{"text": "respuesta de prueba"}]}}
        ],
        "usageMetadata": {
            "promptTokenCount": 10,
            "candidatesTokenCount": 5,
            "totalTokenCount": 15,
        },
    }
    with patch.object(monolitico, "enviar_peticion", return_value=datos) as enviar:
        texto = cliente.consultar_modelo("pregunta de prueba")

    assert texto == "respuesta de prueba"
    enviar.assert_called_once()
    assert cliente.tokens_ultima_operacion == 15
    assert cliente.costo_total_sesion > 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
