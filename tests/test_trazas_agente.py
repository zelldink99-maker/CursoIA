"""Pruebas del registro y la revisión de trazas sin llamadas de red."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_1.trazas_agente import (
    marcar_repeticiones_sospechosas,
    registrar_traza,
)


def test_registrar_traza_persiste_jsonl_y_acepta_resultado_sin_pasos(
    tmp_path: Path,
) -> None:
    archivo = tmp_path / "trazas.jsonl"

    registrar_traza(
        "cliente-123",
        "¿Qué es LangChain?",
        {"output": "Una biblioteca.", "intermediate_steps": []},
        archivo,
    )
    registrar_traza(
        "cliente-456",
        "¿Qué hay de nuevo?",
        {"output": "Respuesta sin herramientas."},
        archivo,
    )

    lineas = archivo.read_text(encoding="utf-8").splitlines()
    primero, segundo = (json.loads(linea) for linea in lineas)
    assert len(lineas) == 2
    assert primero["session_id"] == "cliente-123"
    assert primero["entrada"] == "¿Qué es LangChain?"
    assert primero["acciones"] == []
    assert primero["respuesta_final"] == "Una biblioteca."
    assert primero["timestamp"].endswith("+00:00")
    assert segundo["acciones"] == []


def test_registrar_traza_incluye_herramienta_argumentos_y_observacion(
    tmp_path: Path,
) -> None:
    archivo = tmp_path / "trazas.jsonl"
    accion = SimpleNamespace(
        tool="buscar_en_documentacion",
        tool_input={"consulta": "costos"},
    )

    registrar_traza(
        "cliente-123",
        "Busca costos.",
        {
            "output": "Tarifas configuradas.",
            "intermediate_steps": [(accion, "Información de costos.")],
        },
        archivo,
    )

    registro = json.loads(archivo.read_text(encoding="utf-8"))
    assert registro["acciones"] == [
        {
            "herramienta": "buscar_en_documentacion",
            "argumentos": {"consulta": "costos"},
            "observacion": "Información de costos.",
        }
    ]


def test_marcar_repeticiones_solo_detecta_llamadas_consecutivas(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    archivo = tmp_path / "trazas.jsonl"
    registros = [
        {
            "session_id": "cliente-123",
            "acciones": [
                {"herramienta": "calcular"},
                {"herramienta": "buscar"},
                {"herramienta": "calcular"},
            ],
        },
        {
            "session_id": "cliente-456",
            "acciones": [
                {"herramienta": "buscar"},
                {"herramienta": "buscar"},
            ],
        },
    ]
    archivo.write_text(
        "".join(json.dumps(registro) + "\n" for registro in registros),
        encoding="utf-8",
    )

    mensajes = marcar_repeticiones_sospechosas(archivo)

    assert mensajes == [
        "Revisar: cliente-456 usó 'buscar' dos veces seguidas"
    ]
    assert capsys.readouterr().out.strip() == mensajes[0]


def test_marcar_repeticiones_informa_si_no_existe_el_archivo(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    archivo = tmp_path / "inexistente.jsonl"

    assert marcar_repeticiones_sospechosas(archivo) == []
    assert "No se encontró" in capsys.readouterr().out


def test_marcar_repeticiones_no_oculta_json_corrupto(tmp_path: Path) -> None:
    archivo = tmp_path / "trazas.jsonl"
    archivo.write_text("{registro inválido}\n", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        marcar_repeticiones_sospechosas(archivo)
