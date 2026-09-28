"""Panorama: que se midio, como esta organizado el estudio y por donde empezar."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import LEAF_TYPE_LABELS, SPECIES_PENDING_LABEL, rust_risk_class
from src.indices import file_index_table, leaf_date_table, quality_flags
from src.parser import campaign_options, get_dataset, sorted_campaigns
from src.severity import leaf_date_similarity, severity_baselines
from src.ui import chart, note, page_header, section, sidebar_footer

page_header(
    "Resumen",
    "Panorama del estudio",
    "Espectros de reflectancia foliar (espectrómetro de contacto, 440–1000 nm) de cuatro variedades "
    "de café, medidos semana a semana sobre las mismas hojas para estudiar cómo se ve la roya "
    "(<i>Hemileia vastatrix</i>) en el espectro y cómo cambian las hojas sin síntomas.",
)

df = get_dataset()
if df.empty:
    st.warning("No se encontraron espectros en `data/`.")
    st.stop()
sidebar_footer(df)

files, _ = file_index_table(df)
ld = quality_flags(leaf_date_table(files))
reales = df[df["species"] != SPECIES_PENDING_LABEL]
fechas = pd.to_datetime(reales["campaign_date"])

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Espectros", f"{len(df):,}", help="Archivos .txt válidos tras las exclusiones de «Datos y calidad».")
c2.metric("Campañas", reales["campaign_id"].nunique(), help=f"{fechas.min():%d/%m/%Y} a {fechas.max():%d/%m/%Y}, una por semana aprox.")
c3.metric("Variedades", reales["species"].nunique(), help="Bourbon y Pacamara (susceptibles) · Canefora y Cuscatleco (controles sin roya).")
c4.metric("Hojas seguidas", ld["leaf_id"].nunique(), help="Hojas físicas identificadas (M1, M2, T1, T2, R1 por variedad) medidas en varias campañas.")
c5.metric("Hojas-fecha", len(ld), help="Unidad de análisis: una hoja en una campaña (media de p1–p3).")

# --------------------------------------------------------------------------------------------
section(
    "Diseño del muestreo",
    "Hojas medidas por variedad y campaña. Son las mismas hojas en todas las fechas: el estudio es "
    "longitudinal. Un guion indica que la variedad no se midió esa semana.",
)
etiquetas = campaign_options(reales)
orden = sorted_campaigns(reales)
cobertura = (
    ld.groupby(["species", "campaign_id"])["leaf"].nunique()
    .unstack(fill_value=0)
    .reindex(columns=orden, fill_value=0)
    .reindex(["Bourbon", "Pacamara", "Canefora", "Cuscatleco"])
    .dropna(how="all")
)
z = cobertura.to_numpy(dtype=float)
fig = go.Figure(go.Heatmap(
    z=z, x=[etiquetas[c][:5] for c in cobertura.columns], y=cobertura.index.tolist(),
    colorscale=[[0, "#161716"], [0.2, "#1D2733"], [1, "#2D5C92"]], zmin=0, zmax=max(z.max(), 1),
    showscale=False, xgap=3, ygap=3,
    text=np.where(z > 0, z.astype(int).astype(str), "–"), texttemplate="%{text}",
    textfont=dict(size=12, color="#ECEBE6"),
    hovertemplate="%{y} · %{x}<br>%{z:.0f} hojas medidas<extra></extra>",
))
fig.update_layout(margin=dict(l=0, r=0, t=4, b=0), xaxis=dict(side="top", showgrid=False, ticks=""),
                  yaxis=dict(autorange="reversed", showgrid=False, ticks="", tickfont=dict(size=12, color="#ECEBE6")))
chart(fig, height=190)

d1, d2, d3 = st.columns(3, gap="large")
d1.markdown(
    """<dl class="rf-kv">
<dt>Susceptibles</dt><dd>Bourbon, Pacamara</dd>
<dt>Controles</dt><dd>Canefora, Cuscatleco (sin roya)</dd>
<dt>Hojas</dt><dd>M1, M2 maduras · T1, T2 tiernas · R1 con roya</dd>
</dl>""", unsafe_allow_html=True)
d2.markdown(
    """<dl class="rf-kv">
