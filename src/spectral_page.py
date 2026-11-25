"""Contexto compartido y barra lateral de las paginas de analisis espectral por hoja.

Las cuatro paginas (derivadas, correlacion con el tiempo, cambio + PCA, rasgos) usan los mismos
archivos, la misma exclusion de espectros y la misma seleccion de hoja, que se conserva al pasar
de una a otra. Ver docs/plan_analisis_espectral.md (secciones 3.1 y 4.2).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from src.config import NDVI_SIN_HOJA
from src.indices import QC_MIN_INDICES, QC_Z_THRESHOLD
from src.parser import get_dataset
from src.temporal import file_indices, leaf_mean_spectra, leaf_timeseries, qc_flags
from src.temporal_plots import SPECIES_ORDER, TYPE_ORDER
from src.ui import keep_widget_state, sidebar_footer

NORM_OPTIONS = {"Área 440–900 nm": "area", "Meseta NIR 750–900 nm": "nir"}
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

_K_SP, _K_LEAF, _K_NORM, _K_SIN, _K_EXCL = "_esp_species", "_esp_leaf", "_esp_norm", "_esp_sin_hoja", "_esp_excl"
_WIDGET_KEYS = ("w_esp_species", "w_esp_leaf", "w_esp_norm", "w_esp_sin_hoja", "w_esp_excl")


@dataclass
class SpectralContext:
    df: pd.DataFrame  # dataset completo (para el pie de la barra lateral)
    files: pd.DataFrame  # archivos M/T/R p1-p3, ya sin los excluidos
    ts: pd.DataFrame  # hoja-fecha (leaf_timeseries) con qc_atipico y qc_n_atipicos
    spectra: pd.DataFrame  # leaf_mean_spectra de `files`
    meta: pd.DataFrame  # ts reducido: claves de hoja, campaign_date, dia, n_puntos, qc_atipico
    t_cero: pd.Timestamp
    species_with_rust: set
    n_sin_hoja: int  # archivos excluidos por NDVI < NDVI_SIN_HOJA (0 si se incluyen)
    leaves: pd.DataFrame  # species, leaf_id, leaf, leaf_type, leaf_num; ordenado por variedad, tipo M,T,R y numero
    n_atipicas_excluidas: int = 0  # hojas-fecha atipicas excluidas (0 si no se excluyen)


@dataclass
class Selection:
    species: str
    leaf: str  # codigo, p. ej. "M1"
    leaf_id: str  # "Bourbon|M1"
    leaf_type: str
    norm_method: str  # "area" | "nir"
    include_sin_hoja: bool
    excl_atipicas: bool


@st.cache_data(show_spinner="Preparando espectros por hoja...")
def load_context(include_sin_hoja: bool = False, excl_atipicas: bool = False) -> SpectralContext:
    df = get_dataset()
    files_all, _ = file_indices(df)
    if files_all.empty:
        empty = pd.DataFrame()
        return SpectralContext(df, files_all, empty, empty, empty, pd.NaT, set(), 0, empty)
    sin_hoja = files_all["NDVI"] < NDVI_SIN_HOJA
    n_sin_hoja = 0 if include_sin_hoja else int(sin_hoja.sum())
    files = files_all if include_sin_hoja else files_all[~sin_hoja]  # a nivel de ARCHIVO, antes de promediar

    ts_qc = qc_flags(leaf_timeseries(files))
    n_atip = 0
    if excl_atipicas:
        flagged = ts_qc[ts_qc["qc_atipico"]]
        n_atip = len(flagged)
        fuera = set(zip(flagged["leaf_id"], flagged["campaign_date"]))
        files = files[[(l, d) not in fuera for l, d in zip(files["leaf_id"], files["campaign_date"])]]
    ts = leaf_timeseries(files).merge(
        ts_qc[["leaf_id", "campaign_date", "qc_n_atipicos", "qc_atipico"]],
        on=["leaf_id", "campaign_date"], how="left",
    )
    ts["qc_atipico"] = ts["qc_atipico"].fillna(False).astype(bool)
    spectra = leaf_mean_spectra(files[["leaf_id", "campaign_date", "point", "path"]])
    leaves = ts[["species", "leaf_id", "leaf", "leaf_type", "leaf_num"]].drop_duplicates("leaf_id").copy()
    leaves["_s"] = leaves["species"].map({s: i for i, s in enumerate(SPECIES_ORDER)}).fillna(99)
    leaves["_t"] = leaves["leaf_type"].map(TYPE_ORDER).fillna(9)
    leaves = leaves.sort_values(["_s", "_t", "leaf_num"]).drop(columns=["_s", "_t"]).reset_index(drop=True)
    meta = ts[["species", "leaf_id", "leaf", "leaf_type", "leaf_num", "campaign_date", "dia", "n_puntos", "qc_atipico"]]
    return SpectralContext(
        df=df, files=files, ts=ts, spectra=spectra, meta=meta, t_cero=ts["campaign_date"].min(),
        species_with_rust=set(files_all.loc[files_all["leaf_type"] == "R", "species"]),
        n_sin_hoja=n_sin_hoja, leaves=leaves, n_atipicas_excluidas=n_atip,
    )


def date_label(date, n=None, atipico: bool = False) -> str:
    """"16-Nov (n=3)", con " ⚠" si la hoja-fecha es atipica."""
    d = pd.Timestamp(date)
    txt = f"{d.day:02d}-{MESES[d.month - 1]}"
    if n is not None:
        txt += f" (n={int(n)})"
    return txt + (" ⚠" if atipico else "")


def date_labels(ctx: SpectralContext, leaf_id: str, dates, n_puntos=None) -> list[str]:
    """Etiquetas de fila/fecha de una hoja; marca con ⚠ las fechas atipicas de `ctx.meta`."""
    m = ctx.meta[ctx.meta["leaf_id"] == leaf_id].set_index("campaign_date")
    atip = m["qc_atipico"].reindex(pd.DatetimeIndex(dates)).fillna(False).to_numpy()
    ns = [None] * len(dates) if n_puntos is None else n_puntos
    return [date_label(d, n, a) for d, n, a in zip(dates, ns, atip)]


def _persist(widget_key: str, state_key: str, mapping: dict | None = None):
    v = st.session_state[widget_key]
    st.session_state[state_key] = mapping[v] if mapping else v


def _species_label(sp: str, with_rust: set) -> str:
    return sp if sp in with_rust else f"{sp} · control sin roya"


def sidebar() -> tuple[Selection, SpectralContext]:
    """Barra lateral comun. Devuelve (seleccion, contexto) y detiene la pagina si no hay datos.

    La seleccion vive en claves de `session_state` que no son de widget (`_esp_*`) y se usa como valor
    inicial de los controles de cada pagina, asi se conserva al cambiar de pagina.
    """
    keep_widget_state(keys=_WIDGET_KEYS)
    ss = st.session_state
    with st.sidebar:
        c_sp, c_leaf, c_norm, c_tog = st.container(), st.container(), st.container(), st.container()

    with c_tog:
        include_sin = st.toggle(
            "Incluir espectros sin firma de hoja", value=ss.get(_K_SIN, False), key="w_esp_sin_hoja",
            on_change=_persist, args=("w_esp_sin_hoja", _K_SIN),
            help=(f"Sin firma de hoja: NDVI < {NDVI_SIN_HOJA} en el archivo (espectro plano, p. ej. una "
                  "referencia blanca guardada con nombre de hoja). Por defecto se excluyen porque destruyen "
                  "cualquier análisis de forma. Se quitan archivo por archivo, antes de promediar."))
        excl = st.toggle(
            "Excluir hojas-fecha atípicas", value=ss.get(_K_EXCL, False), key="w_esp_excl",
            on_change=_persist, args=("w_esp_excl", _K_EXCL),
            help=(f"Atípica: {QC_MIN_INDICES} o más de los 7 índices con |z robusto| > {QC_Z_THRESHOLD} "
                  "respecto de la propia serie de la hoja (misma regla que Evolución temporal). Excluirlas "
                  "recalcula todo. Las fechas atípicas se marcan con ⚠."))

    ctx = load_context(bool(include_sin), bool(excl))
    if ctx.files.empty:
        st.warning("No hay espectros válidos para el análisis espectral.")
        st.stop()

    present = [s for s in SPECIES_ORDER if s in set(ctx.leaves["species"])]
    sp0 = ss.get(_K_SP)
    with c_sp:
        species = st.selectbox(
            "Variedad", present, index=present.index(sp0) if sp0 in present else 0, key="w_esp_species",
            format_func=lambda s: _species_label(s, ctx.species_with_rust),
            on_change=_persist, args=("w_esp_species", _K_SP),
            help="Se analiza una hoja física a la vez; las hojas nunca se promedian entre sí.")
    leaves = ctx.leaves[ctx.leaves["species"] == species]["leaf"].tolist()
    if ss.get("w_esp_leaf") not in leaves:
        ss.pop("w_esp_leaf", None)
    l0 = ss.get(_K_LEAF)
    with c_leaf:
        leaf = st.selectbox(
            "Hoja", leaves, index=leaves.index(l0) if l0 in leaves else 0, key="w_esp_leaf",
            on_change=_persist, args=("w_esp_leaf", _K_LEAF),
            help="M: madura. T: tierna al inicio. R: con roya. Mismas hojas físicas en todas las campañas.")
    n0 = ss.get(_K_NORM, "area")
    with c_norm:
        norm_label = st.selectbox(
            "Normalización", list(NORM_OPTIONS), index=list(NORM_OPTIONS.values()).index(n0), key="w_esp_norm",
            on_change=_persist, args=("w_esp_norm", _K_NORM, NORM_OPTIONS),
            help=("Versión «normalizada» de las figuras. Área: R / media(R, 440–900 nm). Meseta NIR: "
                  "R / media(R, 750–900 nm), la misma de Evolución temporal. Ambas quitan cambios de nivel "
                  "(acople de la sonda, referencia) y dejan la forma. La versión cruda siempre se muestra."))
    if not include_sin and ctx.n_sin_hoja:
        st.sidebar.caption(f"{ctx.n_sin_hoja} espectros sin firma de hoja excluidos.")
    sidebar_footer(ctx.df)

    row = ctx.leaves[(ctx.leaves["species"] == species) & (ctx.leaves["leaf"] == leaf)].iloc[0]
    sel = Selection(species=species, leaf=leaf, leaf_id=row["leaf_id"], leaf_type=row["leaf_type"],
                    norm_method=NORM_OPTIONS[norm_label], include_sin_hoja=bool(include_sin), excl_atipicas=bool(excl))
    return sel, ctx
