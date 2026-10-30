"""Pruebas de selección y preparación de revisiones cualitativas."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.GATE_1 import revisar_cualitativamente


def _resultados(cantidad: int) -> list[dict[str, object]]:
    return [
        {
            "consulta": f"Consulta {indice}",
            "referencia": f"Referencia {indice}",
            "respuesta": f"Respuesta {indice}",
            "precision": 0.5,
            "cobertura": 0.5,
            "f1": indice / cantidad,
        }
        for indice in range(cantidad)
    ]


def _revisiones_completas() -> list[dict[str, object]]:
    return [
        {
            **caso,
            "correccion_factual": "sí",
            "completitud": "parcialmente",
            "contradiccion": "no",
            "nota": "La respuesta omite un dato importante de la referencia.",
        }
        for caso in revisar_cualitativamente.preparar_revision(_resultados(20))
    ]


@pytest.mark.parametrize(
    ("cantidad", "indices_esperados"),
    [
        (0, []),
        (1, [0]),
        (6, [0, 1, 2, 3, 4, 5]),
        (8, [0, 1, 2, 3, 4, 5, 6, 7]),
        (12, [0, 1, 2, 3, 4, 7, 8, 9, 10, 11]),
    ],
)
def test_seleccionar_muestra_sin_duplicar_casos(
    cantidad: int,
    indices_esperados: list[int],
) -> None:
    muestra = revisar_cualitativamente.seleccionar_muestra(_resultados(cantidad))

    assert [int(caso["consulta"].split()[-1]) for caso in muestra] == (
        indices_esperados
    )
    assert len({caso["consulta"] for caso in muestra}) == len(muestra)


def test_preparar_revision_incluye_campos_de_rubrica() -> None:
    muestra = revisar_cualitativamente.preparar_revision(_resultados(1))

    assert muestra[0]["correccion_factual"] == ""
    assert muestra[0]["completitud"] == ""
    assert muestra[0]["contradiccion"] == ""
    assert muestra[0]["nota"] == ""


def test_seleccionar_muestra_rechaza_resultado_sin_f1() -> None:
    with pytest.raises(ValueError, match="F1 numérico"):
        revisar_cualitativamente.seleccionar_muestra([{"consulta": "Consulta"}])


def test_preparar_revision_rechaza_campos_requeridos_ausentes() -> None:
    with pytest.raises(ValueError, match="consulta, referencia, respuesta"):
        revisar_cualitativamente.preparar_revision([{"f1": 0.5}])


def test_validar_revision_requiere_muestra_completa_y_rastreable() -> None:
    revisar_cualitativamente.validar_revision_manual(
        _resultados(20),
        _revisiones_completas(),
    )


def test_validar_revision_rechaza_una_nota_vacia() -> None:
    revisiones = _revisiones_completas()
    revisiones[0]["nota"] = ""

    with pytest.raises(ValueError, match="incluir una nota"):
        revisar_cualitativamente.validar_revision_manual(
            _resultados(20),
            revisiones,
        )


def test_validar_revision_rechaza_una_muestra_sin_un_extremo() -> None:
    revisiones = _revisiones_completas()
    revisiones[-1] = {
        **_resultados(20)[10],
        "correccion_factual": "sí",
        "completitud": "parcialmente",
        "contradiccion": "no",
        "nota": "La respuesta omite un dato importante de la referencia.",
    }

    with pytest.raises(ValueError, match="cinco F1 más bajos"):
        revisar_cualitativamente.validar_revision_manual(
            _resultados(20),
            revisiones,
        )


def test_validar_documentacion_exige_hallazgo_vinculado_a_revision(
    tmp_path: Path,
) -> None:
    resultados = _resultados(20)
    revisiones = _revisiones_completas()
    caso = revisiones[0]
    documento = tmp_path / "limites.md"
    documento.write_text(
        f"""# Límites

## Qué mide
Coincidencia de palabras.

## Modos de falla conocidos
- Consulta: {caso["consulta"]} | F1: {caso["f1"]:.2f} | Hallazgo: omitió un dato.

## Muestra revisada
- Respuestas generadas: 20
- Casos revisados: 10
- Fecha de revisión: 2026-10-30
- Criterio de selección: cinco con menor F1 y cinco con mayor F1.

## Recomendación de uso
Revisar manualmente las respuestas con datos verificables.
""",
        encoding="utf-8",
    )

    revisar_cualitativamente.validar_documentacion(
        documento,
        resultados,
        revisiones,
    )


def test_validar_documentacion_rechaza_hallazgo_no_revisado(
    tmp_path: Path,
) -> None:
    resultados = _resultados(20)
    revisiones = _revisiones_completas()
    documento = tmp_path / "limites.md"
    documento.write_text(
        """# Límites

