from math import hypot
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SALIDA = Path("docs/diagrama_arquitectura.png")
ANCHO = 1500
ALTO = 900


def fuente(nombre, tamano):
    try:
        return ImageFont.truetype(nombre, tamano)
    except OSError:
        return ImageFont.load_default()


def dibujar():
    imagen = Image.new("RGB", (ANCHO, ALTO), "white")
    dibujo = ImageDraw.Draw(imagen)
    azul = (45, 110, 170)
    claro = (230, 240, 250)
    gris = (70, 70, 70)
    borde = (125, 135, 145)

    titulo = fuente("arial.ttf", 34)
    encabezado = fuente("arial.ttf", 24)
    normal = fuente("arial.ttf", 18)
    caja = fuente("arial.ttf", 20)

    dibujo.text((45, 25), "Arquitectura: revision de datos post-ETL",
                font=titulo, fill=(20, 60, 100))

    componentes = [
        (35, 275, 235, 355, "Usuario"),
        (35, 610, 235, 690, "CSV de ventas"),
        (300, 280, 510, 360, "FastAPI"),
        (610, 280, 820, 360, "LangGraph"),
        (300, 620, 510, 700, "Proceso ETL"),
        (610, 620, 820, 700, "Datos procesados"),
        (610, 470, 820, 550, "Calculos controlados"),
        (900, 470, 1110, 550, "Chroma"),
        (1200, 280, 1460, 360, "Modelo"),
    ]

    dibujo.rounded_rectangle(
        (265, 190, 1145, 770),
        radius=24,
        outline=borde,
        width=3,
    )
    dibujo.text((285, 200), "Docker: servicio, datos procesados e indice",
                font=encabezado, fill=gris)

    for x1, y1, x2, y2, texto in componentes:
        dibujo.rounded_rectangle(
            (x1, y1, x2, y2),
            radius=18,
            fill=claro,
            outline=azul,
            width=3,
        )
        dibujo.text(
            (x1 + 18, y1 + 35),
            texto,
            font=caja,
            fill=(20, 40, 70),
        )

    def punta(x, y, dx, dy):
        longitud = hypot(dx, dy)
        ux = dx / longitud
        uy = dy / longitud
        base_x = x - 12 * ux
        base_y = y - 12 * uy
        dibujo.polygon(
            [
                (x, y),
                (base_x - 7 * uy, base_y + 7 * ux),
                (base_x + 7 * uy, base_y - 7 * ux),
            ],
            fill=azul,
        )

    def flecha(x1, y1, x2, y2, etiqueta, tx, ty):
        dibujo.line((x1, y1, x2, y2), fill=azul, width=4)
        punta(x2, y2, x2 - x1, y2 - y1)
        dibujo.text((tx, ty), etiqueta, font=normal, fill=gris)

    def flecha_doble(x1, y1, x2, y2, etiqueta, tx, ty):
        dibujo.line((x1, y1, x2, y2), fill=azul, width=4)
        punta(x1, y1, x1 - x2, y1 - y2)
        punta(x2, y2, x2 - x1, y2 - y1)
        dibujo.text((tx, ty), etiqueta, font=normal, fill=gris)

    flecha(235, 315, 300, 315, "pregunta", 235, 285)
    flecha(300, 345, 235, 345, "respuesta JSON", 225, 365)
    flecha(235, 650, 300, 650, "archivo CSV", 225, 620)
    flecha(510, 320, 610, 320, "consulta", 525, 285)
    flecha(510, 660, 610, 660, "filas limpias", 515, 625)
    flecha(715, 360, 715, 470, "calcular reporte", 725, 395)
    flecha(715, 620, 715, 550, "filas limpias", 725, 575)
    flecha_doble(820, 330, 900, 485, "consulta", 825, 405)
    flecha(820, 300, 1200, 300, "solicitud al modelo", 900, 265)
    flecha(1200, 340, 820, 340, "texto de respuesta", 940, 350)

    dibujo.text((1190, 410), "Gemini: API externa", font=encabezado, fill=gris)
    dibujo.text((1190, 465), "Clave: variable de entorno", font=normal, fill=gris)
    dibujo.text((1190, 495), "No se guarda en el repositorio", font=normal, fill=gris)
    dibujo.text((35, 790),
                "FastAPI, LangGraph y Chroma se ejecutan dentro del contenedor.",
                font=normal, fill=gris)

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(SALIDA)
    print(f"Diagrama generado: {SALIDA}")


if __name__ == "__main__":
    dibujar()
