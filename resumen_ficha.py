import sys
from pathlib import Path

from ficha_datos import RUTA, cargar


def lista(elementos):
    return ", ".join(elementos) if elementos else "ninguno"


def resumen(ficha):
    rf = ficha["rf"]
    rnf = ficha["rnf"]
    cajones = ficha["cajones"]
    con_criterio = {
        requerimiento
        for criterio in ficha["criterios"]
        for requerimiento in criterio["cubre"]
    }
    probados = {
        criterio
        for hito in ficha["hitos"]
        for criterio in hito["criterios"]
    }
    ids_criterios = {criterio["id"] for criterio in ficha["criterios"]}
    exigidos = cajones["Imprescindible"] + list(rnf)

    lineas = [
        f"RF: {len(rf)} | RNF: {len(rnf)}",
        (
            "Alcance: imprescindibles "
            f"{len(cajones['Imprescindible'])}, "
            f"deseables {len(cajones['Deseable'])}, "
            f"fuera de alcance {len(cajones['Fuera de alcance'])}"
        ),
        f"Criterios de aceptacion: {len(ficha['criterios'])}",
        "Imprescindibles y RNF sin criterio: "
        + lista([rid for rid in exigidos if rid not in con_criterio]),
    ]

    total = sum(hito["horas"] for hito in ficha["hitos"])
    disponibles = ficha["disponibles"]
    margen = ficha["margen"]
    linea_hitos = f"Hitos: {len(ficha['hitos'])}"
    linea_hitos += f" | Horas planificadas: {total:.1f} h"
    if disponibles is not None and margen is not None:
        tope = disponibles - margen
        linea_hitos += f" de {tope:.1f} h posibles"
        linea_hitos += (
            f" ({disponibles:.1f} h menos {margen:.1f} h de margen)"
        )
    lineas.append(linea_hitos)
    lineas.append(
        "Criterios que ningun hito comprueba: "
        + lista(sorted(ids_criterios - probados))
    )
    lineas.append(
        "Hitos sin criterio: "
        + lista(
            [
                hito["id"]
                for hito in ficha["hitos"]
                if not hito["criterios"]
            ]
        )
    )

    for linea in lineas:
        print(linea)
    return lineas


if __name__ == "__main__":
    if not Path(RUTA).is_file():
        sys.exit(f"No existe {RUTA}. Ejecuta el comando desde la raiz.")
    resumen(cargar())
