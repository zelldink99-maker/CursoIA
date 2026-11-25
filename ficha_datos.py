import re
from pathlib import Path

from verificar_ficha import RUTA, leer_secciones


NUMERO = r"(\d+(?:[.,]\d+)?)"
PATRON_RF = re.compile(r"(?m)^- (RF-\d{2}): (.+)$")
PATRON_RNF = re.compile(r"(?m)^- (RNF-\d{2}): (.+)$")
PATRON_CA = re.compile(
    r"(?m)^- (CA-\d{2}) \(((?:RNF|RF)-\d{2})\): (.+)$"
)
PATRON_HITO = re.compile(
    rf"(?m)^- (H\d+) \({NUMERO} h\): (.+)$"
)
PATRON_ID = re.compile(r"\b(?:RNF|RF)-\d{2}\b")


def a_numero(texto):
    return float(texto.replace(",", "."))


def cargar(ruta=RUTA):
    ruta_ficha = Path(ruta)
    if not ruta_ficha.is_file():
        raise FileNotFoundError(f"No existe la ficha: {ruta_ficha}")

    texto = ruta_ficha.read_text(encoding="utf-8")
    return cargar_desde_texto(texto)


def cargar_desde_texto(texto):
    secciones = leer_secciones(texto)
    faltantes = [numero for numero in (2, 4, 5) if numero not in secciones]
    if faltantes:
        raise ValueError(
            "Faltan secciones necesarias para leer la ficha: "
            + ", ".join(str(numero) for numero in faltantes)
        )

    req = secciones[2][1]
    cuerpo4 = secciones[4][1]
    cuerpo5 = secciones[5][1]
    ficha = {
        "rf": dict(PATRON_RF.findall(req)),
        "rnf": dict(PATRON_RNF.findall(req)),
        "cajones": {},
        "criterios": [
            {"id": id_, "cubre": [cubre], "texto": texto_ca}
            for id_, cubre, texto_ca in PATRON_CA.findall(cuerpo4)
        ],
        "hitos": [],
        "texto4": cuerpo4,
        "texto5": cuerpo5,
    }

    for nombre in ("Imprescindible", "Deseable", "Fuera de alcance"):
        coincidencia = re.search(rf"(?m)^{nombre}:\s*(.*)$", req)
        ficha["cajones"][nombre] = (
            re.findall(r"RF-\d{2}", coincidencia.group(1))
            if coincidencia
            else []
        )

    for etiqueta, clave in (
        ("Horas disponibles", "disponibles"),
        ("Margen de imprevistos", "margen"),
    ):
        coincidencia = re.search(
            rf"(?m)^{etiqueta}:\s*{NUMERO} h\b",
            cuerpo5,
        )
        ficha[clave] = (
            a_numero(coincidencia.group(1))
            if coincidencia
            else None
        )

    for id_, horas, resto in PATRON_HITO.findall(cuerpo5):
        coincidencia = re.search(
            r"Cubre:(.*?)Se comprueba con:(.*)$",
            resto,
        )
        ficha["hitos"].append(
            {
                "id": id_,
                "horas": a_numero(horas),
                "cubre": (
                    PATRON_ID.findall(coincidencia.group(1))
                    if coincidencia
                    else []
                ),
                "criterios": (
                    re.findall(r"CA-\d{2}", coincidencia.group(2))
                    if coincidencia
                    else []
                ),
            }
        )

    return ficha
