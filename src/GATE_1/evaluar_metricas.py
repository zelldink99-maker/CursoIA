"""Evalúa respuestas generadas con precisión, cobertura y F1."""

import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict

if __package__:
    from .cliente import consultar_modelo
    from .pipeline_texto import calcular_metricas
else:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.GATE_1.cliente import consultar_modelo
    from src.GATE_1.pipeline_texto import calcular_metricas


class ResultadoEvaluacion(TypedDict):
    consulta: str
    referencia: str
    respuesta: str
    precision: float
    cobertura: float
    f1: float


class ResumenMetricas(TypedDict):
    precision_promedio: float
    cobertura_promedio: float
    f1_promedio: float


CASOS_EVALUACION = (
    (
        "¿Qué es Python?",
        "Python es un lenguaje de programación interpretado.",
    ),
    ("¿Cuándo se creó Python?", "Python fue creado en 1991."),
    (
        "¿Qué es una lista en Python?",
        "Una lista es una colección ordenada y modificable.",
    ),
)


def guardar_resultados(
    resultados: list[ResultadoEvaluacion],
    ruta: str | Path = "resultados_metricas.json",
) -> None:
    """Guarda el estado actual de la evaluación como JSON UTF-8."""
    with Path(ruta).open("w", encoding="utf-8") as archivo:
        # Mantiene tildes y caracteres españoles legibles en el archivo.
        json.dump(resultados, archivo, indent=2, ensure_ascii=False)


def evaluar_casos(
    casos: Sequence[tuple[str, str]],
    ruta_resultados: str | Path = "resultados_metricas.json",
) -> list[ResultadoEvaluacion]:
    """Genera y evalúa cada respuesta, persistiendo resultados parciales."""
    resultados: list[ResultadoEvaluacion] = []
    # Inicializa el archivo; luego cada respuesta correcta se persiste enseguida.
    guardar_resultados(resultados, ruta_resultados)

    for consulta, referencia in casos:
        # Esta llamada usa el cliente real y puede generar consumo de API.
        respuesta = consultar_modelo(consulta)
        metricas = calcular_metricas(referencia, respuesta)
        resultados.append(
            {
                "consulta": consulta,
                "referencia": referencia,
                "respuesta": respuesta,
                **metricas,
            }
        )
        # Si una consulta posterior falla, las anteriores ya quedan guardadas.
        guardar_resultados(resultados, ruta_resultados)

    return resultados


def resumir_metricas(
    resultados: Sequence[ResultadoEvaluacion],
) -> ResumenMetricas:
    """Calcula el promedio de cada métrica; una lista vacía produce ceros."""
    if not resultados:
        return {
            "precision_promedio": 0.0,
            "cobertura_promedio": 0.0,
            "f1_promedio": 0.0,
        }

    cantidad = len(resultados)
    return {
        # Se usa promedio simple: cada caso aporta el mismo peso al resumen.
        "precision_promedio": sum(r["precision"] for r in resultados) / cantidad,
        "cobertura_promedio": sum(r["cobertura"] for r in resultados) / cantidad,
        "f1_promedio": sum(r["f1"] for r in resultados) / cantidad,
    }


def main() -> int:
    """Evalúa los casos de ejemplo y prioriza las respuestas con menor F1."""
    resultados = evaluar_casos(CASOS_EVALUACION)

    for resultado in resultados:
        print(
            f'{resultado["consulta"]} '
            f'Precisión: {resultado["precision"]:.2f} '
            f'Cobertura: {resultado["cobertura"]:.2f} '
            f'F1: {resultado["f1"]:.2f}'
        )

    print(f"Promedios: {resumir_metricas(resultados)}")
    print("Peores casos:")
    # Orden ascendente para revisar primero las respuestas con menor F1.
    for resultado in sorted(resultados, key=lambda caso: caso["f1"])[:3]:
        print(f'{resultado["consulta"]} {resultado["f1"]:.2f}')
    print("Resultados guardados en resultados_metricas.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
