"""Pruebas del gate de aprobación y la matriz de riesgos."""

from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_2.supervision_riesgos import (
    RIESGOS_EJEMPLO,
    VersionadorPrompts,
    ordenar_riesgos,
    puntuar_riesgo,
)


def test_version_prompt_queda_pausada_hasta_aprobacion_y_despliegue(
    tmp_path: Path,
) -> None:
    archivo = tmp_path / "versiones.jsonl"
    versionador = VersionadorPrompts(archivo)
    huella = versionador.proponer(
        "Instrucciones versión nueva",
        "revisar seguridad antes del despliegue",
    )

    assert versionador.prompt_activo is None
    assert versionador.interrupcion_pendiente == {
        "huella": huella,
        "motivo": "revisar seguridad antes del despliegue",
    }
    with pytest.raises(RuntimeError, match="aprobada"):
        versionador.activar(huella)

    versionador.aprobar(huella)
    assert versionador.prompt_activo is None
    versionador.activar(huella)
    recargado = VersionadorPrompts(archivo)

    assert recargado.prompt_activo == "Instrucciones versión nueva"
    assert recargado.interrupcion_pendiente is None
    assert recargado.versiones[huella].estado == "activa"


def test_rechazar_propuesta_no_cambia_version_activa(tmp_path: Path) -> None:
    versionador = VersionadorPrompts(tmp_path / "versiones.jsonl")
    anterior = versionador.proponer("Versión inicial", "primer despliegue")
    versionador.aprobar(anterior)
    versionador.activar(anterior)
    propuesta = versionador.proponer("Versión experimental", "evaluación")
    versionador.rechazar(propuesta)

    assert versionador.prompt_activo == "Versión inicial"
    assert versionador.versiones[propuesta].estado == "rechazada"


def test_matriz_puntua_y_ordena_riesgos_y_exige_revision_humana() -> None:
    riesgos = ordenar_riesgos()

    assert len(riesgos) == len(RIESGOS_EJEMPLO)
    assert [riesgo.puntaje for riesgo in riesgos] == [16, 15, 9, 8, 6]
    assert [riesgo.nivel for riesgo in riesgos] == [
        "CRÍTICO",
        "CRÍTICO",
        "ALTO",
        "MEDIO",
        "MEDIO",
    ]
    assert all(
        riesgo.requiere_supervision_humana
        for riesgo in riesgos
        if riesgo.nivel in {"ALTO", "CRÍTICO"}
    )
    assert all(
        riesgo.riesgo.punto_supervision.strip()
        for riesgo in riesgos
        if riesgo.nivel in {"ALTO", "CRÍTICO"}
    )
    assert not riesgos[-1].requiere_supervision_humana


@pytest.mark.parametrize(
    ("probabilidad", "impacto"),
    [(0, 3), (6, 2), (True, 4), (2, False)],
)
def test_puntuar_riesgo_rechaza_valores_fuera_de_escala(
    probabilidad: int,
    impacto: int,
) -> None:
    with pytest.raises(ValueError, match="entero entre 1 y 5"):
        puntuar_riesgo(probabilidad, impacto)
