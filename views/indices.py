"""Indices espectrales por tipo de hoja: que indices distinguen la hoja con roya de la tierna y la madura."""

import pandas as pd
import streamlit as st

from src.config import LEAF_TYPE_COLORS, LEAF_TYPE_LABELS, SPECIES_PENDING_LABEL
from src.indices import DISPLAY_INDICES, file_index_table, leaf_date_table, point_table, quality_flags
from src.parser import get_dataset
from src.ui import (campaign_range, index_column_config, leaf_legend, leaf_sort, note, page_header,
                    index_sheet_table, section, sidebar_footer)
from src.viz_groups import distributions, effect_matrix, global_test, pair_table, technical_detail

page_header(
    "Análisis exploratorio",
    "Índices por tipo de hoja",
    "¿Qué índices distinguen a la hoja con roya de las hojas sin síntomas, y cuánto? La unidad es la "
    "hoja-fecha: una hoja en una campaña, con la media de sus puntos p1–p3.",
)

df = get_dataset()
if df.empty:
    st.warning("No se encontraron espectros en `data/`.")
    st.stop()
files_all, read_errors = file_index_table(df)
files_all = files_all[files_all["species"] != SPECIES_PENDING_LABEL]

with st.sidebar:
    especies = [s for s in ["Bourbon", "Pacamara", "Canefora", "Cuscatleco"] if s in set(files_all["species"])]
    species = st.selectbox("Variedad", especies, key="idx_sp")
    files_sp = files_all[files_all["species"] == species]
    sel_c = campaign_range(df[df["species"] == species], key="idx_camp")
    files_sp = files_sp[files_sp["campaign_id"].isin(sel_c)]
    tipos_disp = leaf_sort([t for t in ["T", "M", "V", "R"] if (files_sp["leaf_type"] == t).any()])
    sel_tipos = st.pills("Tipos de hoja", tipos_disp, default=tipos_disp, selection_mode="multi",
                         format_func=LEAF_TYPE_LABELS.get, key=f"idx_tipos_{species}")
sidebar_footer(df)

sel_tipos = leaf_sort(sel_tipos or [])
files_sel = files_sp[files_sp["leaf_type"].isin(sel_tipos)]
if files_sel.empty:
    st.info("No hay datos con esta combinación de filtros.")
    st.stop()

# Control de calidad sobre la serie completa de cada hoja (necesita su historia), luego se filtra.
ld_full = quality_flags(leaf_date_table(files_all[files_all["species"] == species]))
ld = ld_full[ld_full["campaign_id"].isin(sel_c) & ld_full["leaf_type"].isin(sel_tipos)].copy()
ld["Tipo"] = ld["leaf_type"].map(LEAF_TYPE_LABELS)
presentes = [t for t in sel_tipos if (ld["leaf_type"] == t).any()]
nombres = [LEAF_TYPE_LABELS[t] for t in presentes]

leaf_legend(presentes)
conteo = ld.groupby("leaf_type").agg(hojas=("leaf", "nunique"), n=("leaf", "size"))
st.caption(" · ".join(
    f"{LEAF_TYPE_LABELS[t]}: {conteo.loc[t, 'n']} hojas-fecha de {conteo.loc[t, 'hojas']} "
    f"hoja{'s' if conteo.loc[t, 'hojas'] != 1 else ''}" for t in presentes))
if "R" in presentes:
    note("limite", f"En {species} hay **una sola hoja con roya** (R1). Sus {conteo.loc['R', 'n']} hojas-fecha son "
                   "mediciones repetidas de esa hoja, no hojas distintas: las diferencias describen a R1, no a "
                   "la roya en general.")

# --------------------------------------------------------------------------------------------
section("Tamaño de efecto entre tipos de hoja",
        "δ de Cliff de cada índice para cada par de tipos de hoja. Es la respuesta principal de esta vista: "
        "cuánto se solapan los dos grupos, independientemente de la escala del índice.")
if len(presentes) < 2:
    st.info("Se necesitan al menos dos tipos de hoja para comparar.")
    tabla = pd.DataFrame()
else:
    orden_pares = [("R", "T"), ("R", "M"), ("R", "V"), ("M", "T"), ("V", "T"), ("V", "M")]
    pares = [(LEAF_TYPE_LABELS[a], LEAF_TYPE_LABELS[b]) for a, b in orden_pares if a in presentes and b in presentes]
    tabla = effect_matrix(ld, "Tipo", DISPLAY_INDICES, pares)

# --------------------------------------------------------------------------------------------
section("Distribución de cada índice", "Caja: mediana y cuartiles; bigotes hasta 1.5 × RIC. Puntos desplazados a la derecha de cada caja.")
distributions(ld, "Tipo", nombres, {LEAF_TYPE_LABELS[t]: LEAF_TYPE_COLORS[t] for t in presentes}, DISPLAY_INDICES,
              flag_col="qc_flag")

# --------------------------------------------------------------------------------------------
section("Más detalle")
t1, t2, t3, t4, t5 = st.tabs(["Comparaciones por pares", "Prueba global", "Datos", "Detalle técnico", "Índices"])
with t1:
    pair_table(tabla)
with t2:
    if len(presentes) >= 2:
        global_test(ld, "Tipo", DISPLAY_INDICES)
with t3:
    cols_hd = ["species", "leaf", "Tipo", "campaign_date", "n_puntos", "n_archivos", "qc_flag", *DISPLAY_INDICES]
    st.markdown("**Hoja-fecha** (unidad de análisis)")
    st.dataframe(ld[cols_hd], width="stretch", hide_index=True, column_config={
        **index_column_config(DISPLAY_INDICES), "campaign_date": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
        "qc_flag": st.column_config.CheckboxColumn("Marcada QC")})
    st.download_button("Descargar hoja-fecha (CSV)", ld[cols_hd].to_csv(index=False).encode("utf-8"),
                       file_name=f"indices_{species.lower()}_hoja_fecha.csv", mime="text/csv", icon=":material/download:")
    st.markdown("**Por punto** (media de repeticiones)")
    pts = point_table(files_sel)
    st.dataframe(pts[["leaf", "campaign_date", "point", "n_archivos", *DISPLAY_INDICES]], width="stretch", hide_index=True,
                 column_config={**index_column_config(DISPLAY_INDICES), "campaign_date": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY")})
    cols_det = ["leaf", "campaign_date", "point", "repetition", "filename", *DISPLAY_INDICES]
    st.download_button("Descargar espectro por espectro (CSV, incluye p4–p6)", files_sel[cols_det].to_csv(index=False).encode("utf-8"),
                       file_name=f"indices_{species.lower()}_detalle.csv", mime="text/csv", icon=":material/download:")
with t4:
    st.caption("Shapiro–Wilk por grupo y ANOVA/Tukey o Kruskal–Wallis/Dunn según normalidad, sobre hoja-fecha y sin "
               "corrección entre índices. Útil para revisar supuestos; la inferencia de la vista es la matriz por pares.")
    technical_detail(ld, "Tipo", nombres, DISPLAY_INDICES)
with t5:
    index_sheet_table(DISPLAY_INDICES)

if read_errors:
    st.caption(f"{len(read_errors)} espectros no se pudieron leer (ver «Datos y calidad»).")
