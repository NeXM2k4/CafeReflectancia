"""Correlación de Spearman entre la reflectancia de cada λ y el tiempo, por hoja y para todas las hojas."""

import numpy as np
import pandas as pd
import streamlit as st

from src import spectral, spectral_page
from src.config import SHADE_BANDS, TEMPORAL_MIN_FECHAS_TENDENCIA
from src.plots_forma import all_leaves_heatmap, correlation_figure
from src.ui import chart, keep_widget_state, note, numeric_column_config, page_header, section

keep_widget_state(keys=("tabs_corr", "corr_heat_view"))

sel, ctx = spectral_page.sidebar()

page_header(
    "Seguimiento de hojas",
    "Correlación con el tiempo",
    "¿En qué longitudes de onda la reflectancia de una hoja sube o baja de forma sostenida a lo largo de "
    "las campañas? Una hoja a la vez, en cruda y en forma normalizada.",
)

REGIONS = {f"{n} ({lo}–{hi})": (lo, hi) for n, lo, hi, _ in SHADE_BANDS}
REGIONS["NIR (760–900)"] = (760, 900)
NORM_NAME = {"area": "área 440–900 nm", "nir": "meseta NIR 750–900 nm"}


@st.cache_data(show_spinner="Calculando ρ de todas las hojas...", max_entries=8)
def _all_leaves(include_sin: bool, excl: bool, norm_method: str):
    """ρ de Spearman por λ de las 18 hojas (cruda y normalizada) y tabla resumen por hoja y región."""
    c = spectral_page.load_context(include_sin, excl)
    rows, rho = [], {"raw": [], "norm": []}
    pf = {"raw": [], "norm": []}
    wl_ref, used = None, []
    for lf in c.leaves.itertuples():
        m = spectral.leaf_matrix(c.spectra, lf.leaf_id, t_cero=c.t_cero)
        if m.n_dates == 0:
            continue
        if wl_ref is None:
            wl_ref = m.wl
        used.append(lf.leaf_id)
        cors = {"raw": spectral.spearman_by_wl(m.R, m.dias, wl=m.wl),
                "norm": spectral.spearman_by_wl(spectral.normalize(m.R, m.wl, norm_method), m.dias, wl=m.wl)}
        for k, cr in cors.items():
            cr = cr.set_index("wavelength").reindex(wl_ref)  # misma grilla en todas las filas del mapa
            rho[k].append(cr["rho"].to_numpy())
            pf[k].append(cr["p_fdr"].to_numpy())
        name = f"{lf.species} {lf.leaf}"
        for rname, (lo, hi) in REGIONS.items():
            row = {"Hoja": name, "Región": rname, "Fechas": m.n_dates}
            for k, lab in (("raw", "Cruda"), ("norm", "Normalizada")):
                cr = cors[k]
                s = cr[cr["wavelength"].between(lo, hi)]
                row[f"{lab}: ρ mediana"] = float(s["rho"].median()) if len(s) else np.nan
                row[f"{lab}: % λ FDR<0,05"] = float((s["p_fdr"] < 0.05).mean() * 100) if s["p_fdr"].notna().any() else np.nan
                row[f"{lab}: % λ p<0,05"] = float((s["p"] < 0.05).mean() * 100) if s["p"].notna().any() else np.nan
            rows.append(row)
    leaves = c.leaves[c.leaves["leaf_id"].isin(used)]
    return {
        "wl": wl_ref,
        "labels": [f"{s} {l}" for s, l in zip(leaves["species"], leaves["leaf"])],
        "species": leaves["species"].tolist(),
        "rho": {k: np.array(v) for k, v in rho.items()},
        "p_fdr": {k: np.array(v) for k, v in pf.items()},
        "summary": pd.DataFrame(rows),
    }


lm = spectral.leaf_matrix(ctx.spectra, sel.leaf_id, t_cero=ctx.t_cero)
if lm.n_dates == 0:
    st.warning("Esta hoja no tiene espectros con los filtros actuales.")
    st.stop()

st.markdown(f"**{sel.species} {sel.leaf}** · {lm.n_dates} fechas "
            f"({spectral_page.date_label(lm.dates[0])} a {spectral_page.date_label(lm.dates[-1])}) · "
            f"normalización: {NORM_NAME[sel.norm_method]}")

