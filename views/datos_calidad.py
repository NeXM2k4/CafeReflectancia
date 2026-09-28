"""Datos y calidad: inventario de espectros y todo lo que se excluye o marca antes de analizar."""

import pandas as pd
import streamlit as st

from src.config import LEAF_TYPE_HELP, LEAF_TYPE_LABELS, SPECIES_PENDING_LABEL
from src.indices import file_index_table, leaf_date_table, quality_flags
from src.parser import campaign_options, get_dataset, raw_dataset, sorted_campaigns
from src.ui import html_table, note, page_header, render_styled_pivot, section, sidebar_footer

page_header(
    "Datos y operación",
    "Datos y calidad",
    "Qué espectros hay, cuáles quedan fuera del análisis y por qué. Nada se borra: todo sigue en "
    "<code>data/</code> y cada exclusión o marca puede revisarse aquí.",
)

with st.sidebar:
    if st.button("Volver a escanear data/", icon=":material/refresh:", width="stretch",
                 help="El escaneo se actualiza solo al agregar o modificar archivos; esto lo fuerza."):
        st.cache_data.clear()
        st.rerun()

df = get_dataset()
if df.empty:
    st.warning("No se encontraron espectros en `data/`.")
    st.stop()
sidebar_footer(df)

raw = raw_dataset()
recognized = df[df["name_recognized"]]
unrecognized = df[~df["name_recognized"]]
files_all, read_errors = file_index_table(df)
ld_all = quality_flags(leaf_date_table(files_all))
etiquetas = campaign_options(df)

# --------------------------------------------------------------------------------------------
section("Inventario", "Número de espectros (archivos) por variedad. Cada espectro es una repetición en un punto de una hoja.")
tab_c, tab_t, tab_s, tab_id = st.tabs(["Por campaña", "Por tipo de hoja", "Susceptibilidad", "Campañas detectadas"])
with tab_c:
    pivot = (
        df.pivot_table(index="species", columns="campaign_id", values="filename", aggfunc="count", fill_value=0)
        .reindex(columns=sorted_campaigns(df), fill_value=0)
    )
    pivot.columns = [etiquetas[c][:5] for c in pivot.columns]
    pivot = pivot.rename(index={SPECIES_PENDING_LABEL: "Hoja vieja sin variedad"})
    pivot["Total"] = pivot.sum(axis=1)
    render_styled_pivot(pivot)
    st.caption(f"Fechas en dd/mm de {pd.to_datetime(df['campaign_date']).dt.year.min()}. «Hoja vieja sin "
               "variedad»: hojas viejas cuya variedad no se registró; quedan fuera del análisis.")
with tab_t:
    tipo = recognized.replace({"species": {SPECIES_PENDING_LABEL: "Hoja vieja sin variedad"}}).pivot_table(index="species", columns="session", values="filename", aggfunc="count", fill_value=0)
    tipo = tipo[[c for c in ["T", "M", "V", "R"] if c in tipo.columns]]
    tipo.columns = [LEAF_TYPE_LABELS[c] for c in tipo.columns]
    render_styled_pivot(tipo)
    st.caption(" · ".join(f"**{LEAF_TYPE_LABELS[c]}**: {LEAF_TYPE_HELP[c]}" for c in ["T", "M", "V", "R"]))
with tab_s:
    susc = raw[raw["susceptibility"].notna()]
    if susc.empty:
        st.caption("Sin datos de susceptibilidad.")
    else:
        render_styled_pivot(susc.pivot_table(index="species", columns="susceptibility", values="filename",
                                             aggfunc="count", fill_value=0))
        st.caption("Propiedad de la planta (variedad), registrada solo en Pacamara. Incluye los espectros "
                   "«No susceptible», que se excluyen del análisis.")
with tab_id:
    camp = df[["campaign_id", "campaign_date"]].drop_duplicates().set_index("campaign_id").loc[sorted_campaigns(df)].reset_index()
    camp["Fecha"] = camp["campaign_id"].map(etiquetas)
    camp["Espectros"] = camp["campaign_id"].map(df["campaign_id"].value_counts())
    html_table(camp[["Fecha", "campaign_id", "Espectros"]].rename(columns={"campaign_id": "Identificador interno"}),
               num_cols=("Espectros",), mono_cols=("Identificador interno",))

