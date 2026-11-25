"""Cambio espectral y PCA: Δ de cada hoja contra su línea base y PCA por hoja (una hoja a la vez)."""

import numpy as np
import pandas as pd
import streamlit as st

from src import spectral, spectral_page
from src.config import DELTA_REGIONS, LEAF_TYPE_COLORS, TEMPORAL_BASELINE_CAMPAIGNS, TEMPORAL_MIN_FECHAS_TENDENCIA
from src.plots_cambio import (
    common_space_trajectories,
    delta_heatmap_pair,
    pca_explained,
    pca_loadings,
    pca_scores,
)
from src.temporal import leaf_trends
from src.ui import chart, keep_widget_state, note, numeric_column_config, page_header, section

keep_widget_state(keys=("w_cp_nbase", "tabs_cp"))

page_header(
    "Seguimiento de hojas",
    "Cambio espectral y PCA",
    "Cuánto y dónde cambia el espectro completo de una hoja respecto de sus primeras campañas, y qué patrones "
    "resume la PCA de esa misma hoja. Se analiza una hoja física a la vez; las hojas nunca se promedian entre sí.",
)

sel, ctx = spectral_page.sidebar()

with st.sidebar:
    n_base = st.selectbox(
        "Campañas de línea base", [1, 2, 3], index=[1, 2, 3].index(TEMPORAL_BASELINE_CAMPAIGNS), key="w_cp_nbase",
        help="Δ(λ, t) = R(λ, t) − media de las primeras n fechas de la propia hoja. Con 2 hay menos ruido que con 1. "
             "Para R1 la línea base son sus primeras fechas (15/07), no las del conjunto de datos.")

lm = spectral.leaf_matrix(ctx.spectra, sel.leaf_id, t_cero=ctx.t_cero)
if lm.n_dates == 0:
    st.info("Esta hoja no tiene espectros válidos.")
    st.stop()

NORM_LABEL = "área 440–900 nm" if sel.norm_method == "area" else "meseta NIR 750–900 nm"
leaf_title = f"{sel.species} · {sel.leaf}"
labels = spectral_page.date_labels(ctx, sel.leaf_id, lm.dates, lm.n_puntos)
R_norm = spectral.normalize(lm.R, lm.wl, sel.norm_method)


@st.cache_data(show_spinner="Calculando tendencias de Δ por región...")
def _delta_trends(include_sin: bool, excl: bool, norm_method: str, n_base: int) -> pd.DataFrame:
    c = spectral_page.load_context(include_sin, excl)
    out = []
    for nm, fam in (("none", "Δ región cruda"), (norm_method, "Δ región normalizada")):
        tbl = spectral.region_delta_table(c.spectra, c.meta, nm, n_base)
        out.append(leaf_trends(tbl, list(DELTA_REGIONS), fam))
    return pd.concat(out, ignore_index=True)


@st.cache_data(show_spinner="Calculando PCA por hoja...")
def _pca_trends(include_sin: bool, excl: bool, norm_method: str) -> pd.DataFrame:
    c = spectral_page.load_context(include_sin, excl)
    out = []
    for nm, fam in (("none", "PCA por hoja cruda"), (norm_method, "PCA por hoja normalizada")):
        partes = []
        for r in c.leaves.itertuples():
            m = spectral.leaf_matrix(c.spectra, r.leaf_id, t_cero=c.t_cero)
            if m.n_dates < 2:
                continue
            res = spectral.pca(spectral.normalize(m.R, m.wl, nm), 3, dias=m.dias)
            d = pd.DataFrame({"species": r.species, "leaf_id": r.leaf_id, "leaf": r.leaf, "leaf_type": r.leaf_type,
                              "campaign_date": m.dates, "dia": m.dias.astype(int)})
            for j in range(3):
                d[f"PC{j + 1}"] = res["scores"][:, j]
            partes.append(d)
        if partes:
            out.append(leaf_trends(pd.concat(partes, ignore_index=True), ["PC1", "PC2", "PC3"], fam))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


