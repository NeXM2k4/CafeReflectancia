"""Espectros de reflectancia: curvas individuales y media ± DE por tipo de hoja."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import INDEX_WAVELENGTHS, LEAF_NUM_DASH, LEAF_TYPE_COLORS, LEAF_TYPE_LABELS, SG_POLYORDER, SG_WINDOW, SPECIES_PENDING_LABEL, X_MAX
from src.parser import get_dataset, leaf_label, load_spectrum
from src.processing import prepare_spectrum
from src.ui import INK_MUTED, LEAF_ORDER, campaign_range, chart, leaf_legend, leaf_sort, note, page_header, rgba, sidebar_footer

# Por debajo de 440 nm la relacion senal/ruido es tan baja que parte de los espectros con roya da
# reflectancia negativa (METODOLOGIA.md §2). Solo afecta lo que se dibuja.
WL_MIN = 440
GRID = np.arange(WL_MIN, X_MAX + 0.1, 2.0)


@st.cache_data(show_spinner="Leyendo y suavizando espectros...", max_entries=64)
def curvas(paths: tuple, window: int, poly: int) -> tuple[np.ndarray, np.ndarray, list]:
    """Espectros suavizados y crudos interpolados a una grilla de 2 nm (una fila por archivo)."""
    suav, crudo, errores = [], [], []
    for p in paths:
        try:
            s = prepare_spectrum(load_spectrum(p), window, poly, x_max=X_MAX)
            suav.append(np.interp(GRID, s["wavelength"], s["smooth"], left=np.nan, right=np.nan))
            crudo.append(np.interp(GRID, s["wavelength"], s["reflectance"], left=np.nan, right=np.nan))
        except ValueError as e:
            suav.append(np.full(len(GRID), np.nan))
            crudo.append(np.full(len(GRID), np.nan))
            errores.append((p, str(e)))
    return np.array(suav), np.array(crudo), errores


page_header(
    "Análisis exploratorio",
    "Espectros de reflectancia",
    "Cada curva es un espectro (una repetición en un punto de una hoja). El color indica el tipo "
    "de hoja y el trazo, el número de hoja. La media ± DE se calcula por tipo de hoja sobre los "
    "espectros visibles.",
)

df = get_dataset()
if df.empty:
    st.warning("No se encontraron espectros en `data/`.")
    st.stop()
recognized = df[df["name_recognized"] & (df["species"] != SPECIES_PENDING_LABEL)]

with st.sidebar:
    especies = [s for s in ["Bourbon", "Pacamara", "Canefora", "Cuscatleco"] if s in set(recognized["species"])]
    species = st.selectbox("Variedad", especies, key="esp_sp")
    sub = recognized[recognized["species"] == species]
    sel_c = campaign_range(sub, key="esp_camp")
    sub = sub[sub["campaign_id"].isin(sel_c)]
    tipos_disp = leaf_sort([t for t in ["T", "M", "V", "R"] if (sub["session"] == t).any()])
    sel_tipos = st.pills("Tipo de hoja", tipos_disp, default=tipos_disp, selection_mode="multi",
                         format_func=LEAF_TYPE_LABELS.get, key=f"esp_tipos_{species}")
    puntos_disp = sorted(int(p) for p in sub["point"].dropna().unique())
    sel_puntos = st.pills("Puntos", puntos_disp, default=[p for p in puntos_disp if p <= 3], selection_mode="multi",
                          format_func=lambda p: f"p{p}", key=f"esp_pts_{species}",
                          help="El análisis usa solo p1–p3. p4–p6 aparecen en algunas campañas.")
    vista = st.segmented_control("Mostrar", ["Curvas", "Media ± DE", "Ambas"], default="Ambas", key="esp_vista")
    bandas = st.toggle("Marcar bandas de los índices", value=False, key="esp_bandas")
    with st.expander("Suavizado (solo esta vista)"):
        sg_window = st.slider("Ventana Savitzky–Golay", 5, 101, SG_WINDOW, step=2, key="esp_sgw")
        sg_poly = st.slider("Orden del polinomio", 1, 5, SG_POLYORDER, key="esp_sgp")
        ver_crudo = st.toggle("Superponer espectro sin suavizar", value=False, key="esp_raw")
        if (sg_window, sg_poly) != (SG_WINDOW, SG_POLYORDER):
            st.caption(f"Distinto del valor del análisis ({SG_WINDOW}/{SG_POLYORDER}).")
sidebar_footer(df)

sel_tipos = sel_tipos or []
sub = sub[sub["session"].isin(sel_tipos) & sub["point"].isin(sel_puntos or [])]
if sub.empty:
    st.info("No hay espectros con esta combinación de filtros.")
    st.stop()
vista = vista or "Ambas"

sub = sub.sort_values(["session", "session_num", "campaign_date", "point", "repetition"]).reset_index(drop=True)
Y, Y_raw, errores = curvas(tuple(sub["path"]), sg_window, sg_poly)

leaf_legend(sel_tipos)
fig = go.Figure()

if vista in ("Curvas", "Ambas"):
    alpha = 0.5 if vista == "Curvas" else 0.14
    grupos = sorted(sub.groupby(["session", "session_num"], sort=False), key=lambda kv: (LEAF_ORDER.index(kv[0][0]), kv[0][1]))
    for (tipo, num), g in grupos:
        color = LEAF_TYPE_COLORS[tipo]
        hoja = leaf_label(tipo, num)
        idx = g.index.to_numpy()
        # Todas las curvas de una hoja en una sola traza (separadas por NaN): mucho mas liviano.
        xs = np.tile(np.append(GRID, np.nan), len(idx))
        ys = np.hstack([np.append(Y[i], np.nan) for i in idx])
        info = np.repeat([f"{pd.Timestamp(r.campaign_date):%d/%m/%Y} · p{int(r.point)} · rep. {int(r.repetition) if pd.notna(r.repetition) else '?'}"
                          for r in g.itertuples()], len(GRID) + 1)
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", name=f"{hoja} ({len(idx)})", legendgroup=hoja,
            line=dict(color=rgba(color, alpha), width=1, dash=LEAF_NUM_DASH.get(int(num), "dot")),
            customdata=info, hovertemplate=f"<b>{hoja}</b> · %{{customdata}}<br>%{{x:.0f}} nm · %{{y:.1f}} %<extra></extra>",
        ))
        if ver_crudo:
            ys_r = np.hstack([np.append(Y_raw[i], np.nan) for i in idx])
            fig.add_trace(go.Scatter(x=xs, y=ys_r, mode="lines", showlegend=False, legendgroup=hoja,
                                     line=dict(color=rgba(color, 0.15), width=0.6), hoverinfo="skip"))

resumen = []
if vista in ("Media ± DE", "Ambas"):
    for tipo in leaf_sort(sel_tipos):
        idx = sub.index[sub["session"] == tipo].to_numpy()
        if len(idx) < 2:
            continue
        m, sd = np.nanmean(Y[idx], axis=0), np.nanstd(Y[idx], axis=0, ddof=1)
        color = LEAF_TYPE_COLORS[tipo]
        nombre = LEAF_TYPE_LABELS[tipo]
        fig.add_trace(go.Scatter(x=GRID, y=m + sd, mode="lines", line=dict(width=0), showlegend=False,
                                 legendgroup=f"m{tipo}", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=GRID, y=m - sd, mode="lines", line=dict(width=0), fill="tonexty",
                                 fillcolor=rgba(color, 0.16), showlegend=False, legendgroup=f"m{tipo}", hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=GRID, y=m, mode="lines", name=f"Media {nombre.lower()} (n = {len(idx)})", legendgroup=f"m{tipo}",
            line=dict(color=color, width=2.6), customdata=sd,
            hovertemplate=f"<b>{nombre}</b> media<br>%{{x:.0f}} nm · %{{y:.1f}} ± %{{customdata:.1f}} %<extra></extra>",
        ))
        n_hojas = sub.loc[idx, "session_num"].nunique()
        resumen.append(f"{nombre}: {len(idx)} espectros de {n_hojas} hoja{'s' if n_hojas != 1 else ''}")

if bandas:
    for w in INDEX_WAVELENGTHS:
        fig.add_vline(x=w, line_width=1, line_color="rgba(200,200,190,0.18)")
        fig.add_annotation(x=w, y=1, yref="paper", text=str(w), showarrow=False, yshift=8,
                           font=dict(size=9, color=INK_MUTED))

fig.update_layout(
    xaxis_title="Longitud de onda (nm)", yaxis_title="Reflectancia (%)", hovermode="closest",
    legend=dict(y=1.06 if bandas else 1.02), margin=dict(t=60 if bandas else 36),
)
fig.update_xaxes(range=[WL_MIN, X_MAX], dtick=50)
fig.update_yaxes(rangemode="tozero")
chart(fig, height=580)

n_hojas_fechas = sub.groupby(["session", "session_num", "campaign_id"]).ngroups
st.caption(
    f"{species} · {len(sub)} espectros · {n_hojas_fechas} hojas-fecha · {len(sel_c)} campañas. "
    + (" · ".join(resumen) + ". " if resumen else "")
    + "La DE es entre espectros individuales (incluye variación entre puntos, hojas y fechas)."
)
if np.nanmin(Y) < 0:
    note("aviso", "Algún espectro visible tiene reflectancia negativa: señal débil del espectrómetro en "
                  "esa medición, no un valor físico.")
if errores:
    with st.expander(f"Espectros que no se pudieron leer ({len(errores)})"):
        for p, e in errores:
            st.text(f"{p}: {e}")
