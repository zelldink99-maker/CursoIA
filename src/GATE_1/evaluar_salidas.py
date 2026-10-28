"""Compara una respuesta real con su referencia, antes y después de limpiar."""

import sys
from pathlib import Path

if __package__:
    from .cliente import consultar_modelo
    from .pipeline_texto import procesar_texto
else:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.GATE_1.cliente import consultar_modelo
    from src.GATE_1.pipeline_texto import procesar_texto

def main() -> int:
    """Consulta el modelo e imprime la coincidencia cruda y procesada."""
    consulta = "¿Qué es Python?"
    referencia = "Python es un lenguaje de programación interpretado."

    respuesta = consultar_modelo(consulta)

    crudo_ref = referencia.split()
    crudo_resp = respuesta.split()
    comunes_crudo = set(crudo_ref) & set(crudo_resp)
    pct_crudo = len(comunes_crudo) / len(set(crudo_ref)) if crudo_ref else 0.0

    tokens_ref = procesar_texto(referencia)
    tokens_resp = procesar_texto(respuesta)
    comunes = set(tokens_ref) & set(tokens_resp)
    pct_proc = len(comunes) / len(set(tokens_ref)) if tokens_ref else 0.0

    print(f"[Caso 1] Coincidencia texto crudo: {pct_crudo:.1%}")
    print(f"[Caso 1] Coincidencia texto procesado: {pct_proc:.1%}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
