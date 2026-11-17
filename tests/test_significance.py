"""Asteriscos de significancia (cajas y tendencias) y la curva LOWESS de la evolucion temporal."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.stats_utils import pairwise_effects, stars
from src.temporal_plots import lowess_curve
from src.viz_groups import _brackets


def test_stars_umbral():
    assert [stars(p) for p in (0.0009, 0.001, 0.009, 0.049, 0.05, np.nan, None)] == ["***", "**", "**", "*", "ns", "", ""]


def _datos():
    rng = np.random.default_rng(0)
    return pd.DataFrame({
        "g": ["T"] * 12 + ["M"] * 12 + ["R"] * 12,
        "x": np.r_[rng.normal(0, 1, 12), rng.normal(0.2, 1, 12), rng.normal(4, 1, 12)],
    })


def test_corchetes_usan_el_p_holm_de_la_tabla():
    d = _datos()
    orden = ["T", "M", "R"]
    tabla = pairwise_effects(d, "g", ["x"], [("R", "T"), ("R", "M"), ("M", "T")])
    formas, textos, rango = _brackets(tabla, orden, d["x"].to_numpy(), "x", "y", solo_significativos=False)
    assert len(formas) == len(textos) == 3
    esperado = {(min(orden.index(a), orden.index(b)), max(orden.index(a), orden.index(b))): stars(p)
                for a, b, p in zip(tabla["A"], tabla["B"], tabla["p Holm"])}
    for f, t in zip(formas, textos):
        xs = [float(tok.split(",")[0]) for tok in f["path"].replace("M ", "").replace("L ", "").split(" ") if "," in tok]
        assert t["text"] == esperado[(int(min(xs)), int(max(xs)))]
    # El rango Y contiene el corchete mas alto.
    assert rango[1] > max(t["y"] for t in textos)
    # Primero los pares vecinos (T-M, M-R), al final el que salta (T-R), mas arriba.
    assert textos[-1]["y"] == max(t["y"] for t in textos)


def test_corchetes_solo_significativos():
    d = _datos()
    tabla = pairwise_effects(d, "g", ["x"], [("R", "T"), ("R", "M"), ("M", "T")])
    _, textos, _ = _brackets(tabla, ["T", "M", "R"], d["x"].to_numpy(), "x", "y", solo_significativos=True)
    assert all(t["text"] != "ns" for t in textos)
    assert len(textos) == int((tabla["p Holm"] < 0.05).sum())


def test_lowess_minimo_de_fechas_y_huecos():
    assert lowess_curve(np.arange(4) * 7.0, np.arange(4.0)) is None
    dias = np.array([0, 7, 14, np.nan, 28, 35, 42], float)
    y = np.array([1, 2, 3, 4, np.nan, 6, 7], float)  # una fecha sin dia y otra sin valor: quedan 5
    xs, ys = lowess_curve(dias, y)
    assert xs[0] == 0 and xs[-1] == 42 and np.all(np.isfinite(ys))
    # Una recta exacta se reproduce (LOWESS local lineal).
    xs, ys = lowess_curve(np.arange(8) * 7.0, 2 + 0.5 * np.arange(8))
    np.testing.assert_allclose(ys, 2 + 0.5 * xs / 7.0, atol=1e-9)
