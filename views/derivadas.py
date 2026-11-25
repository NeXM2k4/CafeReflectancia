"""Derivadas espectrales de una hoja a lo largo de las campañas (primera y segunda derivada)."""

import pandas as pd
import streamlit as st

from src import spectral, spectral_page
from src.config import SPECTRAL_DERIV_WINDOW, TEMPORAL_MIN_FECHAS_TENDENCIA
from src.plots_forma import derivative_figure
from src.temporal import leaf_trends
from src.ui import chart, keep_widget_state, note, numeric_column_config, page_header, section

keep_widget_state(keys=("tabs_deriv", "deriv_win"))

sel, ctx = spectral_page.sidebar()

page_header(
    "Seguimiento de hojas",
    "Derivadas espectrales",
    "La forma del espectro entre las bandas de los índices: posición y empinamiento del borde rojo y pico verde, "
    "una hoja física a la vez, una curva por campaña.",
)

lm = spectral.leaf_matrix(ctx.spectra, sel.leaf_id, t_cero=ctx.t_cero)
if lm.n_dates == 0:
    st.warning("Esta hoja no tiene espectros con los filtros actuales.")
    st.stop()
labels = spectral_page.date_labels(ctx, sel.leaf_id, lm.dates, lm.n_puntos)
norm_name = "área 440–900 nm" if sel.norm_method == "area" else "meseta NIR 750–900 nm"
st.markdown(f"**{sel.species} {sel.leaf}** · {lm.n_dates} fechas "
            f"({spectral_page.date_label(lm.dates[0])} a {spectral_page.date_label(lm.dates[-1])}) · "
            f"normalización: {norm_name}")

with st.expander("Avanzado: sensibilidad de la ventana de suavizado"):
    opts = [5, 7, 11]
    window = st.selectbox(
        "Ventana de Savitzky–Golay (puntos de la grilla, ≈1,87 nm cada uno)", opts,
        index=opts.index(SPECTRAL_DERIV_WINDOW), key="deriv_win",
        help="Polinomio de grado 3. 7 puntos ≈ 13 nm (por defecto). Más puntos suaviza más el ruido pero "
             "aplana detalles finos; menos puntos deja más ruido, sobre todo en 440–500 nm.")

with st.expander("Cómo leer"):
    st.markdown(
        "- Cada curva es la derivada del espectro medio (p1–p3) de **una campaña**; el color va de morado "
        "(primera) a amarillo (última).\n"
        "- **Cruda**: pendiente de la reflectancia en %/nm; mezcla cambios de nivel y de forma. "
        "**Normalizada**: la reflectancia se divide por su media (ver barra lateral) antes de derivar, "
        "así queda solo la forma.\n"
        "- En el borde rojo (650–780 nm) la altura del máximo es el empinamiento y su posición en λ es el "
        "«REP»; un desplazamiento hacia el azul es la señal clásica de pérdida de clorofila.\n"
        "- **Franja ρ vs. tiempo** (bajo cada panel): correlación de Spearman entre el valor de la derivada "
        "en esa λ y el tiempo. Punto relleno: significativa tras corregir por multiplicidad (FDR de "
        "Benjamini–Hochberg sobre las λ de esta hoja); punto hueco: solo p < 0,05 sin corregir.")


@st.cache_data(show_spinner="Calculando rasgos y tendencias de todas las hojas...")
def _features_trends(include_sin: bool, excl: bool):
    """Rasgos y tendencias de TODAS las hojas, con FDR sobre toda la familia «rasgos» (como la página Rasgos)."""
    c = spectral_page.load_context(include_sin, excl)
    ft = spectral.features_table(c.spectra, c.meta)
    tr = leaf_trends(ft, list(spectral.FEATURE_COLUMNS), "rasgos")
    return ft, tr


@st.cache_data(show_spinner=False, max_entries=16)
def _deriv_inputs(include_sin: bool, excl: bool, leaf_id: str, norm_method: str, order: int, win: int):
    """Derivadas cruda y normalizada de una hoja y su ρ vs tiempo (cacheado por hoja y ventana)."""
    c = spectral_page.load_context(include_sin, excl)
    m = spectral.leaf_matrix(c.spectra, leaf_id, t_cero=c.t_cero)
    d_raw = spectral.derivative(m.R, m.wl, order, window=win)
    d_norm = spectral.derivative(spectral.normalize(m.R, m.wl, norm_method), m.wl, order, window=win)
    return (d_raw, d_norm, spectral.spearman_by_wl(d_raw, m.dias, wl=m.wl),
            spectral.spearman_by_wl(d_norm, m.dias, wl=m.wl))


