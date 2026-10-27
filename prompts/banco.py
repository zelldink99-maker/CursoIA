"""Prueba prompts de salida estructurada y guarda un resumen JSON."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.GATE_1.monolitico import (  # noqa: E402
    GeminiError,
    armar_peticion,
    enviar_peticion,
    extraer_texto,
)

INTENTOS_POR_PROMPT = 3
PAUSA_ENTRE_INTENTOS = 1
# El reporte se guarda junto al banco, independientemente de la carpeta actual.
ARCHIVO_RESULTADOS = Path(__file__).resolve().with_name("registro_resultados.json")

# Cada elemento define el texto de prueba y las claves que debe producir Gemini.
BANCO_DE_PROMPTS = [
    {
        "nombre": "extraccion_contacto",
        "system_instruction": (
            "Extrae del texto los datos solicitados. Devuelve únicamente un "
            "objeto JSON válido, sin explicaciones."
        ),
        "ejemplo_usuario": (
            "Extrae nombre, ciudad y profesión de este texto: "
            "Lucía Pérez vive en Chile y trabaja como diseñadora."
        ),
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "nombre": {"type": "STRING"},
                "ciudad": {"type": "STRING"},
                "profesion": {"type": "STRING"},
            },
            "required": ["nombre", "ciudad", "profesion"],
        },
        "claves_esperadas": ["nombre", "ciudad", "profesion"],
    },
    {
        "nombre": "clasificacion_sentimiento",
        "system_instruction": (
            "Clasifica el sentimiento del texto. Devuelve únicamente un objeto "
            "JSON válido."
        ),
        "ejemplo_usuario": (
            "Clasifica el sentimiento de este comentario: "
            "El producto llegó rápido y funciona perfectamente."
        ),
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "sentimiento": {"type": "STRING"},
                "motivo": {"type": "STRING"},
            },
            "required": ["sentimiento", "motivo"],
        },
        "claves_esperadas": ["sentimiento", "motivo"],
    },
    {
        "nombre": "resumen_texto",
        "system_instruction": (
            "Resume el contenido solicitado. Devuelve únicamente un objeto "
            "JSON válido."
        ),
        "ejemplo_usuario": (
            "Resume en una oración: Las abejas polinizan muchas plantas y "
            "contribuyen a la producción de alimentos."
        ),
        "response_schema": {
            "type": "OBJECT",
            "properties": {"resumen": {"type": "STRING"}},
            "required": ["resumen"],
        },
        "claves_esperadas": ["resumen"],
    },
]


def parsear_respuesta_json(texto: str) -> dict[str, object]:
    """Convierte la respuesta del modelo en un objeto JSON."""
    if not isinstance(texto, str):
        raise ValueError("la respuesta debe ser texto")
    contenido = texto.strip()
    # Algunos modelos envuelven el JSON en bloques Markdown; se quitan antes del parseo.
    if contenido.startswith("```"):
        lineas = contenido.splitlines()
        if lineas and lineas[0].startswith("```"):
            lineas = lineas[1:]
        if lineas and lineas[-1].strip() == "```":
            lineas = lineas[:-1]
        contenido = "\n".join(lineas).strip()

    try:
        datos = json.loads(contenido)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"la respuesta no contiene JSON válido: {error.msg}"
        ) from error

    if not isinstance(datos, dict):
        raise ValueError("la respuesta JSON debe ser un objeto")
    return datos


def es_consistente(
    respuestas: list[dict[str, object]],
    intentos: int = INTENTOS_POR_PROMPT,
) -> bool:
    """Indica si todos los intentos produjeron la misma respuesta JSON válida."""
    return (
        intentos > 0
        and len(respuestas) == intentos
        and all(respuesta == respuestas[0] for respuesta in respuestas[1:])
    )


def _armar_peticion_prompt(prompt: dict[str, object]) -> tuple[str, dict[str, object]]:
    """Añade la instrucción y el esquema al cuerpo creado por el cliente Gemini."""
    if not isinstance(prompt, dict):
        raise ValueError("cada prompt debe ser un objeto")
    pregunta = prompt.get("ejemplo_usuario")
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("ejemplo_usuario debe ser texto")

    instruccion = prompt.get("system_instruction")
    if not isinstance(instruccion, str) or not instruccion.strip():
        raise ValueError("system_instruction debe ser texto no vacío")

    url, cuerpo = armar_peticion(pregunta, instruccion)

    esquema = prompt.get("response_schema")
    if esquema is not None:
        if not isinstance(esquema, dict):
            raise ValueError("response_schema debe ser un objeto")
        # Solicita JSON y comunica al endpoint la forma esperada de la respuesta.
        cuerpo["generationConfig"] = {
            "responseMimeType": "application/json",
            "responseSchema": esquema,
        }

    return url, cuerpo


def main() -> int:
    """Ejecuta los prompts, registra resultados y devuelve un código de salida."""
    registro: dict[str, dict[str, object]] = {}

    try:
        # Cada prompt se evalúa varias veces para resumir su consistencia.
        for prompt in BANCO_DE_PROMPTS:
            if not isinstance(prompt, dict):
                raise ValueError("cada prompt del banco debe ser un objeto")
            respuestas_validas: list[dict[str, object]] = []
            nombre = prompt.get("nombre")
            claves_esperadas = prompt.get("claves_esperadas")
            if not isinstance(nombre, str) or not nombre.strip():
                raise ValueError("cada prompt debe tener un nombre no vacío")
            if not isinstance(claves_esperadas, list) or not all(
                isinstance(clave, str) and clave for clave in claves_esperadas
            ):
                raise ValueError(
                    f"claves_esperadas debe ser una lista de textos para {nombre}"
                )

            for intento in range(1, INTENTOS_POR_PROMPT + 1):
                url, cuerpo = _armar_peticion_prompt(prompt)
                respuesta = enviar_peticion(url, cuerpo)
                texto = extraer_texto(respuesta)

                try:
                    datos = parsear_respuesta_json(texto)
                    # Cuenta el intento como válido solo si están todas las claves requeridas.
                    faltantes = [
                        clave for clave in claves_esperadas if clave not in datos
                    ]
                    if faltantes:
                        print(
                            f"  intento {intento} falló: faltan las claves "
                            f"{', '.join(faltantes)}"
                        )
                    else:
                        respuestas_validas.append(datos)
                except ValueError as error:
                    print(f"  intento {intento} falló: {error}")

                if intento < INTENTOS_POR_PROMPT:
                    time.sleep(PAUSA_ENTRE_INTENTOS)

            exitos = len(respuestas_validas)
            consistente = es_consistente(respuestas_validas)
            print(f"{nombre}: {exitos}/{INTENTOS_POR_PROMPT} respuestas válidas")
            print(f"  Consistente: {'sí' if consistente else 'no'}")
            registro[nombre] = {
                "exitos": exitos,
                "intentos": INTENTOS_POR_PROMPT,
                "consistente": consistente,
                "pregunta": prompt["ejemplo_usuario"],
                "respuestas": respuestas_validas,
            }

    except (GeminiError, ValueError, TypeError) as error:
        print(f"Error al ejecutar el banco de prompts: {error}", file=sys.stderr)
        return 1

    try:
        # write_text crea o reemplaza el archivo de resultados en una sola operación.
        ARCHIVO_RESULTADOS.write_text(
            json.dumps(registro, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        print(f"No se pudo guardar el reporte: {error}", file=sys.stderr)
        return 1

    print(f"Resultados guardados en: {ARCHIVO_RESULTADOS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
