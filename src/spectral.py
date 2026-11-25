"""Analisis espectral por hoja: derivadas, correlacion con el tiempo, cambio vs linea base, PCA y rasgos.

Calculo puro (numpy / pandas / scipy), sin Streamlit. La unidad es la hoja-fecha (espectro medio de
p1-p3, `temporal.leaf_mean_spectra`); las hojas nunca se promedian entre si. Decisiones de metodo
en docs/plan_analisis_espectral.md (seccion 3).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from scipy.stats import rankdata, spearmanr
from scipy.stats import t as t_dist
from statsmodels.stats.multitest import multipletests

from src.config import (
    DELTA_REGIONS,
    SPECTRAL_DERIV_POLY,
    SPECTRAL_DERIV_WINDOW,
    SPECTRAL_WL,
    TEMPORAL_BASELINE_CAMPAIGNS,
    TEMPORAL_MIN_FECHAS_TENDENCIA,
)

NIR_PLATEAU = (750, 900)

# Nombres de las columnas de rasgos (las paginas los referencian por constante)
F_REP_MAX = "REP máx (nm)"
F_REP_LIN = "REP lineal (nm)"
F_DMAX = "D máx (%/nm)"
F_DOBLE = "Doble pico"
F_LGREEN = "λ verde (nm)"
F_RGREEN = "R verde (%)"
F_PROF = "Prof. clorofila"
F_AREA = "Área clorofila (nm)"
F_SAM_BASE = "SAM base (°)"
F_SAM_R1 = "SAM R1 (°)"
SHAPE_FEATURES = [F_REP_MAX, F_REP_LIN, F_DMAX, F_DOBLE, F_LGREEN, F_RGREEN, F_PROF, F_AREA]  # salida de spectral_features
FEATURE_COLUMNS = SHAPE_FEATURES + [F_SAM_BASE, F_SAM_R1]  # todas las de features_table

# nombre -> (unidad, definicion, por que)
FEATURE_DEFINITIONS = {
    F_REP_MAX: ("nm", "λ del máximo de dR/dλ entre 680 y 760 nm, refinado con una parábola sobre 3 puntos.",
                "Posición del borde rojo (clorofila); los índices solo ven su pendiente."),
    F_REP_LIN: ("nm", "Guyot y Baret (1988): Rre = (R670 + R780)/2; 700 + 40·(Rre − R700)/(R740 − R700).",
                "Robusto al doble pico del borde rojo."),
    F_DMAX: ("%/nm", "Máximo de dR/dλ entre 680 y 760 nm.", "Amplitud (empinamiento) del borde rojo."),
    F_DOBLE: ("razón", "Máx. dR/dλ en 695–712 nm dividido por el máx. dR/dλ en 715–735 nm.",
              "Visible como doble pico de la derivada; se asocia a estrés."),
    F_LGREEN: ("nm", "λ del máximo de R entre 500 y 600 nm.", "Posición del pico verde."),
    F_RGREEN: ("%", "Valor de R en el máximo entre 500 y 600 nm.", "Altura del pico verde."),
    F_PROF: ("fracción", "1 − R/Rc mínimo entre 600 y 720 nm, con continuo lineal Rc entre 540 y 760 nm.",
             "Profundidad del pozo de absorción de clorofila, independiente del nivel de reflectancia."),
    F_AREA: ("nm", "∫ (1 − R/Rc) dλ entre 540 y 760 nm (mismo continuo lineal).", "Lo mismo, integrado."),
    F_SAM_BASE: ("°", "Ángulo espectral (440–900 nm) contra la línea base de la hoja (primeras fechas).",
                 "Cambio de forma total, invariante a la escala."),
    F_SAM_R1: ("°", "Ángulo espectral contra R1 de su variedad el mismo día (solo M y T de variedades con R).",
               "Parecido de forma con la hoja con roya."),
}


@dataclass
class LeafMatrix:
    leaf_id: str
    dates: pd.DatetimeIndex  # ordenadas
    dias: np.ndarray  # dias desde la primera campaña del dataset
    wl: np.ndarray
    R: np.ndarray  # n_fechas x n_wl, % crudo
    n_puntos: np.ndarray  # int, puntos p1-p3 promediados en cada fecha
    sd: np.ndarray  # n_fechas x n_wl, SD entre puntos (NaN con un solo punto)

    @property
    def n_dates(self) -> int:
        return len(self.dates)


def leaf_matrix(spectra: pd.DataFrame, leaf_id: str, wl=SPECTRAL_WL, t_cero=None) -> LeafMatrix:
    """Matriz fechas x λ de una hoja a partir de `temporal.leaf_mean_spectra` (recortada a `wl`).

    `t_cero`: fecha del dia 0; por defecto la primera fecha de `spectra` (todas las hojas).
    """
    if t_cero is None:
        t_cero = spectra["campaign_date"].min()
    s = spectra[(spectra["leaf_id"] == leaf_id) & spectra["wavelength"].between(wl[0], wl[1])]
    if s.empty:
        z = np.empty((0, 0))
        return LeafMatrix(leaf_id, pd.DatetimeIndex([]), np.empty(0), np.empty(0), z, np.empty(0, int), z)
    R = s.pivot(index="campaign_date", columns="wavelength", values="mean").sort_index()
    sd = s.pivot(index="campaign_date", columns="wavelength", values="sd").reindex(R.index)
    npts = s.groupby("campaign_date")["n_puntos"].first().reindex(R.index)
    dates = pd.DatetimeIndex(R.index)
    return LeafMatrix(
        leaf_id=leaf_id, dates=dates, dias=(dates - pd.Timestamp(t_cero)).days.to_numpy(float),
        wl=R.columns.to_numpy(float), R=R.to_numpy(float), n_puntos=npts.to_numpy(int), sd=sd.to_numpy(float),
    )


def _mask(wl, lo, hi) -> np.ndarray:
    wl = np.asarray(wl)
    return (wl >= lo) & (wl <= hi)


def normalize(R, wl, method: str = "area") -> np.ndarray:
    """"area": R / media(R, 440-900); "nir": R / media(R, 750-900); "none": sin cambios (copia)."""
    R = np.asarray(R, float)
    if method == "none":
        return R.copy()
    rng = {"area": SPECTRAL_WL, "nir": NIR_PLATEAU}[method]
    m = _mask(wl, *rng)
    with np.errstate(invalid="ignore", divide="ignore"):
        ref = np.nanmean(R[..., m], axis=-1, keepdims=True)
        return R / np.where(ref == 0, np.nan, ref)


def _fill_nan_1d(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    bad = np.isnan(y)
    if not bad.any() or bad.all():
        return y
    out = y.copy()
    out[bad] = np.interp(x[bad], x[~bad], y[~bad])
    return out


def derivative(R, wl, order: int, window: int = SPECTRAL_DERIV_WINDOW, poly: int = SPECTRAL_DERIV_POLY) -> np.ndarray:
    """Derivada de Savitzky-Golay sobre la grilla uniforme (delta = paso medio de la grilla).

    Unidades: R/nm (order 1) o R/nm² (order 2). Las filas con NaN se interpolan solo para el filtro
    y quedan NaN si no hay ningun dato.
    """
    R = np.asarray(R, float)
    wl = np.asarray(wl, float)
    delta = float(np.median(np.diff(wl)))
    window = min(window, len(wl) - (1 - len(wl) % 2))  # impar y <= largo
    if window <= poly:
        return np.full_like(R, np.nan)
    flat = R.reshape(-1, R.shape[-1])
    out = np.full_like(flat, np.nan)
    for i, y in enumerate(flat):
        if np.isnan(y).all():
            continue
        out[i] = savgol_filter(_fill_nan_1d(y, wl), window, poly, deriv=order, delta=delta)
    return out.reshape(R.shape)


def spearman_by_wl(Y, dias, min_fechas: int = TEMPORAL_MIN_FECHAS_TENDENCIA, wl=None) -> pd.DataFrame:
    """ρ de Spearman entre cada columna de Y (fechas x λ) y `dias`, con p bilateral y FDR de BH.

    p y p_fdr son NaN si hay menos de `min_fechas` fechas validas o la columna / el tiempo es constante.
    Equivale a `scipy.stats.spearmanr` por columna, vectorizado.
    """
    Y = np.asarray(Y, float)
    x = np.asarray(dias, float)
    n_wl = Y.shape[1]
    wl = np.arange(n_wl, dtype=float) if wl is None else np.asarray(wl, float)
    rho = np.full(n_wl, np.nan)
    p = np.full(n_wl, np.nan)
    ok_col = ~np.isnan(Y).any(axis=0)
    n = len(x)
    if ok_col.any() and n >= 3 and np.ptp(x) > 0:
        rx = rankdata(x)
        ry = rankdata(Y[:, ok_col], axis=0)
        rx_c = rx - rx.mean()
        ry_c = ry - ry.mean(axis=0)
        den = np.sqrt((rx_c ** 2).sum() * (ry_c ** 2).sum(axis=0))
        with np.errstate(invalid="ignore", divide="ignore"):
            r = (rx_c[:, None] * ry_c).sum(axis=0) / den
        r = np.where(den > 0, np.clip(r, -1, 1), np.nan)
        rho[ok_col] = r
        if n >= min_fechas:
            with np.errstate(invalid="ignore", divide="ignore"):
                t = r * np.sqrt((n - 2) / (1 - r ** 2))
            pv = 2 * t_dist.sf(np.abs(t), n - 2)
            pv = np.where(np.abs(r) >= 1, 0.0, pv)
            pv = np.where(np.isnan(r), np.nan, pv)
            p[ok_col] = pv
    p_fdr = np.full(n_wl, np.nan)
    ev = ~np.isnan(p)
    if ev.any():
        p_fdr[ev] = multipletests(p[ev], method="fdr_bh")[1]
    return pd.DataFrame({"wavelength": wl, "rho": rho, "p": p, "p_fdr": p_fdr})


def delta_vs_baseline(R, n_base: int = TEMPORAL_BASELINE_CAMPAIGNS) -> np.ndarray:
    """R − media de las primeras `n_base` fechas (filas) de la propia hoja."""
    R = np.asarray(R, float)
    if len(R) == 0:
        return R.copy()
    return R - np.nanmean(R[: max(1, n_base)], axis=0)


def region_means(Y, wl, regions: dict | None = None) -> pd.DataFrame:
    """Media de Y (fechas x λ) en cada region (λ0, λ1): DataFrame fechas x regiones."""
    regions = DELTA_REGIONS if regions is None else regions
    Y = np.asarray(Y, float)
    cols = {}
    for name, (lo, hi) in regions.items():
        m = _mask(wl, lo, hi)
        cols[name] = np.nanmean(Y[:, m], axis=1) if m.any() else np.full(len(Y), np.nan)
    return pd.DataFrame(cols)


def pca(R, n_comp: int = 3, dias=None) -> dict:
    """PCA de la matriz fechas x λ, centrada por λ y sin escalar (SVD de numpy).

    Devuelve scores (n x k), loadings (k x n_wl), explained (k,), mean (n_wl,). Con `dias`, cada PC se
    orienta para que su puntaje tenga ρ de Spearman >= 0 con el tiempo (si ρ = 0 exacto o no definido,
    queda el signo de la SVD). Si hay menos de k componentes posibles, se rellena con NaN.
    """
    R = np.asarray(R, float)
    n, n_wl = R.shape
    scores = np.full((n, n_comp), np.nan)
    loadings = np.full((n_comp, n_wl), np.nan)
    explained = np.full(n_comp, np.nan)
    mean = np.nanmean(R, axis=0) if n else np.full(n_wl, np.nan)
    if n < 2 or np.isnan(R).any():
        return {"scores": scores, "loadings": loadings, "explained": explained, "mean": mean}
    X = R - mean
    U, S, Vt = np.linalg.svd(X, full_matrices=False)
    k = min(n_comp, len(S))
    sc = U[:, :k] * S[:k]
    ld = Vt[:k].copy()
    if dias is not None and n >= 3:
        for j in range(k):
            rho = spearmanr(sc[:, j], dias)[0] if np.ptp(sc[:, j]) > 1e-12 and np.ptp(dias) > 0 else np.nan
            if not np.isnan(rho) and rho < 0:
                sc[:, j] *= -1
                ld[j] *= -1
    tot = (S ** 2).sum()
    scores[:, :k], loadings[:k] = sc, ld
    if tot > 0:
        explained[:k] = S[:k] ** 2 / tot
    return {"scores": scores, "loadings": loadings, "explained": explained, "mean": mean}


def sam_deg(a, b) -> float | np.ndarray:
    """Angulo espectral en grados entre a y b (eje λ al final). NaN si algun vector es nulo o tiene NaN."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    dot = (a * b).sum(axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        cos = dot / (np.linalg.norm(a, axis=-1) * np.linalg.norm(b, axis=-1))
    ang = np.degrees(np.arccos(np.clip(cos, -1, 1)))
    return float(ang) if np.ndim(ang) == 0 else ang


