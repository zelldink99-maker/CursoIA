"""Herramientas locales para estimar y fundamentar una estrategia de personalizacion."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from pathlib import Path
import sys

from google import genai
from google.genai import errors, types

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUTA_DECISION_DOCUMENTADA = (
    PROJECT_ROOT / "docs" / "decision_personalizacion.md"
)

CLAVES_RESPUESTAS = (
    "informacion_cambia_seguido",
    "problema_de_formato_o_tono",
    "dataset_grande_y_de_calidad",
    "presupuesto_limitado_o_iterar_rapido",
    "necesita_multiples_variantes",
)


def estimar_costo_de_etiquetar(
    num_ejemplos: int | float,
    minutos_por_ejemplo: int | float,
    costo_por_hora: int | float,
) -> tuple[float, float]:
    """Devuelve las horas y el costo estimados del etiquetado."""
    valores = (num_ejemplos, minutos_por_ejemplo, costo_por_hora)
    if any(not isfinite(valor) or valor < 0 for valor in valores):
        raise ValueError("Los valores del calculo deben ser finitos y no negativos.")

    horas = num_ejemplos * minutos_por_ejemplo / 60
    return horas, horas * costo_por_hora


def recomendar_estrategia(
    respuestas: Mapping[str, bool],
) -> tuple[dict[str, int], list[str]]:
    """Puntua RAG, fine-tuning completo y PEFT, conservando todos los empates."""
    faltantes = [clave for clave in CLAVES_RESPUESTAS if clave not in respuestas]
    if faltantes:
        raise ValueError(f"Faltan respuestas para: {', '.join(faltantes)}.")
    invalidas = [
        clave for clave in CLAVES_RESPUESTAS if type(respuestas[clave]) is not bool
    ]
    if invalidas:
        raise TypeError(
            "Las respuestas deben ser True o False (booleanos) para: "
            f"{', '.join(invalidas)}."
        )

    puntos = {"RAG": 0, "Fine-tuning completo": 0, "PEFT": 0}
    if respuestas["informacion_cambia_seguido"]:
        puntos["RAG"] += 3
    if respuestas["problema_de_formato_o_tono"]:
        puntos["PEFT"] += 2
        puntos["Fine-tuning completo"] += 1
    if respuestas["dataset_grande_y_de_calidad"]:
        puntos["Fine-tuning completo"] += 2
        puntos["PEFT"] += 1
    if respuestas["presupuesto_limitado_o_iterar_rapido"]:
        puntos["RAG"] += 2
        puntos["PEFT"] += 1
    if respuestas["necesita_multiples_variantes"]:
        puntos["PEFT"] += 2

    maximo = max(puntos.values())
    ganadoras = [tecnica for tecnica, puntaje in puntos.items() if puntaje == maximo]
    return puntos, ganadoras


def generar_esqueleto_decision(
    problema: str,
    puntos: Mapping[str, int],
    ganadoras: list[str],
    justificacion: str | None = None,
    requisitos: str | None = None,
) -> str:
    """Genera las cuatro secciones, con o sin sus textos finales."""
    if not problema.strip():
        raise ValueError("Describe el problema antes de generar el documento.")
    if set(puntos) != {"RAG", "Fine-tuning completo", "PEFT"}:
        raise ValueError(
            "Se requieren los puntajes de RAG, Fine-tuning completo y PEFT."
        )
    if not ganadoras or any(tecnica not in puntos for tecnica in ganadoras):
        raise ValueError("Indica una o más técnicas candidatas válidas.")

    empate = len(ganadoras) > 1
    lineas = [
        "# Decisión de personalización",
        "",
        "## 1. El problema",
        problema,
        "",
        "## 2. Resultado del método de decisión",
    ]
    lineas.extend(
        f"- {tecnica}: {puntaje} puntos"
        for tecnica, puntaje in sorted(puntos.items(), key=lambda item: -item[1])
    )
    if empate:
        lineas.extend(["", f"**Empate entre: {', '.join(ganadoras)}**"])
    lineas.extend(["", "## 3. Técnica elegida y por qué"])
    if empate:
        lineas.append(
            justificacion
            or (
                "[COMPLETAR: el puntaje no resolvió el empate; justifica la elección "
                "con los costos de datos, infraestructura y tiempo]"
            )
        )
    else:
        lineas.append(
            justificacion
            or f"[COMPLETAR: por qué {ganadoras[0]} responde mejor a este caso]"
        )
    lineas.extend(
        [
            "",
            "## 4. Qué necesitarías para ejecutarla",
            requisitos
            or (
                "[COMPLETAR: corpus por indexar o cantidad de ejemplos etiquetados "
                "disponibles y faltantes]"
            ),
        ]
    )
    return "\n".join(lineas)


def main(ruta_salida: str | Path | None = None) -> int:
    """Imprime y guarda un ejemplo completo de decisión sin sobrescribir archivos."""
    salida = (
        RUTA_DECISION_DOCUMENTADA
        if ruta_salida is None
        else Path(ruta_salida)
    )
    salida.parent.mkdir(parents=True, exist_ok=True)
    if salida.exists():
        print(f"Error: {salida} ya existe; no se sobrescribió.")
        return 1

    respuestas_ejemplo = {
        "informacion_cambia_seguido": False,
        "problema_de_formato_o_tono": True,
        "dataset_grande_y_de_calidad": True,
        "presupuesto_limitado_o_iterar_rapido": False,
        "necesita_multiples_variantes": False,
    }
    puntos, ganadoras = recomendar_estrategia(respuestas_ejemplo)
    documento = generar_esqueleto_decision(
        "El clasificador de errores del cliente no responde con un formato consistente.",
        puntos,
        ganadoras,
        justificacion=(
            "Elijo PEFT. El empate con fine-tuning completo se resuelve por costo: "
            "el problema es la consistencia del formato, y PEFT permite entrenar "
            "menos parámetros. La elección se debe validar con ejemplos que no "
            "se usaron durante el entrenamiento."
        ),
        requisitos=(
            "Tengo 200 ejemplos etiquetados y revisados. Etiquetarlos a 5 minutos "
            "cada uno representa unas 16.67 horas de trabajo. Antes de entrenar, "
            "reviso el balance entre categorías y valido el dataset."
        ),
    )
    salida.write_text(documento, encoding="utf-8")

    separador = "=" * 70
    print(separador)
    print("PASO 1: el método corre sobre un caso de ejemplo")
    print(separador)
    print(puntos)
    print("candidatas:", ganadoras)
    print()
    print(separador)
    print(f"PASO 2: {salida} (ejemplo completo)")
    print(separador)
    print(documento)
    return 0


def obtener_estadisticas_tuning(
    client: genai.Client,
    nombre_trabajo: str,
) -> types.SupervisedTuningDataStats:
    """Consulta estadísticas de un trabajo existente; nunca inicia un tuning."""
    if not nombre_trabajo.strip():
        raise ValueError("Indica el nombre de un trabajo de tuning existente.")
    try:
        trabajo = client.tunings.get(name=nombre_trabajo)
    except errors.APIError as error:
        raise RuntimeError(
            f"No se pudo consultar el trabajo de tuning: {error}"
        ) from error

    if (
        trabajo.tuning_data_stats is None
        or trabajo.tuning_data_stats.supervised_tuning_data_stats is None
    ):
        raise RuntimeError(
            "El trabajo todavía no tiene estadísticas de datos. "
            "Espera a que termine y vuelve a consultar."
        )
    return trabajo.tuning_data_stats.supervised_tuning_data_stats


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
