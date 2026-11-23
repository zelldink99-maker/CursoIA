"""Autochequeo integrado de los cuatro criterios no compensables del Gate 2."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.types import Command

from src.GATE_2 import indexar_corpus, registro_rag, unidad_completa_supervision
from src.GATE_2.recuperacion_citas import validar_citas


class EmbeddingsLocales(Embeddings):
    """Embeddings deterministas para probar Chroma sin red ni credenciales."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        vector = [0.0] * 8
        for position, character in enumerate(text.casefold()):
            vector[position % len(vector)] += ord(character) / 1000
        return vector


@pytest.fixture
def servicio_local(tmp_path: Path):
    embeddings = EmbeddingsLocales()
    vectorstore = indexar_corpus.indexar_corpus(
        embeddings,
        persist_directory=tmp_path / "vectorstore",
    )
    return embeddings, vectorstore


def ejecutar_servicio(
    pregunta: str,
    embeddings: Embeddings,
    vectorstore,
    *,
    registro_path: Path | None = None,
) -> tuple[str, dict[int, str], dict[str, object]]:
    modelo = FakeListChatModel(
        responses=["El cliente reintenta errores transitorios hasta tres veces [1]."]
    )
    respuesta, fuentes, registro = registro_rag.ejecutar_consulta(
        pregunta,
        embeddings=embeddings,
        vectorstore=vectorstore,
        chat_model=modelo,
    )
    if registro_path is not None:
        registro_rag.guardar_registro(registro, registro_path)
    return respuesta, fuentes, registro


def test_1_pipeline_indexa_recupera_y_responde_sin_excepciones(
    servicio_local,
) -> None:
    embeddings, vectorstore = servicio_local

    respuesta, fuentes, _ = ejecutar_servicio(
        "¿Cuántas veces reintenta el cliente?",
        embeddings,
        vectorstore,
    )

    assert respuesta.strip()
    assert fuentes


def test_2_respuesta_cita_una_fuente_recuperada(servicio_local) -> None:
    embeddings, vectorstore = servicio_local

    respuesta, fuentes, _ = ejecutar_servicio(
        "¿Qué errores reintenta el cliente?",
        embeddings,
        vectorstore,
    )

    assert fuentes
    validar_citas(respuesta, fuentes)
    assert any(f"[{numero}]" in respuesta for numero in fuentes)


def test_3_registro_no_persiste_consulta_ni_pii(
    servicio_local,
    tmp_path: Path,
) -> None:
    embeddings, vectorstore = servicio_local
    correo = "ana.perez@example.com"
    pregunta = f"¿Qué dice el proyecto? Mi correo es {correo}"
    archivo = tmp_path / "registros.jsonl"

    _, _, registro = ejecutar_servicio(
        pregunta,
        embeddings,
        vectorstore,
        registro_path=archivo,
    )

    texto_registrado = archivo.read_text(encoding="utf-8")
    assert registro["pregunta_len"] == len(pregunta)
    assert correo not in texto_registrado
    assert pregunta not in texto_registrado
    assert all(
        evento["trace_id"] == registro["trace_id"]
        for evento in registro["eventos"]
    )


def test_4_supervision_pausa_y_reanuda_con_decision_humana() -> None:
    config = {
        "configurable": {"thread_id": f"test-gate2-{uuid4().hex}"},
    }
    entrada = {
        "huella_nueva": "gate2-test-prompt",
        "aprobado": False,
    }

    pausado = unidad_completa_supervision.app_despliegue.invoke(
        entrada,
        config=config,
    )
    assert "__interrupt__" in pausado

    final = unidad_completa_supervision.app_despliegue.invoke(
        Command(resume=True),
        config=config,
    )
    assert "__interrupt__" not in final
    assert final["aprobado"] is True
