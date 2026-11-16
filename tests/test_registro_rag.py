"""Pruebas del registro RAG sin red, credenciales ni costo de API."""

import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_1 import registro_rag


def test_registro_se_ejecuta_como_script_fuera_de_la_raiz(
    tmp_path: Path,
) -> None:
    script = ROOT_DIR / "src" / "GATE_1" / "registro_rag.py"
    resultado = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert "--pregunta PREGUNTA" in resultado.stdout


def test_registrar_consulta_mide_etapas_y_agrega_jsonl(
    tmp_path: Path,
) -> None:
    archivo = tmp_path / "registros.jsonl"
    embeddings = Mock()
    embeddings.embed_query.return_value = [0.1, 0.2]
    vectorstore = Mock()
    vectorstore.get.return_value = {"ids": ["src/GATE_1/cliente.py::chunk-0"]}
    retriever = Mock()
    retriever.invoke.return_value = [
        Document(
            page_content="El cliente reintenta tres veces.",
            id="src/GATE_1/cliente.py::chunk-0",
            metadata={"source": "src/GATE_1/cliente.py"},
        )
    ]
    vectorstore.as_retriever.return_value = retriever
    modelo = Mock()
    modelo.invoke.return_value = AIMessage(
        content="Reintenta tres veces [1].",
        usage_metadata={
            "input_tokens": 150,
            "output_tokens": 38,
            "total_tokens": 188,
        },
    )

    registro = registro_rag.registrar_consulta(
        "¿Cuántas veces reintenta?",
        tmp_path / "vectorstore",
        k=3,
        embeddings=embeddings,
        vectorstore=vectorstore,
        chat_model=modelo,
    )
    registro_rag.guardar_registro(registro, archivo)

    assert set(registro) == {
        "timestamp",
        "pregunta",
        "k",
        "tiempos_ms",
        "tiempo_total_ms",
        "tokens",
    }
    assert set(registro["tiempos_ms"]) == {"embed_y_busqueda", "generacion"}
    assert registro["tiempo_total_ms"] == pytest.approx(
        sum(registro["tiempos_ms"].values()),
        abs=0.02,
    )
    assert registro["tokens"]["input_tokens"] == 150
    guardado = json.loads(archivo.read_text(encoding="utf-8"))
    assert guardado == registro
    vectorstore.as_retriever.assert_called_once_with(search_kwargs={"k": 3})
    retriever.invoke.assert_called_once_with("¿Cuántas veces reintenta?")
    assert "[1] Fuente: src/GATE_1/cliente.py" in modelo.invoke.call_args.args[0]


def test_registrar_consulta_conserva_tokens_nulos_si_no_hay_uso() -> None:
    embeddings = Mock()
    embeddings.embed_query.return_value = [0.1]
    vectorstore = Mock()
    vectorstore.get.return_value = {"ids": ["doc"]}
    vectorstore.as_retriever.return_value.invoke.return_value = []
    modelo = Mock()
    modelo.invoke.return_value = AIMessage(content="No hay contexto suficiente.")

    registro = registro_rag.registrar_consulta(
        "Pregunta sin resultados",
        embeddings=embeddings,
        vectorstore=vectorstore,
        chat_model=modelo,
    )

    assert registro["tokens"] is None


def test_registrar_consulta_conserva_usage_metadata_de_langchain() -> None:
    embeddings = Mock()
    embeddings.embed_query.return_value = [0.1]
    vectorstore = Mock()
    vectorstore.get.return_value = {"ids": ["doc"]}
    vectorstore.as_retriever.return_value.invoke.return_value = []
    modelo = Mock()
    modelo.invoke.return_value = AIMessage(
        content="Sin contexto.",
        usage_metadata={
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
        },
    )

    registro = registro_rag.registrar_consulta(
        "Pregunta",
        embeddings=embeddings,
        vectorstore=vectorstore,
        chat_model=modelo,
    )

    assert registro["tokens"] == {
        "input_tokens": 10,
        "output_tokens": 5,
        "total_tokens": 15,
    }


def test_registrar_consulta_no_genera_respuesta_si_el_indice_esta_vacio() -> None:
    vectorstore = Mock()
    vectorstore.get.return_value = {"ids": []}
    modelo = Mock()

    with pytest.raises(ValueError, match="No hay chunks indexados"):
        registro_rag.registrar_consulta(
            "Pregunta",
            embeddings=Mock(),
            vectorstore=vectorstore,
            chat_model=modelo,
        )

    modelo.invoke.assert_not_called()


def test_actividad_core_imprime_pasos_compara_k_y_cuenta_jsonl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    archivo = tmp_path / "registros.jsonl"
    monkeypatch.setattr(registro_rag, "crear_embeddings", Mock(return_value=Mock()))
    monkeypatch.setattr(registro_rag, "abrir_vectorstore", Mock(return_value=Mock()))
    monkeypatch.setattr(registro_rag, "crear_chat_modelo", Mock(return_value=Mock()))

    def registrar(
        pregunta: str,
        *,
        k: int,
        **kwargs: object,
    ) -> dict[str, object]:
        del kwargs
        return {
            "pregunta": pregunta,
            "k": k,
            "tokens": {"input_tokens": 144 if k == 3 else 203},
        }

    monkeypatch.setattr(registro_rag, "registrar_consulta", registrar)

    registros = registro_rag.ejecutar_actividad_core(ruta_registro=archivo)

    salida = capsys.readouterr().out
    assert len(registros) == 5
    assert "PASO 1: registrando 3 consultas distintas" in salida
    assert "PASO 2: misma pregunta con k=3 y k=6" in salida
    assert "k=3 -> input_tokens: 144" in salida
    assert "k=6 -> input_tokens: 203" in salida
    assert "registros.jsonl tiene 5 líneas" in salida
    assert len(archivo.read_text(encoding="utf-8").splitlines()) == 5


@pytest.mark.parametrize("k", [0, -1, True])
def test_registrar_consulta_rechaza_k_invalido(k: int) -> None:
    with pytest.raises(ValueError, match="entero positivo"):
        registro_rag.registrar_consulta("Pregunta", k=k)


def test_registrar_consulta_rechaza_pregunta_vacia() -> None:
    with pytest.raises(ValueError, match="pregunta"):
        registro_rag.registrar_consulta(" ")
