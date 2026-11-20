"""Comprueba la redacción de datos de contacto en trazas persistidas."""

import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_2.trazas_agente import registrar_traza


def test_registrar_traza_redacta_email_y_telefono_en_campos_anidados(
    tmp_path: Path,
) -> None:
    archivo = tmp_path / "trazas.jsonl"
    accion = SimpleNamespace(
        tool="buscar",
        tool_input={"contacto": "ana@example.com", "nota": "llamar al +54 11 1234-5678"},
    )
    registrar_traza(
        "sesion",
        "Escribe a ana@example.com o llama al +54 11 1234-5678",
        {
            "output": "Contacto: ana@example.com",
            "intermediate_steps": [(accion, "Teléfono +54 11 1234-5678")],
        },
        archivo,
    )

    guardado = archivo.read_text(encoding="utf-8")
    registro = json.loads(guardado)

    assert "ana@example.com" not in guardado
    assert "+54 11 1234-5678" not in guardado
    assert registro["entrada"].count("[EMAIL]") == 1
    assert "[TELEFONO]" in registro["entrada"]
    assert registro["acciones"][0]["argumentos"]["contacto"] == "[EMAIL]"
    assert registro["acciones"][0]["observacion"] == "Teléfono [TELEFONO]"
    assert registro["respuesta_final"] == "Contacto: [EMAIL]"
