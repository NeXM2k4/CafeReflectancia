"""Indices espectrales (NDVI, PRI, PSRI, CARI) por punto de muestreo, con estadistica automatica."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import GROUP_COLORS, INDEX_DEFINITIONS, SG_POLYORDER, SG_WINDOW, X_MAX, X_MIN
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

st.set_page_config(page_title="Indices Espectrales", page_icon="🧪", layout="wide")
inject_base_css()
render_header("Indices Espectrales — comparacion por especie")

df = get_dataset()
if df.empty:
    st.warning("No hay datos en `data/`. Ve a la pagina de inicio.")
    st.stop()

recognized = df[df["name_recognized"]]

# Dimensiones de comparacion disponibles para la especie seleccionada.
# "Estado sanitario" (Sana/Con roya) es la comparacion principal para deteccion de roya.
GROUP_DIMENSIONS = {
    "Estado sanitario (Sana / Con roya)": "health_status",
    "Susceptibilidad": "susceptibility",
    "Madurez de hoja (Madura / Tierna)": "leaf_maturity",
}

with st.sidebar:
    st.markdown("**Filtros**")
    with st.container(border=True):
        filter_tag("Especie")
        species = st.selectbox("Especie", sorted(df["species"].unique()), label_visibility="collapsed")
        sub = recognized[recognized["species"] == species].copy()

        campaigns = sorted(sub["campaign_id"].dropna().unique())
        filter_tag("Campana")
        sel_campaigns = st.multiselect("Campana", campaigns, default=campaigns, label_visibility="collapsed")
        sub = sub[sub["campaign_id"].isin(sel_campaigns)]

        available_dims = [
            label for label, col in GROUP_DIMENSIONS.items()
            if sub[col].dropna().nunique() >= 2
        ]
        if not available_dims:
            st.warning(
                f"**{species}** todavia no tiene al menos 2 grupos en ninguna dimension "
                "(estado sanitario, susceptibilidad o madurez) con los filtros actuales."
            )
            st.stop()
        filter_tag("Agrupar / comparar por")
        group_label = st.radio("Agrupar / comparar por", available_dims, label_visibility="collapsed")
        group_col = GROUP_DIMENSIONS[group_label]

    with st.expander("⚙️ Parametros de suavizado (Savitzky-Golay)"):
        sg_window = st.slider("Ventana", 5, 101, SG_WINDOW, step=2)
        sg_poly = st.slider("Orden del polinomio", 1, 5, SG_POLYORDER)

if sub.empty:
    st.info("Ajusta los filtros: no hay archivos con esta combinacion.")
    st.stop()

sub = sub[sub[group_col].notna()]

# --- calculo de indices por archivo ---
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
            "Susceptibilidad": row["susceptibility"],
            "Madurez": row["leaf_maturity"],
            "Hoja": f"{row['session']}{row['session_num']}",
            "Punto": row["point"],
            "Medida": row["repetition"],
            "Archivo": row["filename"],
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

group_display_col = {
    "health_status": "Estado sanitario",
    "susceptibility": "Susceptibilidad",
    "leaf_maturity": "Madurez",
}[group_col]

# cada hoja (M1, M2, T1, T2, ...) se midio en 3 puntos, cada punto con 3 mediciones repetidas.
# el promedio real es por (hoja, punto): promedia solo las 3 mediciones repetidas de ESE punto
# en ESA hoja, sin mezclar M1 con M2 (son hojas fisicamente distintas).
group_keys = ["Especie", "Campana", "Estado sanitario", "Susceptibilidad", "Madurez", "Hoja", "Punto"]
df_points = df_raw.groupby(group_keys, dropna=False)[indices].mean().reset_index()

render_index_legend(INDEX_DEFINITIONS)

with st.container(border=True):
    st.subheader("Detalle de cada medicion (sin promediar)")
    st.caption("Una fila por cada medicion individual: hoja, punto y numero de medida repetida.")
    detail_cols = ["Especie", "Campana", "Estado sanitario", "Susceptibilidad", "Madurez", "Hoja", "Punto", "Medida", "Archivo", *indices]
    df_detail = df_raw[detail_cols].sort_values(["Hoja", "Punto", "Medida"]).reset_index(drop=True)
    st.dataframe(df_detail, width='stretch', hide_index=True, column_config=index_column_config(indices))
    st.download_button(
        "Descargar CSV (detalle)",
        df_detail.to_csv(index=False).encode("utf-8"),
        file_name=f"indices_{species.lower()}_detalle.csv",
        mime="text/csv",
        icon="⬇️",
    )

with st.container(border=True):
    st.subheader("Tabla de indices por punto y hoja (promedio de las 3 medidas repetidas)")
    st.dataframe(df_points, width='stretch', hide_index=True, column_config=index_column_config(indices))
    st.download_button(
        "Descargar CSV",
        df_points.to_csv(index=False).encode("utf-8"),
        file_name=f"indices_{species.lower()}.csv",
        mime="text/csv",
        icon="⬇️",
    )

st.subheader("Distribucion por grupo")
cols = st.columns(2)
for i, idx_name in enumerate(indices):
    with cols[i % 2]:
        fig = px.box(
            df_points, x=group_display_col, y=idx_name, color=group_display_col,
            color_discrete_map=GROUP_COLORS, points="all",
        )
        fig.update_layout(showlegend=False, height=350, margin=dict(t=30))
        st.plotly_chart(fig, width='stretch')

st.subheader("Estadistica automatica (Shapiro-Wilk → ANOVA/Tukey o Kruskal-Wallis/Dunn)")
for idx_name in indices:
    with st.expander(f"{idx_name}", expanded=False):
        groups = {
            str(g): vals.tolist()
            for g, vals in df_points.groupby(group_display_col)[idx_name]
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