## Qué mide
Coincidencia de palabras.

## Modos de falla conocidos
- Consulta: Consulta ajena | F1: 0.99 | Hallazgo: no aparece en la muestra.

## Muestra revisada
- Respuestas generadas: 20
- Casos revisados: 10
- Fecha de revisión: 2026-10-30
- Criterio de selección: cinco con menor F1 y cinco con mayor F1.

## Recomendación de uso
Revisar manualmente las respuestas con datos verificables.
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="no coincide con un caso revisado"):
        revisar_cualitativamente.validar_documentacion(
            documento,
            resultados,
            revisiones,
        )


def test_script_es_importable_fuera_de_la_raiz(tmp_path: Path) -> None:
    script = ROOT_DIR / "src" / "GATE_1" / "revisar_cualitativamente.py"
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


def test_main_carga_resultados_y_guarda_borrador(
    tmp_path: Path,
) -> None:
    entrada = tmp_path / "resultados.json"
    salida = tmp_path / "revision.json"
    entrada.write_text(json.dumps(_resultados(20)), encoding="utf-8")
    script = ROOT_DIR / "src" / "GATE_1" / "revisar_cualitativamente.py"

    resultado = subprocess.run(
        [
            sys.executable,
            str(script),
            "--entrada",
            str(entrada),
            "--salida",
            str(salida),
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr
    revision = json.loads(salida.read_text(encoding="utf-8"))
    assert len(revision) == 10
    assert all(caso["nota"] == "" for caso in revision)


def test_main_no_sobrescribe_el_archivo_de_entrada(tmp_path: Path) -> None:
    entrada = tmp_path / "resultados.json"
    contenido = json.dumps(_resultados(1))
    entrada.write_text(contenido, encoding="utf-8")
    script = ROOT_DIR / "src" / "GATE_1" / "revisar_cualitativamente.py"

    resultado = subprocess.run(
        [
            sys.executable,
            str(script),
            "--entrada",
            str(entrada),
            "--salida",
            str(entrada),
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )

    assert resultado.returncode != 0
    assert "deben ser archivos distintos" in resultado.stderr
    assert entrada.read_text(encoding="utf-8") == contenido


def test_main_reemplaza_automaticamente_una_revision_manual_existente(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    resultados = tmp_path / "resultados_metricas.json"
    resultados.write_text(json.dumps(_resultados(3)), encoding="utf-8")
    revision = tmp_path / "revision_manual.json"
    contenido = '[{"nota": "calificación manual"}]'
    revision.write_text(contenido, encoding="utf-8")
    monkeypatch.setattr(revisar_cualitativamente, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["revisar_cualitativamente.py"])

    assert revisar_cualitativamente.main() == 0

    nuevo_contenido = json.loads(revision.read_text(encoding="utf-8"))
    assert nuevo_contenido != json.loads(contenido)
    assert len(nuevo_contenido) == 3
    assert all(caso["nota"] == "" for caso in nuevo_contenido)
    assert "Muestra preparada" in capsys.readouterr().out


def test_ruta_predeterminada_usa_resultados_metricas_si_falta_lote_core(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(revisar_cualitativamente, "PROJECT_ROOT", tmp_path)

    assert (
        revisar_cualitativamente.ruta_resultados_predeterminada()
        == tmp_path / "resultados_metricas.json"
    )


def test_ruta_predeterminada_prioriza_resultados_core(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archivo_core = tmp_path / "resultados_actividad_core.json"
    archivo_core.touch()
    monkeypatch.setattr(revisar_cualitativamente, "PROJECT_ROOT", tmp_path)

    assert revisar_cualitativamente.ruta_resultados_predeterminada() == archivo_core


def test_main_prepara_muestra_parcial_si_hay_menos_de_veinte_resultados(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "resultados_metricas.json").write_text(
        json.dumps(_resultados(3)),
        encoding="utf-8",
    )
    monkeypatch.setattr(revisar_cualitativamente, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["revisar_cualitativamente.py"])

    assert revisar_cualitativamente.main() == 0

    revision = json.loads((tmp_path / "revision_manual.json").read_text("utf-8"))
    assert len(revision) == 3
    salida = capsys.readouterr().out
    assert "Esta muestra parcial no completa la entrega" in salida
    assert "la actividad requiere al menos 10" in salida
