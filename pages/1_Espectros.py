"""Curvas de reflectancia: color por tipo de hoja, promedio +- SD por grupo visible.

Reescrita en la fase F2 de plan_mejora_app.md. Cambios respecto de la version anterior:
- **Color = tipo de hoja** (Madura/Tierna/Con roya/Vieja), trazo (solido/discontinuo) = numero
  de hoja. Antes cada hoja fisica tenia su propio color de una paleta de 8 tonos, asi que con
  varias campañas seleccionadas las 12 curvas de "M1" (una por fecha) se veian todas del mismo
  color sin ningun criterio visible que las agrupara con las demas M.
- **El promedio ± SD se calcula por tipo de hoja**, no sobre todo lo seleccionado junto: antes
  mezclaba, por ejemplo, hojas Con roya y Tierna en un solo promedio, lo que no representa a
  ninguno de los dos grupos.
- Aviso si aparece reflectancia negativa en el rango mostrado (indicio de señal debil del
  espectrometro, no un valor real).
"""

import plotly.graph_objects as go
import streamlit as st

from src.config import (
    LEAF_NUM_DASH,
    LEAF_TYPE_COLORS,
    LEAF_TYPE_HELP,
    LEAF_TYPE_LABELS,
    SG_POLYORDER,
    SG_WINDOW,
    X_MAX,
)
from src.parser import campaign_options, get_dataset, leaf_label, load_spectrum, sorted_campaigns
from src.processing import average_group, prepare_spectrum
from src.ui import filter_tag, inject_base_css, render_header

# Rango de despliegue: por debajo de 440 nm el espectrometro tiene señal/ruido tan bajo que una
# parte de los espectros con roya da reflectancia negativa (ver evoluciontemporal.md, seccion 6.1
# y make_ieee_figures.py). No cambia el rango usado para calcular indices (X_MIN en config.py
# sigue en 420 nm), solo lo que se muestra en esta pagina.
DISPLAY_X_MIN = 440


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"

st.set_page_config(page_title="Espectros", page_icon="📈", layout="wide")
inject_base_css()
render_header("Espectros — reflectancia por tipo de hoja")

df = get_dataset()
if df.empty:
    st.warning("No hay datos en `data/`. Ve a la página de inicio.")
    st.stop()

recognized = df[df["name_recognized"]]

with st.sidebar:
    st.markdown("**Filtros**")
    with st.container(border=True):
        filter_tag("Especie")
        species = st.selectbox("Especie", sorted(df["species"].unique()), label_visibility="collapsed")
        sub = recognized[recognized["species"] == species]

        campaigns = sorted_campaigns(sub)
        labels_camp = campaign_options(sub)
        filter_tag("Campaña")
        sel_campaigns = st.multiselect(
            "Campaña", campaigns, default=campaigns, format_func=labels_camp.get,
            label_visibility="collapsed",
        )
        sub = sub[sub["campaign_id"].isin(sel_campaigns)]

        tipos_disp = [t for t in ["M", "T", "R", "V"] if (sub["session"] == t).any()]
        filter_tag("Tipo de hoja")
        sel_tipos = st.multiselect(
            "Tipo de hoja", tipos_disp, default=tipos_disp,
            format_func=lambda t: LEAF_TYPE_LABELS[t], label_visibility="collapsed",
        )
        sub = sub[sub["session"].isin(sel_tipos)]

        point_opts = sorted(sub["point"].dropna().unique())
        filter_tag("Punto")
        sel_points = st.multiselect("Punto", point_opts, default=point_opts, label_visibility="collapsed")
        sub = sub[sub["point"].isin(sel_points)]

    with st.expander("⚙️ Avanzado: suavizado (Savitzky-Golay)"):
        st.caption("Solo cambia esta grafica; el resto de la app usa los valores por defecto.")
        sg_window = st.slider("Ventana", 5, 101, SG_WINDOW, step=2)
        sg_poly = st.slider("Orden del polinomio", 1, 5, SG_POLYORDER)

    show_raw = st.checkbox("Mostrar curva cruda", value=False)
    show_avg = st.checkbox("Mostrar promedio ± SD por tipo de hoja", value=True)

for t in sel_tipos:
    st.caption(f"**{LEAF_TYPE_LABELS[t]}** — {LEAF_TYPE_HELP[t]}")
