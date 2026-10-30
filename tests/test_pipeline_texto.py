"""Pruebas del pipeline local de texto, sin llamadas de red."""

import sys
from collections import Counter
from pathlib import Path
import subprocess
from unittest.mock import Mock

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_1 import evaluar_salidas
from src.GATE_1.pipeline_texto import (
    calcular_metricas,
    calcular_precision_cobertura_f1,
    contar_coincidencias,
    limpiar_texto,
    procesar_texto,
    tokenizar,
    vectorizar,
)


def test_limpiar_texto_normaliza_mayusculas_puntuacion_y_espacios() -> None:
    assert limpiar_texto("  El Cielo, es AZUL!  ") == "el cielo es azul"


def test_limpiar_texto_conserva_tildes_enie_y_numeros() -> None:
    assert limpiar_texto("¡El pingüino niño tiene 3 años!") == (
        "el pingüino niño tiene 3 años"
    )


def test_limpiar_texto_rechaza_entradas_que_no_son_texto() -> None:
    with pytest.raises(TypeError, match="espera str, no int"):
        limpiar_texto(42)  # type: ignore[arg-type]


def test_procesar_texto_normaliza_mayusculas_y_puntuacion() -> None:
    assert procesar_texto("El Cielo, es AZUL!") == ["el", "cielo", "es", "azul"]


def test_procesar_texto_solo_puntuacion_devuelve_lista_vacia() -> None:
    assert procesar_texto("¡¡¡...!!!") == []


def test_tokenizar_separa_por_espacios() -> None:
    assert tokenizar("el gato y el perro") == ["el", "gato", "y", "el", "perro"]


def test_vectorizar_cuenta_repeticiones() -> None:
    assert vectorizar(["el", "gato", "y", "el", "perro"]) == Counter(
        {"el": 2, "gato": 1, "y": 1, "perro": 1}
    )


def test_contar_coincidencias_respeta_repeticiones() -> None:
    assert contar_coincidencias(
        ["el", "gato", "el", "gato"],
        ["el", "gato"],
    ) == 2


def test_contar_coincidencias_rechaza_texto_sin_tokenizar() -> None:
    with pytest.raises(TypeError, match="tokens_referencia debe ser una lista"):
        contar_coincidencias("el gato", ["el", "gato"])  # type: ignore[arg-type]


def test_calcular_precision_cobertura_f1_ejemplo_de_la_leccion() -> None:
    assert calcular_precision_cobertura_f1(
        ["el", "gato", "duerme", "en", "el", "sofá"],
        ["el", "gato", "duerme", "en", "el", "sillón", "todo", "el", "día"],
    ) == pytest.approx(
        {"precision": 5 / 9, "cobertura": 5 / 6, "f1": 2 * 5 / (9 + 6)}
    )


@pytest.mark.parametrize(
    ("referencia", "respuesta", "esperado"),
    [
        ("", "respuesta", {"precision": 0.0, "cobertura": 0.0, "f1": 0.0}),
        ("referencia", "", {"precision": 0.0, "cobertura": 0.0, "f1": 0.0}),
        (
            "El auto es veloz.",
            "El vehículo es rápido.",
            {"precision": 0.5, "cobertura": 0.5, "f1": 0.5},
        ),
        (
            "Python fue creado en 1991.",
            "Python fue creado en 1989.",
            {"precision": 0.8, "cobertura": 0.8, "f1": 0.8},
        ),
        (
            "Python no es un lenguaje compilado.",
            "Python es un lenguaje compilado.",
            {
                "precision": 1.0,
                "cobertura": 5 / 6,
                "f1": 10 / 11,
            },
        ),
    ],
)
def test_calcular_metricas_y_limites_de_coincidencia_lexica(
    referencia: str,
    respuesta: str,
    esperado: dict[str, float],
) -> None:
    assert calcular_metricas(referencia, respuesta) == pytest.approx(esperado)


def test_coincidencia_mide_formato_crudo_y_procesado() -> None:
    referencia = "El cielo es azul."
    respuesta = "el cielo es azul"

    tokens_crudos_ref = referencia.split()
    tokens_crudos_resp = respuesta.split()
    assert len(set(tokens_crudos_ref) & set(tokens_crudos_resp)) / len(
        set(tokens_crudos_ref)
    ) == 0.5

    tokens_ref = procesar_texto(referencia)
    tokens_resp = procesar_texto(respuesta)
    assert len(set(tokens_ref) & set(tokens_resp)) / len(set(tokens_ref)) == 1.0


def test_evaluar_salidas_se_puede_importar_como_script_fuera_de_la_raiz(
    tmp_path: Path,
) -> None:
    script = ROOT_DIR / "src" / "GATE_1" / "evaluar_salidas.py"
    codigo = (
        "import runpy; "
        f"runpy.run_path({str(script)!r}, run_name='import_check')"
    )

    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr


def test_evaluar_salidas_imprime_solo_las_dos_metricas(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        evaluar_salidas,
        "consultar_modelo",
        Mock(return_value="python es un lenguaje de programación, interpretado!"),
    )

    assert evaluar_salidas.main() == 0

    assert capsys.readouterr().out.splitlines() == [
        "[Caso 1] Coincidencia texto crudo: 57.1%",
        "[Caso 1] Coincidencia texto procesado: 100.0%",
    ]
