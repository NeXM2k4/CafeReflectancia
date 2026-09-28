"""Estado actual de cada hoja: similitud espectral con la hoja con roya, hoja por hoja y fecha por fecha."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import LEAF_TYPE_LABELS, RUST_RISK_CLASSES, rust_risk_action, rust_risk_class
from src.indices import DISPLAY_INDICES, file_index_table, leaf_date_table, quality_flags
from src.parser import get_dataset
from src.severity import leaf_date_similarity, severity_baselines
from src.ui import (AXIS, INK, INK_2, SIMILARITY_SCALE, campaign_range, chart, html_table, note,
                    page_header, section, sidebar_footer)

SUSCEPTIBLES = ["Bourbon", "Pacamara"]
FILAS = ["M1", "M2", "·", "T1", "T2", "R1"]  # "·" separa hojas evaluadas de referencias

page_header(
    "Seguimiento de hojas",
    "Estado actual de las hojas",
    "Similitud espectral de cada hoja con la hoja con roya de su variedad: 0 % se parece a una hoja "
    "tierna, 100 % a la hoja con roya. Las hojas maduras son las de estado desconocido; tiernas y R1 "
    "son las referencias que definen la escala.",
)

df = get_dataset()
if df.empty:
    st.warning("No se encontraron espectros en `data/`.")
    st.stop()

with st.sidebar:
    sel_sp = st.pills("Variedades", SUSCEPTIBLES, default=SUSCEPTIBLES, selection_mode="multi", key="est_sp")
    sel_c = campaign_range(df[df["species"].isin(SUSCEPTIBLES)], key="est_camp")
sidebar_footer(df)
sel_sp = [s for s in SUSCEPTIBLES if s in (sel_sp or [])]
if not sel_sp or not sel_c:
    st.info("Elegir al menos una variedad y una campaña.")
    st.stop()

files_all, _ = file_index_table(df)
baselines = severity_baselines(df)  # anclas con todo el dataset: mismas que Telegram y Evolución
ld = quality_flags(leaf_date_table(files_all[files_all["species"].isin(sel_sp)]))
sim = leaf_date_similarity(ld[ld["campaign_id"].isin(sel_c)], baselines)
if sim.empty:
    st.info("No hay datos con los filtros elegidos.")
    st.stop()

# --------------------------------------------------------------------------------------------
section("Similitud por hoja y fecha",
        "Cada celda es una hoja-fecha. Un asterisco indica una hoja-fecha marcada por el control de calidad "
        "(excluida de las anclas). Celda vacía: la hoja no se midió esa fecha.")
niveles = [c[0] * 100 for c in RUST_RISK_CLASSES]
nombres_clase = [c[1] for c in RUST_RISK_CLASSES]
fechas = sorted(sim["campaign_date"].unique())
xlab = [f"{pd.Timestamp(f):%d/%m}" for f in fechas]
for sp in sel_sp:
    d = sim[sim["species"] == sp]
    piv = d.pivot_table(index="leaf", columns="campaign_date", values="similitud").reindex(index=FILAS, columns=fechas) * 100
    flag = d.pivot_table(index="leaf", columns="campaign_date", values="qc_flag", aggfunc="max").reindex(index=FILAS, columns=fechas)
    z = piv.to_numpy(dtype=float)
    fl = flag.astype(float).fillna(0).to_numpy() > 0
    txt = np.where(np.isnan(z), "", np.char.add(np.nan_to_num(z).round().astype(int).astype(str), np.where(fl, "*", "")))
    ylab = [" " if h == "·" else (f"{h} · madura" if h[0] == "M" else f"{h} · ref. {LEAF_TYPE_LABELS[h[0]].lower()}")
            for h in FILAS]
    fig = go.Figure(go.Heatmap(
        z=z, x=xlab, y=ylab, zmin=0, zmax=100, colorscale=SIMILARITY_SCALE, xgap=2, ygap=2,
        text=txt, texttemplate="%{text}", textfont=dict(size=12, color=INK), hoverongaps=False,
        colorbar=dict(tickvals=niveles,
                      ticktext=[f"{v:.0f}" for v in niveles], len=1.0, thickness=8),
        hovertemplate="%{y} · %{x}<br>Similitud %{z:.1f} %<extra></extra>",
    ))
    fig.update_layout(title=dict(text=sp), margin=dict(l=0, r=0, t=34, b=0),
                      xaxis=dict(showgrid=False, ticks="", side="bottom"),
                      yaxis=dict(autorange="reversed", showgrid=False, ticks="", tickfont=dict(size=12, color=INK_2)))
    chart(fig, height=250, key=f"heat_{sp}")

st.caption("Escala: " + " · ".join(f"{v:.0f} % {n.lower()}" for v, n in zip(niveles, nombres_clase))
           + ". Cada hoja-fecha se asigna a la clase de nivel más cercano.")
note("leer", "T1 y T2 deberían quedar cerca de 0 % y R1 cerca de 100 %, porque son las hojas que fijan la escala. "
             "Una tierna alta suele ser una hoja que ya maduró (las tiernas envejecen durante las 12 semanas) o una "
             "medición dudosa; revisar esa columna antes de interpretar las maduras de la misma fecha.")

# --------------------------------------------------------------------------------------------
section("Cómo se forma el porcentaje de una hoja-fecha",
        "Cada índice ubica la hoja entre sus dos anclas (0 = tierna, 1 = con roya). La similitud es la mediana "
        "de esas posiciones, recortadas a [0, 1].")
c1, c2, c3 = st.columns(3)
sp_det = c1.selectbox("Variedad", sel_sp, key="det_sp")
hojas = [h for h in FILAS if h in set(sim.loc[sim["species"] == sp_det, "leaf"])]
hoja_det = c2.selectbox("Hoja", hojas, key=f"det_hoja_{sp_det}")
fechas_h = sorted(sim.loc[(sim["species"] == sp_det) & (sim["leaf"] == hoja_det), "campaign_date"].unique(), reverse=True)
fecha_det = c3.selectbox("Fecha", fechas_h, format_func=lambda f: f"{pd.Timestamp(f):%d/%m/%Y}", key=f"det_f_{sp_det}_{hoja_det}")

fila = sim[(sim["species"] == sp_det) & (sim["leaf"] == hoja_det) & (sim["campaign_date"] == fecha_det)].iloc[0]
anclas = baselines.get(sp_det, {}).get("indices", {})
filas = []
for idx in DISPLAY_INDICES:
    a = anclas.get(idx, {})
    s0, s1, v = a.get("sana"), a.get("enferma"), fila[idx]
    pos = (v - s0) / (s1 - s0) if all(x is not None and pd.notna(x) for x in (s0, s1, v)) and s1 != s0 else np.nan
    filas.append({"Índice": idx, "Valor": v, "Ancla tierna": s0, "Ancla con roya": s1, "pos": pos})
comp = pd.DataFrame(filas)

izq, der = st.columns([1, 2.2], gap="large")
with izq:
    score = fila["similitud"]
    _, clase, _, desc = rust_risk_class(score if pd.notna(score) else 0)
    st.metric(f"{sp_det} {hoja_det} · {pd.Timestamp(fecha_det):%d/%m}", "—" if pd.isna(score) else f"{score * 100:.0f} %",
              delta=clase, delta_color="off", delta_arrow="off")
    st.caption(f"{desc} {rust_risk_action(score) if pd.notna(score) and hoja_det.startswith('M') else ''}")
    st.caption(f"{int(fila['n_puntos'])} puntos medidos · {int(fila['similitud_n_indices'])} de {len(DISPLAY_INDICES)} índices comparables"
               + (" · hoja-fecha marcada por control de calidad" if fila.get("qc_flag") else ""))
with der:
    fig = go.Figure()
    y = comp["Índice"].tolist()
    for yy in y:
        fig.add_shape(type="line", x0=0, x1=1, y0=yy, y1=yy, line=dict(color=AXIS, width=6), layer="below")
    clip = comp["pos"].clip(0, 1)
    fuera = comp["pos"].notna() & (comp["pos"] != clip)
    fig.add_trace(go.Scatter(
        x=clip, y=y, mode="markers", marker=dict(size=12, color="#F08A5D", line=dict(width=2, color="#111211"),
                                                  symbol=np.where(fuera, "diamond", "circle").tolist()),
        customdata=np.stack([comp["pos"], comp["Valor"], comp["Ancla tierna"], comp["Ancla con roya"]], axis=-1),
        hovertemplate="<b>%{y}</b><br>posición %{customdata[0]:.2f} (recortada a %{x:.2f})<br>valor %{customdata[1]:.4f}"
                      "<br>tierna %{customdata[2]:.4f} · roya %{customdata[3]:.4f}<extra></extra>", showlegend=False,
    ))
    if pd.notna(score):
        fig.add_vline(x=score, line=dict(color=INK, width=1.2, dash="dot"))
        fig.add_annotation(x=score, y=1.02, yref="paper", text=f"mediana = {score * 100:.0f} %", showarrow=False,
                           font=dict(size=11, color=INK), yanchor="bottom")
    fig.update_xaxes(range=[-0.05, 1.12], tickvals=[0, 0.25, 0.5, 0.75, 1],
                     ticktext=["0 · tierna", "0.25", "0.5", "0.75", "1 · con roya"], showgrid=False)
    fig.update_yaxes(autorange="reversed", showgrid=False, ticks="", tickfont=dict(size=12, color=INK))
    fig.update_layout(margin=dict(l=0, r=24, t=30, b=0))
    chart(fig, height=320, key="det_fig")
    st.caption("Rombo: el índice cae fuera del intervalo entre anclas y se recorta al extremo más cercano.")

tabla = comp.assign(**{
    "Valor": comp["Valor"].map(lambda v: f"{v:.4f}"), "Ancla tierna": comp["Ancla tierna"].map(lambda v: f"{v:.4f}"),
    "Ancla con roya": comp["Ancla con roya"].map(lambda v: f"{v:.4f}"),
    "Posición": comp["pos"].map(lambda v: "—" if pd.isna(v) else f"{v:+.2f}"),
    "Recortada": comp["pos"].map(lambda v: "—" if pd.isna(v) else f"{min(max(v, 0), 1):.2f}"),
})[["Índice", "Valor", "Ancla tierna", "Ancla con roya", "Posición", "Recortada"]]
with st.expander("Valores y anclas de esta hoja-fecha"):
    html_table(tabla, num_cols=("Valor", "Ancla tierna", "Ancla con roya", "Posición", "Recortada"), strong_cols=("Índice",))
    st.caption("Anclas calculadas con todas las campañas: media por hoja-fecha de las hojas tiernas (0) y de la hoja "
               "con roya (1) de la variedad, sin hojas-fecha marcadas. Son las mismas que usa la alerta de campo.")

with st.expander("Tabla completa (todas las hojas y fechas del filtro)"):
    t = sim.assign(**{"Similitud (%)": (sim["similitud"] * 100).round(1)})[
        ["species", "leaf", "campaign_date", "n_puntos", "Similitud (%)", "similitud_n_indices", "qc_flag", *DISPLAY_INDICES]]
    st.dataframe(t, width="stretch", hide_index=True, column_config={
        "species": "Variedad", "leaf": "Hoja", "campaign_date": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
        "n_puntos": "Puntos", "similitud_n_indices": "Índices", "qc_flag": st.column_config.CheckboxColumn("Marcada QC"),
        "Similitud (%)": st.column_config.ProgressColumn("Similitud", min_value=0, max_value=100, format="%.0f %%"),
        **{i: st.column_config.NumberColumn(i, format="%.4f") for i in DISPLAY_INDICES}})
    st.download_button("Descargar (CSV)", t.to_csv(index=False).encode("utf-8"), file_name="similitud_hoja_fecha.csv",
                       mime="text/csv", icon=":material/download:")
