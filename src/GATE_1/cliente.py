"""Cliente modular de Gemini con reintentos y registro de costos."""

import sys
from pathlib import Path
from typing import Any

# Soporta tanto la importación como paquete como la ejecución directa del archivo.
if __package__:
    from . import monolitico
    from .cliente_reintento import con_reintento
    from .costo import calcular_costo
else:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.GATE_1 import monolitico
    from src.GATE_1.cliente_reintento import con_reintento
    from src.GATE_1.costo import calcular_costo

INSTRUCCION_PREDETERMINADA = "Responde de forma clara y concisa."
costo_total_sesion = 0.0
# Se actualizan después de cada respuesta válida para que main muestre su resumen.
costo_ultima_operacion = 0.0
tokens_ultima_operacion = 0
PREGUNTAS_ENSAYO = (
    "¿Cuál es la capital de Chile?",
    "¿Cuál es la fórmula química del agua?",
    "¿Qué tipo de estrella es el Sol?",
    "¿Cuál es la velocidad aproximada de la luz?",
    "¿Cuál es el planeta más grande del sistema solar?",
    "¿Qué gas absorben las plantas durante la fotosíntesis?",
    "¿Cuántos lados tiene un hexágono?",
    "¿Cuál es el océano más grande de la Tierra?",
    "¿Quién escribió Don Quijote de la Mancha?",
    "¿Cuál es el satélite natural de la Tierra?",
)


class ServicioNoDisponibleError(RuntimeError):
    """No se pudo completar una operación tras agotar los reintentos."""


def _enviar_peticion_reintentable(url: str, cuerpo: dict[str, Any]) -> dict[str, Any]:
    """Clasifica los errores de Gemini para reintentar solo fallos transitorios."""
    try:
        return monolitico.enviar_peticion(url, cuerpo)
    except monolitico.GeminiHTTPError as error:
        # La autenticación y otros errores 4xx no se arreglan repitiendo la llamada.
        if error.status_code in (401, 403):
            raise ValueError(
                "Credencial inválida o sin permiso. Revisa tu GEMINI_API_KEY."
            ) from error
        if error.status_code == 429 or error.status_code >= 500:
            raise TimeoutError(
                "El proveedor no pudo procesar la petición. Hay que esperar y reintentar."
            ) from error
        raise
    except (monolitico.GeminiTimeoutError, monolitico.GeminiConnectionError) as error:
        raise TimeoutError(
            "No se pudo contactar al proveedor. Puede ser momentáneo."
        ) from error


def registrar_costo(respuesta: dict[str, Any]) -> float:
    """Calcula el costo de una operación y lo suma al total de la sesión."""
    global costo_total_sesion, costo_ultima_operacion, tokens_ultima_operacion
    # Reutiliza el validador del cliente Gemini para no inventar valores de tokens.
    uso = monolitico.extraer_metadatos_uso(respuesta)
    # El cálculo compartido valida los contadores y aplica las tarifas del modelo.
    costo_operacion = calcular_costo(respuesta)
    costo_total_sesion += costo_operacion
    costo_ultima_operacion = costo_operacion
    tokens_ultima_operacion = uso["totalTokenCount"]
    return costo_operacion


def consultar_modelo(
    pregunta: str,
    system_instruction: str = INSTRUCCION_PREDETERMINADA,
) -> str:
    """Consulta Gemini, reintenta fallos transitorios y registra el costo."""
    url, cuerpo = monolitico.armar_peticion(pregunta, system_instruction)
    try:
        respuesta = con_reintento(
            lambda: _enviar_peticion_reintentable(url, cuerpo)
        )
    except TimeoutError as error:
        raise ServicioNoDisponibleError(
            "El servicio no respondió tras varios intentos. Intenta más tarde."
        ) from error

    # Solo se contabiliza una respuesta procesada correctamente.
    texto = monolitico.extraer_texto(respuesta)
    registrar_costo(respuesta)
    return texto


def ejecutar_ensayo() -> int:
    """Ejecuta las diez consultas de prueba e informa costos por operación."""
    global costo_total_sesion, costo_ultima_operacion, tokens_ultima_operacion
    costo_total_sesion = 0.0
    costo_ultima_operacion = 0.0
    tokens_ultima_operacion = 0
    fallos = 0

    for indice, pregunta in enumerate(PREGUNTAS_ENSAYO):
        try:
            respuesta = consultar_modelo(pregunta)
        except ServicioNoDisponibleError as error:
            # Un fallo transitorio agotado afecta esta pregunta, no las siguientes.
            print(f"Respuesta {indice} falló definitivamente: {error}")
            fallos += 1
            continue
        except (monolitico.GeminiError, ValueError) as error:
            # Errores de configuración, autenticación o respuesta inválida se reportan.
            print(f"Error en respuesta {indice}: {error}", file=sys.stderr)
            fallos += 1
            break

        print(f"Respuesta {indice}: {respuesta[:40]}...")
        # Muestra el uso reportado por Gemini y los costos de esta operación y el total.
        print(
            f"Operación: {tokens_ultima_operacion} tokens, "
            f"costo estimado: ${costo_ultima_operacion:.5f} "
            f"(acumulado: ${costo_total_sesion:.5f})"
        )

    print(f"Costo total del ensayo: ${costo_total_sesion:.5f}")
    return 1 if fallos else 0


def main() -> int:
    """Ejecuta una consulta de ejemplo y muestra el costo acumulado."""
    try:
        respuesta = consultar_modelo("¿Cuál es la capital de Chile?")
    except (
        monolitico.GeminiError,
        ServicioNoDisponibleError,
        ValueError,
    ) as error:
        # Informa el fallo sin exponer la clave ni ocultar la causa del error.
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(respuesta)
    print(f"Costo acumulado de la sesión: ${costo_total_sesion:.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
