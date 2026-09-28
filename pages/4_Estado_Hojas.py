"""Similitud espectral con roya de cada hoja madura, por fecha (antes "Severidad de Roya").

Reescrita en la fase F2 de plan_mejora_app.md. Cambios respecto de la version anterior:
- Unidad **hoja** (una fila por hoja madura fisica), no punto ni archivo. Columnas = fecha.
- Se quita el "resumen por especie" (promediaba 12 semanas y varias hojas en un solo numero) y
  el boxplot por punto: escondian mas de lo que mostraban.
- Las hojas Tierna y Con roya de la misma especie aparecen como referencia (deberian salir cerca
  de 0 % y 100 % respectivamente, por construccion: si no, es señal de un problema de medicion
  ese dia, no de la biologia).
- Mismo numero de similitud que la pagina 5 y que veria Telegram (`severity.leaf_date_similarity`,
  ver X5 de plan_mejora_app.md).
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import (
    INDEX_DEFINITIONS,
    LEAF_TYPE_LABELS,
    rust_risk_class,
)
from src.indices import DISPLAY_INDICES, file_index_table, leaf_date_table
from src.parser import campaign_options, get_dataset, sorted_campaigns
from src.severity import leaf_date_similarity, severity_baselines
from src.ui import filter_tag, inject_base_css, render_header, render_index_legend

SUSCEPTIBLE = ["Bourbon", "Pacamara"]

st.set_page_config(page_title="Estado de las hojas", page_icon="🦠", layout="wide")
inject_base_css()
render_header("Estado de las hojas — similitud espectral con roya, hoja por hoja y fecha")

st.caption(
    "**Similitud con roya** (0-100 %): qué tan parecido es el espectro de una hoja al de la "
    "hoja con roya confirmada de su misma especie, frente a una hoja tierna sana de referencia. "
    "**No es un diagnostico.** Se calcula sobre hojas **Madura**, que son las de estado "
    "sanitario desconocido — es justo lo que esta página trata de estimar."
)

df = get_dataset()
if df.empty:
    st.warning("No hay datos en `data/`. Ve a la página de inicio.")
    st.stop()

with st.sidebar:
    st.markdown("**Filtros**")
    with st.container(border=True):
        campaigns_all = sorted_campaigns(df[df["species"].isin(SUSCEPTIBLE)])
        labels_camp = campaign_options(df)
        filter_tag("Campaña")
        sel_campaigns = st.multiselect(
            "Campaña", campaigns_all, default=campaigns_all, format_func=labels_camp.get,
            label_visibility="collapsed",
        )
        filter_tag("Especie")
        sel_species = st.multiselect("Especie", SUSCEPTIBLE, default=SUSCEPTIBLE, label_visibility="collapsed")

if not sel_campaigns or not sel_species:
    st.info("Selecciona al menos una campaña y una especie.")
    st.stop()

files_all, read_errors = file_index_table(df)
files_sel = files_all[
    files_all["species"].isin(sel_species) & files_all["campaign_id"].isin(sel_campaigns)
]
if read_errors:
    with st.expander(f"⚠️ {len(read_errors)} archivo(s) con error de lectura"):
        for name, err in read_errors:
            st.write(f"- **{name}**: {err}")
if files_sel.empty:
    st.info("No hay datos con los filtros seleccionados.")
    st.stop()

baselines = severity_baselines(df)  # anclas sobre TODO el dataset (mismas que Telegram/pag. 5)
ld = leaf_date_table(files_sel)
sim = leaf_date_similarity(ld, baselines)
sim["Tipo de hoja"] = sim["leaf_type"].map(LEAF_TYPE_LABELS)

n_r_hojas = sim.loc[sim["leaf_type"] == "R", "leaf"].nunique()
if n_r_hojas:
    st.info(
        f"Hay {n_r_hojas} hoja(s) con roya por especie en todo el dataset: la referencia 'con "
        "roya' de abajo describe a esa(s) hoja(s) puntual(es), no una población."
    )

render_index_legend(INDEX_DEFINITIONS)

# ---------- 1. Mapa de calor: similitud de cada hoja madura, por fecha ----------
st.subheader("1. Similitud por hoja y fecha")
for sp in sel_species:
    sp_sim = sim[sim["species"] == sp]
    if sp_sim.empty:
        continue
    st.markdown(f"**{sp}**")
    pivot = sp_sim.pivot_table(index="leaf", columns="campaign_date", values="similitud") * 100
    # Orden de filas: Madura primero (lo que interesa), despues Tierna, despues Con roya.
    orden_tipo = {"M": 0, "T": 1, "R": 2}
    tipo_por_hoja = sp_sim.drop_duplicates("leaf").set_index("leaf")["leaf_type"]
    filas_orden = sorted(pivot.index, key=lambda h: (orden_tipo.get(tipo_por_hoja.get(h, "M"), 9), h))
    pivot = pivot.reindex(filas_orden)
    fechas_fmt = [d.strftime("%d/%m") for d in pivot.columns]

    fig = go.Figure(data=go.Heatmap(
        z=pivot.to_numpy(), x=fechas_fmt, y=pivot.index.tolist(),
        colorscale=[[0, "#199E70"], [0.5, "#C98500"], [1, "#D95926"]],
        zmin=0, zmax=100, colorbar=dict(title="Similitud %"),
        hovertemplate="Hoja %{y} · %{x}<br>Similitud: %{z:.0f} %<extra></extra>",
        text=np.where(np.isnan(pivot.to_numpy()), "", np.round(pivot.to_numpy(), 0).astype(str)),
        texttemplate="%{text}",
    ))
    fig.update_layout(height=120 + 32 * len(pivot.index), margin=dict(t=10, b=10))
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Fila de referencia **T** ≈ 0 % y **R** ≈ 100 % por construccion (son las hojas que "
        "definen las anclas). Si no salen cerca, revisar esa fecha antes de confiar en las "
        "hojas Madura de esa misma columna."
    )

# ---------- 2. Detalle por hoja y fecha ----------
st.subheader("2. Detalle: índices de una hoja en una fecha, contra sus referencias")
c1, c2, c3 = st.columns(3)
with c1:
    especie_det = st.selectbox("Especie", sel_species, key="det_especie")
with c2:
    hojas_det = sorted(sim.loc[sim["species"] == especie_det, "leaf"].unique())
    hoja_det = st.selectbox("Hoja", hojas_det, key="det_hoja")
with c3:
    fechas_det = sorted(sim.loc[(sim["species"] == especie_det) & (sim["leaf"] == hoja_det), "campaign_date"].unique())
    fecha_det = st.selectbox("Fecha", fechas_det, format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"), key="det_fecha")

fila = sim[(sim["species"] == especie_det) & (sim["leaf"] == hoja_det) & (sim["campaign_date"] == fecha_det)]
if fila.empty:
    st.info("No hay datos para esa combinacion.")
else:
    fila = fila.iloc[0]
    _, nombre_clase, emoji_clase, desc_clase = rust_risk_class(fila["similitud"] if pd.notna(fila["similitud"]) else 0)
    st.metric(
        f"{especie_det} {hoja_det} — {pd.Timestamp(fecha_det):%d/%m/%Y}",
        f"{fila['similitud'] * 100:.0f} % — {emoji_clase} {nombre_clase}" if pd.notna(fila["similitud"]) else "sin datos",
        help=desc_clase, border=True,
    )
    idx_baseline = baselines.get(especie_det, {}).get("indices", {})
    ref_rows = []
    for idx_name in DISPLAY_INDICES:
        ref = idx_baseline.get(idx_name, {})
        ref_rows.append({
            "Índice": idx_name,
            f"{hoja_det} ({pd.Timestamp(fecha_det):%d/%m})": fila.get(idx_name),
            "Ref. Tierna (sana)": ref.get("sana"),
            "Ref. Con roya": ref.get("enferma"),
        })
    ref_df = pd.DataFrame(ref_rows).set_index("Índice")
    st.dataframe(
        ref_df, width="stretch",
        column_config={c: st.column_config.NumberColumn(c, format="%.3f") for c in ref_df.columns},
    )
    st.caption(f"n = {fila['n_puntos']} punto(s) medidos esa fecha; similitud calculada con {fila['similitud_n_indices']}/{len(DISPLAY_INDICES)} índices comparables.")

# ---------- 3. Tabla completa + descarga ----------
with st.expander("📄 Tabla completa (todas las hojas, todas las fechas)"):
    cols = ["species", "leaf", "Tipo de hoja", "campaign_date", "n_puntos", "similitud", "similitud_n_indices", *DISPLAY_INDICES]
    tabla = sim[cols].copy()
    tabla["similitud"] = (tabla["similitud"] * 100).round(1)
    tabla = tabla.rename(columns={"similitud": "Similitud (%)", "similitud_n_indices": "n índices"})
    st.dataframe(
        tabla, width="stretch", hide_index=True,
        column_config={"Similitud (%)": st.column_config.ProgressColumn("Similitud (%)", min_value=0, max_value=100, format="%.0f%%")},
    )
    st.download_button(
        "Descargar CSV", tabla.to_csv(index=False).encode("utf-8"),
        file_name="similitud_roya_hoja_fecha.csv", mime="text/csv", icon="⬇️",
    )
