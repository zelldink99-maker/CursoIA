"""Redacción heurística de datos de contacto antes de persistir trazas."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

PATRON_EMAIL = re.compile(
    r"(?<![\w.+-])[\w.!#$%&'*+/=?^_`{|}~-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])",
    re.IGNORECASE,
)
PATRON_TELEFONO = re.compile(
    r"(?<!\w)(?:\+\d{1,3}[\s().-]?)?"
    r"(?:\(?\d{2,4}\)?[\s().-]?)?\d{3,4}[\s.-]?\d{4}(?!\w)"
)


def redactar_pii(valor: Any) -> Any:
    """Redacta correos y teléfonos en texto y estructuras anidadas comunes."""
    if isinstance(valor, str):
        sin_email = PATRON_EMAIL.sub("[EMAIL]", valor)
        return PATRON_TELEFONO.sub("[TELEFONO]", sin_email)
    if isinstance(valor, Mapping):
        return {clave: redactar_pii(elemento) for clave, elemento in valor.items()}
    if isinstance(valor, list):
        return [redactar_pii(elemento) for elemento in valor]
    if isinstance(valor, tuple):
        return tuple(redactar_pii(elemento) for elemento in valor)
    return valor
