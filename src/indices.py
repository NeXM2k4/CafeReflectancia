"""Tabla unica de indices espectrales por archivo, punto y hoja-fecha.

Antes de esta sesion de pulido (ver `plan_mejora_app.md`, fase F1), cada pagina (2, 3, 4) y
`src/severity.py` volvian a calcular `calcular_indices()` en su propio bucle, cada uno con su
propio filtro de puntos y su propio agrupamiento. Este modulo es el unico lugar donde eso
pasa: todas las paginas, la alerta de Telegram y `make_ieee_figures.py` parten de
`file_index_table()` y de las dos funciones de agregacion de aqui.

Regla de unidad de analisis (confirmada por el usuario, ver memoria del proyecto y
`evoluciontemporal.md` seccion 2): los puntos de medicion **no son ubicaciones fijas** entre
campañas, asi que la unidad temporal/comparativa es la **hoja-fecha**, agregando primero las
repeticiones de cada punto y despues los puntos, usando **solo p1-p3** (p4-p6 aparecen en
algunas campañas por motivos de campo y no se promedian con los demas).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from src.config import INDEX_DEFINITIONS, SPECIES_PENDING_LABEL, TEMPORAL_VALID_POINTS
from src.parser import data_fingerprint, leaf_label
from src.store import compute_from_bytes, processed_store

# Todos los indices que calcula calcular_indices(), en el orden de config.INDEX_DEFINITIONS.
INDICES = list(INDEX_DEFINITIONS)

# FSR usa exactamente las mismas bandas que NDVI (config.WL_FSR = WL_NDVI), asi que su valor
# es numericamente identico: no aporta informacion propia. Se sigue calculando (por si algun
# analisis viejo lo necesita) pero las vistas nuevas, la estadistica y la similitud con roya
# recorren DISPLAY_INDICES, no INDICES.
DISPLAY_INDICES = [i for i in INDICES if i != "FSR"]

LEAF_KEYS = ["species", "leaf_id", "leaf", "leaf_type", "leaf_num"]
CONTEXT_KEYS = ["health_status", "susceptibility", "leaf_maturity"]

# --- Control de calidad (F1.6 de plan_mejora_app.md) ---
# Regla 1, "atipico": outlier respecto de la propia historia de la hoja (robust z de Iglewicz &
# Hoaglin 1993). Solo aplica a hojas con varias fechas (una sola medicion no tiene "propia
# historia" contra la cual compararse).
QC_Z_THRESHOLD = 3.5
QC_MIN_INDICES = 4  # mayoria de los 7 indices sin FSR
QC_MIN_FECHAS = 5
# Regla 2, "implausible": mNDVI705 fuera de un rango fisicamente posible. El denominador del
# indice es (R750 + R705 - 2*R445): cuando R445 se acerca a R705 (reflejo especular en el azul
# durante la medicion, visto el 24/08 y el 31/08 de 2026 en Pacamara y Bourbon, ver
# evoluciontemporal.md 12.4), el indice se dispara por encima de 1 o se vuelve negativo sin que
# eso sea una diferencia biologica real. No depende de la historia de la hoja: se puede marcar
# aun con una sola medicion.
IMPLAUSIBLE_MNDVI705 = (-0.05, 1.05)


def quality_flags(leaf_dates: pd.DataFrame) -> pd.DataFrame:
    """Agrega columnas de control de calidad a una tabla hoja-fecha (`leaf_date_table`):

    - `qc_n_atipicos` / `qc_atipico`: cuantos de los 7 indices (sin FSR) superan
      `|robust z| > QC_Z_THRESHOLD` contra la propia serie de esa hoja; `qc_atipico` es True si
      son `QC_MIN_INDICES` o mas (un solo indice raro puede ser biologia, casi todos a la vez
      apunta a un problema de medicion ese dia). Solo se evalua con `QC_MIN_FECHAS` o mas fechas.
    - `qc_implausible`: mNDVI705 fuera de `IMPLAUSIBLE_MNDVI705`, sin necesitar historia.
    - `qc_flag`: OR de las dos anteriores — "no usar esta hoja-fecha para anclas o estadistica
      sin revisarla primero". Nunca se usa para borrar datos, solo para excluirlos de calculos
      agregados; la hoja-fecha sigue visible marcada en toda la app.
    """
    out = leaf_dates.copy()
    out["qc_n_atipicos"] = 0
    dist_indices = [i for i in DISPLAY_INDICES]
    if "leaf_id" in out.columns:
        for _, g in out.groupby("leaf_id"):
            if len(g) < QC_MIN_FECHAS:
                continue
            vals = g[dist_indices]
            med = vals.median()
            mad = (vals - med).abs().median().replace(0, np.nan)
            z = 0.6745 * (vals - med) / mad
            out.loc[g.index, "qc_n_atipicos"] = (z.abs() > QC_Z_THRESHOLD).sum(axis=1)
    out["qc_atipico"] = out["qc_n_atipicos"] >= QC_MIN_INDICES
    lo, hi = IMPLAUSIBLE_MNDVI705
    out["qc_implausible"] = (out["mNDVI705"] < lo) | (out["mNDVI705"] > hi)
    out["qc_flag"] = out["qc_atipico"] | out["qc_implausible"]
    return out

@st.cache_data(show_spinner="Preparando la tabla de índices…")
def file_index_table(dataset: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, str]]]:
    """Indices espectrales por archivo, para todo archivo con nombre reconocido y especie real.

    Se excluye la especie "pendiente" (`SPECIES_PENDING_LABEL`, hojas "vieja" sin especie
    identificada, ver `config.py`), porque no tiene un tipo de hoja util para ningun analisis
    comparativo. No filtra por punto: cada pagina decide si usa `point_table`/`leaf_date_table`
    (solo p1-p3) o el detalle completo.

    Los indices salen del almacen precalculado (`src/store.py`, versionado en `data_cache/`):
    mismo calculo que antes (`calcular_indices(prepare_spectrum(...))`), hecho una sola vez por
    archivo. Devuelve `(tabla, errores_de_lectura)`.
    """
    sel = dataset[dataset["name_recognized"] & (dataset["species"] != SPECIES_PENDING_LABEL)]
    store = processed_store(data_fingerprint())
    calc = store.reindex(sel["path"])
    for path in calc.index[calc["rel_path"].isna()]:
        # Archivo fuera de data/ (p. ej. un dataset de prueba): se calcula directo, sin guardarlo.
        idx, _, err = compute_from_bytes(Path(path).read_bytes(), path)
        calc.loc[path, [*INDICES, "error", "rel_path"]] = [*idx.values(), err, path]
    error = calc["error"].fillna("").astype(str).to_numpy()
    errores = [(f, e) for f, e in zip(sel["filename"], error) if e]
    ok = error == ""
    sel, calc = sel[ok], calc[ok]

    hoja = [leaf_label(s, n) for s, n in zip(sel["session"], sel["session_num"])]
    df = pd.DataFrame({
        "species": sel["species"].to_numpy(),
        "leaf_type": sel["session"].to_numpy(),
        "leaf_num": sel["session_num"].astype(int).to_numpy(),
        "leaf": hoja,
        "leaf_id": [f"{s}|{h}" for s, h in zip(sel["species"], hoja)],
        "campaign_id": sel["campaign_id"].to_numpy(),
        "campaign_date": pd.to_datetime(sel["campaign_date"]).to_numpy(),
        "point": sel["point"].astype(int).to_numpy(),
        "repetition": sel["repetition"].to_numpy(),
        "health_status": sel["health_status"].to_numpy(),
        "susceptibility": sel["susceptibility"].to_numpy(),
        "leaf_maturity": sel["leaf_maturity"].to_numpy(),
        "filename": sel["filename"].to_numpy(),
        "path": sel["path"].to_numpy(),
        **{i: calc[i].to_numpy(dtype=float) for i in INDICES},
    })
    return df, errores


def point_table(files: pd.DataFrame, valid_points: tuple[int, ...] = TEMPORAL_VALID_POINTS) -> pd.DataFrame:
    """Media de las repeticiones de cada punto (son replicas tecnicas). Solo p1-p3 por defecto."""
    df = files[files["point"].isin(valid_points)] if valid_points else files
    claves = [*LEAF_KEYS, *CONTEXT_KEYS, "campaign_id", "campaign_date", "point"]
    agg = df.groupby(claves, dropna=False)
    tabla = agg[INDICES].mean()
    tabla["n_archivos"] = agg.size()
    return tabla.reset_index()


def leaf_date_table(files: pd.DataFrame, valid_points: tuple[int, ...] = TEMPORAL_VALID_POINTS) -> pd.DataFrame:
    """Una fila por hoja y fecha: media de los puntos (que ya son media de sus repeticiones),
    SD entre puntos (heterogeneidad espacial de la hoja ese dia) y n de puntos/archivos.

    Esta es la unidad de analisis por defecto (X4 de `plan_mejora_app.md`): evita tratar cada
    punto o cada repeticion como si fuera una observacion independiente (pseudo-replica).
    """
    puntos = point_table(files, valid_points)
    claves = [*LEAF_KEYS, *CONTEXT_KEYS, "campaign_id", "campaign_date"]
    agg = puntos.groupby(claves, dropna=False)
    medias = agg[INDICES].mean()
    sds = agg[INDICES].std(ddof=1).add_prefix("sd_")
    out = pd.concat([medias, sds], axis=1)
    out["n_puntos"] = agg.size()
    out["n_archivos"] = agg["n_archivos"].sum()
    return out.reset_index().sort_values(["species", "leaf", "campaign_date"]).reset_index(drop=True)