@st.cache_data(show_spinner="Calculando el espacio común...")
def _common_space(include_sin: bool, excl: bool, norm_method: str):
    c = spectral_page.load_context(include_sin, excl)
    mats = []
    for r in c.leaves.itertuples():
        m = spectral.leaf_matrix(c.spectra, r.leaf_id, t_cero=c.t_cero)
        if m.n_dates:
            mats.append((r, m))
    n_wl = max(m.R.shape[1] for _, m in mats)
    mats = [(r, m) for r, m in mats if m.R.shape[1] == n_wl]
    X = np.vstack([spectral.normalize(m.R, m.wl, norm_method) for _, m in mats])
    ok = np.isfinite(X).all(axis=1)
    res = spectral.pca(X[ok], 2)
    sc = np.full((len(X), 2), np.nan)
    sc[ok] = res["scores"]
    rows = pd.concat([
        pd.DataFrame({"leaf_id": r.leaf_id, "species": r.species, "leaf": r.leaf, "leaf_type": r.leaf_type,
                      "campaign_date": m.dates}) for r, m in mats], ignore_index=True)
    rows["PC1"], rows["PC2"] = sc[:, 0], sc[:, 1]
    return rows.dropna(subset=["PC1"]), res["explained"]


def _trend_table(trends: pd.DataFrame, leaf_id: str, unidad_help: str):
    t = trends[trends["leaf_id"] == leaf_id]
    if t.empty:
        st.caption("Sin tendencias para esta hoja.")
        return
    cols = ["Familia", "Variable", "n fechas", "Pendiente / semana", "IC95 inf", "IC95 sup", "tau", "p", "p FDR",
            "Significativa", "Motivo omision"]
    t = t[[c for c in cols if c in t]]
    st.dataframe(t, hide_index=True, width="stretch",
                 column_config={**numeric_column_config(t, 5, exclude=("tau", "p", "p FDR")),
                                **{c: st.column_config.NumberColumn(c, format="%.4f") for c in ("tau", "p", "p FDR") if c in t}})
    st.caption(unidad_help)
    if lm.n_dates < TEMPORAL_MIN_FECHAS_TENDENCIA:
        st.caption(f"Esta hoja tiene {lm.n_dates} fechas: con menos de {TEMPORAL_MIN_FECHAS_TENDENCIA} no se calcula "
                   "tendencia (figuras sí, estadística no).")


tab_d, tab_p = st.tabs(["Δ vs línea base", "PCA por hoja"], key="tabs_cp", on_change="rerun")

with tab_d:
    if tab_d.open:
        section(f"Δ de reflectancia de {leaf_title}",
                f"Cada fila es una fecha; el color es la diferencia con la media de las primeras {n_base} fechas de la "
                "propia hoja (filas marcadas «base»).")
        Z_raw = spectral.delta_vs_baseline(lm.R, n_base)
        Z_nrm = spectral.delta_vs_baseline(R_norm, n_base)
        chart(delta_heatmap_pair(lm.wl, labels, Z_raw, Z_nrm, base_n=n_base,
                                 titles=(f"Δ reflectancia cruda (pp) · {leaf_title}",
                                         f"Δ normalizada ({NORM_LABEL}) · {leaf_title}")),
              key="cp_heat")
        note("leer", "Rojo: la hoja refleja más que en su línea base; azul: menos. Cada panel tiene su propia escala "
                     "simétrica alrededor de 0. En la cruda, una franja de un solo color a lo ancho de todo el espectro "
                     "es un cambio de **nivel** (acople de la sonda, luz); en la normalizada solo queda lo que cambia "
                     "de **forma**. Las líneas punteadas marcan los bordes de las regiones. «n» = puntos p1–p3 promediados.")

        section("Tendencia del Δ por región",
                "Δ medio de cada región por fecha contra el tiempo (Theil–Sen + Mann–Kendall, FDR de Benjamini–Hochberg "
                "sobre todas las hojas × regiones de cada familia).")
        trends = _delta_trends(sel.include_sin_hoja, sel.excl_atipicas, sel.norm_method, n_base)
        _trend_table(trends, sel.leaf_id,
                     "Pendiente en pp de reflectancia por semana (cruda) o en fracción del nivel por semana "
                     "(normalizada). La tendencia se calcula sobre toda la serie, **incluidas** las fechas de línea base "
                     "(donde Δ ≈ 0 por construcción). El p-valor es optimista: las fechas sucesivas son autocorrelacionadas.")

        section("Ruido de referencia",
                "Qué tanto varía la hoja por dentro: desviación estándar entre los puntos p1–p3 en las fechas de línea base.")
        noise = spectral.baseline_noise(lm, n_base)
        dmax = spectral.region_means(Z_raw, lm.wl, DELTA_REGIONS).abs().max()
        nt = pd.DataFrame({"Región": list(DELTA_REGIONS), "SD entre puntos (pp)": noise.to_numpy(),
                           "Máx |Δ| observado (pp)": dmax.to_numpy()})
        nt["Cociente"] = nt["Máx |Δ| observado (pp)"] / nt["SD entre puntos (pp)"].replace(0, np.nan)
        st.dataframe(nt, hide_index=True, width="stretch",
                     column_config={c: st.column_config.NumberColumn(c, format="%.3f") for c in nt.columns[1:]})
        st.caption("Un Δ solo es interpretable si supera claramente el ruido de la hoja (cociente ≫ 1). Con un solo "
                   "punto en la línea base la SD no existe (vacío).")
        note("limite", "Una sola hoja R por variedad, ya infectada el 15/07: su Δ describe a esa hoja, no a «la roya». "
                       "Canefora M2 y T2 tienen 4 fechas: se dibujan pero no se les calcula tendencia.")

