"""Verifica la correlación de callbacks del retriever y el modelo."""

from pathlib import Path
import sys
from unittest.mock import Mock

from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.retrievers import BaseRetriever
from pydantic import Field

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_2.recuperacion_citas import responder_con_citas
from src.GATE_2.trazas_callbacks import TrazaCallbacks


class RetrieverFalso(BaseRetriever):
    documentos: list[Document] = Field(default_factory=list)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        del query, run_manager
        return self.documentos


def test_callbacks_correlacionan_retriever_y_modelo_sin_guardar_contenido() -> None:
    vectorstore = Mock()
    vectorstore.as_retriever.return_value = RetrieverFalso(
        documentos=[
            Document(
                page_content="Dato de prueba.",
                metadata={"source": "prueba.txt"},
            )
        ]
    )
    callbacks = TrazaCallbacks(trace_id="trace-prueba")
    modelo = FakeListChatModel(responses=["Dato de prueba [1]."])

    respuesta, fuentes = responder_con_citas(
        "consulta privada",
        vectorstore,
        modelo,
        callbacks=[callbacks],
    )

    assert respuesta == "Dato de prueba [1]."
    assert fuentes == {1: "prueba.txt"}
    assert [evento["evento"] for evento in callbacks.eventos] == [
        "retriever_start",
        "retriever_end",
        "llm_start",
        "llm_end",
    ]
    padres = {evento["parent_run_id"] for evento in callbacks.eventos}
    assert len(padres) == 1
    assert None not in padres
    contenido_registrado = str(callbacks.eventos)
    assert "consulta privada" not in contenido_registrado
    assert "Dato de prueba [1]." not in contenido_registrado

