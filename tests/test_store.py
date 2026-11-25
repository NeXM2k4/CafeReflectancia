"""Almacen precalculado (`src/store.py`): nunca debe servir un numero distinto del calculo directo."""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import store
from src.parser import read_spectrasuite_file
from src.processing import calcular_indices, prepare_spectrum

ROOT = Path(__file__).resolve().parent.parent
MUESTRA = sorted((ROOT / "data").rglob("*.txt"))[:: max(1, len(list((ROOT / "data").rglob("*.txt"))) // 12)][:12]


def _directo(path: Path) -> tuple[dict, np.ndarray]:
    spec = prepare_spectrum(read_spectrasuite_file(str(path)))
    y = np.interp(store.GRID, spec["wavelength"], spec["smooth"], left=np.nan, right=np.nan)
    return calcular_indices(spec), y


@pytest.fixture()
def mini(tmp_path):
    """Copia de 12 archivos reales repartidos en dos carpetas de campaña."""
    data = tmp_path / "data"
    for k, src in enumerate(MUESTRA):
        destino = data / ("campA" if k % 2 else "campB") / "Bourbon" / f"M1p1bourbon{k}.txt"
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, destino)
    return data, tmp_path / "data_cache"


def _igual(tabla: pd.DataFrame, path: Path):
    idx, y = _directo(path)
    fila = tabla.loc[str(path)]
    assert [fila[k] for k in store.INDICES] == pytest.approx([idx[k] for k in store.INDICES], nan_ok=True, rel=0, abs=0)
    np.testing.assert_array_equal(fila[store.SPEC_COLS].to_numpy(dtype=float), y)


def test_desde_cero_igual_al_calculo_directo(mini):
    data, cache = mini
    tabla, r = store.build_store(data, cache)
    assert r["calculados"] == len(MUESTRA) and r["reutilizados"] == 0
    assert sorted(p.name for p in cache.glob("*.parquet")) == ["campA.parquet", "campB.parquet"]
    for p in data.rglob("*.txt"):
        _igual(tabla, p)


def test_reutiliza_y_detecta_cambios(mini):
    data, cache = mini
    store.build_store(data, cache)
    tabla, r = store.build_store(data, cache)
    assert r["calculados"] == 0 and r["reutilizados"] == len(MUESTRA)

    archivos = sorted(data.rglob("*.txt"))
    # Reemplazar el contenido de un archivo por el de otro (otra medicion, mismo formato).
    shutil.copy(archivos[1], archivos[0])
    nuevo = archivos[0].parent / "T1p1bourbon99.txt"
    shutil.copy(MUESTRA[0], nuevo)
    archivos[2].unlink()
    tabla, r = store.build_store(data, cache)
    assert r["calculados"] == 2 and r["quitados"] == 1
    _igual(tabla, archivos[0])
    _igual(tabla, nuevo)
    assert str(archivos[2]) not in tabla.index
    # Lo escrito en disco ya refleja los cambios: la siguiente lectura no recalcula nada.
    assert store.build_store(data, cache)[1]["calculados"] == 0


def test_cambio_de_metodo_recalcula_todo(mini, monkeypatch):
    data, cache = mini
    store.build_store(data, cache)
    monkeypatch.setattr(store, "method_fingerprint", lambda: "otro-metodo")
    _, r = store.build_store(data, cache)
    assert r["calculados"] == len(MUESTRA)
    metodos = {m for p in cache.glob("*.parquet") for m in pd.read_parquet(p, columns=["method"])["method"]}
    assert metodos == {"otro-metodo"}


def test_archivo_ilegible_queda_con_error(mini):
    data, cache = mini
    malo = data / "campA" / "Bourbon" / "M2p1bourbon1.txt"
    malo.write_text("sin marcador de datos\n", encoding="latin-1")
    tabla, _ = store.build_store(data, cache)
    assert tabla.loc[str(malo), "error"] != ""
    assert tabla.loc[str(malo), store.INDICES].isna().all()


def test_verificacion_rapida_da_la_misma_tabla_sin_leer_archivos(mini, monkeypatch):
    """Modo de la app (`verify_content=False`): misma tabla que verificando por contenido, sin leer."""
    data, cache = mini
    completa, _ = store.build_store(data, cache)
    leidos = []
    original = Path.read_bytes
    monkeypatch.setattr(Path, "read_bytes", lambda self: leidos.append(self) or original(self))
    rapida, r = store.build_store(data, cache, verify_content=False)
    assert leidos == [] and r["calculados"] == 0
    pd.testing.assert_frame_equal(rapida, completa)


def test_verificacion_rapida_detecta_archivos_nuevos_y_cambios_de_tamano(mini):
    data, cache = mini
    store.build_store(data, cache)
    archivos = sorted(data.rglob("*.txt"))
    nuevo = archivos[0].parent / "T1p1bourbon99.txt"
    shutil.copy(MUESTRA[0], nuevo)
    with open(archivos[1], "ab") as f:  # mismo archivo, otro tamaño
        f.write(b"\n")
    tabla, r = store.build_store(data, cache, verify_content=False)
    assert r["calculados"] == 2
    _igual(tabla, nuevo)
    _igual(tabla, archivos[1])


def test_verificacion_rapida_no_ve_un_reemplazo_del_mismo_tamano(mini):
    """Riesgo aceptado y documentado (docs/plan_rendimiento.md, P2): lo detecta solo la
    verificacion por contenido (`build_cache.py` y `test_almacen_versionado_esta_al_dia`)."""
    data, cache = mini
    store.build_store(data, cache)
    a = sorted(data.rglob("*.txt"))[0]
    contenido = bytearray(a.read_bytes())
    i = contenido.rindex(b"5")  # un digito del cuerpo de datos: mismo tamaño, otro valor
    contenido[i:i + 1] = b"6"
    a.write_bytes(bytes(contenido))
    assert store.build_store(data, cache, verify_content=False)[1]["calculados"] == 0
    assert store.build_store(data, cache)[1]["calculados"] == 1


def test_almacen_versionado_esta_al_dia():
    """`data_cache/` del repo debe cubrir todo data/ con el metodo actual (si falla: correr
    `python scripts/build_cache.py` y commitear data_cache/)."""
    _, r = store.build_store(ROOT / "data", store.STORE_DIR, write=False)
    assert r["calculados"] == 0, r