with tab_p:
    if tab_p.open:
        section(f"PCA de {leaf_title}",
                "Matriz fechas × λ de esta hoja, centrada por longitud de onda y sin escalar. Cada componente se orienta "
                "para que su puntaje suba con el tiempo (ρ de Spearman ≥ 0).")
        if lm.n_dates < 3:
            st.info("Se necesitan al menos 3 fechas para la PCA de una hoja.")
        else:
            pr = spectral.pca(lm.R, 3, dias=lm.dias)
            pn = spectral.pca(R_norm, 3, dias=lm.dias)
            st.markdown("**Varianza explicada**")
            chart(pca_explained(pr["explained"], pn["explained"]), key="cp_expl")
            st.markdown("**Cargas contra la longitud de onda**")
            chart(pca_loadings(lm.wl, pr["loadings"], pn["loadings"], pr["explained"], pn["explained"]), key="cp_load")
            st.markdown("**Puntajes contra la fecha**")
            chart(pca_scores(lm.dates, pr["scores"], pn["scores"]), key="cp_scores")
            note("leer", f"Izquierda: espectro crudo; derecha: normalizado ({NORM_LABEL}). Con {lm.n_dates} fechas hay a lo "
                         f"sumo {lm.n_dates - 1} componentes con varianza. Una carga positiva en una región significa que "
                         "esa región sube cuando el puntaje sube, es decir, hacia las fechas más recientes.")

        section("Tendencia de los puntajes",
                "PC1–PC3 contra el tiempo, calculado para todas las hojas (FDR sobre todas las hojas × componentes de "
                "cada familia) y filtrado a la hoja elegida.")
        pt = _pca_trends(sel.include_sin_hoja, sel.excl_atipicas, sel.norm_method)
        if pt.empty:
            st.caption("Sin datos para calcular tendencias.")
        else:
            _trend_table(pt, sel.leaf_id,
                         "Pendiente en unidades del puntaje por semana. Como cada PCA se ajusta a una sola hoja, "
                         "**PC1 de hojas distintas no es el mismo eje**: sus puntajes y pendientes no se comparan entre hojas.")
        note("limite", "PCA con pocas fechas (7–20) y muchas longitudes de onda: la varianza explicada de PC1 suele ser alta "
                       "casi por construcción. Los p-valores son optimistas por la autocorrelación entre fechas.")

        with st.expander("Espacio común: todas las hojas en una misma PCA"):
            st.caption(f"PCA ajustada sobre todas las hojas-fecha de todas las hojas (normalizadas por {NORM_LABEL}); cada "
                       "hoja se dibuja como su propia trayectoria PC1–PC2 (no se promedian hojas). Sirve para ver si las hojas M "
                       "de las variedades susceptibles se mueven hacia R1. La hoja elegida va en grueso, con las fechas en color.")
            traj, expl = _common_space(sel.include_sin_hoja, sel.excl_atipicas, sel.norm_method)
            if traj.empty:
                st.info("No hay datos suficientes para el espacio común.")
            else:
                sub = st.radio("Hojas mostradas", ["Todas las variedades", f"Solo {sel.species}"], horizontal=True,
                               key="cp_common_scope")
                if sub != "Todas las variedades":
                    traj = traj[(traj["species"] == sel.species) | (traj["leaf_id"] == sel.leaf_id)]
                chart(common_space_trajectories(traj, sel.leaf_id, expl, labels_sel=labels), key="cp_common")
                st.caption("Colores por tipo: " + ", ".join(
                    f"{k} = {c}" for k, c in LEAF_TYPE_COLORS.items() if k in {"M", "T", "R"}) +
                    ". Las flechas marcan el último desplazamiento de cada hoja.")
