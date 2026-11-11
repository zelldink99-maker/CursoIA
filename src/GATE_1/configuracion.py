"""Configuración compartida del modelo generativo Gemini."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELO_IA_POR_DEFECTO = "gemini-3.8-flash"
MODELOS_IA_PERMITIDOS = ("gemini-3.5-flash", "gemini-3.8-flash")


def cargar_modelo_ia() -> str:
    """Lee y valida el modelo seleccionado en la variable `modeloIA`."""
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
    modelo = os.getenv("modeloIA", MODELO_IA_POR_DEFECTO).strip()
    if modelo not in MODELOS_IA_PERMITIDOS:
        opciones = ", ".join(MODELOS_IA_PERMITIDOS)
        raise ValueError(f"modeloIA debe ser uno de estos valores: {opciones}.")
    return modelo


modeloIA = cargar_modelo_ia()


def crear_chat_modelo() -> BaseChatModel:
    """Crea un chat Gemini con el modelo centralizado en `modeloIA`."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=modeloIA)
