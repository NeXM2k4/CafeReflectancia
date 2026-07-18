"""Score de severidad de roya en hojas maduras — Bourbon y Pacamara."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import INDEX_DEFINITIONS, SPECIES_COLORS
from src.parser import get_dataset, load_spectrum
from src.processing import calcular_indices, prepare_spectrum, severity_score
from src.severity import severity_baselines
from src.ui import filter_tag, index_column_config, inject_base_css, render_header, render_index_legend

INDICES = list(INDEX_DEFINITIONS)
SUSCEPTIBLE = ["Bourbon", "Pacamara"]

st.set_page_config(page_title="Severidad de Roya", page_icon="🦠", layout="wide")
inject_base_css()
render_header("Severidad de Roya — hojas maduras")

st.caption(
    "Score de 0 % (espectro igual al de una hoja tierna sana) a 100 % "
    "(igual al de una hoja con roya confirmada), calculado con los 7 indices espectrales. "
    "Solo se muestran **Bourbon** y **Pacamara**: son las especies susceptibles a la roya. "
    "Canefora es inmune a la roya; Cuscatleco es muy resistente."
)

df = get_dataset()
if df.empty:
    st.warning("No hay datos en `data/`. Ve a la pagina de inicio.")
    st.stop()

recognized = df[df["name_recognized"]]
maduras = recognized[
    recognized["species"].isin(SUSCEPTIBLE) & (recognized["leaf_maturity"] == "Madura")
]

if maduras.empty:
    st.info("No hay hojas maduras de Bourbon o Pacamara en los datos actuales.")
    st.stop()

with st.sidebar:
    st.markdown("**Filtros**")
    with st.container(border=True):
        campaigns = sorted(maduras["campaign_id"].dropna().unique())
        filter_tag("Campana")
        sel_campaigns = st.multiselect("Campana", campaigns, default=campaigns, label_visibility="collapsed")
        filter_tag("Especie")
        sel_species = st.multiselect("Especie", SUSCEPTIBLE, default=SUSCEPTIBLE, label_visibility="collapsed")

sub = maduras[
    maduras["campaign_id"].isin(sel_campaigns) & maduras["species"].isin(sel_species)
]
if sub.empty:
    st.info("No hay datos con los filtros seleccionados.")
    st.stop()

baselines = severity_baselines(df)
global_range = baselines.get("__global_range__", {})

rows = []
errors = []
for _, row in sub.iterrows():
    especie_bl = baselines.get(row["species"])
    if especie_bl is None:
        continue
    try:
        raw = load_spectrum(row["path"])
        idx = calcular_indices(prepare_spectrum(raw))
    except ValueError as e:
        errors.append((row["filename"], str(e)))
        continue
    sev = severity_score(idx, especie_bl["indices"])
    if sev is None:
        continue
    rows.append({
        "Especie": row["species"],
        "Campana": row["campaign_id"],
        "Hoja": f"{row['session']}{row['session_num']}",
        "Punto": row["point"],
        "Medida": row["repetition"],
        "Score (%)": round(sev["score"] * 100, 1),
        **idx,
    })

if errors:
    with st.expander(f"⚠️ {len(errors)} archivo(s) con error de lectura", expanded=False):
        for name, err in errors:
            st.write(f"- **{name}**: {err}")

if not rows:
    st.warning("No se pudo calcular scores para ningun archivo con estos filtros.")
    st.stop()

result_df = pd.DataFrame(rows)

# promedio por (hoja, punto) — agrega las 3 medidas repetidas de cada punto
df_pts = (
    result_df
    .groupby(["Especie", "Campana", "Hoja", "Punto"], dropna=False)["Score (%)"]
    .mean()
    .reset_index()
)

# ---------- metricas por especie ----------
st.subheader("Resumen por especie")
cols_m = st.columns(len(sel_species))
for i, sp in enumerate(sel_species):
    sp_scores = result_df.loc[result_df["Especie"] == sp, "Score (%)"]
    if sp_scores.empty:
        cols_m[i].metric(sp, "sin datos", border=True)
        continue
    avg = sp_scores.mean()
    label = "🟢 riesgo bajo" if avg < 33 else ("🟡 riesgo medio" if avg < 66 else "🔴 riesgo alto")
    cols_m[i].metric(sp, f"{avg:.0f} % — {label}", border=True)

# ---------- boxplot por especie y campaña ----------
st.subheader("Distribución de scores por especie y campaña")
st.caption(
    "Cada punto representa el promedio de las 3 medidas repetidas de un punto de medicion "
    "en una hoja. Las lineas punteadas marcan los umbrales de riesgo (33 % y 66 %)."
)

fig = px.box(
    df_pts,
    x="Campana",
    y="Score (%)",
    color="Especie",
    color_discrete_map=SPECIES_COLORS,
    points="all",
    hover_data=["Hoja", "Punto"],
)
fig.add_hline(y=33, line_dash="dot", line_color="rgba(255,200,0,0.55)", annotation_text="33 % — riesgo medio")
fig.add_hline(y=66, line_dash="dot", line_color="rgba(220,60,60,0.55)", annotation_text="66 % — riesgo alto")
fig.update_layout(height=440, margin=dict(t=20, b=20), yaxis=dict(range=[0, 105]))
st.plotly_chart(fig, width="stretch")

# ---------- indices promedio vs. referencias ----------
st.subheader("Indices promedio vs. referencias")
st.caption(
    "Valor promedio de cada indice en las hojas maduras seleccionadas, "
    "frente a la referencia sana (hojas Tiernas) y la referencia enferma (hojas Con roya). "
    "El rango global es el min/max observado en todo el conjunto de referencia."
)

for sp in sel_species:
    sp_df = result_df[result_df["Especie"] == sp]
    if sp_df.empty:
        continue
    avg_indices = sp_df[INDICES].mean()
    idx_baseline = baselines.get(sp, {}).get("indices", {})

    ref_rows = []
    for idx_name in INDICES:
        ref = idx_baseline.get(idx_name, {})
        gr = global_range.get(idx_name, {})
        ref_rows.append({
            "Indice": idx_name,
            "Hoja Madura (prom.)": avg_indices[idx_name],
            "Ref. Sana — Tierna (T)": ref.get("sana"),
            "Ref. Enferma — Con Roya (R)": ref.get("enferma"),
            "Min global": gr.get("min"),
            "Max global": gr.get("max"),
        })

    ref_df = pd.DataFrame(ref_rows).set_index("Indice")
    num_cols = list(ref_df.columns)
    with st.container(border=True):
        st.markdown(f"**{sp}**")
        st.dataframe(
            ref_df,
            width="stretch",
            column_config={c: st.column_config.NumberColumn(c, format="%.3f") for c in num_cols},
        )

# ---------- tabla detallada ----------
with st.container(border=True):
    render_index_legend(INDEX_DEFINITIONS)
    st.subheader("Tabla detallada por medicion")
    st.caption("Una fila por medicion individual. Score calculado con los 7 indices espectrales.")
    detail_cols = ["Especie", "Campana", "Hoja", "Punto", "Medida", "Score (%)", *INDICES]
    df_detail = (
        result_df[detail_cols]
        .sort_values(["Especie", "Campana", "Hoja", "Punto", "Medida"])
        .reset_index(drop=True)
    )
    st.dataframe(
        df_detail,
        width="stretch",
        hide_index=True,
        column_config={
            "Score (%)": st.column_config.ProgressColumn(
                "Score (%)", min_value=0, max_value=100, format="%.0f%%"
            ),
            **index_column_config(INDICES),
        },
    )
    st.download_button(
        "Descargar CSV",
        df_detail.to_csv(index=False).encode("utf-8"),
        file_name="severidad_roya_maduras.csv",
        mime="text/csv",
        icon="⬇️",
    )
