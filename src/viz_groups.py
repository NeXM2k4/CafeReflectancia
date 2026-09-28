"""Graficos compartidos por las vistas de comparacion entre grupos (tipo de hoja, variedad)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.stats_utils import compare_groups, pairwise_effects, summarize_indices
from src.ui import DIVERGING_SCALE, INK, INK_MUTED, chart, html_table, numeric_column_config, rgba


def effect_matrix(data: pd.DataFrame, group_col: str, indices: list[str], pairs: list[tuple[str, str]]):
    """Matriz indice x par con el delta de Cliff (color) y su significacion tras Holm (texto)."""
    tabla = pairwise_effects(data, group_col, indices, pairs)
    if tabla.empty or tabla["δ Cliff"].isna().all():
        st.info("No hay datos suficientes (al menos 2 hojas-fecha por grupo) para comparar.")
        return tabla
    etiquetas_par = [f"{a}<br><span style='font-size:10px;color:{INK_MUTED}'>vs {b}</span>" for a, b in pairs]
    z = tabla.pivot(index="Índice", columns="Par", values="δ Cliff").reindex(index=indices, columns=[f"{a} vs {b}" for a, b in pairs])
    p = tabla.pivot(index="Índice", columns="Par", values="p Holm").reindex_like(z)
    mag = tabla.pivot(index="Índice", columns="Par", values="Magnitud").reindex_like(z)
    texto = np.where(
        z.isna(), "",
        np.where(p < 0.05, z.map(lambda v: f"<b>{v:+.2f}</b>" if pd.notna(v) else ""), z.map(lambda v: f"{v:+.2f}" if pd.notna(v) else "")),
    )
    custom = np.dstack([p.to_numpy(dtype=float), mag.to_numpy(dtype=object)])
    fig = go.Figure(go.Heatmap(
        z=z.to_numpy(dtype=float), x=etiquetas_par, y=indices, zmin=-1, zmax=1, zmid=0,
        colorscale=DIVERGING_SCALE, xgap=2, ygap=2, text=texto, texttemplate="%{text}",
        textfont=dict(size=12, color=INK), customdata=custom,
        colorbar=dict(tickvals=[-1, -0.474, 0, 0.474, 1], thickness=8,
                      ticktext=["−1", "−0.47", "0", "+0.47", "+1"], len=0.9),
        hovertemplate="%{y} · %{x}<br>δ = %{z:+.3f} (%{customdata[1]})<br>p Holm = %{customdata[0]:.4f}<extra></extra>",
    ))
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(side="top", showgrid=False, ticks="", tickfont=dict(size=12, color=INK)),
                      yaxis=dict(autorange="reversed", showgrid=False, ticks="", tickfont=dict(size=12, color=INK)))
    chart(fig, height=70 + 42 * len(indices))
    st.caption(
        "δ > 0: el primer grupo tiende a valores más altos; δ < 0, más bajos. En **negrita**, diferencias "
        "significativas tras corregir por Holm sobre toda la matriz (α = 0.05). Magnitud según Romano "
        "et al. (2006): |δ| ≥ 0.474 grande, ≥ 0.33 mediana, ≥ 0.147 pequeña."
    )
    return tabla


def pair_table(tabla: pd.DataFrame, decimals: int = 3):
    """Tabla legible de la comparacion por pares."""
    if tabla.empty:
        return
    t = tabla.copy()
    fmt = lambda v: "—" if pd.isna(v) else f"{v:.{decimals}f}"
    out = pd.DataFrame({
        "Índice": t["Índice"], "Comparación": t["A"] + " vs " + t["B"],
        "Mediana A": t["Mediana A"].map(fmt), "Mediana B": t["Mediana B"].map(fmt),
        "n A / n B": t["n A"].astype(str) + " / " + t["n B"].astype(str),
        "δ Cliff": t["δ Cliff"].map(lambda v: "—" if pd.isna(v) else f"{v:+.2f}"),
        "Magnitud": t["Magnitud"],
        "p Holm": t["p Holm"].map(lambda v: "—" if pd.isna(v) else ("< 0.0001" if v < 1e-4 else f"{v:.4f}")),
    })
    html_table(out, num_cols=("Mediana A", "Mediana B", "n A / n B", "δ Cliff", "p Holm"), strong_cols=("Índice",))


def distributions(data: pd.DataFrame, group_col: str, order: list[str], colors: dict, indices: list[str],
                  flag_col: str | None = None, cols: int = 4):
    """Pequeños multiplos: caja + puntos (una hoja-fecha por punto) para cada indice."""
    rows = int(np.ceil(len(indices) / cols))
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=indices, horizontal_spacing=0.06, vertical_spacing=0.12)
    rng = np.random.default_rng(7)
    for k, idx in enumerate(indices):
        r, c = k // cols + 1, k % cols + 1
        for j, g in enumerate(order):
            d = data[data[group_col] == g].dropna(subset=[idx])
            if d.empty:
                continue
            color = colors[g]
            fig.add_trace(go.Box(
                x=[j] * len(d), y=d[idx], name=g, legendgroup=g, showlegend=k == 0, width=0.5,
                marker=dict(color=color), line=dict(color=color, width=1.2), fillcolor=rgba(color, 0.14),
                boxpoints=False, hoverinfo="skip",
            ), row=r, col=c)
            jit = j + 0.36 + rng.uniform(-0.07, 0.07, len(d))
            flagged = d[flag_col].fillna(False).to_numpy(dtype=bool) if flag_col and flag_col in d else np.zeros(len(d), bool)
            fig.add_trace(go.Scatter(
                x=jit, y=d[idx], mode="markers", showlegend=False, legendgroup=g,
                marker=dict(size=6, color=np.where(flagged, "rgba(0,0,0,0)", color).tolist(),
                            line=dict(width=np.where(flagged, 1.4, 0.6).tolist(), color=np.where(flagged, color, "#111211").tolist())),
                customdata=np.stack([d["leaf"], d["campaign_date"].map(lambda x: f"{pd.Timestamp(x):%d/%m/%Y}"),
                                     np.where(flagged, " · marcada por control de calidad", "")], axis=-1),
                hovertemplate=f"<b>{g}</b> %{{customdata[0]}} · %{{customdata[1]}}<br>{idx} = %{{y:.4f}}%{{customdata[2]}}<extra></extra>",
            ), row=r, col=c)
        fig.update_xaxes(tickvals=list(range(len(order))), ticktext=[""] * len(order), range=[-0.6, len(order) - 0.2],
                         showgrid=False, row=r, col=c)
    for a in fig.layout.annotations:
        a.font = dict(size=12, color=INK)
    fig.update_layout(legend=dict(y=1.04 + 0.02 * (3 - rows)), boxgap=0.3)
    chart(fig, height=250 * rows + 40)
    if flag_col:
        st.caption("Cada punto es una hoja-fecha (media de p1–p3). Los círculos vacíos son hojas-fecha marcadas por el "
                   "control de calidad; se muestran pero no alteran la caja.")


def global_test(data: pd.DataFrame, group_col: str, indices: list[str]):
    res = summarize_indices(data, group_col, indices)
    grupos = [c.replace("Mediana (", "").rstrip(")") for c in res.columns if c.startswith("Mediana (")]
    out = pd.DataFrame({"Índice": res["Índice"], "Prueba": res["Test"].fillna("—")})
    for g in grupos:
        out[f"n {g}"] = res[f"n ({g})"]
    out["p Holm"] = res["p (Holm)"].map(lambda v: "—" if pd.isna(v) else ("< 0.0001" if v < 1e-4 else f"{v:.4f}"))
    html_table(out, num_cols=tuple(c for c in out.columns if c.startswith("n ")) + ("p Holm",), strong_cols=("Índice",))
    st.caption("Prueba global (Kruskal–Wallis con 3 o más grupos, Mann–Whitney con 2), Holm entre índices. "
               "Solo indica si algún grupo difiere; la matriz por pares dice cuál y cuánto.")


def technical_detail(data: pd.DataFrame, group_col: str, order: list[str], indices: list[str]):
    idx = st.selectbox("Índice", indices, key=f"tec_{group_col}")
    result = compare_groups({g: data.loc[data[group_col] == g, idx].tolist() for g in order})
    summary_df = pd.DataFrame(result["summary"]).T
    st.dataframe(summary_df, width="stretch", column_config=numeric_column_config(summary_df, exclude=("n",)))
    if result["message"]:
        st.caption(result["message"])
        return
    st.caption("Normalidad por grupo (Shapiro–Wilk):")
    sh = pd.DataFrame(result["shapiro"]).T
    st.dataframe(sh, width="stretch", column_config=numeric_column_config(sh))
    st.markdown(f"{result['test_name']}: estadístico = {result['stat']:.4f}, p = {result['p_value']:.4f} "
                f"({'significativo' if result['significant'] else 'no significativo'}, sin corrección entre índices).")
    if result["posthoc"] is not None:
        st.caption(f"Post-hoc: {result['posthoc_name']}")
        st.dataframe(result["posthoc"], width="stretch", column_config=numeric_column_config(result["posthoc"]))