tab1, tab2 = st.tabs(["Primera derivada", "Segunda derivada"], key="tabs_deriv", on_change="rerun")
for tab, order, name in ((tab1, 1, "Primera derivada"), (tab2, 2, "Segunda derivada")):
    if not tab.open:
        continue
    with tab:
        d_raw, d_norm, c_raw, c_norm = _deriv_inputs(
            sel.include_sin_hoja, sel.excl_atipicas, sel.leaf_id, sel.norm_method, order, window)
        section(f"{name} · {sel.species} {sel.leaf}",
                "Arriba de cada franja, una curva por fecha. Fila superior: reflectancia cruda; fila inferior: normalizada.")
        if lm.n_dates < TEMPORAL_MIN_FECHAS_TENDENCIA:
            note("limite", f"Esta hoja tiene solo {lm.n_dates} fechas: se dibuja ρ pero no se calcula p "
                          f"(mínimo {TEMPORAL_MIN_FECHAS_TENDENCIA}).")
        fig = derivative_figure(lm.dates, lm.wl, d_raw, d_norm, c_raw, c_norm, labels, order=order)
        chart(fig, key=f"deriv_fig_{order}")

# ------------------------------------------------------------------------------------------------
# Rasgos del borde rojo de esta hoja y su tendencia
# ------------------------------------------------------------------------------------------------
section("Rasgos del borde rojo de esta hoja",
        "Calculados sobre el espectro crudo con la ventana por defecto; son los mismos de la página Rasgos espectrales.")
ft, tr = _features_trends(sel.include_sin_hoja, sel.excl_atipicas)
cols = [spectral.F_REP_MAX, spectral.F_REP_LIN, spectral.F_DMAX, spectral.F_DOBLE]
f = ft[ft["leaf_id"] == sel.leaf_id].sort_values("campaign_date")
if f.empty:
    st.info("No hay rasgos para esta hoja con los filtros actuales.")
else:
    tab_f = f[cols].copy()
    tab_f.insert(0, "Fecha", spectral_page.date_labels(ctx, sel.leaf_id, f["campaign_date"], f["n_puntos"].to_numpy()))
    st.dataframe(tab_f, hide_index=True, width="stretch", column_config=numeric_column_config(tab_f, 3))
    t = tr[(tr["leaf_id"] == sel.leaf_id) & tr["Variable"].isin(cols)].set_index("Variable").reindex(cols)
    tt = pd.DataFrame({
        "Rasgo": cols, "Pendiente / semana": t["Pendiente / semana"].to_numpy(), "tau": t["tau"].to_numpy(),
        "p": t["p"].to_numpy(), "p FDR": t["p FDR"].to_numpy(),
        "Significativa": t["Significativa"].map({True: "sí", False: "no"}).to_numpy(),
    })
    st.markdown("**Tendencia en el tiempo** (Theil–Sen y Mann–Kendall; FDR sobre todas las hojas y todos los rasgos)")
    st.dataframe(tt, hide_index=True, width="stretch", column_config=numeric_column_config(tt, 4))
    if "Motivo omision" in t and t["Motivo omision"].notna().any():
        st.caption("Sin tendencia: " + "; ".join(f"{k}: {v}" for k, v in t["Motivo omision"].dropna().items()))
    try:
        st.page_link("views/rasgos.py", label="Ver todos los rasgos y la comparación entre hojas", icon=":material/arrow_forward:")
    except Exception:  # fuera de la navegación (AppTest autónomo) el enlace no se puede resolver
        pass

note("limite",
     "**Límites.** (1) 440–500 nm es muy ruidoso en la derivada (poca señal del detector); se muestra tal cual, "
     "pruebe la ventana en «Avanzado». (2) Las p son optimistas: las fechas de una misma hoja están "
     "autocorrelacionadas y las λ vecinas no son independientes; el FDR corrige la multiplicidad, no eso. "
     "(3) Una hoja es una trayectoria, no una población: no se promedian hojas, y una sola R por variedad "
     "describe a esa hoja, no a la roya en general.")
