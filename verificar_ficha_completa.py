import re
import sys
from datetime import date
from pathlib import Path

from ficha_datos import RUTA, cargar_desde_texto
from verificar_ficha import verificar


REVISION = Path("docs/revision_alcance.md")
MIN_HITOS = 3
MAX_HITOS = 6
PATRON_RF_RNF = re.compile(r"\b(?:RNF|RF)-\d{2}\b")


def verificar_pendientes(ficha):
    errores = []
    for numero in (4, 5):
        texto = ficha[f"texto{numero}"]
        if "[PENDIENTE" in texto or "[COMPLETAR" in texto:
            errores.append(f"la seccion {numero} todavia tiene marcas")
    return errores


def verificar_criterios(ficha):
    errores, avisos = [], []
    existentes = set(ficha["rf"]) | set(ficha["rnf"])
    criterios = ficha["criterios"]
    escritos = len(re.findall(r"(?m)^- CA", ficha["texto4"]))

    if not criterios:
        errores.append("la seccion 4 no tiene criterios (formato CA-NN)")
    if escritos != len(criterios):
        errores.append(
            f"{escritos - len(criterios)} criterio(s) no siguen el formato "
            "'- CA-NN (RF-NN): texto'"
        )

    cubiertos = set()
    for criterio in criterios:
        for rid in criterio["cubre"]:
            if rid not in existentes:
                errores.append(f"{criterio['id']} cubre {rid}, que no existe")
        cubiertos.update(criterio["cubre"])
        if not re.search(r'\d|"', criterio["texto"]):
            avisos.append(
                f"{criterio['id']} no tiene ningun dato concreto"
            )

    exigidos = ficha["cajones"]["Imprescindible"] + list(ficha["rnf"])
    for rid in exigidos:
        if rid not in cubiertos:
            errores.append(f"{rid} no tiene criterio de aceptacion")

    tiene_negativo = any(
        re.search(
            r"\b(?:sin datos|no hay datos|no presenta|no devuelve|"
            r"no existe|fuera del periodo)\b",
            criterio["texto"],
            re.IGNORECASE,
        )
        for criterio in criterios
    )
    if criterios and not tiene_negativo:
        errores.append("falta al menos un criterio para un caso negativo")

    return errores, avisos


def verificar_plan(ficha):
    errores = []
    hitos = ficha["hitos"]
    ids_criterios = {criterio["id"] for criterio in ficha["criterios"]}
    existentes = set(ficha["rf"]) | set(ficha["rnf"])
    escritos = len(re.findall(r"(?m)^- H\d", ficha["texto5"]))

    if escritos != len(hitos):
        errores.append(
            f"{escritos - len(hitos)} hito(s) no siguen el formato "
            "'- H1 (3 h): descripcion. Cubre: ... "
            "Se comprueba con: ...'"
        )
    if not MIN_HITOS <= len(hitos) <= MAX_HITOS:
        errores.append(
            f"hay {len(hitos)} hitos y se piden entre "
            f"{MIN_HITOS} y {MAX_HITOS}"
        )

    disponibles = ficha["disponibles"]
    margen = ficha["margen"]
    if disponibles is None or margen is None:
        errores.append(
            "faltan las lineas 'Horas disponibles:' y "
            "'Margen de imprevistos:'"
        )
    else:
        tope = disponibles - margen
        total = sum(hito["horas"] for hito in hitos)
        if total > tope:
            errores.append(
                f"los hitos suman {total:.1f} h y el tope es {tope:.1f} h"
            )

    cubiertos, probados = set(), set()
    for hito in hitos:
        if not hito["cubre"]:
            errores.append(f"{hito['id']} no indica que cubre")
        if not hito["criterios"]:
            errores.append(f"{hito['id']} no tiene criterio de aceptacion")
        for rid in hito["cubre"]:
            if rid not in existentes:
                errores.append(f"{hito['id']} cubre {rid}, que no existe")
        for cid in hito["criterios"]:
            if cid not in ids_criterios:
                errores.append(f"{hito['id']} usa {cid}, que no existe")
        cubiertos.update(hito["cubre"])
        probados.update(hito["criterios"])

    for rid in ficha["cajones"]["Imprescindible"]:
        if rid not in cubiertos:
            errores.append(f"{rid} imprescindible sin hito que lo cubra")
    for cid in sorted(ids_criterios - probados):
        errores.append(f"{cid} no lo comprueba ningun hito")

    if hitos:
        ultimo = hitos[-1]["id"]
        linea_final = next(
            (
                linea.lower()
                for linea in ficha["texto5"].splitlines()
                if linea.startswith(f"- {ultimo} ")
            ),
            "",
        )
        if not all(
            palabra in linea_final
            for palabra in ("pruebas", "documentacion", "defensa")
        ):
            errores.append(
                "el ultimo hito debe reservar tiempo para pruebas, "
                "documentacion y defensa"
            )

    return errores


def verificar_revision(texto):
    hallazgos = re.findall(
        r"(?m)^- Hallazgo \d+(?: \([^)]*\))?: .+$",
        texto,
    )
    decisiones = re.findall(
        r"(?m)^  Decisión: (?:aceptado|rechazado|aplazado)\b",
        texto,
    )
    errores = []
    if len(hallazgos) < 2:
        errores.append(
            f"hay {len(hallazgos)} hallazgos y se piden al menos 2"
        )
    if len(decisiones) != len(hallazgos):
        errores.append("cada hallazgo necesita su linea 'Decisión:'")
    if "PENDIENTE" in texto.upper():
        errores.append("la revision conserva marcadores de plantilla")

    revisor = re.search(r"(?m)^Revisor:\s*(.+)$", texto)
    fecha = re.search(r"(?m)^Fecha:\s*(\d{4}-\d{2}-\d{2})$", texto)
    if not revisor or "pendiente" in revisor.group(1).lower():
        errores.append("falta identificar al revisor de la revision cruzada")
    if not fecha:
        errores.append("falta la fecha de la revision en formato AAAA-MM-DD")
    elif not _fecha_valida(fecha.group(1)):
        errores.append("la fecha de revision no es una fecha valida")
    return errores


def _fecha_valida(fecha):
    try:
        date.fromisoformat(fecha)
    except ValueError:
        return False
    return True


def verificar_completa(texto_ficha, texto_revision):
    errores, avisos = verificar(texto_ficha)
    if errores:
        return errores, avisos

    ficha = cargar_desde_texto(texto_ficha)
    errores = verificar_pendientes(ficha)
    if not errores:
        errores, avisos_criterios = verificar_criterios(ficha)
        avisos.extend(avisos_criterios)
        errores.extend(verificar_plan(ficha))
    if not errores:
        errores.extend(verificar_revision(texto_revision))
    return errores, avisos


def main():
    if not Path(RUTA).is_file():
        sys.exit(f"No existe {RUTA}. Ejecuta el script desde la raiz.")
    if not REVISION.is_file():
        sys.exit(f"ERROR: falta {REVISION}: registra la revision cruzada")

    texto_ficha = Path(RUTA).read_text(encoding="utf-8")
    texto_revision = REVISION.read_text(encoding="utf-8")
    errores, avisos = verificar_completa(texto_ficha, texto_revision)

    for aviso in avisos:
        print("AVISO:", aviso)
    for error in errores:
        print("ERROR:", error)
    if errores:
        print(f"\n{len(errores)} problema(s) por resolver")
        return 1
    print("Ficha verificada: las cinco secciones son coherentes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