def _argmax_in(Y: np.ndarray, wl: np.ndarray, lo: float, hi: float):
    """(indice global, valor) del maximo de cada fila de Y dentro de [lo, hi]; NaN si no hay datos."""
    idx = np.flatnonzero(_mask(wl, lo, hi))
    if len(idx) == 0:
        return np.full(len(Y), -1), np.full(len(Y), np.nan)
    sub = Y[:, idx]
    allnan = np.isnan(sub).all(axis=1)
    j = np.argmax(np.where(np.isnan(sub), -np.inf, sub), axis=1)
    val = sub[np.arange(len(Y)), j]
    val = np.where(allnan, np.nan, val)
    return np.where(allnan, -1, idx[j]), val


def spectral_features(R, wl, dR=None) -> pd.DataFrame:
    """Rasgos de forma (SHAPE_FEATURES) de cada fila (fecha) de R (fechas x λ, % crudo)."""
    R = np.atleast_2d(np.asarray(R, float))
    wl = np.asarray(wl, float)
    if dR is None:
        dR = derivative(R, wl, 1)
    n = len(R)
    rows = np.arange(n)
    out = {}

    # REP maximo con refinamiento parabolico
    i_max, d_max = _argmax_in(dR, wl, 680, 760)
    rep = np.full(n, np.nan)
    for r in range(n):
        i = i_max[r]
        if i < 0:
            continue
        rep[r] = wl[i]
        if 0 < i < len(wl) - 1:
            y0, y1, y2 = dR[r, i - 1], dR[r, i], dR[r, i + 1]
            den = y0 - 2 * y1 + y2
            if np.isfinite(den) and den < 0:
                off = float(np.clip(0.5 * (y0 - y2) / den, -1, 1))
                rep[r] = wl[i] + off * (wl[i + 1] - wl[i - 1]) / 2
    out[F_REP_MAX] = rep

    # REP lineal (Guyot y Baret 1988)
    def at(w):
        return np.array([np.interp(w, wl, y) if not np.isnan(y).all() else np.nan for y in R])
    r670, r700, r740, r780 = at(670), at(700), at(740), at(780)
    with np.errstate(invalid="ignore", divide="ignore"):
        den = r740 - r700
        out[F_REP_LIN] = np.where(den != 0, 700 + 40 * ((r670 + r780) / 2 - r700) / den, np.nan)
    out[F_DMAX] = d_max

    # doble pico
    _, a = _argmax_in(dR, wl, 695, 712)
    _, b = _argmax_in(dR, wl, 715, 735)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[F_DOBLE] = np.where(b > 0, a / b, np.nan)

    # pico verde
    ig, rg = _argmax_in(R, wl, 500, 600)
    out[F_LGREEN] = np.where(ig >= 0, wl[np.maximum(ig, 0)], np.nan)
    out[F_RGREEN] = rg

    # pozo de clorofila con continuo lineal 540-760
    r540, r760 = at(540), at(760)
    m = _mask(wl, 540, 760)
    wm = wl[m]
    frac = (wm[None, :] - 540) / (760 - 540)
    rc = r540[:, None] + (r760 - r540)[:, None] * frac
    with np.errstate(invalid="ignore", divide="ignore"):
        depth = 1 - R[:, m] / np.where(rc == 0, np.nan, rc)
    m2 = (wm >= 600) & (wm <= 720)
    if m2.any():
        d2 = depth[:, m2]
        out[F_PROF] = np.where(np.isnan(d2).all(axis=1), np.nan, np.max(np.where(np.isnan(d2), -np.inf, d2), axis=1))
    else:
        out[F_PROF] = np.full(n, np.nan)
    ok = ~np.isnan(depth).any(axis=1)
    area = np.full(n, np.nan)
    if len(wm) > 1:
        trapz = getattr(np, "trapezoid", None) or np.trapz
        area[ok] = trapz(depth[ok], wm, axis=1)
    out[F_AREA] = area
    return pd.DataFrame({k: out[k] for k in SHAPE_FEATURES}, index=rows)


