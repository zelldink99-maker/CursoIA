"""Comprueba la carpeta del índice RAG y su exclusión de Git sin usar API."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUTA_VECTORSTORE = PROJECT_ROOT / "vectorstore"
RUTA_GITIGNORE = PROJECT_ROOT / ".gitignore"


def preflight_check(
    persist_directory: str | Path = RUTA_VECTORSTORE,
    gitignore_path: str | Path = RUTA_GITIGNORE,
) -> list[str]:
    """Devuelve problemas de carpeta o de .gitignore sin modificar archivos."""
    directorio = Path(persist_directory)
    gitignore = Path(gitignore_path)
    nombre_carpeta = f"{directorio.name}/"
    problemas: list[str] = []

    if not directorio.is_dir():
        problemas.append(f"{nombre_carpeta} no existe: corriste la indexación?")
    elif not any(elemento.is_file() for elemento in directorio.rglob("*")):
        problemas.append(f"{nombre_carpeta} existe pero esta vacio.")

    if not gitignore.exists():
        problemas.append(f"no existe {gitignore.name} en este proyecto")
        return problemas

    reglas = {
        linea.strip().replace("\\", "/").lstrip("/")
        for linea in gitignore.read_text(encoding="utf-8").splitlines()
        if linea.strip() and not linea.lstrip().startswith("#")
    }
    if nombre_carpeta not in reglas and nombre_carpeta.rstrip("/") not in reglas:
        problemas.append(f"{nombre_carpeta} no está en {gitignore.name}")
    return problemas


def main() -> int:
    """Imprime el resultado del preflight y retorna un estado comprobable."""
    problemas = preflight_check()
    if problemas:
        print("Preflight con problemas:")
        for problema in problemas:
            print(f" - {problema}")
        return 1

    print(
        "Preflight OK: la carpeta del indice existe, no esta vacia "
        "y esta en .gitignore"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
