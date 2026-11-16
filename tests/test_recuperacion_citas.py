"""Pruebas del flujo RAG con citas sin red ni credenciales de Gemini."""

from pathlib import Path
import runpy
import sys
from typing import Any
from unittest.mock import Mock

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_1 import recuperacion_citas


def test_archivo_se_puede_importar_como_script_sin_paquete() -> None:
    ruta = ROOT_DIR / "src" / "GATE_1" / "recuperacion_citas.py"

    modulo = runpy.run_path(
        str(ruta),
        run_name="recuperacion_citas_import_check",
    )

    assert callable(modulo["main"])
    assert callable(modulo["construir_prompt"])


class ModeloFalso(BaseChatModel):
    """Modelo determinista que conserva el prompt para inspeccionar la entrada."""

    respuesta: str = "El cliente reintenta hasta tres veces [1]."
    prompts: list[str] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "modelo-falso"

    def _generate(
        self,
        messages: list[Any],
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        del stop, kwargs
        self.prompts.append(str(messages[-1].content))
        return ChatResult(
            generations=[
                ChatGeneration(message=AIMessage(content=self.respuesta))
            ]
        )


def test_formatear_contexto_numera_documentos_y_conserva_fuentes() -> None:
    documentos = [
        Document(
            page_content="El cliente reintenta tres veces.",
            metadata={"source": "src/GATE_1/cliente.py", "chunk_index": 0},
        ),
        Document(
            page_content="El agente registra las herramientas.",
            metadata={"source": "src/GATE_1/trazas_agente.py", "chunk_index": 0},
        ),
    ]

    contexto, fuentes = recuperacion_citas.formatear_contexto(documentos)

    assert "[1] Fuente: src/GATE_1/cliente.py" in contexto
    assert "[2] Fuente: src/GATE_1/trazas_agente.py" in contexto
    assert fuentes == {
        1: "src/GATE_1/cliente.py",
        2: "src/GATE_1/trazas_agente.py",
    }


@pytest.mark.parametrize(
    "documento",
    [
        Document(page_content="Sin fuente.", metadata={}),
        Document(page_content="   ", metadata={"source": "doc.md"}),
    ],
)
def test_formatear_contexto_rechaza_fuentes_o_contenidos_invalidos(
    documento: Document,
) -> None:
    with pytest.raises(ValueError):
        recuperacion_citas.formatear_contexto([documento])


def test_construir_prompt_exige_responder_solo_con_contexto_y_citar() -> None:
    prompt = recuperacion_citas.construir_prompt(
        "¿Qué reintenta el cliente?",
        "[1] Fuente: cliente.py\nEl cliente reintenta errores transitorios.",
    )

    assert "usando SOLO el contexto" in prompt
    assert "Cita cada afirmación factual" in prompt
    assert "[1] Fuente: cliente.py" in prompt
    assert "¿Qué reintenta el cliente?" in prompt
    assert "dilo explícitamente en vez de inventar" in prompt


def test_prompt_rechaza_pregunta_vacia() -> None:
    with pytest.raises(ValueError, match="pregunta"):
        recuperacion_citas.construir_prompt(" ", "contexto")


def test_validar_citas_rechaza_numeros_que_no_aparecen_en_el_contexto() -> None:
    with pytest.raises(ValueError, match="no recuperados"):
        recuperacion_citas.validar_citas(
            "Respuesta con referencia inventada [2].",
            {1: "cliente.py"},
        )


def test_validar_citas_exige_referencias_si_hay_contexto() -> None:
    with pytest.raises(ValueError, match="no incluye citas"):
        recuperacion_citas.validar_citas(
            "El cliente reintenta tres veces.",
            {1: "cliente.py"},
        )


def test_validar_citas_permite_abstencion_sin_referencias() -> None:
    recuperacion_citas.validar_citas(
        "No hay información suficiente para responder.",
        {1: "cliente.py"},
    )


def test_responder_busca_contexto_invoca_modelo_y_devuelve_citas() -> None:
    documento = Document(
        page_content="El cliente reintenta tres veces.",
        metadata={"source": "src/GATE_1/cliente.py"},
    )
    vectorstore = Mock()
    vectorstore.similarity_search.return_value = [documento]
    modelo = ModeloFalso()

    respuesta, fuentes = recuperacion_citas.responder_con_citas(
        "¿Cuántas veces reintenta?",
        vectorstore,
        modelo,
    )

    assert respuesta == "El cliente reintenta hasta tres veces [1]."
    assert fuentes == {1: "src/GATE_1/cliente.py"}
    vectorstore.similarity_search.assert_called_once_with(
        "¿Cuántas veces reintenta?",
        k=3,
    )
    assert "[1] Fuente: src/GATE_1/cliente.py" in modelo.prompts[0]


def test_responder_puede_indicar_que_no_hay_contexto() -> None:
    vectorstore = Mock()
    vectorstore.similarity_search.return_value = []
    modelo = ModeloFalso(respuesta="No hay contexto pertinente.")

    respuesta, fuentes = recuperacion_citas.responder_con_citas(
        "Pregunta sin resultados",
        vectorstore,
        modelo,
    )

    assert respuesta == "No hay contexto pertinente."
    assert fuentes == {}
    assert "No se recuperó contexto pertinente." in modelo.prompts[0]


def test_main_reindexa_y_ejecuta_las_dos_preguntas(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    vectorstore = Mock()
    vectorstore.get.return_value = {"ids": ["1", "2", "3", "4", "5"]}
    vectorstore.similarity_search.return_value = [
        Document(
            page_content="Dato respaldado.",
            metadata={"source": "doc.md"},
        )
    ]
    embeddings = Mock()
    modelo = ModeloFalso(respuesta="Respuesta de prueba [1].")
    reindexar = Mock(return_value=vectorstore)
    monkeypatch.setattr(recuperacion_citas, "indexar_corpus", reindexar)

    assert recuperacion_citas.main(embeddings, modelo, tmp_path) == 0

    reindexar.assert_called_once_with(
        embeddings,
        persist_directory=tmp_path,
    )
    assert vectorstore.similarity_search.call_count == 2
    salida = capsys.readouterr().out
    assert "Reindexados 5 chunks" in salida
    assert "PASO 3" in salida
    assert salida.count("citas: {1: 'doc.md'}") == 2


def test_main_no_consulta_el_modelo_si_el_indice_quedo_incompleto(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    vectorstore = Mock()
    vectorstore.get.return_value = {"ids": ["1"]}
    modelo = Mock()
    monkeypatch.setattr(
        recuperacion_citas,
        "indexar_corpus",
        Mock(return_value=vectorstore),
    )

    assert recuperacion_citas.main(Mock(), modelo, tmp_path) == 1

    modelo.invoke.assert_not_called()
    vectorstore.similarity_search.assert_not_called()
    assert "Se esperaban al menos" in capsys.readouterr().err


def test_main_no_oculta_errores_inesperados_del_vectorstore(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        recuperacion_citas,
        "indexar_corpus",
        Mock(side_effect=RuntimeError("fallo inesperado")),
    )

    with pytest.raises(RuntimeError, match="fallo inesperado"):
        recuperacion_citas.main(Mock(), Mock(), tmp_path)
