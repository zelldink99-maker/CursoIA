"""Revisa los módulos de GATE_1 y genera un reporte local o una prueba API opcional."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Optional
from unittest.mock import Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GATE_DIR = Path(__file__).resolve().parent
# Permite importar el paquete cuando el verificador se inicia desde cualquier carpeta.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(GATE_DIR) not in sys.path:
    sys.path.insert(0, str(GATE_DIR))

# Este catálogo sirve como guía de lectura y se imprime antes de las pruebas.
# Cada entrada describe lo que hace el módulo y el comportamiento que se espera.
MODULES = {
    "aritmetica.py": (
        "Realiza operaciones aritméticas básicas.",
        "La división por cero se rechaza explícitamente.",
    ),
    "api_test.py": (
        "Hace una petición sencilla a Gemini para comprobar el endpoint.",
        "Con una clave válida, Gemini devuelve una respuesta HTTP exitosa con texto.",
    ),
    "consumir_gemini.py": (
        "Interfaz de compatibilidad que delega en el cliente principal.",
        "Mantiene la extracción previa y comparte validación, reintentos y costos.",
    ),
    "pipeline_texto.py": (
        "Limpia y tokeniza texto, y calcula coincidencias, precisión, cobertura y F1.",
        "La limpieza conserva tildes/números; las métricas cuentan repeticiones.",
    ),
    "evaluar_salidas.py": (
        "Compara la respuesta del modelo con una referencia antes y después de limpiar.",
        "El script imprime las métricas crudas y procesadas sin depender de la API real.",
    ),
    "evaluar_metricas.py": (
        "Evalúa respuestas por lote con precisión, cobertura y F1 y guarda resultados JSON.",
        "Conserva las respuestas generadas y permite priorizar casos con F1 bajo.",
    ),
    "revisar_cualitativamente.py": (
        "Prepara y valida una muestra de revisión para la actividad core del Bloque 17.",
        "Comprueba 20 resultados, 10 calificaciones justificadas y límites documentados.",
    ),
    "cadena_tres_pasos.py": (
        "Encadena extracción, simplificación y formato con LangChain.",
        "Tres pasos usan StrOutputParser y permiten inyectar un modelo simulado.",
    ),
    "enrutamiento.py": (
        "Clasifica mensajes y los enruta a una respuesta según su categoría.",
        "Normaliza la categoría, cubre tres rutas y usa pregunta como ruta por defecto.",
    ),
    "agente_con_herramientas.py": (
        "Agente de soporte con herramientas estructuradas y memoria por sesión.",
        "Valida argumentos, conserva historial y separa sesiones de conversación.",
    ),
    "indexar_corpus.py": (
        "Divide e indexa documentación en un vector store Chroma persistente.",
        "Crea al menos cinco chunks con metadatos y permite reconectar al índice.",
    ),
    "configuracion.py": (
        "Carga y valida el modelo Gemini compartido desde la variable modeloIA.",
        "Todos los clientes usan el mismo modelo seleccionado en .env.",
    ),
    "replica_corpus_ejemplo.py": (
        "Replica el chunking y la indexación de un corpus de devoluciones aislado.",
        "Produce cinco chunks íntegros de 490 caracteres antes de llamar a Gemini.",
    ),
    "cliente.py": (
        "Cliente modular con clasificación de errores y registro de costos.",
        "Devuelve texto, reintenta fallos transitorios y acumula el costo por operación.",
    ),
    "cliente_reintento.py": (
        "Controla reintentos con backoff exponencial, techo y jitter.",
        "Solo repite TimeoutError y propaga el error al agotarse los intentos.",
    ),
    "costo.py": (
        "Calcula el costo estimado desde los tokens de entrada/salida y sus tarifas.",
        "Con los tokens de ejemplo del módulo, el costo calculado coincide con la fórmula.",
    ),
    "latencia.py": (
        "Mide varias solicitudes y calcula el promedio de latencia y costo final.",
        "Con dos respuestas simuladas, registra dos tiempos y devuelve un promedio no negativo.",
    ),
    "main.py": (
        "Lanzador compatible que delega en el cliente modular de producción.",
        "Una consulta simulada devuelve texto y muestra el costo acumulado.",
    ),
    "module_test.py": (
        "Prueba el envío de una petición usando las funciones de peticiones.py.",
        "Con una clave válida, la API devuelve una respuesta; requiere conexión real.",
    ),
    "monolitico.py": (
        "Prepara y envía una solicitud a Gemini en una implementación simple.",
        "La petición incluye autenticación segura y devuelve el JSON de Gemini.",
    ),
    "peticiones.py": (
        "Construye el cuerpo y encabezados HTTP y envía una petición POST.",
        "El cuerpo conserva la pregunta, la clave va en un encabezado y se recibe texto.",
    ),
    "prompts/banco.py": (
        "Ejecuta un banco de prompts estructurados y registra resultados JSON.",
        "La respuesta JSON se valida y la solicitud incorpora instrucciones y esquema.",
    ),
    "test.py": (
        "Confirma que Python puede ejecutar un script sencillo.",
        "El script imprime un saludo y termina correctamente.",
    ),
}


class Reporte:
    """Acumula comprobaciones y presenta estados legibles sin revelar secretos."""

    def __init__(self) -> None:
        self.resultados: list[tuple[str, str, Optional[bool], str]] = []

    def agregar(
        self, grupo: str, nombre: str, correcto: Optional[bool], detalle: str
    ) -> None:
        """Registra una comprobación y muestra su estado en el reporte."""
        self.resultados.append((grupo, nombre, correcto, detalle))
        estado = (
            "BIEN" if correcto is True else "MAL" if correcto is False else "OMITIDO"
        )
        print(f"  [{estado}] {nombre}: {detalle}")

    @property
    def fallo(self) -> bool:
        """Indica si alguna comprobación terminó con error."""
        return any(correcto is False for _, _, correcto, _ in self.resultados)

    def estado_grupo(self, grupo: str) -> Optional[bool]:
        """Resume un grupo; None significa que quedó pendiente o no se ejecutó."""
        estados = [
            correcto
            for nombre_grupo, _, correcto, _ in self.resultados
            if nombre_grupo == grupo
        ]
        if any(estado is False for estado in estados):
            return False
        if estados and all(estado is True for estado in estados):
            return True
        return None


def _codigo_salida(reporte: Reporte) -> int:
    """Falla si hay errores o si la actividad core sigue pendiente."""
    actividad_core = reporte.estado_grupo("Actividad core Bloque 17")
    return 1 if reporte.fallo or actividad_core is not True else 0


def _importar_modulos() -> dict[str, object]:
    """Importa módulos sin lanzar los scripts que hacen llamadas al importarse."""
    from src.GATE_1 import (
        agente_con_herramientas,
        api_test,
        aritmetica,
        cadena_tres_pasos,
        cliente,
        cliente_reintento,
        consumir_gemini,
        configuracion,
        costo,
        enrutamiento,
        evaluar_metricas,
        evaluar_salidas,
        indexar_corpus,
        latencia,
        main,
        module_test,
        monolitico,
        peticiones,
        pipeline_texto,
        replica_corpus_ejemplo,
        revisar_cualitativamente,
    )
    from prompts import banco as banco_prompts

    return {
        "agente_con_herramientas": agente_con_herramientas,
        "api_test": api_test,
        "aritmetica": aritmetica,
        "cadena_tres_pasos": cadena_tres_pasos,
        "cliente": cliente,
        "cliente_reintento": cliente_reintento,
        "consumir_gemini": consumir_gemini,
        "configuracion": configuracion,
        "costo": costo,
        "enrutamiento": enrutamiento,
        "evaluar_metricas": evaluar_metricas,
        "evaluar_salidas": evaluar_salidas,
        "indexar_corpus": indexar_corpus,
        "latencia": latencia,
        "main": main,
        "module_test": module_test,
        "monolitico": monolitico,
        "peticiones": peticiones,
        "pipeline_texto": pipeline_texto,
        "replica_corpus_ejemplo": replica_corpus_ejemplo,
        "revisar_cualitativamente": revisar_cualitativamente,
        "banco_prompts": banco_prompts,
    }


def _revisar_sintaxis(reporte: Reporte) -> None:
    """Analiza los módulos del Gate 1 sin ejecutarlos."""
    archivos = [
        (
            nombre,
            (
                PROJECT_ROOT / nombre
                if nombre.startswith("prompts/")
                else GATE_DIR / nombre
            ),
        )
        for nombre in MODULES
    ]
    archivos.append(("revision_gate_1.py", Path(__file__)))
    for nombre, ruta in archivos:
        try:
            ast.parse(ruta.read_text(encoding="utf-8-sig"), filename=str(ruta))
        except (OSError, SyntaxError, UnicodeError) as error:
            reporte.agregar(nombre, "Sintaxis", False, str(error))
        else:
            reporte.agregar(nombre, "Sintaxis", True, "archivo Python válido")


def _revisar_dependencias(reporte: Reporte) -> None:
    """Comprueba las dependencias declaradas y la versión mínima de Python."""
    requirements = PROJECT_ROOT / "requirements.txt"
    if not requirements.is_file():
        reporte.agregar("Entorno reproducible", "requirements.txt", False, "no existe")
        return

    try:
        contenido = requirements.read_bytes()
        codificacion = (
            "utf-16"
            if contenido.startswith((b"\xff\xfe", b"\xfe\xff"))
            else "utf-8-sig"
        )
        lineas = contenido.decode(codificacion).splitlines()
    except (OSError, UnicodeError) as error:
        reporte.agregar(
            "Entorno reproducible",
            "requirements.txt",
            False,
            f"no se pudo leer el archivo: {error}",
        )
        return

    declaradas: set[str] = set()
    for linea in lineas:
        entrada = linea.strip()
        if entrada and not entrada.startswith("#"):
            # Compara el nombre de la distribución (p. ej. python-dotenv),
            # no el nombre del módulo que luego se importa (dotenv).
            declaradas.add(re.split(r"[<>=!~]", entrada, maxsplit=1)[0].lower())

    paquetes = {
        "requests": "requests",
        "python-dotenv": "dotenv",
        "langchain": "langchain_core",
        "langchain-classic": "langchain_classic",
        "langchain-google-genai": "langchain_google_genai",
        "langchain-text-splitters": "langchain_text_splitters",
        "langchain-chroma": "langchain_chroma",
        "chromadb": "chromadb",
        "pydantic": "pydantic",
    }
    faltantes = [
        distribucion
        for distribucion, modulo in paquetes.items()
        if distribucion not in declaradas or importlib.util.find_spec(modulo) is None
    ]
    if faltantes:
        reporte.agregar(
            "Entorno reproducible",
            "Dependencias",
            False,
            "faltan en requirements.txt o no están instaladas: " + ", ".join(faltantes),
        )
    else:
        reporte.agregar(
            "Entorno reproducible",
            "Dependencias",
            True,
            "requests, python-dotenv, LangChain, langchain-classic y los "
            "conectores de Gemini, text-splitters y Chroma están declarados "
            "e instalados",
        )

    version_ok = sys.version_info >= (3, 10)
    reporte.agregar(
        "Entorno reproducible",
        "Versión de Python",
        version_ok,
        f"{sys.version_info.major}.{sys.version_info.minor}"
        + (" (mínimo: 3.10)" if version_ok else " (se requiere 3.10 o superior)"),
    )


def _revisar_credenciales(reporte: Reporte) -> str:
    """Revisa la configuración y evita mostrar el valor de la clave API."""
    if importlib.util.find_spec("dotenv") is not None:
        from dotenv import load_dotenv

        # Carga la configuración local si python-dotenv está disponible.
        load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
    archivo_ignore = PROJECT_ROOT / ".gitignore"
    # git check-ignore confirma la regla efectiva, no solo el texto del .gitignore.
    try:
        ignorado = (
            subprocess.run(
                ["git", "check-ignore", "--no-index", "--quiet", ".env"],
                cwd=PROJECT_ROOT,
                check=False,
                capture_output=True,
                text=True,
            ).returncode
            == 0
        )
    except OSError:
        ignorado = False
    reporte.agregar(
        "Credenciales no expuestas",
        ".env excluido por Git",
        ignorado and archivo_ignore.is_file(),
        (
            "Git ignora .env"
            if ignorado
            else ".env no está confirmado como ignorado por Git"
        ),
    )

    # Busca patrones de claves incrustadas en los scripts de este Gate.
    # Si un archivo no puede leerse, el resultado se considera inseguro.
    clave_en_codigo = False
    patron_clave_google = re.compile(r"AIza[0-9A-Za-z_-]{20,}")
    for ruta in GATE_DIR.glob("*.py"):
        try:
            clave_en_codigo |= bool(
                patron_clave_google.search(ruta.read_text(encoding="utf-8-sig"))
            )
        except (OSError, UnicodeError):
            clave_en_codigo = True
    reporte.agregar(
        "Credenciales no expuestas",
        "Sin claves literales en scripts",
        not clave_en_codigo,
        (
            "no se encontraron claves incrustadas"
            if not clave_en_codigo
            else "se encontró una posible clave API en un archivo .py"
        ),
    )

    valor = os.getenv("GEMINI_API_KEY", "").strip()
    if not valor:
        reporte.agregar(
            "API funciona",
            "Clave configurada",
            False,
            "falta GEMINI_API_KEY en el entorno o en el archivo .env",
        )
        return ""
    if valor == "tu_llave_aqui":
        reporte.agregar(
            "API funciona",
            "Clave configurada",
            False,
            "GEMINI_API_KEY conserva el valor de ejemplo",
        )
        return ""

    reporte.agregar(
        "API funciona",
        "Clave configurada",
        True,
        "GEMINI_API_KEY está disponible; el valor no se muestra",
    )
    return valor


def _revisar_peticiones(reporte: Reporte, modulos: dict[str, object]) -> None:
    """Verifica la preparación y el envío HTTP reemplazando la red por un mock."""
    peticiones = modulos["peticiones"]
    prompt = "pregunta de prueba"
    cuerpo = json.loads(peticiones.create_payload(prompt))
    headers = peticiones.create_headers("clave-de-prueba")
    llamada = Mock()
    llamada.text = '{"respuesta":"simulada"}'
    # Sustituye la llamada HTTP: estas comprobaciones nunca contactan al servicio.
    with patch.object(peticiones.requests, "request", return_value=llamada) as request:
        resultado = peticiones.make_request(
            "https://example.invalid/generateContent",
            headers,
            peticiones.create_payload(prompt),
        )
    with patch.object(
        peticiones.requests,
        "request",
        side_effect=peticiones.requests.ConnectionError("fallo simulado"),
    ):
        resultado_error = peticiones.make_request(
            "https://example.invalid/generateContent",
            headers,
            peticiones.create_payload(prompt),
        )
    cuerpo_ok = cuerpo == {"contents": [{"parts": [{"text": prompt}]}]}
    request_ok = (
        resultado == llamada.text
        and request.call_args.kwargs["headers"]["x-goog-api-key"] == "clave-de-prueba"
        and request.call_args.kwargs["data"] == peticiones.create_payload(prompt)
        and resultado_error.startswith("Error:")
    )
    correcto = (
        cuerpo_ok and headers.get("x-goog-api-key") == "clave-de-prueba" and request_ok
    )
    reporte.agregar(
        "peticiones.py",
        "Cuerpo, encabezado y envío simulados",
        correcto,
        (
            "la solicitud usa encabezado seguro y comunica errores de conexión"
            if correcto
            else "falló la comprobación del cuerpo, encabezado, envío o error HTTP"
        ),
    )


def _revisar_costo(reporte: Reporte, modulos: dict[str, object]) -> None:
    """Compara el cálculo del módulo con un resultado conocido."""
    # Los tokens de pensamiento se cobran como tokens de salida.
    datos = {
        "usageMetadata": {
            "promptTokenCount": 850,
            "candidatesTokenCount": 320,
            "thoughtsTokenCount": 7,
            "totalTokenCount": 1177,
        }
    }
    tarifa_entrada = modulos["costo"].PRECIO_ENTRADA_POR_TOKEN
    tarifa_salida = modulos["costo"].PRECIO_SALIDA_POR_TOKEN
    esperado = 850 * tarifa_entrada + (320 + 7) * tarifa_salida
    obtenido = modulos["costo"].calcular_costo(datos)
    tarifa_publicada_ok = (
        modulos["costo"].MODELO_TARIFADO
        in modulos["configuracion"].MODELOS_IA_PERMITIDOS
        and modulos["costo"].PRECIO_ENTRADA_USD_POR_MILLON == 0.75
        and modulos["costo"].PRECIO_SALIDA_USD_POR_MILLON == 3.75
    )
    url, _ = modulos["monolitico"].armar_peticion("prueba", "Responde brevemente.")
    modelo_solicitud_ok = modulos["costo"].MODELO_TARIFADO in url
    reporte.agregar(
        "costo.py",
        "Tarifa publicada y cálculo por uso",
        tarifa_publicada_ok
        and modelo_solicitud_ok
        and abs(obtenido - esperado) < 1e-12,
        f"{modulos['costo'].MODELO_TARIFADO}: esperado ${esperado:.8f}; "
        f"obtenido ${obtenido:.8f}",
    )


def _revisar_validaciones(reporte: Reporte, modulos: dict[str, object]) -> None:
    """Comprueba que varias entradas inválidas se rechacen explícitamente."""
    # Cada caso debe lanzar el error previsto; no basta con que la función termine.
    try:
        modulos["aritmetica"].dividir(10, 0)
    except ZeroDivisionError:
        division_por_cero_rechazada = True
    else:
        division_por_cero_rechazada = False

    try:
        modulos["costo"].calcular_costo({}, 0.1, 0.2)
    except ValueError:
        metadatos_invalidos_rechazados = True
    else:
        metadatos_invalidos_rechazados = False

    try:
        modulos["latencia"].Latencia(pregunta=None)
    except ValueError:
        pregunta_invalida_rechazada = True
    else:
        pregunta_invalida_rechazada = False

    try:
        modulos["banco_prompts"].parsear_respuesta_json(None)
    except ValueError:
        respuesta_invalida_rechazada = True
    else:
        respuesta_invalida_rechazada = False

    correcto = all(
        (
            division_por_cero_rechazada,
            metadatos_invalidos_rechazados,
            pregunta_invalida_rechazada,
            respuesta_invalida_rechazada,
        )
    )
    reporte.agregar(
        "Validación de errores",
        "Entradas inválidas en módulos locales",
        correcto,
        (
            "división, metadatos, latencia y JSON rechazan entradas inválidas"
            if correcto
            else "una o más entradas inválidas no se rechazaron explícitamente"
        ),
    )


def _revisar_cliente(reporte: Reporte, modulos: dict[str, object]) -> None:
    """Comprueba extracción de texto y rechazo de preguntas vacías localmente."""
    cliente = modulos["consumir_gemini"]
    texto = cliente._extraer_texto(
        {
            "candidates": [
                {"content": {"parts": [{"text": "respuesta"}, {"text": " lista"}]}}
            ]
        }
    )
    formato_ok = texto == "respuesta lista"
    try:
        cliente.obtener_dato_de_prueba("   ")
    except ValueError:
        pregunta_vacia_rechazada = True
    else:
        pregunta_vacia_rechazada = False

    with patch.object(
        cliente.cliente,
        "consultar_modelo",
        return_value="simulada",
    ) as consulta:
        respuesta = cliente.obtener_dato_de_prueba("pregunta válida")
    delegacion_ok = respuesta == "simulada" and consulta.call_args.args == (
        "pregunta válida",
    )
    correcto = formato_ok and pregunta_vacia_rechazada and delegacion_ok
    reporte.agregar(
        "consumir_gemini.py",
        "Compatibilidad y delegación al cliente principal",
        correcto,
        (
            "conserva extracción y validación, y comparte el cliente de producción"
            if correcto
            else "falló la extracción, el rechazo de pregunta vacía o la delegación"
        ),
    )


def _revisar_cliente_modular(reporte: Reporte, modulos: dict[str, object]) -> None:
    """Comprueba consulta, clasificación HTTP, backoff y costos sin usar la red."""
    cliente = modulos["cliente"]
    reintentos = modulos["cliente_reintento"]
    respuesta = {
        "candidates": [
            {"content": {"parts": [{"text": "Santiago es la capital de Chile."}]}}
        ],
        "usageMetadata": {
            "promptTokenCount": 100,
            "candidatesTokenCount": 20,
            "totalTokenCount": 120,
        },
    }

    # Aísla el acumulador para que el resultado no dependa de llamadas anteriores.
    with patch.object(cliente, "costo_total_sesion", 0.0):
        with patch.object(cliente.monolitico, "enviar_peticion", return_value=respuesta):
            texto = cliente.consultar_modelo("¿Cuál es la capital de Chile?")
        costo_esperado = cliente.calcular_costo(respuesta)
        costo_acumulado_ok = abs(cliente.costo_total_sesion - costo_esperado) < 1e-12

        credencial_rechazada = True
        credencial_sin_reintento = True
        # Los errores de autenticación son permanentes y deben fallar sin reintentar.
        for codigo in (401, 403):
            with patch.object(
                cliente.monolitico,
                "enviar_peticion",
                side_effect=cliente.monolitico.GeminiHTTPError(
                    codigo, "sin permiso"
                ),
            ) as solicitud:
                try:
                    cliente.consultar_modelo("pregunta")
                except ValueError as error:
                    credencial_rechazada &= "GEMINI_API_KEY" in str(error)
                else:
                    credencial_rechazada = False
            credencial_sin_reintento &= solicitud.call_count == 1

        # Un límite de uso (429) debe dar lugar a un reintento tras la espera.
        with patch.object(
            cliente.monolitico,
            "enviar_peticion",
            side_effect=[
                cliente.monolitico.GeminiHTTPError(429, "límite"),
                respuesta,
            ],
        ) as solicitud:
            with patch.object(reintentos.time, "sleep") as dormir:
                with patch.object(reintentos.random, "uniform", return_value=0.0):
                    texto_reintentado = cliente.consultar_modelo("pregunta")
        rate_limit_reintentado = (
            solicitud.call_count == 2
            and dormir.call_count == 1
            and texto_reintentado == "Santiago es la capital de Chile."
        )

        # Un error de solicitud (400) es permanente y no debe repetirse.
        with patch.object(
            cliente.monolitico,
            "enviar_peticion",
            side_effect=cliente.monolitico.GeminiHTTPError(400, "solicitud inválida"),
        ) as solicitud:
            try:
                cliente.consultar_modelo("pregunta")
            except cliente.monolitico.GeminiHTTPError:
                error_permanente_no_reintentado = solicitud.call_count == 1
            else:
                error_permanente_no_reintentado = False

        # Un error de servicio (503) es transitorio y se puede reintentar.
        with patch.object(
            cliente.monolitico,
            "enviar_peticion",
            side_effect=[
                cliente.monolitico.GeminiHTTPError(503, "servicio ocupado"),
                respuesta,
            ],
        ) as solicitud:
            with patch.object(reintentos.time, "sleep") as dormir:
                with patch.object(reintentos.random, "uniform", return_value=0.0):
                    texto_503 = cliente.consultar_modelo("pregunta")
        servicio_transitorio_reintentado = (
            solicitud.call_count == 2
            and dormir.call_count == 1
            and texto_503 == "Santiago es la capital de Chile."
        )

        # También se reintentan fallos de conexión y tiempos de espera.
        errores_red_reintentados = True
        for error_red in (
            cliente.monolitico.GeminiTimeoutError("timeout simulado"),
            cliente.monolitico.GeminiConnectionError("conexión simulada"),
        ):
            with patch.object(
                cliente.monolitico,
                "enviar_peticion",
                side_effect=[error_red, respuesta],
            ) as solicitud:
                with patch.object(reintentos.time, "sleep"):
                    with patch.object(
                        reintentos.random, "uniform", return_value=0.0
                    ):
                        resultado_red = cliente.consultar_modelo("pregunta")
            errores_red_reintentados &= (
                solicitud.call_count == 2
                and resultado_red == "Santiago es la capital de Chile."
            )

        # Al agotar los intentos, el cliente comunica el fallo como RuntimeError.
        with patch.object(
            cliente,
            "_enviar_peticion_reintentable",
            side_effect=TimeoutError("fallo transitorio"),
        ) as enviar:
            with patch.object(reintentos.time, "sleep"):
                with patch.object(reintentos.random, "uniform", return_value=0.0):
                    try:
                        cliente.consultar_modelo("pregunta")
                    except RuntimeError as error:
                        reintentos_agotados = "varios intentos" in str(error)
                    else:
                        reintentos_agotados = False
        intentos_agotados_correctos = enviar.call_count == 3

    # Fuerza el mayor jitter para verificar el cálculo y el límite de espera.
    with patch.object(reintentos.time, "sleep") as dormir:
        with patch.object(
            reintentos.random,
            "uniform",
            side_effect=lambda minimo, maximo: maximo,
        ):
            intentos_backoff = 0

            def operacion_transitoria() -> str:
                nonlocal intentos_backoff
                intentos_backoff += 1
                if intentos_backoff < 4:
                    raise TimeoutError("fallo simulado")
                return "ok"

            resultado_backoff = reintentos.con_reintento(
                operacion_transitoria,
                intentos=4,
                espera_base=2,
                espera_maxima=5,
            )
    esperas = [llamada.args[0] for llamada in dormir.call_args_list]
    backoff_correcto = (
        resultado_backoff == "ok"
        and esperas == [2.2, 4.4, 5.0]
        and max(esperas) <= 5
    )

    # Comprueba el manejo del error por la interfaz de consola, sin llamar a Gemini.
    with patch.object(
        cliente,
        "consultar_modelo",
        side_effect=cliente.ServicioNoDisponibleError("fallo simulado"),
    ):
        with redirect_stderr(StringIO()) as salida_error:
            codigo_error = cliente.main()
    manejo_error_publico = (
        codigo_error == 1 and "fallo simulado" in salida_error.getvalue()
    )

    # main() debe hacer una consulta y mostrar el costo acumulado al terminar.
    with patch.object(cliente, "costo_total_sesion", 0.00008):
        with patch.object(cliente, "consultar_modelo", return_value="Santiago") as consulta:
            with redirect_stdout(StringIO()) as salida_principal:
                codigo_principal = cliente.main()
    bloque_principal_correcto = (
        codigo_principal == 0
        and consulta.call_count == 1
        and "Santiago" in salida_principal.getvalue()
        and "Costo acumulado de la sesión: $0.00008" in salida_principal.getvalue()
    )

    # La simulación actualiza el costo igual que una respuesta recibida del modelo.
    def consulta_ensayo_simulada(pregunta: str) -> str:
        """Registra uso simulado igual que una respuesta válida del proveedor."""
        cliente.registrar_costo(respuesta)
        return f"Respuesta simulada para {pregunta}, con texto adicional."

    with patch.object(
        cliente,
        "consultar_modelo",
        side_effect=consulta_ensayo_simulada,
    ) as consultar:
        with redirect_stdout(StringIO()) as salida_ensayo:
            codigo_ensayo = cliente.ejecutar_ensayo()
    lineas_ensayo = salida_ensayo.getvalue()
    ensayo_de_diez_correcto = (
        codigo_ensayo == 0
        and consultar.call_count == 10
        and "Respuesta 0:" in lineas_ensayo
        and "Respuesta 9:" in lineas_ensayo
        and "120 tokens, costo estimado: $0.00015" in lineas_ensayo
        and "(acumulado: $0.00150)" in lineas_ensayo
        and "Costo total del ensayo: $0.00150" in lineas_ensayo
    )

    correcto = all(
        (
            texto == "Santiago es la capital de Chile.",
            costo_acumulado_ok,
            credencial_rechazada,
            credencial_sin_reintento,
            rate_limit_reintentado,
            error_permanente_no_reintentado,
            servicio_transitorio_reintentado,
            errores_red_reintentados,
            reintentos_agotados,
            intentos_agotados_correctos,
            backoff_correcto,
            manejo_error_publico,
            bloque_principal_correcto,
            ensayo_de_diez_correcto,
        )
    )
    reporte.agregar(
        "cliente modular",
        "Errores, backoff y costos simulados",
        correcto,
        (
            "clasifica HTTP, aplica backoff acotado y registra costos reales"
            if correcto
            else "falló una comprobación de consulta, reintentos, techo o costo"
        ),
    )


def _revisar_monolitico(reporte: Reporte, modulos: dict[str, object]) -> None:
    """Comprueba el cliente simple con una respuesta HTTP simulada."""
    monolitico = modulos["monolitico"]
    clave = "clave-local-de-prueba"
    # La clave se inyecta solo durante la prueba y se verifica que no vaya en la URL.
    with patch.dict(os.environ, {"GEMINI_API_KEY": clave}):
        url, body = monolitico.armar_peticion("pregunta", "Responde brevemente.")
        respuesta = Mock()
        respuesta_json = {
            "candidates": [],
            "usageMetadata": {
                "promptTokenCount": 12,
                "candidatesTokenCount": 48,
                "totalTokenCount": 60,
            },
        }
        respuesta.json.return_value = respuesta_json
        with patch.object(monolitico.requests, "post", return_value=respuesta) as post:
            resultado = monolitico.enviar_peticion(url, body)
    llamada = post.call_args
    correcto = (
        clave not in url
        and llamada.kwargs["headers"].get("x-goog-api-key") == clave
        and llamada.kwargs["timeout"] > 0
        and resultado == respuesta_json
        and monolitico.extraer_metadatos_uso(resultado)
        == respuesta_json["usageMetadata"]
    )
    reporte.agregar(
        "monolitico.py",
        "Autenticación segura y respuesta simulada",
        correcto,
        (
            "la clave no aparece en la URL y se envía en el encabezado"
            if correcto
            else "la clave podría exponerse o la petición no cumplió lo esperado"
        ),
    )

    respuesta_demo = {
        "candidates": [{"content": {"parts": [{"text": "respuesta de prueba"}]}}],
        "usageMetadata": {
            "promptTokenCount": 12,
            "candidatesTokenCount": 48,
            "totalTokenCount": 60,
        },
    }
    with patch.object(monolitico, "enviar_peticion", return_value=respuesta_demo):
        with redirect_stdout(StringIO()) as salida:
            codigo_demo = monolitico.main()
    demo_ok = (
        codigo_demo == 0
        and "respuesta de prueba" in salida.getvalue()
        and "Tokens de entrada: 12" in salida.getvalue()
        and "Tokens de salida: 48" in salida.getvalue()
        and "Total: 60" in salida.getvalue()
    )
    reporte.agregar(
        "monolitico.py",
        "Presentación de tokens de respuesta",
        demo_ok,
        (
            "muestra tokens de entrada, salida y total"
            if demo_ok
            else "no se mostraron correctamente los metadatos de tokens"
        ),
    )

    try:
        monolitico.extraer_metadatos_uso({"candidates": []})
    except monolitico.GeminiResponseError:
        metadata_ausente_rechazada = True
    else:
        metadata_ausente_rechazada = False
    reporte.agregar(
        "monolitico.py",
        "Validación de metadatos de tokens",
        metadata_ausente_rechazada,
        (
            "informa explícitamente cuando falta usageMetadata"
            if metadata_ausente_rechazada
            else "no se rechazaron los metadatos de uso ausentes"
        ),
    )


def _revisar_latencia(reporte: Reporte, modulos: dict[str, object]) -> None:
    """Comprueba los intentos de latencia con respuestas simuladas."""
    latencia = modulos["latencia"]
    datos = {
        "usageMetadata": {
            "promptTokenCount": 2,
            "candidatesTokenCount": 3,
            "totalTokenCount": 5,
        }
    }
    # Las respuestas simuladas permiten comprobar cantidad y promedio sin red.
    with patch.object(latencia, "enviar_peticion", return_value=datos) as enviar:
        with redirect_stdout(StringIO()):
            promedio = latencia.Latencia(intentos=2).ejecutar()
    correcto = enviar.call_count == 2 and promedio >= 0
    reporte.agregar(
        "latencia.py",
        "Dos solicitudes simuladas",
        correcto,
        f"se hicieron {enviar.call_count} envíos; promedio {promedio:.4f} s",
    )


def _revisar_banco_prompts(reporte: Reporte, modulos: dict[str, object]) -> None:
    """Comprueba el parseo JSON y la construcción de prompts sin usar la red."""
    banco = modulos["banco_prompts"]
    datos = banco.parsear_respuesta_json('{"nombre":"Lucía","ciudad":"Chile"}')
    ejemplos_ok = len(banco.BANCO_DE_PROMPTS) == 3
    # La consistencia exige resultados iguales y también el número esperado de intentos.
    consistencia_ok = (
        banco.es_consistente([{"resultado": "igual"}] * banco.INTENTOS_POR_PROMPT)
        and not banco.es_consistente(
            [{"resultado": "igual"}, {"resultado": "distinto"}]
            + [{"resultado": "igual"}] * (banco.INTENTOS_POR_PROMPT - 2)
        )
        and not banco.es_consistente([{"resultado": "igual"}])
        and not banco.es_consistente([])
    )
    for ejemplo in banco.BANCO_DE_PROMPTS:
        url_ejemplo, cuerpo_ejemplo = banco._armar_peticion_prompt(ejemplo)
        pregunta_ejemplo = ejemplo["ejemplo_usuario"]
        instruccion_ejemplo = ejemplo["system_instruction"]
        esquema_ejemplo = ejemplo["response_schema"]
        propiedades_ejemplo = (
            esquema_ejemplo.get("properties", {})
            if isinstance(esquema_ejemplo, dict)
            else {}
        )
        ejemplos_ok = ejemplos_ok and (
            "/models/" in url_ejemplo
            and ":generateContent" in url_ejemplo
            and cuerpo_ejemplo["contents"][0]["parts"][0]["text"] == pregunta_ejemplo
            and cuerpo_ejemplo["systemInstruction"]["parts"][0]["text"]
            == instruccion_ejemplo
            and cuerpo_ejemplo["generationConfig"]["responseMimeType"]
            == "application/json"
            and cuerpo_ejemplo["generationConfig"]["responseSchema"] == esquema_ejemplo
            and all(
                clave in propiedades_ejemplo for clave in ejemplo["claves_esperadas"]
            )
        )

    prompt = {
        "ejemplo_usuario": "Extrae nombre y ciudad.",
        "system_instruction": "Devuelve únicamente JSON.",
        "response_schema": {
            "type": "OBJECT",
            "properties": {"nombre": {"type": "STRING"}},
        },
    }
    _, cuerpo = banco._armar_peticion_prompt(prompt)
    solicitud_ok = (
        cuerpo["contents"] == [{"parts": [{"text": "Extrae nombre y ciudad."}]}]
        and cuerpo["systemInstruction"]["parts"][0]["text"]
        == "Devuelve únicamente JSON."
        and cuerpo["generationConfig"]["responseMimeType"] == "application/json"
    )
    try:
        banco.parsear_respuesta_json("no es JSON")
    except ValueError:
        json_invalido_rechazado = True
    else:
        json_invalido_rechazado = False

    correcto = (
        datos == {"nombre": "Lucía", "ciudad": "Chile"}
        and solicitud_ok
        and ejemplos_ok
        and consistencia_ok
        and json_invalido_rechazado
    )
    reporte.agregar(
        "prompts/banco.py",
        "Validación y preparación local",
        correcto,
        (
            "valida JSON, construye la solicitud y contiene tres ejemplos"
            if correcto
            else "falló la validación JSON, la solicitud o el banco de tres ejemplos"
        ),
    )


def _revisar_pipeline_texto(reporte: Reporte, modulos: dict[str, object]) -> None:
    """Ejecuta las comprobaciones de limpieza y tokenización del pipeline de texto."""
    pipeline = modulos["pipeline_texto"]

    normalizado = pipeline.limpiar_texto("  El Cielo, es AZUL!  ")
    con_tildes = pipeline.limpiar_texto("¡El pingüino niño tiene 3 años!")
    texto_limpio_ok = (
        normalizado == "el cielo es azul"
        and con_tildes == "el pingüino niño tiene 3 años"
    )

    try:
        pipeline.limpiar_texto(42)  # type: ignore[arg-type]
    except TypeError:
        tipo_rechazado = True
    else:
        tipo_rechazado = False

    tokens_ok = pipeline.procesar_texto("El Cielo, es AZUL!") == [
        "el",
        "cielo",
        "es",
        "azul",
    ]
    vector_ok = pipeline.vectorizar(["el", "gato", "y", "el", "perro"]) == {
        "el": 2,
        "gato": 1,
        "y": 1,
        "perro": 1,
    }
    metricas = pipeline.calcular_metricas(
        "El gato duerme en el sofá.",
        "El gato duerme en el sillón todo el día.",
    )
    metricas_esperadas = {
        "precision": 5 / 9,
        "cobertura": 5 / 6,
        "f1": 2 * 5 / (9 + 6),
    }
    metricas_ok = all(
        abs(metricas[nombre] - valor) < 1e-12
        for nombre, valor in metricas_esperadas.items()
    )

    correcto = (
        texto_limpio_ok
        and tipo_rechazado
        and tokens_ok
        and vector_ok
        and metricas_ok
        and pipeline.procesar_texto("¡¡¡...!!!") == []
    )
    reporte.agregar(
        "pipeline_texto.py",
        "Limpieza, tokenización y vectorización",
        correcto,
        (
            "normaliza texto, rechaza tipos inválidos y devuelve tokens/vectores esperados"
            if correcto
            else "una o más funciones del pipeline de texto no cumplen la validación local"
        ),
    )

    evaluador_metricas = modulos["evaluar_metricas"]
    resumen = evaluador_metricas.resumir_metricas(
        [
            {
                "consulta": "consulta",
                "referencia": "referencia",
                "respuesta": "respuesta",
                "precision": 0.8,
                "cobertura": 0.6,
                "f1": 0.7,
            }
        ]
    )
    reporte.agregar(
        "evaluar_metricas.py",
        "Resumen de métricas",
        resumen
        == {
            "precision_promedio": 0.8,
            "cobertura_promedio": 0.6,
            "f1_promedio": 0.7,
        },
        "calcula los promedios localmente sin consultar la API",
    )

    revisor = modulos["revisar_cualitativamente"]
    resultados = [
        {
            "consulta": f"consulta {indice}",
            "referencia": f"referencia {indice}",
            "respuesta": f"respuesta {indice}",
            "precision": 0.5,
            "cobertura": 0.5,
            "f1": indice / 12,
        }
        for indice in range(12)
    ]
    muestra = revisor.preparar_revision(resultados)
    muestra_ok = (
        len(muestra) == 10
        and [caso["consulta"] for caso in muestra]
        == [
            "consulta 0",
            "consulta 1",
            "consulta 2",
            "consulta 3",
            "consulta 4",
            "consulta 7",
            "consulta 8",
            "consulta 9",
            "consulta 10",
            "consulta 11",
        ]
        and all(
            caso["correccion_factual"] == ""
            and caso["completitud"] == ""
            and caso["contradiccion"] == ""
            and caso["nota"] == ""
            for caso in muestra
        )
    )
    muestra_pequena = revisor.seleccionar_muestra(resultados[:6])
    muestra_pequena_ok = len(muestra_pequena) == len(
        {caso["consulta"] for caso in muestra_pequena}
    )
    reporte.agregar(
        "revisar_cualitativamente.py",
        "Selección y rúbrica manual",
        muestra_ok and muestra_pequena_ok,
        (
            "selecciona extremos sin duplicados y prepara los campos de la rúbrica"
            if muestra_ok and muestra_pequena_ok
            else "falló la selección de extremos o la preparación de la rúbrica"
        ),
    )

    evaluar = modulos["evaluar_salidas"]
    with patch.object(
        evaluar,
        "consultar_modelo",
        return_value="python es un lenguaje de programación, interpretado!",
    ):
        with redirect_stdout(StringIO()) as salida:
            codigo = evaluar.main()
    salida_ok = (
        codigo == 0
        and salida.getvalue().splitlines() == [
            "[Caso 1] Coincidencia texto crudo: 57.1%",
            "[Caso 1] Coincidencia texto procesado: 100.0%",
        ]
    )
    reporte.agregar(
        "evaluar_salidas.py",
        "Comparación de texto crudo y procesado",
        salida_ok,
        (
            "imprime las dos métricas esperadas sin consultar la API real"
            if salida_ok
            else "la comparación no produjo el formato ni los valores esperados"
        ),
    )


def _revisar_actividad_core(
    reporte: Reporte,
    modulos: dict[str, object],
) -> None:
    """Comprueba los entregables de la actividad core sin generar llamadas API."""
    revisor = modulos["revisar_cualitativamente"]
    ruta_resultados = revisor.ruta_resultados_predeterminada()
    ruta_revision = PROJECT_ROOT / "revision_manual.json"
    ruta_limites = PROJECT_ROOT / "docs" / "limites_metrica.md"

    try:
        resultados = revisor.cargar_resultados(ruta_resultados)
    except FileNotFoundError:
        resultados = None
        reporte.agregar(
            "Actividad core Bloque 17",
            "20 respuestas generadas",
            None,
            "pendiente: genera al menos 20 respuestas; "
            "usa evaluar_metricas.py --actividad-core o completa resultados_metricas.json",
        )
    except (OSError, ValueError) as error:
        resultados = None
        reporte.agregar(
            "Actividad core Bloque 17",
            "20 respuestas generadas",
            False,
            f"{ruta_resultados.name} no es válido: {error}",
        )
    else:
        if len(resultados) < revisor.MINIMO_RESULTADOS:
            reporte.agregar(
                "Actividad core Bloque 17",
                "20 respuestas generadas",
                None,
                f"pendiente: hay {len(resultados)} de al menos "
                f"{revisor.MINIMO_RESULTADOS} respuestas",
            )
        else:
            try:
                revisor.validar_resultados(resultados)
            except ValueError as error:
                reporte.agregar(
                    "Actividad core Bloque 17",
                    "20 respuestas generadas",
                    False,
                    str(error),
                )
                resultados = None
            else:
                reporte.agregar(
                    "Actividad core Bloque 17",
                    "20 respuestas generadas",
                    True,
                    f"{len(resultados)} respuestas con métricas completas",
                )

    if resultados is None or len(resultados) < revisor.MINIMO_RESULTADOS:
        reporte.agregar(
            "Actividad core Bloque 17",
            "10 revisiones manuales",
            None,
            "pendiente de generar y evaluar al menos 20 respuestas",
        )
        reporte.agregar(
            "Actividad core Bloque 17",
            "Límites basados en la revisión",
            None,
            "pendiente de completar las revisiones manuales",
        )
        return

    try:
        revisiones = revisor.cargar_resultados(ruta_revision)
    except FileNotFoundError:
        revisiones = None
        reporte.agregar(
            "Actividad core Bloque 17",
            "10 revisiones manuales",
            None,
            "pendiente: genera revision_manual.json y completa la rúbrica y las notas",
        )
    except (OSError, ValueError) as error:
        revisiones = None
        reporte.agregar(
            "Actividad core Bloque 17",
            "10 revisiones manuales",
            False,
            f"revision_manual.json no es válido: {error}",
        )
    else:
        campos_revision = (
            "correccion_factual",
            "completitud",
            "contradiccion",
            "nota",
        )
        incompletas = [
            caso
            for caso in revisiones
            if any(
                not isinstance(caso.get(campo), str)
                or not caso[campo].strip()
                for campo in campos_revision
            )
        ]
        if len(revisiones) < revisor.MINIMO_REVISIONES or incompletas:
            reporte.agregar(
                "Actividad core Bloque 17",
                "10 revisiones manuales",
                None,
                f"pendiente: {len(revisiones)} casos; "
                f"{len(incompletas)} aún sin completar",
            )
        else:
            try:
                revisor.validar_revision_manual(resultados, revisiones)
            except ValueError as error:
                reporte.agregar(
                    "Actividad core Bloque 17",
                    "10 revisiones manuales",
                    False,
                    str(error),
                )
                revisiones = None
            else:
                reporte.agregar(
                    "Actividad core Bloque 17",
                    "10 revisiones manuales",
                    True,
                    f"{len(revisiones)} casos con rúbrica, nota y extremos de F1",
                )

    if revisiones is None:
        reporte.agregar(
            "Actividad core Bloque 17",
            "Límites basados en la revisión",
            None,
            "pendiente de completar y validar las revisiones manuales",
        )
        return

    try:
        revisor.validar_documentacion(ruta_limites, resultados, revisiones)
    except (OSError, ValueError) as error:
        reporte.agregar(
            "Actividad core Bloque 17",
            "Límites basados en la revisión",
            None,
            f"pendiente: actualiza docs/limites_metrica.md con los hallazgos: {error}",
        )
    else:
        reporte.agregar(
            "Actividad core Bloque 17",
            "Límites basados en la revisión",
            True,
            "documenta secciones requeridas, muestra y hallazgos rastreables",
        )


def _revisar_cadena_langchain(
    reporte: Reporte,
    modulos: dict[str, object],
) -> None:
    """Prueba los tres pasos de LangChain usando respuestas simuladas."""
    from langchain_core.messages import AIMessage

    modelo_falso = Mock(
        side_effect=[
            AIMessage(content="punto uno\npunto dos\npunto tres"),
            AIMessage(content="texto sencillo"),
            AIMessage(content="- viñeta uno\n- viñeta dos"),
        ]
    )
    cadena = modulos["cadena_tres_pasos"].construir_cadena(modelo_falso)
    resultado = cadena.invoke({"texto": "Texto de prueba para el gate"})
    correcto = (
        modelo_falso.call_count == 3
        and resultado == "- viñeta uno\n- viñeta dos"
        and isinstance(resultado, str)
        and "Texto de prueba para el gate"
        in modelo_falso.call_args_list[0].args[0].to_string()
        and "punto uno" in modelo_falso.call_args_list[1].args[0].to_string()
        and "texto sencillo"
        in modelo_falso.call_args_list[2].args[0].to_string()
    )
    reporte.agregar(
        "cadena_tres_pasos.py",
        "Tres pasos con modelo simulado",
        correcto,
        (
            "extrae, simplifica y formatea con tres invocaciones locales"
            if correcto
            else "la chain no conectó las tres etapas como se esperaba"
        ),
    )


def _revisar_enrutamiento_langchain(
    reporte: Reporte,
    modulos: dict[str, object],
) -> None:
    """Prueba normalización y enrutamiento de una queja sin llamadas a Gemini."""
    from langchain_core.messages import AIMessage
    from langchain_core.runnables import RunnableLambda

    modelo_falso = Mock(return_value=AIMessage(content=" Queja \n"))
    respuesta_falsa = Mock(return_value="respuesta empática")
    paso = modulos["enrutamiento"].construir_paso_clasificacion(modelo_falso)
    cadena = modulos["enrutamiento"].construir_cadena_con_enrutamiento(
        paso_clasificacion=paso,
        cadena_queja=RunnableLambda(respuesta_falsa),
    )
    resultado = cadena.invoke({"mensaje": "La app dejó de funcionar"})
    entrada_ruta = respuesta_falsa.call_args.args[0]
    correcto = (
        resultado == "respuesta empática"
        and modelo_falso.call_count == 1
        and respuesta_falsa.call_count == 1
        and entrada_ruta
        == {"mensaje": "La app dejó de funcionar", "categoria": "queja"}
    )
    reporte.agregar(
        "enrutamiento.py",
        "Clasificación y ruta simuladas",
        correcto,
        (
            "normaliza la clasificación, conserva el mensaje y elige la ruta de queja"
            if correcto
            else "la clasificación o la ruta no produjo el resultado esperado"
        ),
    )


def _revisar_agente_langchain(
    reporte: Reporte,
    modulos: dict[str, object],
) -> None:
    """Prueba herramientas estructuradas y memoria aislada sin llamadas al modelo."""
    agente = modulos["agente_con_herramientas"]
    resultado_documentacion = agente.buscar_en_documentacion.invoke("reintentos")
    resultado_costo = agente.calcular_costo_tokens.invoke(
        {"tokens_entrada": 1000, "tokens_salida": 200}
    )
    campos = agente.calcular_costo_tokens.args_schema.model_fields
    historial_uno = agente.obtener_historial("revision-gate-bloque-22-uno")
    historial_dos = agente.obtener_historial("revision-gate-bloque-22-dos")
    historial_uno.add_user_message("mensaje privado de prueba")
    correcto = (
        "3 veces" in resultado_documentacion
        and "USD 0.00150000" in resultado_costo
        and "costo estimado" in resultado_costo.lower()
        and agente.calcular_costo_tokens.name == "calcular_costo_tokens_gemini"
        and set(campos)
        == {"tokens_entrada", "tokens_salida", "tokens_pensamiento"}
        and all(campo.description for campo in campos.values())
        and historial_dos.messages == []
    )
    agente.cerrar_sesion("revision-gate-bloque-22-uno")
    agente.cerrar_sesion("revision-gate-bloque-22-dos")
    reporte.agregar(
        "agente_con_herramientas.py",
        "Herramienta estructurada y memoria",
        correcto,
        (
            "el esquema documenta argumentos y los historiales quedan separados"
            if correcto
            else "falló la validación del esquema, herramienta o aislamiento de sesión"
        ),
    )


def _revisar_chunking_rag(
    reporte: Reporte,
    modulos: dict[str, object],
) -> None:
    """Comprueba localmente que el corpus se divida con metadatos de origen."""
    indexador = modulos["indexar_corpus"]
    chunks = indexador.dividir_corpus()
    correcto = (
        len(indexador.CORPUS_DOCUMENTOS) >= 5
        and len(chunks) >= 5
        and all(chunk.page_content.strip() for chunk in chunks)
        and all(chunk.metadata.get("source") for chunk in chunks)
        and all(
            len(chunk.page_content) <= indexador.TAMANO_CHUNK
            for chunk in chunks
        )
    )
    reporte.agregar(
        "indexar_corpus.py",
        "Chunking local del corpus RAG",
        correcto,
        (
            f"{len(indexador.CORPUS_DOCUMENTOS)} documentos producen "
            f"{len(chunks)} chunks con origen"
            if correcto
            else "el corpus o los metadatos de los chunks no cumplen los requisitos"
        ),
    )


def _revisar_replica_corpus_ejemplo(
    reporte: Reporte,
    modulos: dict[str, object],
) -> None:
    """Comprueba localmente el chunking de la réplica sin llamar a Gemini."""
    replica = modulos["replica_corpus_ejemplo"]
    chunks = replica.dividir_corpus()
    with redirect_stdout(StringIO()):
        replica.verificar_integridad(chunks)

    longitudes = [len(chunk.page_content) for chunk in chunks]
    correcto = (
        len(chunks) == 5
        and longitudes == [106, 103, 99, 85, 97]
        and sum(longitudes) == 490
    )
    reporte.agregar(
        "replica_corpus_ejemplo.py",
        "Integridad local del corpus de ejemplo",
        correcto,
        (
            f"{len(chunks)} chunks, {sum(longitudes)} caracteres y sin llamadas "
            "a Gemini"
            if correcto
            else "el número, longitudes o total de caracteres no coincide "
            "con el corpus de ejemplo"
        ),
    )


def _revisar_scripts(reporte: Reporte, modulos: dict[str, object]) -> None:
    """Verifica los scripts de ejemplo sin enviar solicitudes a la red."""
    clave = "clave-local-de-prueba"

    # Captura salida y sustituye HTTP para probar los scripts sin efectos externos.
    api_test = modulos["api_test"]
    respuesta = Mock()
    respuesta.text = '{"candidates":[{"content":{"parts":[{"text":"ok"}]}}]}'
    with patch.dict(os.environ, {"GEMINI_API_KEY": clave}):
        with patch.object(api_test.requests, "post", return_value=respuesta) as post:
            with redirect_stdout(StringIO()) as salida:
                codigo_api = api_test.main()
    api_ok = (
        codigo_api == 0
        and "La API respondió correctamente." in salida.getvalue()
        and post.call_args.kwargs["headers"]["x-goog-api-key"] == clave
    )
    reporte.agregar(
        "api_test.py",
        "Resultado HTTP simulado",
        api_ok,
        (
            "imprime éxito solo después de una respuesta HTTP correcta"
            if api_ok
            else "no informó correctamente la respuesta simulada"
        ),
    )

    modulo_test = modulos["module_test"]
    with patch.dict(os.environ, {"GEMINI_API_KEY": clave}):
        with patch.object(
            modulo_test, "make_request", return_value="respuesta simulada"
        ) as request:
            with redirect_stdout(StringIO()) as salida:
                codigo_modulo = modulo_test.main()
    modulo_ok = (
        codigo_modulo == 0
        and "respuesta simulada" in salida.getvalue()
        and request.call_args.kwargs["headers"]["x-goog-api-key"] == clave
    )
    reporte.agregar(
        "module_test.py",
        "Envío de módulo simulado",
        modulo_ok,
        (
            "envía la clave en el encabezado y muestra la respuesta"
            if modulo_ok
            else "falló la llamada simulada del módulo"
        ),
    )

    modulo_main = modulos["main"]
    with patch.object(modulo_main.cliente, "costo_total_sesion", 0.00008):
        with patch.object(
            modulo_main.cliente,
            "consultar_modelo",
            return_value="respuesta simulada",
        ) as consulta:
            with redirect_stdout(StringIO()) as salida:
                codigo_main = modulo_main.main()
    main_ok = (
        codigo_main == 0
        and consulta.call_count == 1
        and "respuesta simulada" in salida.getvalue()
        and "Costo acumulado de la sesión: $0.00008" in salida.getvalue()
    )
    reporte.agregar(
        "main.py",
        "Delegación al flujo principal",
        main_ok,
        (
            "usa el cliente modular para una consulta y muestra su costo"
            if main_ok
            else "no delegó correctamente en el cliente modular"
        ),
    )

    with patch.object(
        modulo_main.cliente,
        "consultar_modelo",
        side_effect=modulo_main.cliente.ServicioNoDisponibleError(
            "fallo local simulado"
        ),
    ):
        with redirect_stdout(StringIO()):
            with redirect_stderr(StringIO()) as errores:
                codigo_main_error = modulo_main.main()
    main_error_ok = (
        codigo_main_error == 1 and "fallo local simulado" in errores.getvalue()
    )
    reporte.agregar(
        "main.py",
        "Propagación de errores del cliente",
        main_error_ok,
        (
            "informa el error del cliente en stderr y devuelve código 1"
            if main_error_ok
            else "no comunicó correctamente el error del cliente"
        ),
    )


def _probar_api(reporte: Reporte, modulos: dict[str, object], clave: str) -> None:
    """Hace una petición real para comprobar disponibilidad y redacta la clave."""
    if not clave:
        reporte.agregar(
            "API funciona",
            "Prueba real de Gemini",
            False,
            "no se puede probar sin GEMINI_API_KEY válida",
        )
        return
    try:
        # Esta es la única verificación del archivo que realiza una petición real.
        texto = modulos["consumir_gemini"].obtener_dato_de_prueba(
            "Responde únicamente: conexión correcta"
        )
    except (RuntimeError, ValueError) as error:
        detalle = str(error).replace(clave, "[REDACTADA]")
        reporte.agregar("API funciona", "Prueba real de Gemini", False, detalle)
    else:
        correcto = bool(texto.strip())
        reporte.agregar(
            "API funciona",
            "Prueba real de Gemini",
            correcto,
            (
                f"se recibió una respuesta de {len(texto)} caracteres"
                if correcto
                else "Gemini respondió sin texto"
            ),
        )


def main() -> int:
    """Ejecuta las comprobaciones y devuelve un código distinto de cero si fallan."""
    for salida in (sys.stdout, sys.stderr):
        if hasattr(salida, "reconfigure"):
            salida.reconfigure(encoding="utf-8")

    # La prueba real se puede omitir para ejecutar únicamente verificaciones locales.
    parser = argparse.ArgumentParser(
        description=(
            "Describe y verifica los módulos de GATE_1 y el banco de prompts. "
            "Por defecto comprueba Gemini con una petición real."
        )
    )
    parser.add_argument(
        "--omitir-api",
        action="store_true",
        help="omite la petición real a Gemini y deja ese check como pendiente",
    )
    argumentos = parser.parse_args()

    print("REVISIÓN DE GATE_1")
    print(f"Proyecto: {PROJECT_ROOT}")
    print("\nMÓDULOS Y RESULTADO ESPERADO")
    for nombre, (proposito, esperado) in MODULES.items():
        print(f"\n- {nombre}: {proposito}")
        print(f"  Esperado: {esperado}")

    # Separa los chequeos por categoría para que el resultado sea fácil de revisar.
    reporte = Reporte()
    print("\n1. CÓDIGO EJECUTABLE")
    _revisar_sintaxis(reporte)
    try:
        modulos = _importar_modulos()
    except (ImportError, ModuleNotFoundError) as error:
        reporte.agregar(
            "Código ejecutable", "Importaciones del paquete", False, str(error)
        )
        modulos = {}
    else:
        reporte.agregar(
            "Código ejecutable",
            "Importaciones del paquete",
            True,
            "los módulos de lógica se importan desde la raíz del proyecto",
        )

    print("\n2. ENTORNO REPRODUCIBLE")
    _revisar_dependencias(reporte)

    print("\n3. CREDENCIALES NO EXPUESTAS")
    clave = _revisar_credenciales(reporte)

    if modulos:
        print("\n4. PRUEBAS LOCALES (sin llamadas de red)")
        # Se ejecutan únicamente si las importaciones funcionaron correctamente.
        _revisar_validaciones(reporte, modulos)
        _revisar_peticiones(reporte, modulos)
        _revisar_costo(reporte, modulos)
        _revisar_cliente(reporte, modulos)
        _revisar_cliente_modular(reporte, modulos)
        _revisar_monolitico(reporte, modulos)
        _revisar_latencia(reporte, modulos)
        _revisar_banco_prompts(reporte, modulos)
        _revisar_pipeline_texto(reporte, modulos)
        _revisar_actividad_core(reporte, modulos)
        _revisar_cadena_langchain(reporte, modulos)
        _revisar_enrutamiento_langchain(reporte, modulos)
        _revisar_agente_langchain(reporte, modulos)
        _revisar_chunking_rag(reporte, modulos)
        _revisar_replica_corpus_ejemplo(reporte, modulos)
        _revisar_scripts(reporte, modulos)

    print("\n5. DISPONIBILIDAD DE LA API")
    if not argumentos.omitir_api:
        if modulos:
            _probar_api(reporte, modulos, clave)
        else:
            reporte.agregar(
                "API funciona",
                "Prueba real de Gemini",
                False,
                "no se importó el cliente",
            )
    else:
        reporte.agregar(
            "API funciona",
            "Prueba real de Gemini",
            None,
            "omitida por --omitir-api; vuelve a ejecutar sin esa opción para probarla",
        )

    print("\nCHECKLIST DEL GATE 1")
    for grupo in (
        "API funciona",
        "Entorno reproducible",
        "Credenciales no expuestas",
        "Código ejecutable",
        "Actividad core Bloque 17",
    ):
        estado = reporte.estado_grupo(grupo)
        etiqueta = (
            "BIEN" if estado is True else "MAL" if estado is False else "PENDIENTE"
        )
        print(f"- [{etiqueta}] {grupo}")

    print("\nLas claves API nunca se imprimen.")
    if not argumentos.omitir_api:
        print("La prueba de disponibilidad envió una petición real a Gemini.")
    else:
        print("Las pruebas ejecutadas se hicieron sin llamadas de red.")
    return _codigo_salida(reporte)


if __name__ == "__main__":
    raise SystemExit(main())