# --------------------------------------------------------------------------------------------
section("Exclusiones y marcas", "Se aplican antes de calcular índices, estadística y similitud.")
n_no_susc = int(((raw["species"] == "Pacamara") & (raw["susceptibility"] == "No susceptible")).sum())
n_pend = int((df["species"] == SPECIES_PENDING_LABEL).sum())
n_p4 = int((~files_all["point"].isin([1, 2, 3])).sum())
n_atip = int(ld_all["qc_atipico"].sum())
n_impl = int(ld_all["qc_implausible"].sum())
# Espectro sin firma de hoja: NDVI casi nulo con reflectancia visible alta (p. ej. una referencia
# blanca guardada con nombre de hoja). Solo se marca: la decision de excluirlo es del equipo.
NDVI_SIN_HOJA = 0.05
sin_hoja = files_all[files_all["NDVI"] < NDVI_SIN_HOJA]
filas = [
    ("Excluido", "Pacamara «No susceptible»", n_no_susc, "espectros",
     "Variedad fuera del foco del estudio. No aparece en ninguna vista."),
    ("Excluido", "Hoja vieja sin variedad", n_pend, "espectros",
     "No se registró a qué variedad pertenecen. Se cuentan aparte y nunca se mezclan con las cuatro variedades."),
    ("Excluido", "Nombre de archivo no reconocido", len(unrecognized), "espectros",
     "No siguen el patrón {M|T|R|V}{n}p{punto}{variedad}{repetición}. Listados abajo."),
    ("Excluido", "Puntos p4–p6", n_p4, "espectros",
     "Solo p1–p3 entran en índices, estadística y similitud (criterio acordado con el equipo de campo)."),
    ("Marcado", "Hoja-fecha atípica", n_atip, "hojas-fecha",
     "≥ 4 de 7 índices con |z robusto| > 3.5 frente a la propia serie de la hoja. Se excluye solo de las anclas."),
    ("Marcado", "Espectro sin firma de hoja", len(sin_hoja), "espectros",
     f"NDVI < {NDVI_SIN_HOJA}: espectro plano, sin el borde rojo de una hoja (probable referencia blanca). "
     "Hoy entra en los promedios; revisar y decidir si se excluye."),
    ("Marcado", "mNDVI705 fuera de rango físico", n_impl, "hojas-fecha",
     "mNDVI705 < −0.05 o > 1.05: probable reflexión especular en 445 nm. Se excluye solo de las anclas."),
]
html_table(pd.DataFrame(filas, columns=["Tipo", "Criterio", "Cantidad", "Unidad", "Motivo"]),
           num_cols=("Cantidad",), strong_cols=("Criterio",))
note("metodo", "Las hojas-fecha marcadas siguen visibles en todas las vistas (con su marca); solo dejan de "
               "participar en el cálculo de las anclas de similitud.")

if not sin_hoja.empty:
    note("aviso", f"Hay **{len(sin_hoja)} espectros sin firma de hoja** dentro del análisis. Afectan la media de "
                  + ", ".join(sorted({f"{r.species} {r.leaf} el {pd.Timestamp(r.campaign_date):%d/%m}" for r in sin_hoja.itertuples()}))
                  + ". Conviene confirmar con el equipo de campo si son referencias blancas antes de excluirlos.")
    with st.expander(f"Espectros sin firma de hoja ({len(sin_hoja)})", expanded=False):
        html_table(sin_hoja.assign(
            Fecha=sin_hoja["campaign_date"].map(lambda d: f"{pd.Timestamp(d):%d/%m/%Y}"),
            Punto=sin_hoja["point"].map(lambda p: f"p{int(p)}"),
            NDVI=sin_hoja["NDVI"].map(lambda v: f"{v:.3f}"),
        )[["species", "leaf", "Fecha", "Punto", "filename", "NDVI"]].rename(
            columns={"species": "Variedad", "leaf": "Hoja", "filename": "Archivo"}),
            num_cols=("NDVI",), mono_cols=("Archivo",))

marcadas = ld_all[ld_all["qc_atipico"] | ld_all["qc_implausible"]]
if not marcadas.empty:
    with st.expander(f"Hojas-fecha marcadas ({len(marcadas)})"):
        t = marcadas.assign(
            Fecha=marcadas["campaign_date"].map(lambda d: f"{pd.Timestamp(d):%d/%m/%Y}"),
            Motivo=[("atípica (" + str(int(n)) + " índices)" if a else "") + (" · " if a and i else "") + ("mNDVI705 fuera de rango" if i else "")
                    for n, a, i in zip(marcadas["qc_n_atipicos"], marcadas["qc_atipico"], marcadas["qc_implausible"])],
            mNDVI705=marcadas["mNDVI705"].round(3),
        )[["species", "leaf", "Fecha", "Motivo", "mNDVI705"]].rename(columns={"species": "Variedad", "leaf": "Hoja"})
        html_table(t, num_cols=("mNDVI705",))
if not unrecognized.empty:
    with st.expander(f"Archivos con nombre no reconocido ({len(unrecognized)})"):
        html_table(unrecognized.assign(Archivo=unrecognized["filename"], Carpeta=unrecognized["species"])[["Archivo", "Carpeta"]],
                   mono_cols=("Archivo",))
if read_errors:
    with st.expander(f"Archivos con error de lectura ({len(read_errors)})"):
        html_table(pd.DataFrame(read_errors, columns=["Archivo", "Error"]), mono_cols=("Archivo",))