st.caption(f"{len(sub)} archivo(s) seleccionados de **{species}**.")

if sub.empty:
    st.info("Ajusta los filtros: no hay archivos con esta combinacion.")
    st.stop()

spectra = {}
meta_by_file = {}
errors = []
for _, row in sub.iterrows():
    try:
        raw = load_spectrum(row["path"])
        spectra[row["filename"]] = prepare_spectrum(raw, sg_window, sg_poly, x_max=X_MAX)
        meta_by_file[row["filename"]] = {
            "hoja": leaf_label(row["session"], row["session_num"]),
            "tipo": row["session"],
            "num": int(row["session_num"]),
            "fecha": row["campaign_date"],
        }
    except ValueError as e:
        errors.append((row["filename"], str(e)))

if errors:
    with st.expander(f"⚠️ {len(errors)} archivo(s) con error de lectura"):
        for name, err in errors:
            st.write(f"- **{name}**: {err}")

# Leyenda agrupada por (tipo, numero de hoja): con muchas campañas, cada hoja fisica aporta una
# curva por fecha, pero comparten color+trazo y una sola entrada de leyenda. La fecha y el
# archivo se mantienen en el hover.
legend_shown = set()
fig = go.Figure()
for name, spec in spectra.items():
    meta = meta_by_file[name]
    color = LEAF_TYPE_COLORS[meta["tipo"]]
    dash = LEAF_NUM_DASH.get(meta["num"], "dot")
    legend_key = (meta["tipo"], meta["num"])
    show_legend_here = legend_key not in legend_shown
    legend_shown.add(legend_key)
    mask = spec["wavelength"] >= DISPLAY_X_MIN
    if show_raw:
        fig.add_trace(go.Scatter(
            x=spec.loc[mask, "wavelength"], y=spec.loc[mask, "reflectance"], mode="lines",
            line=dict(color=color, width=0.7), opacity=0.5, showlegend=False,
            legendgroup=str(legend_key), hoverinfo="skip",
        ))
    fig.add_trace(go.Scatter(
        x=spec.loc[mask, "wavelength"], y=spec.loc[mask, "smooth"], mode="lines",
        line=dict(color=color, width=1.6, dash=dash), opacity=0.75,
        name=f"Hoja {meta['hoja']}", legendgroup=str(legend_key), showlegend=show_legend_here,
        hovertemplate=f"{name}<br>{meta['fecha']}<br>%{{x}} nm · %{{y:.1f}}%<extra></extra>",
    ))

if show_avg:
    for t in sel_tipos:
        specs_tipo = [spec for name, spec in spectra.items() if meta_by_file[name]["tipo"] == t]
        if len(specs_tipo) < 2:
            continue
        df_avg = average_group(specs_tipo)
        if df_avg is None:
            continue
        mask = df_avg["wavelength"] >= DISPLAY_X_MIN
        color = LEAF_TYPE_COLORS[t]
        etiqueta = LEAF_TYPE_LABELS[t]
        fig.add_trace(go.Scatter(
            x=df_avg.loc[mask, "wavelength"], y=df_avg.loc[mask, "mean"] + df_avg.loc[mask, "std"],
            mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
            legendgroup=f"avg-{t}",
        ))
        fig.add_trace(go.Scatter(
            x=df_avg.loc[mask, "wavelength"], y=df_avg.loc[mask, "mean"] - df_avg.loc[mask, "std"],
            mode="lines", line=dict(width=0), fill="tonexty", fillcolor=_rgba(color, 0.18),
            name=f"± 1 SD ({etiqueta})", legendgroup=f"avg-{t}", hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=df_avg.loc[mask, "wavelength"], y=df_avg.loc[mask, "mean"], mode="lines",
            line=dict(color=color, width=3, dash="dash"),
            name=f"Promedio ({etiqueta})", legendgroup=f"avg-{t}",
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

reflect_neg = any((spec.loc[spec["wavelength"] >= DISPLAY_X_MIN, "reflectance"] < 0).any() for spec in spectra.values())
if reflect_neg:
    st.caption(
        "⚠️ Alguna curva tiene reflectancia negativa en el rango mostrado: señal débil del "
        "espectrómetro en esa medición, no un valor físico real."
    )
