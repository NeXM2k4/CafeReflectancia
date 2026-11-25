"""Rasgos espectrales: posición del borde rojo, pico verde, pozo de clorofila y ángulo espectral, hoja por hoja."""

import pandas as pd
import streamlit as st

from src import spectral, spectral_page
from src.config import LEAF_TYPE_COLORS, TEMPORAL_BASELINE_CAMPAIGNS, TEMPORAL_MIN_FECHAS_TENDENCIA
from src.plots_cambio import feature_small_multiples
from src.spectral import F_SAM_R1, FEATURE_COLUMNS, FEATURE_DEFINITIONS
from src.temporal import index_change_summary, leaf_trends
from src.temporal_plots import SPECIES_ORDER, TREND_CAPTION
from src.ui import chart, keep_widget_state, note, numeric_column_config, page_header, section

keep_widget_state(keys=("rasgos_sp", "rasgos_tipo"))

page_header(
    "Seguimiento de hojas",
    "Rasgos espectrales",
    "Lo que los siete índices no ven: dónde está el borde rojo, cuánto empina, dónde cae el pico verde y qué tan "
    "profundo es el pozo de clorofila. Cada rasgo se calcula por hoja y fecha sobre el espectro completo.",
)

sel, ctx = spectral_page.sidebar()


@st.cache_data(show_spinner="Calculando rasgos espectrales...")
def _features(include_sin: bool, excl: bool, n_base: int) -> pd.DataFrame:
    c = spectral_page.load_context(include_sin, excl)
    return spectral.features_table(c.spectra, c.meta, n_base)


@st.cache_data(show_spinner="Calculando tendencias de los rasgos...")
def _feature_trends(include_sin: bool, excl: bool, n_base: int) -> pd.DataFrame:
    return leaf_trends(_features(include_sin, excl, n_base), FEATURE_COLUMNS, "rasgos")


ft = _features(sel.include_sin_hoja, sel.excl_atipicas, TEMPORAL_BASELINE_CAMPAIGNS)
if ft.empty:
    st.warning("No hay datos para calcular rasgos.")
    st.stop()
ft_leaf = ft[ft["leaf_id"] == sel.leaf_id]
leaf_title = f"{sel.species} · {sel.leaf}"

# ---------- series de la hoja ----------
section(f"Rasgos de {leaf_title} en el tiempo",
        "Cada punto es una hoja-fecha (media de p1–p3); la línea es una tendencia suavizada (LOWESS) descriptiva.")
if ft_leaf.empty:
    st.info("Esta hoja no tiene espectros válidos.")
else:
    if ft_leaf[F_SAM_R1].isna().all():
        st.caption("«SAM R1» no aplica a esta hoja: solo se calcula para hojas M y T de variedades que tienen una hoja R "
                   "(Bourbon y Pacamara); la propia R1 y los controles quedan sin valor.")
    chart(feature_small_multiples(ft_leaf, FEATURE_COLUMNS, LEAF_TYPE_COLORS.get(sel.leaf_type, "#6B6A64"),
                                  na_columns=(F_SAM_R1,)), key="rasgos_series")
    st.caption(f"{TREND_CAPTION} SAM base: ángulo contra la media de las primeras {TEMPORAL_BASELINE_CAMPAIGNS} fechas "
               "de la hoja (por eso es ≈ 0 al inicio).")
    if len(ft_leaf) < TEMPORAL_MIN_FECHAS_TENDENCIA:
        st.caption(f"Esta hoja tiene {len(ft_leaf)} fechas: se muestran sin curva suavizada ni tendencia "
                   f"(mínimo {TEMPORAL_MIN_FECHAS_TENDENCIA}).")

# ---------- tendencias de todas las hojas ----------
trends = _feature_trends(sel.include_sin_hoja, sel.excl_atipicas, TEMPORAL_BASELINE_CAMPAIGNS)
section("Tendencias por hoja",
        f"Pendiente de Theil–Sen (unidades del rasgo por semana) y Mann–Kendall con al menos "
        f"{TEMPORAL_MIN_FECHAS_TENDENCIA} fechas. La corrección de Benjamini–Hochberg se aplica sobre **todas las hojas y "
        "todos los rasgos a la vez**, así que no cambia al mover los filtros.")
c1, c2, c3 = st.columns([2, 2, 1])
sp_pick = c1.pills("Variedad", SPECIES_ORDER, default=[sel.species], selection_mode="multi", key="rasgos_sp") or []
tipo_pick = c2.pills("Tipo de hoja", ["M", "T", "R"], default=["M", "T", "R"], selection_mode="multi",
                     key="rasgos_tipo") or []
solo_sig = c3.toggle("Solo significativas", value=False, key="rasgos_sig")
tab = trends[trends["Especie"].isin(sp_pick) & trends["Tipo"].isin(tipo_pick)]
if solo_sig:
    tab = tab[tab["Significativa"] == True]  # noqa: E712
cols = ["Especie", "Hoja", "Variable", "n fechas", "Pendiente / semana", "IC95 inf", "IC95 sup", "tau", "p", "p FDR",
        "Significativa", "r1 residuos", "Motivo omision"]
tab = tab[[c for c in cols if c in tab]].sort_values(["Especie", "Hoja", "Variable"])
st.dataframe(tab, hide_index=True, width="stretch",
             column_config={**numeric_column_config(tab, 4, exclude=("Pendiente / semana", "IC95 inf", "IC95 sup")),
                            **{c: st.column_config.NumberColumn(c, format="%.5f")
                               for c in ("Pendiente / semana", "IC95 inf", "IC95 sup") if c in tab}})
st.caption("Los rasgos sin evaluar (p. ej. SAM R1 en R1 y en los controles, o hojas con menos de "
           f"{TEMPORAL_MIN_FECHAS_TENDENCIA} fechas, como Canefora M2 y T2) aparecen con su motivo de omisión.")

# ---------- lectura por grupos ----------
section("Lectura por grupos: ¿envejecimiento o roya?",
        "Mismas reglas fijas que en «Evolución temporal»: por rasgo y grupo de hojas, cuántas tendencias significativas "
        "suben o bajan, y una lectura por reglas.")
resumen = index_change_summary(trends, ctx.species_with_rust).rename(columns={"Índice": "Rasgo"})
st.dataframe(resumen, hide_index=True, width="stretch",
             column_config={c: st.column_config.NumberColumn(c, format="%.5f") for c in resumen.columns if "mediana" in c})
note("limite", "Una sola hoja R por variedad, ya infectada el 15/07: «propio de la roya» describe a esa hoja, no "
               "a la enfermedad en general. Las mediciones sucesivas de una hoja son autocorrelacionadas, así que los "
               "p-valores son optimistas (el FDR controla la multiplicidad, no la autocorrelación). Canefora M2 y T2 "
               "tienen 4 fechas y no entran en ningún test.")

# ---------- definiciones ----------
section("Definición de cada rasgo")
defs = pd.DataFrame([{"Rasgo": k, "Unidad": u, "Definición": d, "Por qué importa": w}
                     for k, (u, d, w) in FEATURE_DEFINITIONS.items()])
st.dataframe(defs, hide_index=True, width="stretch")
