"""Registro persistente y revisión básica de trazas del agente."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def registrar_traza(
    session_id: str,
    entrada: str,
    resultado: Mapping[str, Any],
    archivo: str | Path = "trazas_agente.jsonl",
) -> None:
    """Agrega una interacción del agente al archivo JSONL."""
    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "entrada": entrada,
        "acciones": [
            {
                "herramienta": accion.tool,
                "argumentos": accion.tool_input,
                "observacion": observacion,
            }
            for accion, observacion in resultado.get("intermediate_steps", [])
        ],
        "respuesta_final": resultado["output"],
    }

    with Path(archivo).open("a", encoding="utf-8") as destino:
        destino.write(json.dumps(registro, ensure_ascii=False) + "\n")


def marcar_repeticiones_sospechosas(
    archivo: str | Path = "trazas_agente.jsonl",
) -> list[str]:
    """Imprime y devuelve sesiones con llamadas consecutivas a la misma herramienta."""
    mensajes: list[str] = []
    try:
        with Path(archivo).open(encoding="utf-8") as fuente:
            registros = [json.loads(linea) for linea in fuente if linea.strip()]
    except FileNotFoundError:
        print(
            f"No se encontró '{archivo}'. Registra al menos una interacción "
            "antes de revisar repeticiones."
        )
        return mensajes

    for registro in registros:
        herramientas = [
            accion["herramienta"]
            for accion in registro.get("acciones", [])
        ]
        for anterior, actual in zip(herramientas, herramientas[1:]):
            if actual == anterior:
                mensaje = (
                    f"Revisar: {registro['session_id']} usó "
                    f"'{actual}' dos veces seguidas"
                )
                print(mensaje)
                mensajes.append(mensaje)
                break

    return mensajes
