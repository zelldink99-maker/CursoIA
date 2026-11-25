from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SALIDA = Path("docs/diagrama_arquitectura.png")
ANCHO = 1400
ALTO = 860


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

    titulo = fuente("arial.ttf", 34)
    encabezado = fuente("arial.ttf", 24)
    normal = fuente("arial.ttf", 18)
    caja = fuente("arial.ttf", 20)

    dibujo.text(
        (45, 25),
        "Arquitectura: revision de datos post-ETL",
        font=titulo,
        fill=(20, 60, 100),
    )

    componentes = [
        (40, 130, 300, 220, "Archivo CSV simulado"),
        (40, 300, 300, 390, "Proceso ETL"),
        (40, 470, 300, 560, "Datos procesados"),
        (390, 130, 650, 220, "Usuario"),
        (390, 300, 650, 390, "Servicio FastAPI"),
        (740, 300, 1000, 390, "LangGraph"),
        (1090, 130, 1340, 220, "Chroma"),
        (1090, 300, 1340, 390, "Modelo"),
        (1090, 470, 1340, 560, "Calculos controlados"),
        (740, 650, 1000, 740, "Respuesta JSON"),
        (1090, 650, 1340, 740, "Docker"),
    ]

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

    dibujo.text((35, 100), "ENTRADA Y ETL", font=encabezado, fill=gris)
    dibujo.text((385, 100), "EXPUESTO", font=encabezado, fill=gris)
    dibujo.text((735, 270), "ORQUESTACION", font=encabezado, fill=gris)
    dibujo.text((1085, 100), "IA Y DATOS", font=encabezado, fill=gris)

    def flecha(x1, y1, x2, y2, etiqueta):
        dibujo.line((x1, y1, x2, y2), fill=azul, width=4)
        dibujo.polygon(
            [(x2, y2), (x2 - 12, y2 - 8), (x2 - 12, y2 + 8)],
            fill=azul,
        )
        dibujo.text(
            ((x1 + x2) // 2 - 45, (y1 + y2) // 2 - 22),
            etiqueta,
            font=normal,
            fill=gris,
        )

    flecha(170, 220, 170, 300, "CSV origen")
    flecha(170, 390, 170, 470, "filas procesadas")
    flecha(300, 345, 390, 345, "filas y pregunta")
    flecha(650, 345, 740, 345, "pregunta")
    flecha(870, 390, 870, 650, "tipo de reporte")
    flecha(1000, 345, 1090, 175, "definiciones")
    flecha(1215, 220, 1215, 300, "API externa")
    flecha(1215, 390, 1215, 470, "indicadores")
    flecha(1090, 510, 1000, 695, "metricas")
    flecha(740, 695, 650, 695, "respuesta JSON")
    flecha(650, 695, 390, 695, "respuesta al usuario")

    dibujo.rectangle(
        (20, 250, 1360, 780),
        outline=(150, 150, 150),
        width=2,
    )
    dibujo.text(
        (30, 805),
        "Contenedor Docker: FastAPI + LangGraph + dependencias",
        font=caja,
        fill=gris,
    )
    dibujo.text(
        (30, 830),
        "Clave de API: variable de entorno",
        font=normal,
        fill=gris,
    )

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(SALIDA)
    print(f"Diagrama generado: {SALIDA}")


if __name__ == "__main__":
    dibujar()
