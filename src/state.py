"""Registro local de la ultima vez que se reviso data/ para notificar novedades."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import streamlit as st

from src.config import DATA_DIR

STATE_FILE = Path(__file__).resolve().parent.parent / ".state" / "last_run.json"


@st.cache_data(show_spinner=False)
def _content_hash(path: str, _mtime_ns: int) -> str:
    """Hash del contenido de un archivo, cacheado por archivo+version.

    Mismo patron que `parser.read_spectrasuite()`: `_mtime_ns` solo se usa para invalidar
    el cache cuando el archivo cambia en disco, nunca se guarda como parte de la identidad.
    """
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:16]


def file_key(path: str, mtime_ns: int, data_dir: Path = DATA_DIR) -> str:
    """Identifica un archivo por **ruta relativa a `data/` + hash de su contenido**.

    No usa la ruta absoluta (cambia si el proyecto se mueve o se clona en otra maquina) ni
    depende de que el `mtime` se conserve entre copias (se pierde al clonar el repo o
    descomprimir un zip). Mover el proyecto de carpeta, o clonarlo en otra PC, no genera
    "archivos nuevos" falsos mientras el contenido no cambie.

    (Antes de 2026-09-28 la clave era `ruta_absoluta|mtime_ns`. Cambiar el formato invalida
    cualquier registro viejo, asi que la migracion al formato nuevo debe re-marcar el estado
    actual como "visto" una sola vez, sin disparar Telegram — ver `st_ok_to_reset` en app.py.)
    """
    try:
        rel = Path(path).resolve().relative_to(Path(data_dir).resolve()).as_posix()
    except ValueError:
        rel = path  # fuera de data_dir; no deberia pasar, se deja como fallback
    return f"{rel}|{_content_hash(path, mtime_ns)}"


def load_last_run() -> set[str]:
    if not STATE_FILE.exists():
        return set()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return set(data.get("files", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_last_run(file_keys: set[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"files": sorted(file_keys)}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
