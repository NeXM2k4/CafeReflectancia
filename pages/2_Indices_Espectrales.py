"""Indices espectrales por tipo de hoja, con estadistica automatica y veredicto.

Reescrita en la fase F2 de plan_mejora_app.md: antes agrupaba por 3 dimensiones que se pisaban
(estado sanitario, susceptibilidad, madurez) y calculaba sus propios indices archivo por archivo,
sin filtrar puntos. Ahora agrupa por **tipo de hoja** (Madura/Tierna/Con roya/Vieja, ver Inicio),
usa la tabla unica de `src.indices` y la unidad de analisis es la **hoja-fecha** (X4 de
plan_mejora_app.md): un punto por hoja fisica y campaña, no por medicion individual.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import INDEX_DEFINITIONS, LEAF_TYPE_COLORS, LEAF_TYPE_HELP, LEAF_TYPE_LABELS
from src.indices import DISPLAY_INDICES, file_index_table, leaf_date_table, point_table
from src.parser import campaign_options, get_dataset, sorted_campaigns
from src.stats_utils import compare_groups, summarize_indices
from src.ui import filter_tag, index_column_config, inject_base_css, numeric_column_config, render_header, render_index_legend

st.set_page_config(page_title="Índices Espectrales", page_icon="🧪", layout="wide")
inject_base_css()
render_header("Índices Espectrales — qué índices separan cada tipo de hoja")

df = get_dataset()
if df.empty:
    st.warning("No hay datos en `data/`. Ve a la página de inicio.")
    st.stop()

with st.sidebar:
    st.markdown("**Filtros**")
    with st.container(border=True):
        filter_tag("Especie")
        species = st.selectbox("Especie", sorted(df["species"].unique()), label_visibility="collapsed")

        campaigns_all = sorted_campaigns(df[df["species"] == species])
        labels_camp = campaign_options(df)
        filter_tag("Campaña")
        sel_campaigns = st.multiselect(
            "Campaña", campaigns_all, default=campaigns_all, format_func=labels_camp.get,
            label_visibility="collapsed",
        )

        files_sp, read_errors = file_index_table(df)
        files_sp = files_sp[(files_sp["species"] == species) & (files_sp["campaign_id"].isin(sel_campaigns))]
        tipos_disponibles = [t for t in ["M", "T", "R", "V"] if (files_sp["leaf_type"] == t).any()]
        filter_tag("Tipo de hoja")
        sel_tipos = st.multiselect(
            "Tipo de hoja", tipos_disponibles, default=tipos_disponibles,
            format_func=lambda t: LEAF_TYPE_LABELS[t], label_visibility="collapsed",
        )

if read_errors:
    with st.expander(f"⚠️ {len(read_errors)} archivo(s) con error de lectura"):
        for name, err in read_errors:
            st.write(f"- **{name}**: {err}")

files_sel = files_sp[files_sp["leaf_type"].isin(sel_tipos)]
if files_sel.empty:
    st.info("Ajusta los filtros: no hay archivos con esta combinacion.")
    st.stop()

n_r_hojas = files_sel.loc[files_sel["leaf_type"] == "R", "leaf"].nunique()
if n_r_hojas:
    st.warning(
        f"**{species}** tiene {n_r_hojas} sola(s) hoja(s) con roya en todo el dataset. Todo lo "
        "que se ve aquí para 'Con roya' describe esa(s) hoja(s) puntual(es), no una muestra "
        "poblacional — ver la sección de limitaciones en Evolución Temporal."
    )

ld = leaf_date_table(files_sel)  # unidad de analisis: hoja-fecha (solo p1-p3)
tipos_presentes = [t for t in sel_tipos if (ld["leaf_type"] == t).any()]
ld_display = ld.copy()
ld_display["Tipo de hoja"] = ld_display["leaf_type"].map(LEAF_TYPE_LABELS)

render_index_legend(INDEX_DEFINITIONS)
for code in tipos_presentes:
    st.caption(f"**{LEAF_TYPE_LABELS[code]}** — {LEAF_TYPE_HELP[code]}")

st.subheader("Resumen: qué índices separan cada tipo de hoja")
st.caption(
    "Cada fila es un índice; cada columna 'n' y 'Mediana' es un tipo de hoja. Con 2 tipos de "
    "hoja se usa Mann-Whitney U + tamaño de efecto (δ de Cliff, -1 a +1); con 3 o más, "
    "Kruskal-Wallis. El p se ajusta por Holm entre todos los índices de esta tabla."
)

if len(tipos_presentes) < 2:
    st.info("Selecciona al menos 2 tipos de hoja para poder compararlos.")
else:
    resumen = summarize_indices(ld_display, "Tipo de hoja", DISPLAY_INDICES).set_index("Índice")

    def _resalta_veredicto(v):
        color = {
            "Separa claramente los grupos": "#0CA30C",
            "Diferencia moderada": "#C98500",
            "Diferencia débil (estadísticamente significativa, pero el solape es grande)": "#8A8A8A",
            "No separa los grupos": "#7A7E85",
        }.get(v, "#7A7E85")
        return f"color: {color}; font-weight: 600"

    st.dataframe(
        resumen.style.map(_resalta_veredicto, subset=["Veredicto"]),
        width="stretch",
        column_config=numeric_column_config(resumen, decimals=4),
    )

st.subheader("Distribución por tipo de hoja (una hoja-fecha por punto)")
cols = st.columns(2)
for i, idx_name in enumerate(DISPLAY_INDICES):
    with cols[i % 2]:
        fig = px.box(
            ld_display, x="Tipo de hoja", y=idx_name, color="Tipo de hoja",
            color_discrete_map={LEAF_TYPE_LABELS[c]: LEAF_TYPE_COLORS[c] for c in tipos_presentes},
            points="all", hover_data=["leaf", "campaign_date"],
        )
        fig.update_layout(showlegend=False, height=330, margin=dict(t=30))
        st.plotly_chart(fig, width="stretch")

with st.expander("📄 Datos: tablas por hoja-fecha, por punto y detalle sin promediar"):
    st.markdown("**Hoja-fecha** (unidad de análisis de arriba): media de los puntos de esa hoja en esa campaña.")
    cols_hd = ["species", "leaf", "Tipo de hoja", "campaign_id", "campaign_date", "n_puntos", "n_archivos", *DISPLAY_INDICES]
    st.dataframe(ld_display[cols_hd], width="stretch", hide_index=True, column_config=index_column_config(DISPLAY_INDICES))
    st.download_button(
        "Descargar CSV (hoja-fecha)", ld_display[cols_hd].to_csv(index=False).encode("utf-8"),
        file_name=f"indices_{species.lower()}_hoja_fecha.csv", mime="text/csv", icon="⬇️",
    )

    st.markdown("**Por punto** (promedio de las 3 repeticiones de cada punto, antes de agregar a hoja-fecha):")
    pts = point_table(files_sel)
    pts_display = pts.copy()
    pts_display["Tipo de hoja"] = pts_display["leaf_type"].map(LEAF_TYPE_LABELS)
    cols_pt = ["species", "leaf", "Tipo de hoja", "campaign_id", "campaign_date", "point", "n_archivos", *DISPLAY_INDICES]
    st.dataframe(pts_display[cols_pt], width="stretch", hide_index=True, column_config=index_column_config(DISPLAY_INDICES))

    st.markdown("**Detalle sin promediar** (una fila por medición individual, incluye FSR y puntos p4+):")
    cols_detalle = ["species", "leaf", "leaf_type", "campaign_id", "campaign_date", "point", "repetition", "filename", *list(INDEX_DEFINITIONS)]
    st.dataframe(files_sp[files_sp["leaf_type"].isin(sel_tipos)][cols_detalle], width="stretch", hide_index=True,
                 column_config=index_column_config(list(INDEX_DEFINITIONS)))
    st.download_button(
        "Descargar CSV (detalle sin promediar)",
        files_sp[files_sp["leaf_type"].isin(sel_tipos)][cols_detalle].to_csv(index=False).encode("utf-8"),
        file_name=f"indices_{species.lower()}_detalle.csv", mime="text/csv", icon="⬇️",
    )

with st.expander("🔬 Detalle técnico: Shapiro-Wilk, ANOVA/Tukey o Kruskal-Wallis/Dunn (sin corrección, por hoja-fecha)"):
    st.caption(
        "Mismo pipeline que antes de esta reescritura, ahora sobre hoja-fecha en vez de puntos "
        "individuales. Sin corrección por comparaciones múltiples entre índices (para eso, la "
        "tabla resumen de arriba). Útil para ver la normalidad y el post-hoc completo por par."
    )
    for idx_name in DISPLAY_INDICES:
        with st.expander(idx_name, expanded=False):
            groups = {
                LEAF_TYPE_LABELS[t]: ld.loc[ld["leaf_type"] == t, idx_name].tolist()
                for t in tipos_presentes
            }
            result = compare_groups(groups)
            summary_df = pd.DataFrame(result["summary"]).T
            st.dataframe(summary_df, width="stretch", column_config=numeric_column_config(summary_df, exclude=("n",)))
            if result["message"]:
                st.info(result["message"])
                continue
            shapiro_df = pd.DataFrame(result["shapiro"]).T
            st.caption("Normalidad por grupo (Shapiro-Wilk):")
            st.dataframe(shapiro_df, width="stretch", column_config=numeric_column_config(shapiro_df))
            sig = "significativo ✅" if result["significant"] else "no significativo"
            st.write(f"**{result['test_name']}**: estadístico = {result['stat']:.4f}, p = {result['p_value']:.4f} ({sig})")
            if result["posthoc"] is not None:
                st.caption(f"Post-hoc: {result['posthoc_name']}")
                st.dataframe(result["posthoc"], width="stretch", column_config=numeric_column_config(result["posthoc"]))
