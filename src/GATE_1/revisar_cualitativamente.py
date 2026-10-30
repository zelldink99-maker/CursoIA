"""Prepara una muestra de resultados para revisión cualitativa manual."""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def seleccionar_muestra(
    resultados: Sequence[Mapping[str, object]],
    extremos: int = 5,
) -> list[dict[str, object]]:
    """Selecciona los F1 más bajos y altos sin repetir casos."""
    if isinstance(extremos, bool) or not isinstance(extremos, int) or extremos < 1:
        raise ValueError("extremos debe ser un entero positivo")

    for indice, resultado in enumerate(resultados):
        f1 = resultado.get("f1")
        if isinstance(f1, bool) or not isinstance(f1, (int, float)):
            raise ValueError(f"El resultado {indice} debe incluir un F1 numérico")
        if not math.isfinite(f1):
            raise ValueError(f"El F1 del resultado {indice} debe ser finito")

    ordenados = sorted(resultados, key=lambda resultado: resultado["f1"])
    cantidad_bajos = min(extremos, (len(ordenados) + 1) // 2)
    cantidad_altos = min(extremos, len(ordenados) - cantidad_bajos)
    seleccionados = ordenados[:cantidad_bajos]
    if cantidad_altos:
        seleccionados.extend(ordenados[-cantidad_altos:])
    return [dict(resultado) for resultado in seleccionados]


def preparar_revision(
    resultados: Sequence[Mapping[str, object]],
    extremos: int = 5,
) -> list[dict[str, object]]:
    """Añade campos vacíos para completar la rúbrica en cada caso."""
    muestra = seleccionar_muestra(resultados, extremos)
    campos_requeridos = ("consulta", "referencia", "respuesta")
    for indice, caso in enumerate(muestra):
        faltantes = [campo for campo in campos_requeridos if campo not in caso]
        if faltantes:
            raise ValueError(
                f"El resultado seleccionado {indice} no incluye: "
                f"{', '.join(faltantes)}"
            )
        caso.update(
            {
                "correccion_factual": "",
                "completitud": "",
                "contradiccion": "",
                "justificacion": "",
            }
        )
    return muestra


def cargar_resultados(ruta: str | Path) -> list[dict[str, object]]:
    """Carga el archivo JSON generado por evaluar_metricas."""
    with Path(ruta).open(encoding="utf-8") as archivo:
        contenido = json.load(archivo)
    if not isinstance(contenido, list):
        raise ValueError("El archivo de resultados debe contener una lista JSON")
    if any(not isinstance(resultado, dict) for resultado in contenido):
        raise ValueError("Cada resultado del archivo debe ser un objeto JSON")
    return contenido


def main() -> int:
    """Guarda un borrador de revisión manual sin llamar al modelo."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--entrada",
        type=Path,
        default=PROJECT_ROOT / "resultados_metricas.json",
        help="JSON generado por evaluar_metricas.py",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=PROJECT_ROOT / "revision_cualitativa.json",
        help="archivo JSON editable con la muestra y la rúbrica",
    )
    argumentos = parser.parse_args()

    if argumentos.entrada.resolve() == argumentos.salida.resolve():
        raise ValueError("La entrada y la salida deben ser archivos distintos")

    muestra = preparar_revision(cargar_resultados(argumentos.entrada))
    with argumentos.salida.open("w", encoding="utf-8") as archivo:
        json.dump(muestra, archivo, indent=2, ensure_ascii=False)
        archivo.write("\n")

    print(f"Muestra preparada: {len(muestra)} casos en {argumentos.salida}")
    print(
        "Completa correccion_factual y completitud con "
        "'sí', 'no' o 'parcialmente'; contradiccion con 'sí' o 'no', "
        "y añade la justificacion."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
