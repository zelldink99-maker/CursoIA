"""Prepara una muestra de resultados para revisión cualitativa manual."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MINIMO_RESULTADOS = 20
MINIMO_REVISIONES = 10
VALORES_SI_NO_PARCIAL = {"sí", "si", "no", "parcialmente"}
VALORES_SI_NO = {"sí", "si", "no"}


def ruta_resultados_predeterminada() -> Path:
    """Usa el archivo del modo core o, si no existe, el del Bloque 16."""
    resultados_core = PROJECT_ROOT / "resultados_actividad_core.json"
    if resultados_core.is_file():
        return resultados_core
    return PROJECT_ROOT / "resultados_metricas.json"


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
                "nota": "",
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


def validar_resultados(
    resultados: Sequence[Mapping[str, object]],
    exigir_minimo: bool = True,
) -> None:
    """Comprueba los campos y, si corresponde, el mínimo de resultados."""
    if not resultados:
        raise ValueError("No hay resultados para preparar la revisión")
    if exigir_minimo and len(resultados) < MINIMO_RESULTADOS:
        raise ValueError(
            f"Se requieren al menos {MINIMO_RESULTADOS} resultados generados"
        )

    consultas: set[str] = set()
    for indice, caso in enumerate(resultados):
        for campo in ("consulta", "referencia", "respuesta"):
            valor = caso.get(campo)
            if not isinstance(valor, str) or not valor.strip():
                raise ValueError(
                    f"El resultado {indice} debe incluir {campo} no vacío"
                )
        consulta = caso["consulta"]
        if consulta in consultas:
            raise ValueError(f"La consulta del resultado {indice} está duplicada")
        consultas.add(consulta)
        for campo in ("precision", "cobertura", "f1"):
            valor = caso.get(campo)
            if (
                isinstance(valor, bool)
                or not isinstance(valor, (int, float))
                or not math.isfinite(valor)
                or not 0 <= valor <= 1
            ):
                raise ValueError(
                    f"El resultado {indice} debe incluir {campo} "
                    "numérico entre 0 y 1"
                )


def validar_revision_manual(
    resultados: Sequence[Mapping[str, object]],
    revisiones: Sequence[Mapping[str, object]],
) -> None:
    """Valida que diez revisiones completas correspondan a ambos extremos."""
    validar_resultados(resultados)
    if len(revisiones) < MINIMO_REVISIONES:
        raise ValueError(
            f"Se requieren al menos {MINIMO_REVISIONES} casos revisados"
        )

    muestra_esperada = seleccionar_muestra(resultados)
    claves_esperadas = {
        (caso["consulta"], caso["f1"])
        for caso in muestra_esperada
    }
    claves_resultados = {
        (caso["consulta"], caso["f1"])
        for caso in resultados
    }
    resultados_por_clave = {
        (caso["consulta"], caso["f1"]): caso
        for caso in resultados
    }
    claves_revisadas: set[tuple[object, object]] = set()
    for indice, caso in enumerate(revisiones):
        if not isinstance(caso.get("consulta"), str):
            raise ValueError(f"La revisión {indice} debe incluir una consulta")
        f1 = caso.get("f1")
        if isinstance(f1, bool) or not isinstance(f1, (int, float)):
            raise ValueError(f"La revisión {indice} debe incluir un F1 numérico")
        clave = (caso["consulta"], f1)
        if clave in claves_revisadas:
            raise ValueError(f"La revisión {indice} duplica otro caso")
        if clave not in claves_resultados:
            raise ValueError(
                f"La revisión {indice} no corresponde a un resultado evaluado"
            )
        resultado_original = resultados_por_clave[clave]
        for campo in ("referencia", "respuesta", "precision", "cobertura"):
            if caso.get(campo) != resultado_original[campo]:
                raise ValueError(
                    f"La revisión {indice} no conserva el campo {campo} "
                    "del resultado original"
                )
        claves_revisadas.add(clave)

    if not claves_esperadas.issubset(claves_revisadas):
        raise ValueError(
            "La revisión debe incluir los cinco F1 más bajos y los cinco más altos"
        )

    for indice, caso in enumerate(revisiones):
        for campo in ("referencia", "respuesta"):
            if not isinstance(caso.get(campo), str) or not caso[campo].strip():
                raise ValueError(f"La revisión {indice} debe incluir {campo}")

        for campo in ("correccion_factual", "completitud"):
            valor = caso.get(campo)
            if (
                not isinstance(valor, str)
                or valor.strip().casefold() not in VALORES_SI_NO_PARCIAL
            ):
                raise ValueError(
                    f"La revisión {indice} debe calificar {campo} "
                    "con sí, no o parcialmente"
                )

        contradiccion = caso.get("contradiccion")
        if (
            not isinstance(contradiccion, str)
            or contradiccion.strip().casefold() not in VALORES_SI_NO
        ):
            raise ValueError(
                f"La revisión {indice} debe calificar contradiccion con sí o no"
            )

        nota = caso.get("nota")
        if not isinstance(nota, str) or not nota.strip():
            raise ValueError(f"La revisión {indice} debe incluir una nota")


def validar_documentacion(
    ruta: str | Path,
    resultados: Sequence[Mapping[str, object]],
    revisiones: Sequence[Mapping[str, object]],
) -> None:
    """Comprueba que límites y hallazgos reflejen la actividad realizada."""
    contenido = Path(ruta).read_text(encoding="utf-8")
    secciones_requeridas = (
        "## Qué mide",
        "## Modos de falla conocidos",
        "## Muestra revisada",
        "## Recomendación de uso",
    )
    faltantes = [
        seccion for seccion in secciones_requeridas if seccion not in contenido
    ]
    if faltantes:
        raise ValueError(
            f"Faltan secciones requeridas: {', '.join(faltantes)}"
        )

    seccion_muestra = contenido.split("## Muestra revisada", 1)[1].split(
        "\n## ", 1
    )[0]
    if f"Respuestas generadas: {len(resultados)}" not in seccion_muestra:
        raise ValueError("Documenta la cantidad real de respuestas generadas")
    if f"Casos revisados: {len(revisiones)}" not in seccion_muestra:
        raise ValueError("Documenta la cantidad real de casos revisados")
    fecha = re.search(
        r"Fecha de revisión: (\d{4}-\d{2}-\d{2})",
        seccion_muestra,
    )
    if not fecha:
        raise ValueError("Documenta la fecha de la revisión manual")
    try:
        date.fromisoformat(fecha.group(1))
    except ValueError as error:
        raise ValueError("La fecha de revisión debe ser una fecha válida") from error
    if not re.search(
        r"Criterio de selección: (?!PENDIENTE|TODO|\[).+",
        seccion_muestra,
    ):
        raise ValueError("Documenta cómo seleccionaste la muestra")

    seccion_fallas = contenido.split("## Modos de falla conocidos", 1)[1].split(
        "\n## ", 1
    )[0]
    patrones = re.findall(
        r"^- Consulta: (.+?) \| F1: ([0-9]+(?:\.[0-9]+)?) "
        r"\| Hallazgo: (.+)$",
        seccion_fallas,
        flags=re.MULTILINE,
    )
    if not patrones:
        raise ValueError(
            "Añade al menos un hallazgo concreto vinculado a una revisión"
        )
    revisiones_por_clave = {(caso["consulta"], caso["f1"]) for caso in revisiones}
    for consulta, f1_texto, hallazgo in patrones:
        f1_documentado = float(f1_texto)
        if not any(
            consulta_revisada == consulta
            and isinstance(f1_revisado, (int, float))
            and not isinstance(f1_revisado, bool)
            and math.isclose(f1_revisado, f1_documentado, abs_tol=0.005)
            for consulta_revisada, f1_revisado in revisiones_por_clave
        ):
            raise ValueError(
                f"El hallazgo de «{consulta}» no coincide con un caso revisado"
            )
        if (
            hallazgo.strip().casefold() in {"pendiente", "todo"}
            or hallazgo.strip().startswith("[")
        ):
            raise ValueError("Reemplaza el texto de ejemplo por un hallazgo real")

    seccion_recomendacion = contenido.split("## Recomendación de uso", 1)[1]
    if not seccion_recomendacion.strip() or re.search(
        r"\b(PENDIENTE|TODO)\b|\[",
        seccion_recomendacion,
        flags=re.IGNORECASE,
    ):
        raise ValueError("Completa la recomendación de uso basada en la revisión")


def main() -> int:
    """Guarda una plantilla de revisión manual sin llamar al modelo."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--entrada",
        type=Path,
        default=None,
        help=(
            "JSON generado por evaluar_metricas.py "
            "(por defecto, prioriza resultados_actividad_core.json y luego "
            "usa resultados_metricas.json)"
        ),
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=PROJECT_ROOT / "revision_manual.json",
        help="archivo JSON editable con la muestra y la rúbrica",
    )
    argumentos = parser.parse_args()

    ruta_entrada = argumentos.entrada or ruta_resultados_predeterminada()
    if ruta_entrada.resolve() == argumentos.salida.resolve():
        raise ValueError("La entrada y la salida deben ser archivos distintos")

    try:
        resultados = cargar_resultados(ruta_entrada)
        validar_resultados(resultados, exigir_minimo=False)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    muestra = preparar_revision(resultados)
    with argumentos.salida.open("w", encoding="utf-8") as archivo:
        json.dump(muestra, archivo, indent=2, ensure_ascii=False)
        archivo.write("\n")

    print(f"Muestra preparada: {len(muestra)} casos en {argumentos.salida}")
    if len(resultados) < MINIMO_RESULTADOS:
        print(
            f"Aviso: hay {len(resultados)} resultados; la actividad core requiere "
            f"{MINIMO_RESULTADOS}. Esta muestra parcial no completa la entrega."
        )
    if len(muestra) < MINIMO_REVISIONES:
        print(
            f"Aviso: hay {len(muestra)} casos disponibles para revisar; "
            f"la actividad requiere al menos {MINIMO_REVISIONES}."
        )
    print(
        "Completa correccion_factual y completitud con "
        "'sí', 'no' o 'parcialmente'; contradiccion con 'sí' o 'no', "
        "y explica cada calificación en nota."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
