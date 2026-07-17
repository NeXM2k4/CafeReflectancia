"""Suavizado, filtrado por rango, indices espectrales y promedios de grupo."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

from src.config import (
    SG_POLYORDER,
    SG_WINDOW,
    WL_CARI,
    WL_EDI,
    WL_FSR,
    WL_NDVI,
    WL_PRI,
    WL_PSRI,
    WL_RCI,
    X_MAX,
    X_MIN,
)


def smooth(df: pd.DataFrame, window: int = SG_WINDOW, polyorder: int = SG_POLYORDER) -> pd.DataFrame:
    """Aplica Savitzky-Golay sobre 'reflectance', devuelve copia con columna 'smooth'."""
    df = df.copy()
    n = len(df)
    w = window if window % 2 == 1 else window + 1
    w = min(w, n if n % 2 == 1 else n - 1)
    if w < polyorder + 1:
        df["smooth"] = df["reflectance"]
        return df
    df["smooth"] = savgol_filter(df["reflectance"], window_length=w, polyorder=polyorder)
    return df


def filter_range(df: pd.DataFrame, x_min: float = X_MIN, x_max: float = X_MAX) -> pd.DataFrame:
    return df[(df["wavelength"] >= x_min) & (df["wavelength"] <= x_max)].reset_index(drop=True)


def prepare_spectrum(df: pd.DataFrame, window: int = SG_WINDOW, polyorder: int = SG_POLYORDER,
                      x_min: float = X_MIN, x_max: float = X_MAX) -> pd.DataFrame:
    """Pipeline completo: suavizar y recortar al rango util."""
    return filter_range(smooth(df, window, polyorder), x_min, x_max)


def reflectance_at(df: pd.DataFrame, wavelength: float, tol: float = 5, column: str = "smooth") -> float:
    """Reflectancia mas cercana a una longitud de onda dada (columna suavizada por defecto)."""
    if df.empty:
        return np.nan
    idx = (df["wavelength"] - wavelength).abs().idxmin()
    if abs(df.loc[idx, "wavelength"] - wavelength) <= tol:
        return df.loc[idx, column]
    return np.nan


def calcular_indices(df: pd.DataFrame) -> dict:
    """NDVI, PRI, PSRI y CARI a partir de un espectro suavizado."""

    def R(wl):
        return reflectance_at(df, wl)

    r800, r670 = R(WL_NDVI[0]), R(WL_NDVI[1])
    ndvi = (r800 - r670) / (r800 + r670) if (r800 + r670) else np.nan

    r531, r570 = R(WL_PRI[0]), R(WL_PRI[1])
    pri = (r531 - r570) / (r531 + r570) if (r531 + r570) else np.nan

    r678, r500, r750 = R(WL_PSRI[0]), R(WL_PSRI[1]), R(WL_PSRI[2])
    psri = (r678 - r500) / r750 if r750 else np.nan

    r550, r670_c, r700 = R(WL_CARI[0]), R(WL_CARI[1]), R(WL_CARI[2])
    if r670_c and not np.isnan(r670_c):
        a = (r700 - r550) / 150
        b = r550 - WL_CARI[0] * a
        # nota: formula correcta usa la longitud de onda (670), no la reflectancia R670
        cari_num = abs(a * WL_CARI[1] + r670_c + b)
        cari_den = np.sqrt(a ** 2 + 1)
        cari = (r700 / r670_c) * (cari_num / cari_den) if cari_den else np.nan
    else:
        cari = np.nan

    r510, r550_rci = R(WL_RCI[0]), R(WL_RCI[1])
    rci = (1 / r510 - 1 / r550_rci) if (r510 and r550_rci) else np.nan

    r705, r750_edi = R(WL_EDI[0]), R(WL_EDI[1])
    edi = (r750_edi - r705) / (r750_edi + r705) if (r750_edi + r705) else np.nan

    r_nir, r_red = R(WL_FSR[0]), R(WL_FSR[1])
    fsr = (r_nir - r_red) / (r_nir + r_red) if (r_nir + r_red) else np.nan

    return {
        "NDVI": ndvi, "PRI": pri, "PSRI": psri, "CARI": cari,
        "RCI": rci, "EDI": edi, "FSR": fsr,
    }


def severity_score(values: dict, baseline: dict) -> dict | None:
    """Normaliza los indices de un archivo a un score de severidad de roya, 0 (sana) a 1 (enferma).

    `values`: salida de `calcular_indices()` para ese archivo.
    `baseline`: dict {indice: {"sana": ancla_hoja_tierna, "enferma": ancla_hoja_con_roya}} de
    la especie de ese archivo (ver `_severity_baselines()` en app.py). La hoja Tierna se usa
    como ancla sana porque la roya todavia no tuvo tiempo de manifestarse en tejido nuevo.

    Cada indice se normaliza por separado entre sus dos anclas (con clip a 0-1) y el score
    final es la mediana de esos valores — mas robusto ante un indice atipico que el promedio,
    y permite combinar los 7 indices en una sola lectura sin que uno solo domine el resultado.
    """
    normalizados = {}
    for idx_name, value in values.items():
        ref = baseline.get(idx_name)
        if ref is None or value is None or np.isnan(value):
            continue
        sana, enferma = ref["sana"], ref["enferma"]
        if sana is None or enferma is None or np.isnan(sana) or np.isnan(enferma) or sana == enferma:
            continue
        normalizados[idx_name] = float(np.clip((value - sana) / (enferma - sana), 0.0, 1.0))

    if not normalizados:
        return None

    scores = list(normalizados.values())
    return {
        "score": float(np.median(scores)),
        "n_indices": len(scores),
        "detalle": normalizados,
    }


def average_group(dfs: list[pd.DataFrame], n_points: int = 1000) -> pd.DataFrame | None:
    """Interpola espectros suavizados a una grilla comun y calcula media y SD."""
    if not dfs:
        return None
    wl_min = max(d["wavelength"].min() for d in dfs)
    wl_max = min(d["wavelength"].max() for d in dfs)
    if wl_min >= wl_max:
        return None
    grid = np.linspace(wl_min, wl_max, n_points)
    interp = [np.interp(grid, d["wavelength"], d["smooth"]) for d in dfs]
    matrix = np.array(interp)
    return pd.DataFrame({
        "wavelength": grid,
        "mean": matrix.mean(axis=0),
        "std": matrix.std(axis=0, ddof=1) if len(dfs) > 1 else np.zeros(n_points),
    })
