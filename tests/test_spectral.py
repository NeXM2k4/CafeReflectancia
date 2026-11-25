"""Analisis espectral por hoja (docs/plan_analisis_espectral.md, seccion 6): sinteticos de resultado conocido + datos reales."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from src import spectral as sp
from src.config import DELTA_REGIONS, NDVI_SIN_HOJA, SPECTRAL_WL
from src.parser import get_dataset
from src.temporal import file_indices, leaf_mean_spectra, leaf_timeseries, leaf_trends

WL = np.linspace(440, 900, 246)


def _logistic(center=720.0, width=12.0, lo=5.0, hi=50.0):
    return lo + (hi - lo) / (1 + np.exp(-(WL - center) / width))


def test_normalize_invariante_a_escala_y_media_uno():
    R = np.vstack([_logistic(), 3 * _logistic()])
    for m in ("area", "nir"):
        N = sp.normalize(R, WL, m)
        np.testing.assert_allclose(N[0], N[1])
    N = sp.normalize(R, WL, "area")
    np.testing.assert_allclose(N[:, (WL >= 440) & (WL <= 900)].mean(axis=1), 1.0)
    np.testing.assert_allclose(sp.normalize(R, WL, "none"), R)


def test_derivada_de_una_recta_y_de_una_logistica():
    d1 = sp.derivative(2.0 + 0.05 * WL, WL, 1)
    np.testing.assert_allclose(d1[10:-10], 0.05, atol=1e-8)
    R = _logistic()[None, :]
    d = sp.derivative(R, WL, 1)[0]
    assert abs(WL[np.nanargmax(d)] - 720) <= 1.0
    feats = sp.spectral_features(R, WL)
    assert abs(feats[sp.F_REP_MAX].iloc[0] - 720) < 1.0
    assert feats[sp.F_DMAX].iloc[0] == pytest.approx(45 / (4 * 12), rel=0.05)


def test_spearman_monotona_y_pocas_fechas():
    dias = np.arange(10) * 7.0
    Y = np.outer(np.arange(1, 11), np.ones(5)) * (1 + np.arange(5))
    out = sp.spearman_by_wl(Y, dias)
    assert np.allclose(out["rho"], 1.0) and (out["p_fdr"] < 0.05).all()
    corto = sp.spearman_by_wl(Y[:4], dias[:4])
    assert corto["rho"].notna().all() and corto["p"].isna().all() and corto["p_fdr"].isna().all()


def test_spearman_coincide_con_scipy_y_columna_constante():
    rng = np.random.default_rng(1)
    Y = rng.normal(size=(12, 6))
    Y[:, 2] = 3.0
    dias = np.sort(rng.choice(200, 12, replace=False)).astype(float)
    out = sp.spearman_by_wl(Y, dias)
    for j in (0, 1, 3, 4, 5):
        r, p = spearmanr(Y[:, j], dias)
        assert out["rho"][j] == pytest.approx(r) and out["p"][j] == pytest.approx(p)
    assert np.isnan(out["rho"][2]) and np.isnan(out["p"][2])


def test_delta_las_filas_base_promedian_cero():
    rng = np.random.default_rng(2)
    R = rng.normal(30, 5, size=(8, 20))
    D = sp.delta_vs_baseline(R, 2)
    np.testing.assert_allclose(D[:2].mean(axis=0), 0, atol=1e-12)
    np.testing.assert_allclose(sp.delta_vs_baseline(R, 1)[0], 0, atol=1e-12)


def test_region_means():
    Y = np.vstack([np.ones(len(WL)), 2 * np.ones(len(WL))])
    t = sp.region_means(Y, WL, DELTA_REGIONS)
    assert list(t.columns) == list(DELTA_REGIONS) and t.iloc[1].eq(2).all()


def test_pca_rango_uno_y_orientacion():
    rng = np.random.default_rng(3)
    t = np.arange(10, dtype=float)
    perfil = rng.normal(size=40)
    R = 20 + (10 - t)[:, None] * perfil[None, :]  # el puntaje decrece con el tiempo
    out = sp.pca(R, 3, dias=t * 7)
    assert out["explained"][0] == pytest.approx(1.0)
    assert spearmanr(out["scores"][:, 0], t)[0] >= 0
    assert out["scores"].shape == (10, 3) and out["loadings"].shape == (3, 40)


def test_sam():
    v = np.array([1.0, 2.0, 3.0])
    assert sp.sam_deg(v, 3 * v) == pytest.approx(0, abs=1e-6)
    assert sp.sam_deg(np.array([1.0, 0.0]), np.array([0.0, 1.0])) == pytest.approx(90)
    out = sp.sam_deg(np.vstack([v, v]), v[None, :])
    assert out.shape == (2,)


def test_rep_lineal_de_un_espectro_lineal():
    R = (10 + 0.1 * (WL - 670))[None, :]  # lineal en todo el rango: R670, R700, R740, R780 colineales
    f = sp.spectral_features(R, WL)
    assert f[sp.F_REP_LIN].iloc[0] == pytest.approx(725.0, abs=1e-6)


def test_features_nan_no_rompe():
    R = np.full((2, len(WL)), np.nan)
    f = sp.spectral_features(R, WL)
    assert f.shape == (2, len(sp.SHAPE_FEATURES)) and f.isna().all().all()
    assert set(sp.FEATURE_DEFINITIONS) == set(sp.FEATURE_COLUMNS)


# ----------------------------------------------------------------------------- datos reales
@pytest.fixture(scope="module")
def real():
    files, _ = file_indices(get_dataset())
    files = files[files["NDVI"] >= NDVI_SIN_HOJA]
    ts = leaf_timeseries(files)
    spectra = leaf_mean_spectra(files[["leaf_id", "campaign_date", "point", "path"]])
    return ts, spectra


def test_tablas_con_las_18_hojas_y_leaf_trends(real):
    ts, spectra = real
    n_hojas = ts["leaf_id"].nunique()
    assert n_hojas == 18
    feats = sp.features_table(spectra, ts)
    rd = sp.region_delta_table(spectra, ts, "area", 2)
    needed = {"species", "leaf_id", "leaf", "leaf_type", "campaign_date", "dia"}
    for tabla, cols in ((feats, sp.FEATURE_COLUMNS), (rd, list(DELTA_REGIONS))):
        assert tabla["leaf_id"].nunique() == n_hojas
        assert needed <= set(tabla.columns) and set(cols) <= set(tabla.columns)
        tr = leaf_trends(tabla, cols, "prueba")
        assert len(tr) == n_hojas * len(cols)
    # SAM R1 solo en M/T de variedades con R; SAM base de la primera fecha ~ 0 con n_base=1
    assert feats.loc[feats["leaf_type"] == "R", sp.F_SAM_R1].isna().all()
    assert feats[sp.F_SAM_R1].notna().any()
    assert feats[sp.F_REP_MAX].between(680, 760).all()
    f1 = sp.features_table(spectra, ts, n_base=1)
    primera = f1.sort_values("campaign_date").groupby("leaf_id").head(1)
    assert (primera[sp.F_SAM_BASE] < 1e-3).all()


def test_leaf_matrix_real(real):
    ts, spectra = real
    lm = sp.leaf_matrix(spectra, ts["leaf_id"].iloc[0], t_cero=ts["campaign_date"].min())
    assert lm.R.shape == (lm.n_dates, len(lm.wl)) and lm.wl.min() >= SPECTRAL_WL[0] and lm.wl.max() <= SPECTRAL_WL[1]
    assert (np.diff(lm.dias) > 0).all() and lm.n_puntos.min() >= 1
