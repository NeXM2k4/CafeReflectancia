"""Figuras de Plotly para Cambio espectral y PCA y Rasgos espectrales (funciones puras, sin Streamlit).

Convencion: en los mapas de calor la primera fecha va arriba (igual que `spectral_plots.heatmap_delta`).
No se fija plantilla: la pone `ui.chart`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import LEAF_TYPE_COLORS, SHADE_BANDS
from src.spectral_plots import add_region_shading, date_colorbar_trace, date_colors, heatmap_trace
from src.temporal_plots import GRID, TEXT_MUTED, lowess_curve, rgba
from src.ui import defer_layout_items, subplot_refs

PC_COLORS = ["#3987E5", "#D95926", "#9085E9"]
_EDGES = sorted({e for _, lo, hi, _ in SHADE_BANDS for e in (lo, hi)})


def _vlines_cols(fig, cols, xrange):
    """Lineas verticales punteadas en los bordes de las franjas (SHADE_BANDS), en cada columna dada."""
    shapes = []
    for c in cols:
        x, y = subplot_refs(fig, 1, c)
        for e in _EDGES:
            if xrange[0] < e < xrange[1]:
                shapes.append(dict(type="line", xref=x, yref=f"{y} domain", x0=e, x1=e, y0=0, y1=1,
                                   line=dict(color="rgba(40,40,35,0.45)", width=1, dash="dot")))
    defer_layout_items(fig, shapes=shapes)


def delta_heatmap_pair(wl, row_labels, Z_raw, Z_norm, base_n: int = 0, titles=None, height=None) -> go.Figure:
    """Δ vs linea base: cruda (izquierda) | normalizada (derecha), cada una con su escala simetrica."""
    titles = titles or ("Δ reflectancia cruda (pp)", "Δ reflectancia normalizada (forma)")
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.12, subplot_titles=list(titles))
    for c, (Z, unit, cx) in enumerate([(Z_raw, "pp", 0.455), (Z_norm, "relativo", 1.01)], start=1):
        tr = heatmap_trace(Z, wl, row_labels, colorbar_title=unit, base_n=base_n,
                           hovertemplate="%{y}<br>%{x:.0f} nm · Δ %{z:+.3f}<extra></extra>")
        tr.colorbar.update(x=cx, xanchor="left", len=0.95)
        fig.add_trace(tr, row=1, col=c)
    fig.update_yaxes(autorange="reversed", type="category", tickfont=dict(size=10))
    fig.update_xaxes(title_text="Longitud de onda (nm)")
    _vlines_cols(fig, (1, 2), (float(np.min(wl)), float(np.max(wl))))
    n = len(row_labels)
    fig.update_layout(height=height or max(340, 22 * n + 120), margin=dict(t=40, b=10, r=70))
    for a in fig.layout.annotations:
        a.font.size = 12
    return fig


def _two_cols(titles, shared_y=False, spacing=0.09, rows=1):
    return make_subplots(rows=rows, cols=2, shared_yaxes=shared_y, horizontal_spacing=spacing,
                         subplot_titles=list(titles))


def pca_explained(expl_raw, expl_norm) -> go.Figure:
    """Varianza explicada por PC1-PC3, cruda | normalizada."""
    fig = _two_cols(("Cruda", "Normalizada"), shared_y=True)
    for c, e in enumerate((expl_raw, expl_norm), start=1):
        e = np.asarray(e, float)
        fig.add_trace(go.Bar(x=[f"PC{i + 1}" for i in range(len(e))], y=e * 100, marker_color=PC_COLORS[:len(e)],
                             text=[f"{v * 100:.1f} %" if np.isfinite(v) else "" for v in e], textposition="outside",
                             showlegend=False, hovertemplate="%{x}: %{y:.2f} %<extra></extra>"), row=1, col=c)
    fig.update_yaxes(title_text="Varianza explicada (%)", range=[0, 108], col=1, gridcolor=GRID)
    fig.update_layout(height=300, margin=dict(t=40, b=10))
    return fig


def pca_loadings(wl, ld_raw, ld_norm, expl_raw, expl_norm) -> go.Figure:
    """Cargas de PC1-PC3 vs λ (con franjas de region), cruda | normalizada."""
    fig = _two_cols(("Cruda", "Normalizada"), shared_y=False)
    for c, (ld, ex) in enumerate([(ld_raw, expl_raw), (ld_norm, expl_norm)], start=1):
        for j in range(len(ld)):
            if not np.isfinite(ld[j]).any():
                continue
            fig.add_trace(go.Scatter(
                x=wl, y=ld[j], mode="lines", line=dict(color=PC_COLORS[j], width=1.8), legendgroup=f"PC{j + 1}",
                name=f"PC{j + 1} ({ex[j] * 100:.0f} %)" if c == 1 else None, showlegend=(c == 1),
                hovertemplate=f"PC{j + 1}<br>%{{x:.0f}} nm · %{{y:+.3f}}<extra></extra>"), row=1, col=c)
        add_region_shading(fig, 1, c, xrange=(float(wl[0]), float(wl[-1])))
        fig.add_hline(y=0, line_width=1, line_color="rgba(40,40,35,0.4)", row=1, col=c)
    for name, lo, hi, color in SHADE_BANDS:  # franjas en la leyenda (las etiquetas se enciman con los titulos)
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=f"{name} ({lo}–{hi})", hoverinfo="skip",
                                 marker=dict(symbol="square", size=11, color=color.rsplit(",", 1)[0] + ",0.45)")),
                      row=1, col=1)
    fig.update_xaxes(title_text="Longitud de onda (nm)")
    fig.update_yaxes(title_text="Carga", col=1)
    fig.update_xaxes(gridcolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    fig.update_layout(height=360, margin=dict(t=50, b=10), hovermode="x unified",
                      legend=dict(orientation="h", yanchor="bottom", y=1.1, x=0, font=dict(size=11)))
    return fig


def pca_scores(dates, sc_raw, sc_norm) -> go.Figure:
    """Puntajes PC1-PC3 vs fecha, cruda | normalizada (puntos + linea fina; una hoja)."""
    fig = _two_cols(("Cruda", "Normalizada"), shared_y=False)
    for c, sc in enumerate((sc_raw, sc_norm), start=1):
        for j in range(sc.shape[1]):
            if not np.isfinite(sc[:, j]).any():
                continue
            fig.add_trace(go.Scatter(
                x=dates, y=sc[:, j], mode="lines+markers", marker=dict(size=7, color=PC_COLORS[j]),
                line=dict(color=rgba(PC_COLORS[j], 0.45), width=1), name=f"PC{j + 1}", legendgroup=f"PC{j + 1}",
                showlegend=(c == 1),
                hovertemplate=f"PC{j + 1}<br>%{{x|%d-%b}} · %{{y:+.3f}}<extra></extra>"), row=1, col=c)
        fig.add_hline(y=0, line_width=1, line_color="rgba(40,40,35,0.35)", row=1, col=c)
    fig.update_xaxes(gridcolor=GRID, tickformat="%d-%b")
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(title_text="Puntaje", col=1)
    fig.update_layout(height=340, margin=dict(t=50, b=10), hovermode="x unified",
                      legend=dict(orientation="h", yanchor="bottom", y=1.1, x=0, font=dict(size=11)))
    return fig


def common_space_trajectories(traj: pd.DataFrame, selected_leaf_id: str, explained=None, labels_sel=None) -> go.Figure:
    """Trayectorias PC1-PC2 de cada hoja en el espacio comun (sin promediar hojas).

    `traj`: columnas leaf_id, species, leaf, leaf_type, campaign_date, PC1, PC2 (ordenable por fecha).
    La hoja elegida va en grueso con marcadores coloreados por fecha (Viridis); las demas, finas en el
    color de su tipo; las hojas R con linea mas gruesa. Una flecha al final de cada trayectoria.
    """
    fig = go.Figure()
    anns = []
    seen_type = set()
    order = traj.assign(_sel=traj["leaf_id"] == selected_leaf_id).sort_values(["_sel", "leaf_id", "campaign_date"])
    for lid, g in order.groupby("leaf_id", sort=False):
        g = g.sort_values("campaign_date")
        lt = g["leaf_type"].iloc[0]
        color = LEAF_TYPE_COLORS.get(lt, TEXT_MUTED)
        is_sel = lid == selected_leaf_id
        name = lid.replace("|", " ")
        fig.add_trace(go.Scatter(
            x=g["PC1"], y=g["PC2"], mode="lines+markers", name=name, legendgroup=lt, showlegend=False,
            line=dict(color=color if is_sel else rgba(color, 0.55), width=3 if is_sel else (1.8 if lt == "R" else 1)),
            marker=dict(size=9 if is_sel else 4, color=color if not is_sel else date_colors(list(g["campaign_date"])),
                        line=dict(width=1 if is_sel else 0, color="white")),
            customdata=np.stack([g["campaign_date"].dt.strftime("%d-%b")], axis=-1),
            hovertemplate=f"{name}<br>%{{customdata[0]}}<br>PC1 %{{x:+.3f}} · PC2 %{{y:+.3f}}<extra></extra>"))
        if len(g) >= 2:
            x0, y0, x1, y1 = (g["PC1"].iloc[-2], g["PC2"].iloc[-2], g["PC1"].iloc[-1], g["PC2"].iloc[-1])
            anns.append(dict(x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                             arrowhead=2, arrowsize=1.2, arrowwidth=1.5 if is_sel else 1,
                             arrowcolor=color if is_sel else rgba(color, 0.7), text=""))
        if is_sel:
            anns.append(dict(x=g["PC1"].iloc[0], y=g["PC2"].iloc[0], xref="x", yref="y", showarrow=False,
                             text="inicio", yshift=-12, font=dict(size=10, color=TEXT_MUTED)))
    for lt, label in (("M", "M madura"), ("T", "T tierna"), ("R", "R con roya")):
        if lt in set(traj["leaf_type"]):
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=label,
                                     line=dict(color=LEAF_TYPE_COLORS[lt], width=2)))
    fig.add_trace(date_colorbar_trace(list(order.loc[order["leaf_id"] == selected_leaf_id, "campaign_date"]),
                                      labels_sel, title="Fecha (hoja elegida)"))
    defer_layout_items(fig, annotations=anns)
    ex = explained if explained is not None else (np.nan, np.nan)
    fig.update_xaxes(title_text=f"PC1" + (f" ({ex[0] * 100:.0f} %)" if np.isfinite(ex[0]) else ""), gridcolor=GRID,
                     zeroline=True, zerolinecolor="rgba(40,40,35,0.3)")
    fig.update_yaxes(title_text=f"PC2" + (f" ({ex[1] * 100:.0f} %)" if np.isfinite(ex[1]) else ""), gridcolor=GRID,
                     zeroline=True, zerolinecolor="rgba(40,40,35,0.3)")
    fig.update_layout(height=520, margin=dict(t=20, b=10), hovermode="closest",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)))
    return fig


def feature_small_multiples(ft_leaf: pd.DataFrame, columns, color: str, na_columns=(), ncols: int = 2) -> go.Figure:
    """Una serie por rasgo de una hoja: puntos sin unir + curva LOWESS (`ft_leaf` con campaign_date, dia)."""
    n = len(columns)
    rows = -(-n // ncols)
    fig = make_subplots(rows=rows, cols=ncols, subplot_titles=list(columns), vertical_spacing=0.07,
                        horizontal_spacing=0.09)
    f = ft_leaf.sort_values("campaign_date")
    t0 = f["campaign_date"].min()
    anns = []
    for i, col in enumerate(columns):
        r, c = i // ncols + 1, i % ncols + 1
        y = f[col].to_numpy(float)
        if not np.isfinite(y).any():
            x, yd = subplot_refs(fig, r, c)
            anns.append(dict(xref=f"{x} domain", yref=f"{yd} domain", x=0.5, y=0.5, showarrow=False,
                             text="no aplica" if col in na_columns else "sin datos",
                             font=dict(size=13, color=TEXT_MUTED)))
            continue
        fig.add_trace(go.Scatter(
            x=f["campaign_date"], y=y, mode="markers", showlegend=False, marker=dict(size=7, color=color),
            hovertemplate=f"{col}<br>%{{x|%d-%b}} · %{{y:.3f}}<extra></extra>"), row=r, col=c)
        cur = lowess_curve(f["dia"].to_numpy(float), y)
        if cur is not None:
            g, yc = cur
            fig.add_trace(go.Scatter(x=t0 + pd.to_timedelta(g, unit="D"), y=yc, mode="lines", showlegend=False,
                                     line=dict(color=rgba(color, 0.7), width=2), hoverinfo="skip"), row=r, col=c)
    defer_layout_items(fig, annotations=anns)
    fig.update_xaxes(gridcolor=GRID, tickformat="%d-%b", nticks=5)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    for a in fig.layout.annotations:
        a.font.size = 12
    fig.update_layout(height=220 * rows + 40, margin=dict(t=30, b=10), hovermode="closest")
    return fig
