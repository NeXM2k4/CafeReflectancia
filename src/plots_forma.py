"""Figuras de las paginas «Derivadas espectrales» y «Correlación con el tiempo» (funciones puras, sin Streamlit).

Reciben arreglos / DataFrames ya calculados (`src/spectral.py`) y devuelven figuras de Plotly sin
plantilla propia; `ui.chart` las dibuja. Ver docs/plan_analisis_espectral.md (secciones 3.3, 3.4 y 5).
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import DERIV_REGIONS, SHADE_BANDS
from src.spectral_plots import add_region_shading, date_colorbar_trace, date_colors
from src.ui import DIVERGING_SCALE, INK, add_hlines_all

SIG_COLOR = "#C8402F"
ALPHA = 0.05


def _band_legend_color(rgba_str: str) -> str:
    """Mismo color de la franja pero mas opaco, para que se vea en la leyenda."""
    return re.sub(r"[\d.]+\)$", "0.55)", rgba_str)


def _sig_masks(corr: pd.DataFrame):
    fdr = (corr["p_fdr"] < ALPHA).to_numpy()
    raw = ((corr["p"] < ALPHA) & ~(corr["p_fdr"] < ALPHA)).to_numpy()
    return fdr, raw


def _add_rho(fig, corr: pd.DataFrame, row: int, col: int, mask=None, legend: bool = False,
             line_w: float = 1.6, marker: int = 5):
    """Curva de ρ vs λ (negra) con marcadores rojos: rellenos p_FDR<0,05, huecos solo p<0,05."""
    c = corr if mask is None else corr[mask]
    x, rho = c["wavelength"].to_numpy(), c["rho"].to_numpy()
    fdr, raw = _sig_masks(c)
    hover = "%{x:.0f} nm · ρ = %{y:.2f}<extra></extra>"
    fig.add_trace(go.Scatter(x=x, y=rho, mode="lines", line=dict(color=INK, width=line_w), showlegend=False,
                             hovertemplate=hover), row=row, col=col)
    if raw.any():
        fig.add_trace(go.Scatter(
            x=x[raw], y=rho[raw], mode="markers", name="p < 0,05 sin corregir (hueco)", showlegend=legend,
            marker=dict(symbol="circle-open", color=SIG_COLOR, size=marker, line=dict(width=1.2)),
            hovertemplate="%{x:.0f} nm · ρ = %{y:.2f} · sin corregir<extra></extra>"), row=row, col=col)
    if fdr.any():
        fig.add_trace(go.Scatter(
            x=x[fdr], y=rho[fdr], mode="markers", name="p FDR < 0,05 (relleno)", showlegend=legend,
            marker=dict(symbol="circle", color=SIG_COLOR, size=marker),
            hovertemplate="%{x:.0f} nm · ρ = %{y:.2f} · FDR<extra></extra>"), row=row, col=col)


def _thin_ticks(dates, k: int = 6):
    idx = sorted(set(np.linspace(0, len(dates) - 1, min(k, len(dates))).round().astype(int)))
    return [dates[i] for i in idx]


def derivative_figure(dates, wl, Y_raw, Y_norm, corr_raw: pd.DataFrame, corr_norm: pd.DataFrame, labels,
                      order: int = 1, regions: dict | None = None, units_raw: str | None = None,
                      units_norm: str | None = None) -> go.Figure:
    """Derivada espectral de una hoja: 2 columnas (regiones) x [curvas, franja ρ] para cruda y normalizada.

    `Y_raw` / `Y_norm`: derivadas (fechas x λ). `corr_*`: salida de `spectral.spearman_by_wl` de esas derivadas.
    """
    regions = regions or DERIV_REGIONS
    wl = np.asarray(wl, float)
    dates = list(pd.DatetimeIndex(dates))
    cols = date_colors(dates)
    d = "d" if order == 1 else "d²"
    dl = "dλ" if order == 1 else "dλ²"
    un = {1: ("%/nm", "1/nm"), 2: ("%/nm²", "1/nm²")}[order]
    units_raw = units_raw or un[0]
    units_norm = units_norm or un[1]
    names = list(regions)
    titles = []
    for kind in ("cruda", "normalizada"):
        titles += [f"{n} · {kind}" for n in names] + [""] * len(names)
    fig = make_subplots(rows=4, cols=2, row_heights=[0.36, 0.14, 0.36, 0.14], vertical_spacing=0.075,
                        horizontal_spacing=0.07, subplot_titles=titles)
    blocks = [(1, Y_raw, corr_raw, units_raw, f"{d}R/{dl} ({units_raw})"),
              (3, Y_norm, corr_norm, units_norm, f"{d}R̃/{dl} ({units_norm})")]
    for r0, Y, corr, _u, ytitle in blocks:
        for j, (name, (lo, hi)) in enumerate(regions.items(), start=1):
            m = (wl >= lo) & (wl <= hi)
            for i, lab in enumerate(labels):
                fig.add_trace(go.Scatter(
                    x=wl[m], y=Y[i][m], mode="lines", line=dict(color=cols[i], width=1.2), showlegend=False,
                    hovertemplate=f"%{{x:.0f}} nm · %{{y:.4g}}<extra>{lab}</extra>"), row=r0, col=j)
            _add_rho(fig, corr, r0 + 1, j, mask=m, line_w=1, marker=4)
            fig.update_xaxes(range=[lo, hi], showticklabels=False, row=r0, col=j)
            fig.update_xaxes(range=[lo, hi], title_text="Longitud de onda (nm)" if r0 == 3 else None,
                             row=r0 + 1, col=j)
            fig.update_yaxes(range=[-1.05, 1.05], tickvals=[-1, 0, 1], row=r0 + 1, col=j)
            if j == 1:
                fig.update_yaxes(title_text=ytitle, title_font=dict(size=11), row=r0, col=j)
                fig.update_yaxes(title_text="ρ vs. tiempo", title_font=dict(size=10), row=r0 + 1, col=j)
    tick_dates = _thin_ticks(dates)
    fig.add_trace(date_colorbar_trace(tick_dates), row=1, col=2)  # marcas cortas dd-Mmm
    add_hlines_all(fig, 0)
    fig.update_layout(height=760, margin=dict(l=60, r=10, t=40, b=40), hovermode="closest")
    fig.update_annotations(font_size=12)
    return fig


def correlation_figure(corr_raw: pd.DataFrame, corr_norm: pd.DataFrame, xrange=None,
                       titles=("Reflectancia (cruda)", "Reflectancia normalizada (forma)")) -> go.Figure:
    """ρ de Spearman vs tiempo por λ, cruda | normalizada, con franjas de región y significancia."""
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04, subplot_titles=list(titles))
    for j, corr in enumerate((corr_raw, corr_norm), start=1):
        _add_rho(fig, corr, 1, j, legend=(j == 1))
    if xrange is None:
        w = corr_raw["wavelength"]
        xrange = (float(w.min()), float(w.max()))
    for j in (1, 2):
        add_region_shading(fig, 1, j, xrange=xrange)
        fig.update_xaxes(range=list(xrange), title_text="Longitud de onda (nm)", row=1, col=j)
    for name, lo, hi, color in SHADE_BANDS:  # entradas de leyenda de las franjas
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=f"{name} ({lo}–{hi})", hoverinfo="skip",
                                 marker=dict(symbol="square", size=11, color=_band_legend_color(color))),
                      row=1, col=1)
    add_hlines_all(fig, 0, color="rgba(40,40,35,0.4)")
    fig.update_yaxes(range=[-1.05, 1.05], title_text="ρ de Spearman vs. tiempo", row=1, col=1)
    fig.update_yaxes(range=[-1.05, 1.05], row=1, col=2)
    fig.update_layout(height=430, margin=dict(l=60, r=10, t=40, b=40), hovermode="closest",
                      legend=dict(orientation="h", yanchor="top", y=-0.2, x=0, font=dict(size=11)))
    fig.update_annotations(font_size=12)
    return fig


def all_leaves_heatmap(rho: np.ndarray, p_fdr: np.ndarray, wl, row_labels, groups=None, title: str | None = None,
                       dim_opacity: float = 0.3) -> go.Figure:
    """Mapa de calor hojas x λ de ρ (escala divergente simetrica en ±1).

    Las celdas con p_FDR >= 0,05 (o sin p, con menos de 5 fechas) se dibujan atenuadas: una capa con
    todos los valores a baja opacidad y encima otra opaca solo donde p_FDR < 0,05. `groups` (una clave
    por fila, p. ej. variedad) separa los bloques con una fila vacia.
    """
    rho = np.asarray(rho, float)
    p_fdr = np.asarray(p_fdr, float)
    sig = np.where(p_fdr < ALPHA, rho, np.nan)
    labels = list(row_labels)
    if groups is not None:  # filas vacias entre grupos
        R, S, P, L = [], [], [], []
        for i, g in enumerate(groups):
            if i and g != groups[i - 1]:
                for arr in (R, S, P):
                    arr.append(np.full(rho.shape[1], np.nan))
                L.append(" " * (len(L) + 1))
            R.append(rho[i]); S.append(sig[i]); P.append(p_fdr[i]); L.append(labels[i])
        rho, sig, p_fdr, labels = np.array(R), np.array(S), np.array(P), L
    wl = np.asarray(wl, float)
    ptxt = np.where(np.isnan(p_fdr), "sin p (< 5 fechas)", np.char.mod("%.3f", p_fdr))
    base = go.Heatmap(z=rho, x=wl, y=labels, colorscale=DIVERGING_SCALE, zmin=-1, zmax=1, zmid=0, opacity=dim_opacity,
                      showscale=False, customdata=ptxt, xgap=0, ygap=1,
                      hovertemplate="%{y}<br>%{x:.0f} nm · ρ = %{z:.2f}<br>p FDR: %{customdata}<extra></extra>")
    top = go.Heatmap(z=sig, x=wl, y=labels, colorscale=DIVERGING_SCALE, zmin=-1, zmax=1, zmid=0, hoverinfo="skip",
                     ygap=1, colorbar=dict(title=dict(text="ρ", font=dict(size=11)), thickness=12))
    fig = go.Figure([base, top])
    fig.update_yaxes(autorange="reversed", type="category")
    fig.update_xaxes(title_text="Longitud de onda (nm)")
    if title:
        fig.update_layout(title=title)
    fig.update_layout(height=max(380, 24 * len(labels) + 110), margin=dict(l=10, r=10, t=30, b=40),
                      plot_bgcolor="rgba(0,0,0,0)")
    return fig
