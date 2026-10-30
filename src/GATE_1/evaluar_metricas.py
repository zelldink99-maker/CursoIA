"""Evalúa respuestas generadas con precisión, cobertura y F1."""

import argparse
import json
import math
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

CASOS_ACTIVIDAD_CORE = (
    (
        "¿Qué es Python?",
        "Python es un lenguaje de programación interpretado.",
    ),
    (
        "¿Cuándo se publicó Python por primera vez?",
        "Python se publicó en 1991.",
    ),
    ("¿Quién creó Python?", "Python fue creado por Guido van Rossum."),
    (
        "¿Qué es una lista en Python?",
        "Una lista es una colección ordenada y modificable.",
    ),
    (
        "¿Qué estructura guarda pares clave-valor en Python?",
        "Un diccionario guarda pares clave-valor.",
    ),
    (
        "¿Qué tipo de dato representa True o False?",
        "El tipo bool representa valores verdadero o falso.",
    ),
    (
        "¿Qué palabra inicia una función en Python?",
        "La palabra def inicia una función en Python.",
    ),
    (
        "¿Qué palabra se usa para devolver un valor desde una función?",
        "return devuelve un valor desde una función.",
    ),
    (
        "¿Qué símbolo inicia un comentario en Python?",
        "El símbolo # inicia un comentario en Python.",
    ),
    (
        "¿Qué función muestra un valor en pantalla?",
        "La función print muestra un valor en pantalla.",
    ),
    (
        "¿Qué función obtiene la longitud de una colección?",
        "La función len obtiene la longitud de una colección.",
    ),
    (
        "¿Qué palabra importa un módulo en Python?",
        "La palabra import permite importar un módulo.",
    ),
    (
        "¿Qué estructura repite mientras una condición sea verdadera?",
        "El bucle while repite mientras una condición sea verdadera.",
    ),
    (
        "¿Qué estructura recorre los elementos de una secuencia?",
        "El bucle for recorre los elementos de una secuencia.",
    ),
    (
        "¿Qué valor representa la ausencia de valor en Python?",
        "None representa la ausencia de valor en Python.",
    ),
    (
        "¿Qué método agrega un elemento al final de una lista?",
        "El método append agrega un elemento al final de una lista.",
    ),
    (
        "¿Qué operador compara si dos valores son iguales?",
        "El operador == compara si dos valores son iguales.",
    ),
    (
        "¿Qué operador lógico requiere que ambas condiciones sean verdaderas?",
        "El operador and requiere que ambas condiciones sean verdaderas.",
    ),
    (
        "¿Qué excepción ocurre al dividir un número entre cero?",
        "ZeroDivisionError ocurre al dividir un número entre cero.",
    ),
    (
        "¿Qué archivo suele declarar dependencias de Python?",
        "requirements.txt suele declarar dependencias de Python.",
    ),
)
ARCHIVO_RESULTADOS_ACTIVIDAD = Path(__file__).resolve().parents[2] / (
    "resultados_actividad_core.json"
)


def guardar_resultados(
    resultados: list[ResultadoEvaluacion],
    ruta: str | Path = "resultados_metricas.json",
) -> None:
    """Guarda el estado actual de la evaluación como JSON UTF-8."""
    with Path(ruta).open("w", encoding="utf-8") as archivo:
        # Mantiene tildes y caracteres españoles legibles en el archivo.
        json.dump(resultados, archivo, indent=2, ensure_ascii=False)


def _cargar_resultados_existentes(
    ruta: str | Path,
    casos: Sequence[tuple[str, str]],
) -> list[ResultadoEvaluacion]:
    """Carga un lote parcial y confirma que corresponda a las consultas."""
    archivo = Path(ruta)
    if not archivo.exists():
        return []

    with archivo.open(encoding="utf-8") as entrada:
        contenido = json.load(entrada)
    if not isinstance(contenido, list):
        raise ValueError("El archivo de resultados debe contener una lista JSON")

    referencias = dict(casos)
    resultados: list[ResultadoEvaluacion] = []
    consultas_guardadas: set[str] = set()
    for indice, item in enumerate(contenido):
        if not isinstance(item, dict):
            raise ValueError(f"El resultado guardado {indice} no es un objeto JSON")
        consulta = item.get("consulta")
        referencia = item.get("referencia")
        respuesta = item.get("respuesta")
        if not isinstance(consulta, str) or consulta not in referencias:
            raise ValueError(
                f"La consulta guardada {indice} no pertenece a este lote"
            )
        if referencia != referencias[consulta]:
            raise ValueError(
                f"La referencia guardada para la consulta {consulta!r} no coincide"
            )
        if consulta in consultas_guardadas:
            raise ValueError(f"La consulta {consulta!r} aparece más de una vez")
        if not isinstance(respuesta, str) or not respuesta.strip():
            raise ValueError(f"La respuesta guardada para {consulta!r} no es válida")

        metricas: dict[str, float] = {}
        for campo in ("precision", "cobertura", "f1"):
            valor = item.get(campo)
            if (
                isinstance(valor, bool)
                or not isinstance(valor, (int, float))
                or not math.isfinite(valor)
                or not 0 <= valor <= 1
            ):
                raise ValueError(
                    f"La métrica {campo} de la consulta {consulta!r} no es válida"
                )
            metricas[campo] = float(valor)

        resultados.append(
            {
                "consulta": consulta,
                "referencia": referencia,
                "respuesta": respuesta,
                **metricas,
            }
        )
        consultas_guardadas.add(consulta)
    return resultados


def evaluar_casos(
    casos: Sequence[tuple[str, str]],
    ruta_resultados: str | Path = "resultados_metricas.json",
    continuar: bool = False,
) -> list[ResultadoEvaluacion]:
    """Genera y evalúa cada respuesta, persistiendo resultados parciales."""
    resultados = (
        _cargar_resultados_existentes(ruta_resultados, casos) if continuar else []
    )
    consultas_guardadas = {resultado["consulta"] for resultado in resultados}
    guardar_resultados(resultados, ruta_resultados)

    for consulta, referencia in casos:
        if consulta in consultas_guardadas:
            continue
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
        consultas_guardadas.add(consulta)
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
    """Evalúa ejemplos o las 20 consultas de la actividad core."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--actividad-core",
        action="store_true",
        help=(
            "genera 20 respuestas para la actividad cualitativa; "
            "cada consulta puede generar costo de API"
        ),
    )
    argumentos = parser.parse_args()
    casos = CASOS_ACTIVIDAD_CORE if argumentos.actividad_core else CASOS_EVALUACION
    ruta_resultados = (
        ARCHIVO_RESULTADOS_ACTIVIDAD
        if argumentos.actividad_core
        else "resultados_metricas.json"
    )
    resultados = evaluar_casos(
        casos,
        ruta_resultados,
        continuar=argumentos.actividad_core,
    )

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
    print(f"Resultados guardados en {ruta_resultados}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
