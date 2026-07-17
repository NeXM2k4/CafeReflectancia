"""Comparacion de indices espectrales entre las 4 especies de cafe."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import INDEX_DEFINITIONS, SG_POLYORDER, SG_WINDOW, SPECIES_COLORS, X_MAX, X_MIN
from src.parser import get_dataset, load_spectrum
from src.processing import calcular_indices, prepare_spectrum
from src.stats_utils import compare_groups
from src.ui import (
    filter_tag,
    index_column_config,
    inject_base_css,
    numeric_column_config,
    render_header,
    render_index_legend,
)

st.set_page_config(page_title="Comparacion entre especies", page_icon="🌱", layout="wide")
inject_base_css()
render_header("Comparacion entre Especies — Bourbon, Canefora, Cuscatleco y Pacamara")
st.caption(
    "Por ahora solo Bourbon y Pacamara tienen muestras con roya confirmada; "
    "Canefora y Cuscatleco todavia solo tienen hojas sanas (Madura/Tierna)."
)

df = get_dataset()
if df.empty:
    st.warning("No hay datos en `data/`. Ve a la pagina de inicio.")
    st.stop()

recognized = df[df["name_recognized"]]

with st.sidebar:
    st.markdown("**Filtros**")
    with st.container(border=True):
        filter_tag("Especies")
        species_opts = sorted(recognized["species"].unique())
        sel_species = st.multiselect("Especies", species_opts, default=species_opts, label_visibility="collapsed")
        sub = recognized[recognized["species"].isin(sel_species)]

        campaigns = sorted(sub["campaign_id"].dropna().unique())
        filter_tag("Campana")
        sel_campaigns = st.multiselect("Campana", campaigns, default=campaigns, label_visibility="collapsed")
        sub = sub[sub["campaign_id"].isin(sel_campaigns)]

        if sub["health_status"].notna().any():
            health_opts = sorted(sub["health_status"].dropna().unique())
            filter_tag("Estado sanitario")
            sel_health = st.multiselect("Estado sanitario", health_opts, default=health_opts, label_visibility="collapsed")
            sub = sub[sub["health_status"].isin(sel_health)]

    with st.expander("⚙️ Parametros de suavizado (Savitzky-Golay)"):
        sg_window = st.slider("Ventana", 5, 101, SG_WINDOW, step=2)
        sg_poly = st.slider("Orden del polinomio", 1, 5, SG_POLYORDER)

if sub.empty or len(sel_species) < 2:
    st.info("Selecciona al menos 2 especies para comparar.")
    st.stop()

rows = []
errors = []
for _, row in sub.iterrows():
    try:
        raw = load_spectrum(row["path"])
        spec = prepare_spectrum(raw, sg_window, sg_poly, X_MIN, X_MAX)
        idx = calcular_indices(spec)
        rows.append({
            "Especie": row["species"],
            "Campana": row["campaign_id"],
            "Estado sanitario": row["health_status"],
            "Madurez": row["leaf_maturity"],
            "Hoja": f"{row['session']}{row['session_num']}",
            "Punto": row["point"],
            **idx,
        })
    except ValueError as e:
        errors.append((row["filename"], str(e)))

if errors:
    with st.expander(f"⚠️ {len(errors)} archivo(s) con error de lectura"):
        for name, err in errors:
            st.write(f"- **{name}**: {err}")

if not rows:
    st.warning("No se pudo calcular indices para ningun archivo con estos filtros.")
    st.stop()

df_raw = pd.DataFrame(rows)
indices = ["NDVI", "PRI", "PSRI", "CARI", "RCI", "EDI", "FSR"]
# cada hoja (M1, M2, T1, T2...) se promedia solo dentro de si misma, sin mezclar hojas distintas.
group_keys = ["Especie", "Campana", "Estado sanitario", "Madurez", "Hoja", "Punto"]
df_points = df_raw.groupby(group_keys, dropna=False)[indices].mean().reset_index()

render_index_legend(INDEX_DEFINITIONS)

with st.container(border=True):
    st.subheader("Tabla de indices por punto (promedio de repeticiones)")
    st.dataframe(df_points, width='stretch', hide_index=True, column_config=index_column_config(indices))
    st.download_button(
        "Descargar CSV",
        df_points.to_csv(index=False).encode("utf-8"),
        file_name="indices_comparacion_especies.csv",
        mime="text/csv",
        icon="⬇️",
    )

st.subheader("Distribucion por especie")
cols = st.columns(2)
for i, idx_name in enumerate(indices):
    with cols[i % 2]:
        fig = px.box(
            df_points, x="Especie", y=idx_name, color="Especie",
            color_discrete_map=SPECIES_COLORS, points="all",
        )
        fig.update_layout(showlegend=False, height=350, margin=dict(t=30))
        st.plotly_chart(fig, width='stretch')

st.subheader("Estadistica automatica entre especies (Shapiro-Wilk → ANOVA/Tukey o Kruskal-Wallis/Dunn)")
for idx_name in indices:
    with st.expander(f"{idx_name}", expanded=False):
        groups = {
            str(g): vals.tolist()
            for g, vals in df_points.groupby("Especie")[idx_name]
        }
        result = compare_groups(groups)

        summary_df = pd.DataFrame(result["summary"]).T
        st.dataframe(
            summary_df, width='stretch',
            column_config=numeric_column_config(summary_df, exclude=("n",)),
        )

        if result["message"]:
            st.info(result["message"])
            continue

        shapiro_df = pd.DataFrame(result["shapiro"]).T
        st.caption("Normalidad por grupo (Shapiro-Wilk):")
        st.dataframe(shapiro_df, width='stretch', column_config=numeric_column_config(shapiro_df))

        sig = "significativo ✅" if result["significant"] else "no significativo"
        st.write(
            f"**{result['test_name']}**: estadistico = {result['stat']:.4f}, "
            f"p = {result['p_value']:.4f} ({sig})"
        )

        if result["posthoc"] is not None:
            st.caption(f"Post-hoc: {result['posthoc_name']}")
            st.dataframe(
                result["posthoc"], width='stretch',
                column_config=numeric_column_config(result["posthoc"]),
            )
