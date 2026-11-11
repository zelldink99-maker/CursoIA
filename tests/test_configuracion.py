"""Pruebas de carga y uso del modelo Gemini configurado en `.env`."""

from unittest.mock import patch

import pytest

from src.GATE_1 import configuracion


@pytest.mark.parametrize(
    "modelo",
    configuracion.MODELOS_IA_PERMITIDOS,
)
def test_cargar_modelo_ia_lee_el_valor_configurado(
    monkeypatch: pytest.MonkeyPatch,
    modelo: str,
) -> None:
    monkeypatch.setenv("modeloIA", modelo)

    assert configuracion.cargar_modelo_ia() == modelo


def test_cargar_modelo_ia_rechaza_un_modelo_no_admitido(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("modeloIA", "modelo-invalido")

    with pytest.raises(ValueError, match="modeloIA debe ser uno"):
        configuracion.cargar_modelo_ia()


def test_factory_usa_el_modelo_centralizado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    modelo_configurado = configuracion.MODELOS_IA_PERMITIDOS[0]
    monkeypatch.setattr(configuracion, "modeloIA", modelo_configurado)

    with patch(
        "langchain_google_genai.ChatGoogleGenerativeAI"
    ) as modelo_chat:
        resultado = configuracion.crear_chat_modelo()

    assert resultado is modelo_chat.return_value
    modelo_chat.assert_called_once_with(model=modelo_configurado)