<dt>Puntos</dt><dd>p1–p3 por hoja, no fijos entre fechas</dd>
<dt>Repeticiones</dt><dd>3 por punto (hasta 10 en julio)</dd>
<dt>Frecuencia</dt><dd>semanal, 29/06 a 21/09/2026</dd>
</dl>""", unsafe_allow_html=True)
d3.markdown(
    """<dl class="rf-kv">
<dt>Instrumento</dt><dd>espectrómetro de contacto, reflectancia %</dd>
<dt>Suavizado</dt><dd>Savitzky–Golay, ventana 41, orden 2</dd>
<dt>Agregación</dt><dd>repeticiones → punto → hoja-fecha</dd>
</dl>""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------------------
ultima = ld["campaign_date"].max()
section(
    f"Hojas maduras en la última campaña ({pd.Timestamp(ultima):%d/%m/%Y})",
    "Similitud espectral con la hoja con roya de su misma variedad (0 % = como una hoja tierna, "
    "100 % = como la hoja con roya). Es una medida relativa, no un diagnóstico: el detalle y la "
    "serie completa están en «Estado actual» y «Evolución temporal».",
)
sim = leaf_date_similarity(ld[ld["campaign_date"] == ultima], severity_baselines(df))
maduras = sim[(sim["leaf_type"] == "M") & sim["species"].isin(["Bourbon", "Pacamara"])].sort_values(["species", "leaf"])
if maduras.empty:
    st.caption("La última campaña no incluye hojas maduras de las variedades susceptibles.")
else:
    cols = st.columns(len(maduras))
    for col, r in zip(cols, maduras.itertuples()):
        _, clase, _, _ = rust_risk_class(r.similitud if pd.notna(r.similitud) else 0)
        col.metric(f"{r.species} · {r.leaf}", "—" if pd.isna(r.similitud) else f"{r.similitud * 100:.0f} %",
                   delta=clase, delta_color="off", delta_arrow="off", help=f"{r.n_puntos} puntos · {r.similitud_n_indices} de 7 índices comparables")

# --------------------------------------------------------------------------------------------
section("Cómo recorrer la aplicación")
RUTAS = [
    ("Análisis exploratorio", "¿Qué distingue a una hoja con roya?",
     "**Espectros** muestra las curvas; **Índices por tipo de hoja** compara tierna, madura y con roya con tamaño "
     "de efecto; **Comparación entre variedades** contrasta el mismo tipo de hoja entre variedades.",
     "views/indices.py", "Índices por tipo de hoja"),
    ("Seguimiento de hojas", "¿Cómo está y cómo cambia cada hoja?",
     "**Estado actual** ubica cada hoja madura entre sus referencias, fecha por fecha. **Evolución temporal** "
     "separa el cambio por envejecimiento del cambio propio de la roya.",
     "views/evolucion.py", "Evolución temporal"),
    ("Datos y operación", "¿Qué entra al análisis?",
     "**Datos y calidad** lista todo lo excluido o marcado y por qué. **Alerta de campo** revisa las mediciones "
     "nuevas y prepara el aviso por Telegram.",
     "views/datos_calidad.py", "Datos y calidad"),
]
for col, (kick, tit, cuerpo, destino, nombre) in zip(st.columns(3, gap="medium"), RUTAS):
    with col.container(border=True, height="stretch"):
        st.markdown(f'<div class="rf-card-k">{kick}</div><div class="rf-card-t">{tit}</div>', unsafe_allow_html=True)
        st.markdown(cuerpo)
        st.page_link(destino, label=f"Abrir {nombre.lower() if nombre != 'Datos y calidad' else 'datos y calidad'}",
                     icon=":material/arrow_forward:")

st.write("")
note(
    "limite",
    "Hay **una sola hoja con roya por variedad** susceptible, ya infectada en su primera medición, y "
    "no se registró ninguna hoja asintomática infectada. Los resultados describen trayectorias de "
    "hojas concretas; no permiten todavía afirmar detección temprana ni estimar un efecto poblacional.",
)
st.caption(
    "Tipos de hoja: " + " · ".join(f"{k} = {v}" for k, v in LEAF_TYPE_LABELS.items())
    + ". Tierna y madura significan «sin síntomas visibles», no «sana»."
)
