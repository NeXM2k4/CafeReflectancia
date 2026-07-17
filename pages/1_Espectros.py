"""Visualizacion de espectros: curvas individuales, suavizado y promedio +- SD."""

import plotly.graph_objects as go
import streamlit as st

from src.config import SG_POLYORDER, SG_WINDOW, X_MAX, X_MIN, COLOR_AVG, SPECTRA_GROUP_PALETTE
from src.parser import get_dataset, load_spectrum
from src.processing import average_group, prepare_spectrum
from src.ui import filter_tag, inject_base_css, render_header

st.set_page_config(page_title="Espectros", page_icon="📈", layout="wide")
inject_base_css()
render_header("Espectros — curvas de reflectancia individuales y promedio ± SD")

df = get_dataset()
if df.empty:
    st.warning("No hay datos en `data/`. Ve a la pagina de inicio.")
    st.stop()

recognized = df[df["name_recognized"]]

with st.sidebar:
    st.markdown("**Filtros**")
    with st.container(border=True):
        filter_tag("Especie")
        species = st.selectbox("Especie", sorted(df["species"].unique()), label_visibility="collapsed")
        sub = recognized[recognized["species"] == species]

        campaigns = sorted(sub["campaign_id"].dropna().unique())
        filter_tag("Campana")
        sel_campaigns = st.multiselect("Campana", campaigns, default=campaigns, label_visibility="collapsed")
        sub = sub[sub["campaign_id"].isin(sel_campaigns)]

        if sub["health_status"].notna().any():
            health_opts = sorted(sub["health_status"].dropna().unique())
            filter_tag("Estado sanitario")
            sel_health = st.multiselect("Estado sanitario", health_opts, default=health_opts, label_visibility="collapsed")
            sub = sub[sub["health_status"].isin(sel_health)]

        if sub["susceptibility"].notna().any():
            susc_opts = sorted(sub["susceptibility"].dropna().unique())
            filter_tag("Susceptibilidad")
            sel_susc = st.multiselect("Susceptibilidad", susc_opts, default=susc_opts, label_visibility="collapsed")
            sub = sub[sub["susceptibility"].isin(sel_susc)]

        if sub["leaf_maturity"].notna().any():
            maturity_opts = sorted(sub["leaf_maturity"].dropna().unique())
            filter_tag("Madurez de hoja")
            sel_maturity = st.multiselect("Madurez de hoja", maturity_opts, default=maturity_opts, label_visibility="collapsed")
            st.caption("No aplica a muestras con roya (sin marcador M/T).")
            sub = sub[sub["leaf_maturity"].isin(sel_maturity)]

        point_opts = sorted(sub["point"].dropna().unique())
        filter_tag("Punto")
        sel_points = st.multiselect("Punto", point_opts, default=point_opts, label_visibility="collapsed")
        sub = sub[sub["point"].isin(sel_points)]

    with st.expander("⚙️ Parametros de suavizado (Savitzky-Golay)"):
        sg_window = st.slider("Ventana", 5, 101, SG_WINDOW, step=2)
        sg_poly = st.slider("Orden del polinomio", 1, 5, SG_POLYORDER)

    show_raw = st.checkbox("Mostrar curva cruda", value=False)
    show_avg = st.checkbox("Mostrar promedio + SD", value=True)

st.caption(f"{len(sub)} archivo(s) seleccionados de **{species}**.")

if sub.empty:
    st.info("Ajusta los filtros: no hay archivos con esta combinacion.")
    st.stop()

spectra = {}
hoja_by_file = {}
errors = []
for _, row in sub.iterrows():
    try:
        raw = load_spectrum(row["path"])
        spectra[row["filename"]] = prepare_spectrum(raw, sg_window, sg_poly, X_MIN, X_MAX)
        hoja_by_file[row["filename"]] = f"{row['session']}{row['session_num']}"
    except ValueError as e:
        errors.append((row["filename"], str(e)))

if errors:
    with st.expander(f"⚠️ {len(errors)} archivo(s) con error de lectura"):
        for name, err in errors:
            st.write(f"- **{name}**: {err}")

# La leyenda agrupa por "Hoja" (no por archivo individual): con muchos puntos/repeticiones
# seleccionados, una entrada por archivo se vuelve ilegible. Cada hoja fisica comparte color
# y una sola entrada de leyenda; el nombre de archivo se mantiene disponible en el hover.
hojas = sorted(set(hoja_by_file.values()))
hoja_color = {h: SPECTRA_GROUP_PALETTE[i % len(SPECTRA_GROUP_PALETTE)] for i, h in enumerate(hojas)}
legend_shown = set()

fig = go.Figure()
for name, spec in spectra.items():
    hoja = hoja_by_file[name]
    color = hoja_color[hoja]
    show_legend_here = hoja not in legend_shown
    legend_shown.add(hoja)
    if show_raw:
        fig.add_trace(go.Scatter(
            x=spec["wavelength"], y=spec["reflectance"], mode="lines",
            line=dict(color=color, width=0.7), opacity=0.5, showlegend=False,
            legendgroup=hoja, hoverinfo="skip",
        ))
    fig.add_trace(go.Scatter(
        x=spec["wavelength"], y=spec["smooth"], mode="lines",
        line=dict(color=color, width=1.8),
        name=f"Hoja {hoja}", legendgroup=hoja, showlegend=show_legend_here,
        hovertemplate=f"{name}<br>%{{x}} nm · %{{y:.1f}}%<extra></extra>",
    ))

if show_avg and len(spectra) > 1:
    df_avg = average_group(list(spectra.values()))
    if df_avg is not None:
        fig.add_trace(go.Scatter(
            x=df_avg["wavelength"], y=df_avg["mean"] + df_avg["std"],
            mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=df_avg["wavelength"], y=df_avg["mean"] - df_avg["std"],
            mode="lines", line=dict(width=0), fill="tonexty",
            fillcolor="rgba(250,250,250,0.13)", name="± 1 SD", hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=df_avg["wavelength"], y=df_avg["mean"], mode="lines",
            line=dict(color=COLOR_AVG, width=3.5, dash="dash"), name="Promedio",
        ))

fig.update_layout(
    xaxis_title="Longitud de onda (nm)",
    yaxis_title="Reflectancia (%)",
    yaxis_range=[0, 105],
    height=600,
    legend=dict(font=dict(size=9)),
    margin=dict(t=20),
)
st.plotly_chart(fig, width='stretch')