with st.expander("Cómo leer"):
    st.markdown(
        "- Para cada λ se correlaciona (Spearman) la reflectancia de la hoja con los días transcurridos: "
        "+1 sube de forma sostenida, −1 baja, 0 sin tendencia. Es una correlación de **rangos**: no exige "
        "que el cambio sea lineal, pero la magnitud del cambio no se ve aquí.\n"
        "- **Cruda**: mezcla cambios de nivel (todo el espectro sube o baja) y de forma. **Normalizada**: "
        "se divide por la media del espectro, así solo queda la forma; un ρ negativo en el NIR al normalizar "
        "es el rebote de que el visible subió.\n"
        "- **Sin corregir vs. FDR.** Hay ~246 λ: con p < 0,05 sin corregir se esperan ~12 falsos positivos "
        "por azar (marcadores **huecos**). El FDR de Benjamini–Hochberg, calculado sobre las λ de esta hoja, "
        "controla esa proporción (marcadores **rellenos**). Lo defendible son los rellenos.\n"
        f"- Con menos de {TEMPORAL_MIN_FECHAS_TENDENCIA} fechas (Canefora M2 y T2 tienen 4) se dibuja ρ pero no p.")


@st.cache_data(show_spinner=False, max_entries=16)
def _leaf_corr(include_sin: bool, excl: bool, leaf_id: str, norm_method: str):
    c = spectral_page.load_context(include_sin, excl)
    m = spectral.leaf_matrix(c.spectra, leaf_id, t_cero=c.t_cero)
    return (spectral.spearman_by_wl(m.R, m.dias, wl=m.wl),
            spectral.spearman_by_wl(spectral.normalize(m.R, m.wl, norm_method), m.dias, wl=m.wl))


section(f"{sel.species} {sel.leaf}", "ρ de Spearman entre la reflectancia en cada λ y el tiempo.")
if lm.n_dates < TEMPORAL_MIN_FECHAS_TENDENCIA:
    note("aviso", f"Esta hoja tiene solo {lm.n_dates} fechas: se muestra ρ, pero no hay p ni marcadores de "
                  f"significancia (mínimo {TEMPORAL_MIN_FECHAS_TENDENCIA}).")
c_raw, c_norm = _leaf_corr(sel.include_sin_hoja, sel.excl_atipicas, sel.leaf_id, sel.norm_method)
chart(correlation_figure(c_raw, c_norm, titles=("Reflectancia (cruda)",
                                                  f"Reflectancia normalizada (forma, {NORM_NAME[sel.norm_method]})")),
      key="corr_fig")

# ------------------------------------------------------------------------------------------------
section("Todas las hojas",
        "Una fila por hoja física, nunca promediadas. Color: ρ. Las celdas atenuadas no son significativas "
        "tras el FDR (o la hoja tiene menos de 5 fechas).")
tab_heat, tab_tab = st.tabs(["Mapa de calor", "Tabla por región"], key="tabs_corr", on_change="rerun")
if tab_heat.open or tab_tab.open:
    allr = _all_leaves(sel.include_sin_hoja, sel.excl_atipicas, sel.norm_method)
if tab_heat.open:
    with tab_heat:
        view = st.segmented_control(
            "Versión", ["Cruda", "Normalizada"], default="Normalizada", key="corr_heat_view",
            help="Normalización elegida en la barra lateral.") or "Normalizada"
        k = "raw" if view == "Cruda" else "norm"
        fig = all_leaves_heatmap(allr["rho"][k], allr["p_fdr"][k], allr["wl"], allr["labels"], groups=allr["species"])
        chart(fig, key=f"corr_heat_{k}")
        st.caption("Orden: variedad, luego tipo de hoja (M, T, R). Pase el cursor por una celda para ver ρ y p FDR.")
if tab_tab.open:
    with tab_tab:
        s = allr["summary"]
        st.markdown("Mediana de ρ y porcentaje de las λ de la región con p < 0,05, **con FDR** y **sin corregir**.")
        st.dataframe(s, hide_index=True, width="stretch", height=560,
                     column_config={**numeric_column_config(s, 2),
                                    **{c: st.column_config.NumberColumn(c, format="%.0f")
                                       for c in s.columns if c.startswith(("Cruda: %", "Normalizada: %"))}})

note("limite",
     "**Límites.** Las p son optimistas: las fechas de una hoja están autocorrelacionadas (una deriva suave "
     "produce ρ alto sin que sea «efecto de la roya») y las λ vecinas no son independientes, de modo que "
     "«% de λ significativas» no cuenta pruebas independientes. Una hoja es una trayectoria, no una "
     "población, y una sola R por variedad describe a esa hoja. Con 4 fechas no hay p.")
