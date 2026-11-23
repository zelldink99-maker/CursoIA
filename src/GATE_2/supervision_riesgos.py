"""Versionado de prompts con aprobación humana y matriz de riesgos."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUTA_AUDITORIA = PROJECT_ROOT / "prompts" / "versiones_prompt.jsonl"


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


@dataclass
class VersionPrompt:
    huella: str
    contenido: str
    motivo: str
    estado: str = "pendiente"


class VersionadorPrompts:
    """Mantiene versiones locales y no activa ninguna sin aprobación humana."""

    def __init__(self, ruta_auditoria: str | Path = RUTA_AUDITORIA) -> None:
        self.ruta_auditoria = Path(ruta_auditoria)
        self.versiones: dict[str, VersionPrompt] = {}
        self.huella_activa: str | None = None
        if self.ruta_auditoria.exists():
            with self.ruta_auditoria.open(encoding="utf-8") as fuente:
                for linea in fuente:
                    if linea.strip():
                        self._aplicar_evento(json.loads(linea))

    @property
    def prompt_activo(self) -> str | None:
        """Devuelve el contenido activo, si existe."""
        if self.huella_activa is None:
            return None
        return self.versiones[self.huella_activa].contenido

    @property
    def interrupcion_pendiente(self) -> dict[str, str] | None:
        """Expone el punto donde el flujo espera una decisión humana."""
        pendientes = [
            version
            for version in self.versiones.values()
            if version.estado == "pendiente"
        ]
        if not pendientes:
            return None
        version = pendientes[0]
        return {"huella": version.huella, "motivo": version.motivo}

    def proponer(self, contenido: str, motivo: str) -> str:
        """Registra una propuesta y pausa antes de permitir su despliegue."""
        if not isinstance(contenido, str) or not contenido.strip():
            raise ValueError("El prompt propuesto debe ser texto no vacío.")
        if not isinstance(motivo, str) or not motivo.strip():
            raise ValueError("El motivo de aprobación debe ser texto no vacío.")
        if self.interrupcion_pendiente is not None:
            raise RuntimeError("Ya existe una propuesta pendiente de revisión.")

        huella = hashlib.sha256(contenido.encode("utf-8")).hexdigest()[:12]
        if huella in self.versiones:
            raise ValueError("Esta huella ya existe en el historial.")
        self._registrar_evento(
            {
                "evento": "propuesta",
                "huella": huella,
                "contenido": contenido,
                "motivo": motivo.strip(),
            }
        )
        return huella

    def aprobar(self, huella: str) -> None:
        """Reanuda la propuesta como aprobada, pero todavía no la activa."""
        self._resolver(huella, "aprobacion")

    def rechazar(self, huella: str) -> None:
        """Rechaza la propuesta y conserva intacta la versión activa."""
        self._resolver(huella, "rechazo")

    def activar(self, huella: str) -> None:
        """Activa una versión aprobada y archiva la anterior."""
        version = self._obtener_version(huella)
        if version.estado != "aprobada":
            raise RuntimeError(
                "Solo se puede activar una versión aprobada por una persona."
            )
        self._registrar_evento({"evento": "activacion", "huella": huella})

    def _resolver(self, huella: str, evento: str) -> None:
        version = self._obtener_version(huella)
        if version.estado != "pendiente":
            raise RuntimeError("La propuesta ya fue revisada.")
        self._registrar_evento({"evento": evento, "huella": huella})

    def _obtener_version(self, huella: str) -> VersionPrompt:
        try:
            return self.versiones[huella]
        except KeyError as error:
            raise ValueError(f"No existe la versión {huella}.") from error

    def _registrar_evento(self, evento: dict[str, Any]) -> None:
        registro = {
            "ts": datetime.now(timezone.utc).isoformat(),
            **evento,
        }
        self.ruta_auditoria.parent.mkdir(parents=True, exist_ok=True)
        with self.ruta_auditoria.open("a", encoding="utf-8") as destino:
            destino.write(json.dumps(registro, ensure_ascii=False) + "\n")
        self._aplicar_evento(registro)

    def _aplicar_evento(self, evento: dict[str, Any]) -> None:
        tipo = evento.get("evento")
        huella = evento.get("huella")
        if tipo == "propuesta":
            self.versiones[huella] = VersionPrompt(
                huella=huella,
                contenido=evento["contenido"],
                motivo=evento["motivo"],
            )
            return
        version = self._obtener_version(huella)
        if tipo == "aprobacion":
            version.estado = "aprobada"
        elif tipo == "rechazo":
            version.estado = "rechazada"
        elif tipo == "activacion":
            if self.huella_activa is not None:
                self.versiones[self.huella_activa].estado = "archivada"
            version.estado = "activa"
            self.huella_activa = huella
        else:
            raise ValueError(f"Evento de versionado desconocido: {tipo!r}.")


@dataclass(frozen=True)
class Riesgo:
    id: int
    descripcion: str
    probabilidad: int
    impacto: int
    punto_supervision: str


@dataclass(frozen=True)
class PuntuacionRiesgo:
    puntaje: int
    nivel: str

    @property
    def requiere_supervision_humana(self) -> bool:
        return self.nivel in {"ALTO", "CRÍTICO"}


@dataclass(frozen=True)
class RiesgoPuntuado(PuntuacionRiesgo):
    riesgo: Riesgo


RIESGOS_EJEMPLO = (
    Riesgo(
        1,
        "Inyección de prompt vía documento recuperado",
        4,
        4,
        "Cuarentena del documento y aprobación humana antes de reindexarlo.",
    ),
    Riesgo(
        2,
        "Filtración de PII en logs sin redactar",
        5,
        3,
        "Revisión humana de privacidad antes de exportar o compartir registros.",
    ),
    Riesgo(
        3,
        "Dataset de tuning desbalanceado produce sesgo",
        3,
        3,
        "Aprobación humana de métricas de equidad antes de desplegar el modelo.",
    ),
    Riesgo(
        4,
        "Modelo de embeddings deprecado sin aviso",
        2,
        4,
        "Revisión humana de compatibilidad antes de cambiar el modelo de embeddings.",
    ),
    Riesgo(
        5,
        "Chunk no reindexado devuelve información vieja",
        3,
        2,
        "Revisión humana de la fuente y el índice tras una actualización fallida.",
    ),
)


def esta_en_el_limite(probabilidad: int, impacto: int) -> bool:
    """Indica si mover una estimación por un punto cambia su categoría."""
    categoria_actual = puntuar_riesgo(probabilidad, impacto).nivel
    vecinos = (
        (probabilidad + 1, impacto),
        (probabilidad - 1, impacto),
        (probabilidad, impacto + 1),
        (probabilidad, impacto - 1),
    )
    for probabilidad_vecina, impacto_vecino in vecinos:
        if not (1 <= probabilidad_vecina <= 5 and 1 <= impacto_vecino <= 5):
            continue
        if puntuar_riesgo(
            probabilidad_vecina,
            impacto_vecino,
        ).nivel != categoria_actual:
            return True
    return False


def puntuar_riesgo(probabilidad: int, impacto: int) -> PuntuacionRiesgo:
    """Calcula probabilidad por impacto en escala de 1 a 5."""
    for nombre, valor in (
        ("probabilidad", probabilidad),
        ("impacto", impacto),
    ):
        if (
            not isinstance(valor, int)
            or isinstance(valor, bool)
            or not 1 <= valor <= 5
        ):
            raise ValueError(f"{nombre} debe ser un entero entre 1 y 5.")

    puntaje = probabilidad * impacto
    if puntaje >= 15:
        nivel = "CRÍTICO"
    elif puntaje >= 9:
        nivel = "ALTO"
    elif puntaje >= 4:
        nivel = "MEDIO"
    else:
        nivel = "BAJO"
    return PuntuacionRiesgo(puntaje, nivel)


def ordenar_riesgos(
    riesgos: tuple[Riesgo, ...] = RIESGOS_EJEMPLO,
) -> list[RiesgoPuntuado]:
    """Puntúa cada riesgo y los ordena de mayor a menor."""
    puntuados = []
    for riesgo in riesgos:
        puntuacion = puntuar_riesgo(riesgo.probabilidad, riesgo.impacto)
        puntuados.append(
            RiesgoPuntuado(
                puntaje=puntuacion.puntaje,
                nivel=puntuacion.nivel,
                riesgo=riesgo,
            )
        )
    return sorted(puntuados, key=lambda riesgo: riesgo.puntaje, reverse=True)


def main() -> int:
    """Imprime la matriz de riesgos de ejemplo sin llamar a servicios externos."""
    for resultado in ordenar_riesgos():
        nivel = resultado.nivel.replace("CRÍTICO", "CRITICO")
        print(
            f"{nivel:8} ({resultado.puntaje:2}) - "
            f"{resultado.riesgo.descripcion}"
        )
        if resultado.requiere_supervision_humana:
            print(
                f"  Supervisión humana: "
                f"{resultado.riesgo.punto_supervision}"
            )
        if esta_en_el_limite(
            resultado.riesgo.probabilidad,
            resultado.riesgo.impacto,
        ):
            print("[AL LIMITE]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
