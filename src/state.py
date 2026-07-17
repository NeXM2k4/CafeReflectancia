"""Registro local de la ultima vez que se reviso data/ para notificar novedades."""

from __future__ import annotations

import json
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent.parent / ".state" / "last_run.json"


def file_key(path: str, mtime_ns: int) -> str:
    """Identifica un archivo+version: cambia si se agrega, edita o reemplaza."""
    return f"{path}|{mtime_ns}"


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
