"""Comparacion de indices espectrales entre especies, con el mismo tipo de hoja en todas.

Reescrita en la fase F2 de plan_mejora_app.md: la version anterior permitia mezclar estados
sanitarios distintos entre especies (ej. Bourbon Con roya contra Cuscatleco Tierna), lo que
mezcla variedad con estado de la hoja en una sola comparacion. Ahora se elige **un solo tipo de
hoja** para las 4 especies a la vez (por defecto Tierna, la referencia sana), y la unidad de
analisis es la hoja-fecha (X4 de plan_mejora_app.md).
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import INDEX_DEFINITIONS, LEAF_TYPE_HELP, LEAF_TYPE_LABELS, SPECIES_COLORS
from src.indices import DISPLAY_INDICES, file_index_table, leaf_date_table, point_table
from src.parser import campaign_options, get_dataset, sorted_campaigns
from src.stats_utils import compare_groups, summarize_indices
from src.ui import filter_tag, index_column_config, inject_base_css, numeric_column_config, render_header, render_index_legend

st.set_page_config(page_title="Comparación entre especies", page_icon="🌱", layout="wide")
inject_base_css()
render_header("Comparación entre Especies")
st.caption(
    "Bourbon y Pacamara son las dos especies susceptibles a la roya: tienen muestras con roya "
    "confirmada además de hojas Madura/Tierna/Vieja. **Canefora y Cuscatleco son controles sin "
    "roya**: no tienen hojas con roya propias, así que sirven para ver si un patrón es propio de "
    "la variedad o aparece igual en todas (ver Evolución Temporal para el uso completo de estos "
    "controles)."
)

df = get_dataset()
if df.empty:
    st.warning("No hay datos en `data/`. Ve a la página de inicio.")
    st.stop()

files_all, read_errors = file_index_table(df)

with st.sidebar:
    st.markdown("**Filtros**")
    with st.container(border=True):
        species_opts = sorted(df["species"].unique())
        filter_tag("Especies")
        sel_species = st.multiselect("Especies", species_opts, default=species_opts, label_visibility="collapsed")

        campaigns_all = sorted_campaigns(df[df["species"].isin(sel_species)])
        labels_camp = campaign_options(df)
        filter_tag("Campaña")
        sel_campaigns = st.multiselect(
            "Campaña", campaigns_all, default=campaigns_all, format_func=labels_camp.get,
            label_visibility="collapsed",
        )

        tipos_disp = [
            t for t in ["T", "M", "R", "V"]
            if ((files_all["species"].isin(sel_species)) & (files_all["leaf_type"] == t)).any()
        ]
        filter_tag("Tipo de hoja (uno solo)")
        tipo = st.radio(
            "Tipo de hoja", tipos_disp, format_func=lambda t: LEAF_TYPE_LABELS[t],
            label_visibility="collapsed",
            help="Se compara siempre el mismo tipo de hoja entre especies, para no mezclar "
                 "variedad con estado de la hoja.",
        )

if read_errors:
    with st.expander(f"⚠️ {len(read_errors)} archivo(s) con error de lectura"):
        for name, err in read_errors:
            st.write(f"- **{name}**: {err}")

if len(sel_species) < 2:
    st.info("Selecciona al menos 2 especies para comparar.")
    st.stop()

st.caption(f"**{LEAF_TYPE_LABELS[tipo]}** — {LEAF_TYPE_HELP[tipo]}")
if tipo == "R":
    st.warning(
        "Cada especie susceptible tiene **una sola hoja con roya** en todo el dataset: esta "
        "comparación contrasta 1 hoja de Bourbon contra 1 de Pacamara, no una muestra "
        "poblacional de cada variedad."
    )

files_sel = files_all[
    files_all["species"].isin(sel_species)
    & files_all["campaign_id"].isin(sel_campaigns)
    & (files_all["leaf_type"] == tipo)
]
if files_sel.empty:
    st.info("No hay archivos con esta combinacion de filtros.")
    st.stop()

ld = leaf_date_table(files_sel)
especies_presentes = [s for s in sel_species if (ld["species"] == s).any()]

render_index_legend(INDEX_DEFINITIONS)

st.subheader(f"Resumen: diferencias entre especies en hojas {LEAF_TYPE_LABELS[tipo].lower()}")
st.caption(
    "Mediana por especie, tamaño de efecto (si son 2 especies) y p ajustado por Holm entre "
    "todos los índices."
)
if len(especies_presentes) < 2:
    st.info("Con los filtros actuales solo queda 1 especie con datos: no hay nada que comparar.")
else:
    resumen = summarize_indices(ld, "species", DISPLAY_INDICES).set_index("Índice")

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
        width="stretch", column_config=numeric_column_config(resumen),
    )

st.subheader("Distribución por especie")
cols = st.columns(2)
for i, idx_name in enumerate(DISPLAY_INDICES):
    with cols[i % 2]:
        fig = px.box(
            ld, x="species", y=idx_name, color="species",
            color_discrete_map=SPECIES_COLORS, points="all",
            hover_data=["leaf", "campaign_date"],
        )
        fig.update_layout(showlegend=False, height=330, margin=dict(t=30), xaxis_title=None)
        st.plotly_chart(fig, width="stretch")

with st.expander("📄 Datos: tabla por hoja-fecha y por punto"):
    cols_hd = ["species", "leaf", "campaign_id", "campaign_date", "n_puntos", "n_archivos", *DISPLAY_INDICES]
    st.dataframe(ld[cols_hd], width="stretch", hide_index=True, column_config=index_column_config(DISPLAY_INDICES))
    st.download_button(
        "Descargar CSV (hoja-fecha)", ld[cols_hd].to_csv(index=False).encode("utf-8"),
        file_name="comparacion_especies_hoja_fecha.csv", mime="text/csv", icon="⬇️",
    )
    pts = point_table(files_sel)
    cols_pt = ["species", "leaf", "campaign_id", "campaign_date", "point", "n_archivos", *DISPLAY_INDICES]
    st.dataframe(pts[cols_pt], width="stretch", hide_index=True, column_config=index_column_config(DISPLAY_INDICES))

with st.expander("🔬 Detalle técnico: Shapiro-Wilk, ANOVA/Tukey o Kruskal-Wallis/Dunn (sin corrección)"):
    for idx_name in DISPLAY_INDICES:
        with st.expander(idx_name, expanded=False):
            groups = {sp: ld.loc[ld["species"] == sp, idx_name].tolist() for sp in especies_presentes}
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
