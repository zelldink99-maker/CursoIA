"""Pruebas del preflight local del índice RAG, sin llamadas a API."""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_1 import preflight_rag


def test_preflight_confirma_indice_y_gitignore(tmp_path: Path) -> None:
    vectorstore = tmp_path / "vectorstore"
    vectorstore.mkdir()
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("vectorstore/\n", encoding="utf-8")

    assert preflight_rag.preflight_check(vectorstore, gitignore) == []


def test_preflight_informa_indice_y_gitignore_ausentes(
    tmp_path: Path,
) -> None:
    problemas = preflight_rag.preflight_check(
        tmp_path / "vectorstore",
        tmp_path / ".gitignore",
    )

    assert problemas == [
        "vectorstore/ no existe: corriste la indexación?",
        "no existe .gitignore en este proyecto",
    ]


def test_preflight_detecta_indice_no_ignorado(tmp_path: Path) -> None:
    vectorstore = tmp_path / "vectorstore"
    vectorstore.mkdir()
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(".env\n", encoding="utf-8")

    assert preflight_rag.preflight_check(vectorstore, gitignore) == [
        "vectorstore/ no está en .gitignore"
    ]


def test_main_imprime_estado_real_del_proyecto(capsys) -> None:
    assert preflight_rag.main() == 0
    assert "Preflight OK" in capsys.readouterr().out