def _leaf_meta(meta: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in ["species", "leaf_id", "leaf", "leaf_type", "leaf_num"] if c in meta.columns]
    return meta[cols].drop_duplicates("leaf_id").reset_index(drop=True)


def _matrices(spectra: pd.DataFrame, meta: pd.DataFrame) -> dict:
    t0 = meta["campaign_date"].min()
    return {lid: leaf_matrix(spectra, lid, t_cero=t0) for lid in meta["leaf_id"].unique()}


def features_table(spectra: pd.DataFrame, meta: pd.DataFrame, n_base: int = TEMPORAL_BASELINE_CAMPAIGNS) -> pd.DataFrame:
    """Rasgos de todas las hojas-fecha: claves de hoja + campaign_date + dia + FEATURE_COLUMNS.

    SAM base: contra la media de las primeras `n_base` fechas de la hoja. SAM R1: contra R1 de la misma
    variedad el mismo dia, solo para hojas M y T de variedades que tienen una hoja R; NaN en el resto.
    """
    mats = _matrices(spectra, meta)
    info = _leaf_meta(meta).set_index("leaf_id")
    r_of_species = {r.species: r.Index for r in info.itertuples() if r.leaf_type == "R"}
    partes = []
    for lid, lm in mats.items():
        if lm.n_dates == 0 or lid not in info.index:
            continue
        f = spectral_features(lm.R, lm.wl)
        base = np.nanmean(lm.R[: max(1, n_base)], axis=0)
        f[F_SAM_BASE] = sam_deg(lm.R, base[None, :])
        f[F_SAM_R1] = np.nan
        row = info.loc[lid]
        rid = r_of_species.get(row["species"])
        if row["leaf_type"] in ("M", "T") and rid is not None and mats[rid].n_dates:
            rm = mats[rid]
            pos = pd.Series(np.arange(rm.n_dates), index=rm.dates)
            j = pos.reindex(lm.dates).to_numpy()
            has = ~np.isnan(j)
            if has.any() and lm.R.shape[1] == rm.R.shape[1]:
                f.loc[has, F_SAM_R1] = sam_deg(lm.R[has], rm.R[j[has].astype(int)])
        for k, v in info.loc[lid].items():
            f[k] = v
        f["leaf_id"] = lid
        f["campaign_date"] = lm.dates
        f["dia"] = lm.dias.astype(int)
        f["n_puntos"] = lm.n_puntos
        partes.append(f)
    if not partes:
        return pd.DataFrame()
    out = pd.concat(partes, ignore_index=True)
    keys = [c for c in ["species", "leaf_id", "leaf", "leaf_type", "leaf_num"] if c in out.columns]
    return out[[*keys, "campaign_date", "dia", "n_puntos", *FEATURE_COLUMNS]]


