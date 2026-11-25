"""Ayudas comunes de Plotly para las paginas de analisis espectral (no fijan plantilla)."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.colors import sample_colorscale

from src.config import SHADE_BANDS
from src.ui import DIVERGING_SCALE, defer_layout_items, subplot_refs

DATE_SCALE = "Viridis"
_MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _short(d) -> str:
    return f"{d.day:02d}-{_MESES[d.month - 1]}"


def date_colors(dates) -> list[str]:
    """Color Viridis de cada fecha, proporcional al tiempo transcurrido (no al orden)."""
    t = np.array([d.toordinal() for d in dates], float)
    frac = np.zeros_like(t) if t.max() == t.min() else (t - t.min()) / (t.max() - t.min())
    return sample_colorscale(DATE_SCALE, list(np.clip(frac, 0, 1)))


def date_colorbar_trace(dates, labels=None, title: str = "Fecha") -> go.Scatter:
    """Traza invisible que dibuja una barra de color con las fechas como marcas. Agregar una sola vez."""
    t = np.array([d.toordinal() for d in dates], float)
    labels = labels or [_short(d) for d in dates]
    return go.Scatter(
        x=[None], y=[None], mode="markers", showlegend=False, hoverinfo="skip",
        marker=dict(colorscale=DATE_SCALE, cmin=t.min(), cmax=max(t.max(), t.min() + 1), color=[t.min()],
                    showscale=True,
                    colorbar=dict(title=dict(text=title, font=dict(size=11)), tickmode="array", tickvals=list(t),
                                  ticktext=list(labels), tickfont=dict(size=9), len=0.9, thickness=12)),
    )


def add_region_shading(fig, row=None, col=None, xrange=None, bands=SHADE_BANDS, labels: bool = False):
    """Franjas de regiones (SHADE_BANDS) detras de un subgrafico; solo las que caen en `xrange`."""
    x, y = subplot_refs(fig, row, col)
    shapes, anns = [], []
    for name, lo, hi, color in bands:
        if xrange is not None:
            if hi < xrange[0] or lo > xrange[1]:
                continue
            lo, hi = max(lo, xrange[0]), min(hi, xrange[1])
        shapes.append(dict(type="rect", xref=x, yref=f"{y} domain", x0=lo, x1=hi, y0=0, y1=1,
                           fillcolor=color, line=dict(width=0), layer="below"))
        if labels:
            anns.append(dict(xref=x, yref=f"{y} domain", x=(lo + hi) / 2, y=1, text=name, showarrow=False,
                             yanchor="bottom", font=dict(size=9, color="#6B6A64")))
    defer_layout_items(fig, shapes=shapes, annotations=anns)


def heatmap_trace(Z, wl, row_labels, zmax=None, colorbar_title: str = "Δ", base_n: int = 0, **kw) -> go.Heatmap:
    """Mapa de calor fechas x λ con escala divergente simetrica alrededor de 0 (±max |Z|)."""
    Z = np.asarray(Z, float)
    if zmax is None:
        zmax = float(np.nanmax(np.abs(Z))) if np.isfinite(Z).any() else 1.0
    zmax = zmax or 1.0
    labels = [f"{l} (base)" if i < base_n else l for i, l in enumerate(row_labels)]
    return go.Heatmap(z=Z, x=wl, y=labels, colorscale=DIVERGING_SCALE, zmin=-zmax, zmax=zmax, zmid=0,
                      colorbar=dict(title=dict(text=colorbar_title, font=dict(size=11)), thickness=12), **kw)


def heatmap_delta(Z, wl, row_labels, zmax=None, colorbar_title: str = "Δ", base_n: int = 0, title=None,
                  height=None) -> go.Figure:
    """Figura con un mapa de calor Δ (primera fecha arriba)."""
    fig = go.Figure(heatmap_trace(Z, wl, row_labels, zmax, colorbar_title, base_n))
    fig.update_yaxes(autorange="reversed", type="category")
    fig.update_xaxes(title_text="Longitud de onda (nm)")
    if title:
        fig.update_layout(title=title)
    if height:
        fig.update_layout(height=height)
    return fig
