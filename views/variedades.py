"""Comparacion entre variedades con el mismo tipo de hoja."""

import pandas as pd
import streamlit as st

from src.config import LEAF_TYPE_HELP, LEAF_TYPE_LABELS, SPECIES_COLORS, SPECIES_PENDING_LABEL
from src.indices import DISPLAY_INDICES, file_index_table, leaf_date_table, quality_flags
from src.parser import get_dataset
from src.ui import (campaign_range, html_table, index_column_config, index_sheet_table, leaf_sort, note,
                    page_header, section, sidebar_footer)
from src.viz_groups import distributions, effect_matrix, global_test, pair_table, technical_detail

ORDEN = ["Bourbon", "Pacamara", "Canefora", "Cuscatleco"]
SUSCEPTIBLES = {"Bourbon", "Pacamara"}

page_header(
    "Análisis exploratorio",
    "Comparación entre variedades",
    "¿Difieren las variedades cuando se compara el mismo tipo de hoja? Fijar el tipo de hoja evita "
    "confundir el efecto de la variedad con el de la edad o el estado de la hoja.",
)

df = get_dataset()
if df.empty:
    st.warning("No se encontraron espectros en `data/`.")
    st.stop()
files_all, _ = file_index_table(df)
files_all = files_all[files_all["species"] != SPECIES_PENDING_LABEL]

with st.sidebar:
    tipos_disp = leaf_sort([t for t in ["T", "M", "R", "V"] if (files_all["leaf_type"] == t).any()])
    tipo = st.segmented_control("Tipo de hoja", tipos_disp, default="T", format_func=LEAF_TYPE_LABELS.get,
                                key="var_tipo", help="Se compara siempre un único tipo de hoja entre variedades.") or "T"
    disp = [s for s in ORDEN if ((files_all["species"] == s) & (files_all["leaf_type"] == tipo)).any()]
    sel_sp = st.pills("Variedades", disp, default=disp, selection_mode="multi", key=f"var_sp_{tipo}")
    sel_c = campaign_range(df[df["species"].isin(disp)], key="var_camp")
sidebar_footer(df)

sel_sp = [s for s in ORDEN if s in (sel_sp or [])]
st.caption(f"**{LEAF_TYPE_LABELS[tipo]}**: {LEAF_TYPE_HELP[tipo]}")
if tipo == "R":
    note("limite", "Solo Bourbon y Pacamara tienen hoja con roya, y cada una tiene **una sola** (R1): esta "
                   "comparación contrasta dos hojas concretas medidas en varias fechas, no dos poblaciones.")
elif tipo == "V":
    note("limite", "Las hojas viejas solo tienen variedad registrada en pocas campañas (el resto se excluye); "
                   "la comparación descansa en muy pocas hojas-fecha.")
if len(sel_sp) < 2:
    st.info("Se necesitan al menos dos variedades con datos para comparar.")
    st.stop()

ld_full = quality_flags(leaf_date_table(files_all[files_all["species"].isin(sel_sp)]))
ld = ld_full[(ld_full["leaf_type"] == tipo) & ld_full["campaign_id"].isin(sel_c)].copy()
presentes = [s for s in sel_sp if (ld["species"] == s).any()]
if len(presentes) < 2:
    st.info("Con los filtros actuales queda una sola variedad con datos.")
    st.stop()

conteo = ld.groupby("species").agg(hojas=("leaf", "nunique"), n=("leaf", "size")).reindex(presentes)
html_table(pd.DataFrame({
    "Variedad": presentes,
    "Rol": ["susceptible" if s in SUSCEPTIBLES else "control sin roya" for s in presentes],
    "Hojas": conteo["hojas"].tolist(), "Hojas-fecha": conteo["n"].tolist(),
}), num_cols=("Hojas", "Hojas-fecha"), strong_cols=("Variedad",))

# --------------------------------------------------------------------------------------------
section(f"Tamaño de efecto entre variedades · hoja {LEAF_TYPE_LABELS[tipo].lower()}",
        "δ de Cliff para cada par de variedades. Una diferencia que aparece también entre controles sin roya "
        "habla de la variedad, no de la roya.")
pares = [(presentes[i], presentes[j]) for i in range(len(presentes)) for j in range(i + 1, len(presentes))]
tabla = effect_matrix(ld, "species", DISPLAY_INDICES, pares)

section("Distribución de cada índice", "Una hoja-fecha por punto; círculos vacíos: marcadas por control de calidad.")
distributions(ld, "species", presentes, SPECIES_COLORS, DISPLAY_INDICES, flag_col="qc_flag")

section("Más detalle")
t1, t2, t3, t4, t5 = st.tabs(["Comparaciones por pares", "Prueba global", "Datos", "Detalle técnico", "Índices"])
with t1:
    pair_table(tabla)
with t2:
    global_test(ld, "species", DISPLAY_INDICES)
with t3:
    cols_hd = ["species", "leaf", "campaign_date", "n_puntos", "n_archivos", "qc_flag", *DISPLAY_INDICES]
    st.dataframe(ld[cols_hd], width="stretch", hide_index=True, column_config={
        **index_column_config(DISPLAY_INDICES), "campaign_date": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
        "qc_flag": st.column_config.CheckboxColumn("Marcada QC")})
    st.download_button("Descargar hoja-fecha (CSV)", ld[cols_hd].to_csv(index=False).encode("utf-8"),
                       file_name=f"variedades_{LEAF_TYPE_LABELS[tipo].lower().replace(' ', '_')}_hoja_fecha.csv",
                       mime="text/csv", icon=":material/download:")
with t4:
    technical_detail(ld, "species", presentes, DISPLAY_INDICES)
with t5:
    index_sheet_table(DISPLAY_INDICES)
