"""Almacen precalculado por archivo: indices espectrales y espectro suavizado en la grilla comun.

Por que existe (ver `docs/plan_fondo_blanco_tendencias_rendimiento.md`): leer, suavizar y calcular
los indices de cada .txt cuesta ~2-6 ms por archivo; con miles de archivos el primer arranque
tardaba decenas de segundos. En Streamlit Community Cloud el disco se borra cada vez que la app
duerme o se reinicia, asi que un cache en `.state/` no sobrevive: cada arranque en frio
recalculaba todo. Este almacen se **versiona en el repo** (`data_cache/`), asi que viaja con los
datos y la app solo procesa los archivos que todavia no estan en el.

Reglas que garantizan que nunca se sirva un numero viejo:

- Cada archivo se identifica por su ruta relativa a `data/`, su tamaño y el sha1 de su contenido
  (la fecha de modificacion cambia al clonar el repo y el tamaño solo no detecta un archivo
  reemplazado por otra medicion del mismo formato). Si cualquiera cambia, se recalcula.
- `method_fingerprint()` resume el metodo (codigo de `processing.py` y del lector, parametros de
  suavizado, recorte, bandas y grilla). Si cambia, todo el almacen se descarta y se recalcula.
- Se guarda un archivo parquet por carpeta de campaña (primer nivel de `data/`): agregar una
  campaña agrega un archivo y no reescribe los demas (el historial de git no crece de mas).

`scripts/build_cache.py` lo regenera desde cero; la app lo completa sola si falta algo.
"""

from __future__ import annotations

import hashlib
import inspect
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from src import config, processing
from src.config import DATA_DIR, INDEX_DEFINITIONS, TEMPORAL_GRID_POINTS, TEMPORAL_WL_MIN, X_MAX
from src.parser import _parse_body_fast, parse_spectrasuite_text

STORE_DIR = Path(__file__).resolve().parent.parent / "data_cache"
FORMAT_VERSION = 1

INDICES = list(INDEX_DEFINITIONS)
# Grilla comun de los espectros suavizados: la misma que usaba `temporal.leaf_mean_spectra`.
GRID = np.linspace(TEMPORAL_WL_MIN, X_MAX, TEMPORAL_GRID_POINTS)
SPEC_COLS = [f"s{i:03d}" for i in range(len(GRID))]
META_COLS = ["rel_path", "size", "sha1", "error", "method"]


def method_fingerprint() -> str:
    """Huella del metodo de calculo: cambia si cambia cualquier cosa que altere los numeros."""
    h = hashlib.sha1()
    h.update(inspect.getsource(processing).encode("utf-8"))
    h.update(inspect.getsource(parse_spectrasuite_text).encode("utf-8"))
    h.update(inspect.getsource(_parse_body_fast).encode("utf-8"))
    params = {
        "format": FORMAT_VERSION,
        "grid": (TEMPORAL_WL_MIN, X_MAX, TEMPORAL_GRID_POINTS),
        "sg": (config.SG_WINDOW, config.SG_POLYORDER),
        "range": (config.X_MIN, config.X_MAX),
        "bands": sorted((k, v) for k, v in vars(config).items() if k.startswith("WL_")),
        "indices": INDICES,
    }
    h.update(repr(params).encode("utf-8"))
    return h.hexdigest()[:16]


def _rel(path: Path, data_dir: Path) -> str:
    return path.relative_to(data_dir).as_posix()


def _shard_name(rel_path: str) -> str:
    """Archivo del almacen donde vive un .txt: uno por carpeta de primer nivel de data/."""
    first = rel_path.split("/", 1)[0] if "/" in rel_path else "_raiz"
    return f"{first}.parquet"


def compute_from_bytes(contenido: bytes, path: str = "") -> tuple[dict, np.ndarray, str]:
    """Indices y espectro suavizado en `GRID` a partir del contenido crudo de un .txt.

    Mismo camino que el resto de la app: parseo -> Savitzky-Golay + recorte -> indices; el
    espectro se interpola a `GRID` (NaN fuera del rango medido). Un archivo ilegible devuelve
    NaN y el mensaje de error, que la app muestra en «Datos y calidad».
    """
    try:
        spec = processing.prepare_spectrum(parse_spectrasuite_text(contenido.decode("latin-1", errors="replace"), path))
        idx = processing.calcular_indices(spec)
        y = np.interp(GRID, spec["wavelength"], spec["smooth"], left=np.nan, right=np.nan)
        return idx, y, ""
    except ValueError as e:
        return {k: np.nan for k in INDICES}, np.full(len(GRID), np.nan), str(e)


def _read_store(store_dir: Path, metodo: str) -> pd.DataFrame:
    partes = []
    for archivo in sorted(store_dir.glob("*.parquet")):
        try:
            parte = pd.read_parquet(archivo)
        except Exception:  # noqa: BLE001 (archivo corrupto o de otra version: se recalcula)
            continue
        if set(META_COLS + INDICES + SPEC_COLS) - set(parte.columns):
            continue
        partes.append(parte[parte["method"] == metodo])
    if not partes:
        return pd.DataFrame(columns=META_COLS + INDICES + SPEC_COLS)
    return pd.concat(partes, ignore_index=True)