def region_delta_table(spectra: pd.DataFrame, meta: pd.DataFrame, norm_method: str = "area",
                       n_base: int = TEMPORAL_BASELINE_CAMPAIGNS) -> pd.DataFrame:
    """Δ medio por region vs la linea base de cada hoja, apto para `temporal.leaf_trends`.

    Columnas: claves de hoja, campaign_date, dia, es_base (bool) y una columna por region de
    DELTA_REGIONS. `norm_method`: "none" (cruda), "area" o "nir".
    """
    mats = _matrices(spectra, meta)
    info = _leaf_meta(meta).set_index("leaf_id")
    partes = []
    for lid, lm in mats.items():
        if lm.n_dates == 0 or lid not in info.index:
            continue
        Y = normalize(lm.R, lm.wl, norm_method)
        reg = region_means(delta_vs_baseline(Y, n_base), lm.wl, DELTA_REGIONS)
        for k, v in info.loc[lid].items():
            reg[k] = v
        reg["leaf_id"] = lid
        reg["campaign_date"] = lm.dates
        reg["dia"] = lm.dias.astype(int)
        reg["es_base"] = np.arange(lm.n_dates) < max(1, n_base)
        partes.append(reg)
    if not partes:
        return pd.DataFrame()
    out = pd.concat(partes, ignore_index=True)
    keys = [c for c in ["species", "leaf_id", "leaf", "leaf_type", "leaf_num"] if c in out.columns]
    return out[[*keys, "campaign_date", "dia", "es_base", *DELTA_REGIONS]]


def baseline_noise(lm: LeafMatrix, n_base: int = TEMPORAL_BASELINE_CAMPAIGNS) -> pd.Series:
    """Ruido de referencia por region: SD entre puntos p1-p3 (cruda, %), promediada en las fechas base."""
    sd = region_means(lm.sd[: max(1, n_base)], lm.wl, DELTA_REGIONS)
    return sd.mean(axis=0)
