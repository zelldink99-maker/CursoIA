"""Pruebas del cálculo de la rúbrica ponderada del Gate 2."""

from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from rubrica_gate2 import DIMENSIONES, evaluar_gate, promedio_ponderado


PUNTAJES = {
    "pipeline_funcional": 95,
    "recuperacion_citacion": 90,
    "costo_latencia": 85,
    "personalizacion": 88,
    "observabilidad": 92,
    "seguridad_gobernanza": 80,
}


def test_promedio_ponderado_coincide_con_el_ejemplo_de_referencia() -> None:
    assert sum(DIMENSIONES.values()) == pytest.approx(1.0)
    assert promedio_ponderado(PUNTAJES, DIMENSIONES) == pytest.approx(88.75)


def test_no_compensables_impiden_aprobar_con_promedio_alto() -> None:
    promedio, aprueba = evaluar_gate(PUNTAJES, no_compensables_ok=False)

    assert promedio == pytest.approx(88.75)
    assert not aprueba


@pytest.mark.parametrize(
    "puntajes",
    [
        {**PUNTAJES, "pipeline_funcional": 101},
        {**PUNTAJES, "pipeline_funcional": True},
        {clave: 80 for clave in ("una_dimension",)},
    ],
)
def test_rechaza_puntajes_fuera_de_rango_o_dimensiones_incorrectas(
    puntajes: dict[str, int | float],
) -> None:
    with pytest.raises(ValueError):
        promedio_ponderado(puntajes, DIMENSIONES)


if __name__ == "__main__":
    raise SystemExit(pytest.main(["-v", __file__]))