def _write_shard(store_dir: Path, nombre: str, tabla: pd.DataFrame) -> None:
    """Escritura atomica (archivo temporal + reemplazo) para que dos sesiones no se pisen."""
    try:
        store_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=store_dir, suffix=".tmp")
        os.close(fd)
        tabla.sort_values("rel_path").reset_index(drop=True).to_parquet(tmp, index=False, compression="zstd")
        os.replace(tmp, store_dir / nombre)
    except OSError:
        pass  # disco de solo lectura: la app funciona igual, solo no guarda lo calculado


def build_store(data_dir: Path = DATA_DIR, store_dir: Path = STORE_DIR, write: bool = True,
                progress=None) -> tuple[pd.DataFrame, dict]:
    """Tabla completa (una fila por .txt de `data_dir`), reutilizando lo que ya esta en el almacen.

    Devuelve `(tabla, resumen)`; `tabla` esta indexada por la ruta absoluta del archivo (la misma
    cadena que guarda `parser.scan_dataset` en la columna `path`). `resumen` cuenta archivos
    reutilizados, calculados y quitados.
    """
    metodo = method_fingerprint()
    previo = _read_store(store_dir, metodo).set_index("rel_path", drop=False)
    archivos = sorted(data_dir.rglob("*.txt"))

    claves, nuevas = [], []
    for k, path in enumerate(archivos):
        contenido = path.read_bytes()
        rel = _rel(path, data_dir)
        sha = hashlib.sha1(contenido).hexdigest()
        claves.append((str(path), rel, len(contenido), sha))
        vigente = rel in previo.index and previo.at[rel, "sha1"] == sha and int(previo.at[rel, "size"]) == len(contenido)
        if not vigente:
            idx, y, err = compute_from_bytes(contenido, str(path))
            nuevas.append({"rel_path": rel, "size": len(contenido), "sha1": sha, "error": err, "method": metodo,
                           **idx, **dict(zip(SPEC_COLS, y))})
        if progress is not None:
            progress(k + 1, len(archivos))
    calculados = len(nuevas)

    base = pd.DataFrame(claves, columns=["path", "rel_path", "size", "sha1"])
    reusadas = previo[previo.index.isin(set(base["rel_path"]) - {f["rel_path"] for f in nuevas})].reset_index(drop=True)
    partes = [t for t in (reusadas, pd.DataFrame(nuevas, columns=META_COLS + INDICES + SPEC_COLS)) if not t.empty]
    datos = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(columns=META_COLS + INDICES + SPEC_COLS)
    tabla = base[["path", "rel_path"]].merge(datos, on="rel_path", how="left", validate="one_to_one")
    tabla = tabla[["path", *META_COLS, *INDICES, *SPEC_COLS]]
    tabla["size"] = tabla["size"].astype("int64")
    tabla["error"] = tabla["error"].fillna("").astype(str)
    for c in INDICES + SPEC_COLS:
        tabla[c] = tabla[c].astype("float64")

    actuales = set(tabla["rel_path"])
    quitados = [r for r in previo.index if r not in actuales]
    if write:
        shard = tabla["rel_path"].map(_shard_name)
        # Un shard se reescribe si gano, perdio o cambio algun archivo, o si en disco hay
        # alguno calculado con otro metodo (se descarto al leer y hay que reemplazarlo).
        cambiados = set(shard[_recalculados_mask(tabla, previo)]) | {_shard_name(r) for r in quitados}
        cambiados |= _shards_with_other_methods(store_dir, metodo)
        for nombre in sorted(cambiados):
            parte = tabla[shard == nombre].drop(columns="path")
            if parte.empty:
                try:
                    (store_dir / nombre).unlink(missing_ok=True)
                except OSError:
                    pass
            else:
                _write_shard(store_dir, nombre, parte)

    resumen = {"archivos": len(tabla), "calculados": calculados, "reutilizados": len(tabla) - calculados,
               "quitados": len(quitados), "metodo": metodo}
    return tabla.set_index("path"), resumen


def _recalculados_mask(tabla: pd.DataFrame, previo: pd.DataFrame) -> pd.Series:
    """Filas nuevas o cuyo contenido (sha1) cambio respecto del almacen previo."""
    sha_previo = tabla["rel_path"].map(previo["sha1"]) if not previo.empty else pd.Series(np.nan, index=tabla.index)
    return sha_previo.isna() | (sha_previo != tabla["sha1"])


def _shards_with_other_methods(store_dir: Path, metodo: str) -> set[str]:
    """Shards en disco calculados (al menos en parte) con otro metodo, o ilegibles."""
    out = set()
    for archivo in store_dir.glob("*.parquet"):
        try:
            metodos = pd.read_parquet(archivo, columns=["method"])["method"].unique()
        except Exception:  # noqa: BLE001
            out.add(archivo.name)
            continue
        if len(metodos) != 1 or metodos[0] != metodo:
            out.add(archivo.name)
    return out


@st.cache_data(show_spinner="Cargando espectros procesados…", max_entries=2)
def processed_store(fingerprint: str) -> pd.DataFrame:
    """`build_store()` con cache de Streamlit; `fingerprint` (`parser.data_fingerprint()`) es la
    clave del cache: cambia, y el almacen se completa, cuando llegan archivos nuevos."""
    tabla, _ = build_store()
    return tabla


def spectra_matrix(tabla: pd.DataFrame, paths) -> np.ndarray:
    """Espectros suavizados en `GRID` (una fila por ruta, en el orden recibido)."""
    return tabla.loc[list(paths), SPEC_COLS].to_numpy(dtype=float)
