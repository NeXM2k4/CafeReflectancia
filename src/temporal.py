"""Evolucion temporal por hoja fisica: series de indices, severidad relativa, tendencias y espectros.

Cada hoja (M1, M2, T1, T2, R1 de una especie) es la misma hoja fisica en todas las campañas.
Los puntos de medicion no son ubicaciones fijas, asi que la unidad temporal es la hoja: primero
se promedian las repeticiones de cada punto y despues los puntos. Detalle y justificacion de
cada decision en evoluciontemporal.md.
"""

from __future__ import annotations

import hashlib
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from scipy.stats import kendalltau, theilslopes
from statsmodels.stats.multitest import multipletests

from src.config import (
    ALPHA_SIGNIFICANCE,
    INDEX_DEFINITIONS,
    SPECIES_PENDING_LABEL,
    TEMPORAL_BASELINE_CAMPAIGNS,
    TEMPORAL_GRID_POINTS,
    TEMPORAL_LEAF_TYPES,
    TEMPORAL_MIN_FECHAS_TENDENCIA,
    TEMPORAL_VALID_POINTS,
    TEMPORAL_WL_MIN,
    X_MAX,
)
from src.indices import (
    DISPLAY_INDICES,
    QC_MIN_FECHAS,
    QC_MIN_INDICES,
    QC_Z_THRESHOLD,
    file_index_table,
    quality_flags,
)
from src.parser import load_spectrum
from src.processing import prepare_spectrum

INDICES = list(INDEX_DEFINITIONS)
# FSR usa las mismas bandas que NDVI: en una distancia, un test multiple o el control de
# calidad contaria doble. Alias historico de src.indices.DISPLAY_INDICES.
DIST_INDICES = DISPLAY_INDICES

QC_Z_UMBRAL = QC_Z_THRESHOLD  # alias historico (ver src.indices para la regla completa)

LEAF_KEYS = ["species", "leaf_id", "leaf", "leaf_type", "leaf_num"]
DELTA = "Δ "
DELTA_STAR = "Δ* "


def leaf_id(species: str, leaf: str) -> str:
    return f"{species}|{leaf}"


def temporal_selection(dataset: pd.DataFrame) -> pd.DataFrame:
    """Archivos que entran al analisis temporal y archivos excluidos (columna `motivo_exclusion`)."""
    df = dataset.copy()
    motivo = pd.Series(None, index=df.index, dtype=object)
    motivo[~df["name_recognized"]] = "nombre no reconocido"
    motivo[motivo.isna() & (df["species"] == SPECIES_PENDING_LABEL)] = "especie pendiente"
    motivo[motivo.isna() & ~df["session"].isin(TEMPORAL_LEAF_TYPES)] = "tipo de hoja sin serie (V)"
    motivo[motivo.isna() & ~df["point"].isin(TEMPORAL_VALID_POINTS)] = "punto fuera de p1-p3"
    df["motivo_exclusion"] = motivo
    return df


def file_indices(dataset: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, str]]]:
    """Indices espectrales por archivo valido para el analisis temporal (M/T/R, p1-p3).

    Envoltorio de compatibilidad: el calculo real vive en `src.indices.file_index_table()`
    desde 2026-09-28 (ver `plan_mejora_app.md`, fase F1), que es la unica funcion de la app que
    recorre los espectros y llama a `calcular_indices()`. Esta funcion solo filtra y ordena las
    columnas al formato que ya esperaba el resto de este modulo.
    """
    all_files, errores = file_index_table(dataset)
    sel = all_files[
        all_files["leaf_type"].isin(TEMPORAL_LEAF_TYPES) & all_files["point"].isin(TEMPORAL_VALID_POINTS)
    ].copy()
    cols = [*LEAF_KEYS, "campaign_id", "campaign_date", "point", "repetition", "filename", "path", *INDICES]
    return sel[cols].reset_index(drop=True), errores


def point_table(files: pd.DataFrame) -> pd.DataFrame:
    """Media de las repeticiones de cada punto (las repeticiones son replicas tecnicas)."""
    claves = [*LEAF_KEYS, "campaign_id", "campaign_date", "point"]
    agg = files.groupby(claves, dropna=False)
    tabla = agg[INDICES].mean()
    tabla["n_archivos"] = agg.size()
    return tabla.reset_index()


def leaf_timeseries(files: pd.DataFrame) -> pd.DataFrame:
    """Una fila por hoja y fecha: media y SD entre puntos de cada indice, n de puntos y archivos.

    La SD se calcula entre puntos y no entre repeticiones: las repeticiones solo reflejan el
    acople de la sonda y subestimarian la heterogeneidad real de la hoja.
    """
    puntos = point_table(files)
    claves = [*LEAF_KEYS, "campaign_id", "campaign_date"]
    agg = puntos.groupby(claves, dropna=False)
    medias = agg[INDICES].mean()
    sds = agg[INDICES].std(ddof=1).add_prefix("sd ")
    ts = pd.concat([medias, sds], axis=1)
    ts["n_puntos"] = agg.size()
    ts["n_archivos"] = agg["n_archivos"].sum()
    ts = ts.reset_index().sort_values(["species", "leaf", "campaign_date"]).reset_index(drop=True)

    t_cero = ts["campaign_date"].min()
    ts["dia"] = (ts["campaign_date"] - t_cero).dt.days
    primera_roya = ts[ts["leaf_type"] == "R"].groupby("species")["campaign_date"].min()
    inicio_r = ts["species"].map(primera_roya)
    ts["dia_roya"] = np.where(ts["leaf_type"] == "R", (ts["campaign_date"] - inicio_r).dt.days, np.nan)
    return ts


def add_deltas(ts: pd.DataFrame) -> pd.DataFrame:
    """Δ = cambio desde la primera fecha de la hoja; Δ* = Δ menos la mediana de Δ de las hojas T.

    Δ* resta lo que les paso a las hojas sanas de la misma especie en la misma fecha (luz,
    calibracion, estacion). Como las hojas T tambien envejecen, tambien resta el envejecimiento
    normal: es una correccion conservadora a proposito.
    """
    ts = ts.sort_values(["leaf_id", "campaign_date"]).copy()
    base = ts.groupby("leaf_id")[INDICES].transform("first")
    for idx in INDICES:
        ts[DELTA + idx] = ts[idx] - base[idx]

    deriva = (
        ts[ts["leaf_type"] == "T"]
        .groupby(["species", "campaign_date"])[[DELTA + i for i in INDICES]]
        .median()
    )
    deriva_filas = deriva.reindex(pd.MultiIndex.from_frame(ts[["species", "campaign_date"]]))
    for idx in INDICES:
        ts[DELTA_STAR + idx] = ts[DELTA + idx].to_numpy() - deriva_filas[DELTA + idx].to_numpy()
    return ts.sort_values(["species", "leaf", "campaign_date"]).reset_index(drop=True)


def with_gaps(ts: pd.DataFrame, t_cero: pd.Timestamp) -> pd.DataFrame:
    """Agrega filas vacias donde la especie tuvo campaña pero la hoja no se midio.

    Solo dentro del rango [primera, ultima] medicion de la hoja, para que la linea se corte en
    el hueco (p. ej. R1 el 21/07) en vez de unir los puntos vecinos como si hubiera un dato.
    `t_cero` es el dia 0 del dataset completo, no el de la tabla recibida.
    """
    fechas_especie = ts.groupby("species")["campaign_date"].unique()
    partes = []
    for lid, g in ts.groupby("leaf_id", sort=False):
        especie = g["species"].iloc[0]
        fechas = [f for f in fechas_especie[especie]
                  if g["campaign_date"].min() <= f <= g["campaign_date"].max()]
        faltan = sorted(set(fechas) - set(g["campaign_date"]))
        g = g.assign(hueco=False)
        if faltan:
            vacias = pd.DataFrame({"campaign_date": faltan})
            for col in LEAF_KEYS:
                vacias[col] = g[col].iloc[0]
            vacias["dia"] = (vacias["campaign_date"] - t_cero).dt.days
            vacias["hueco"] = True
            g = pd.concat([g, vacias], ignore_index=True)
        partes.append(g.sort_values("campaign_date"))
    return pd.concat(partes, ignore_index=True)


def qc_flags(ts: pd.DataFrame) -> pd.DataFrame:
    """Envoltorio de compatibilidad sobre `src.indices.quality_flags()` (unico lugar donde vive
    la regla desde 2026-09-28, ver `plan_mejora_app.md` F1.6). Agrega tambien `qc_implausible`
    (valores fisicamente imposibles, ej. mNDVI705 fuera de rango), ademas de `qc_atipico`."""
    return quality_flags(ts)


def _leaf_date_values(ts: pd.DataFrame, leaf_type: str) -> pd.DataFrame:
    return ts[ts["leaf_type"] == leaf_type][["species", "campaign_date", *INDICES]]


def severity_anchors(ts: pd.DataFrame) -> dict:
    """Anclas de la severidad temporal, ponderando cada fecha por igual (no cada archivo).

    - sana: media de las hojas T en las primeras TEMPORAL_BASELINE_CAMPAIGNS fechas de la
      especie, cuando todavia eran tiernas.
    - enferma S1: media de los valores hoja-fecha de las hojas R de la especie (o de todas las
      especies con roya si la especie no tiene hoja R propia).
    - enferma S2 (leave-one-campaign-out): para cada fecha, la misma media sin esa fecha.
    """
    t = _leaf_date_values(ts, "T")
    primeras = (
        t[["species", "campaign_date"]].drop_duplicates()
        .sort_values("campaign_date")
        .groupby("species").head(TEMPORAL_BASELINE_CAMPAIGNS)
    )
    sana = t.merge(primeras, on=["species", "campaign_date"]).groupby("species")[INDICES].mean()

    r = _leaf_date_values(ts, "R")
    enferma = r.groupby("species")[INDICES].mean()
    enferma_global = r[INDICES].mean()

    fechas = sorted(ts["campaign_date"].unique())
    loco = {}
    for species in sana.index:
        propia = species in enferma.index
        pool = r[r["species"] == species] if propia else r
        for fecha in fechas:
            resto = pool[pool["campaign_date"] != fecha]
            loco[(species, fecha)] = resto[INDICES].mean()

    return {
        "sana": sana,
        "enferma": pd.DataFrame(
            {sp: (enferma.loc[sp] if sp in enferma.index else enferma_global) for sp in sana.index}
        ).T,
        "referencia_propia": {sp: sp in enferma.index for sp in sana.index},
        "enferma_loco": pd.DataFrame(loco).T,
        "fechas_ancla_sana": primeras.groupby("species")["campaign_date"].apply(list).to_dict(),
    }


def _scores(values: pd.DataFrame, sana: pd.DataFrame, enferma: pd.DataFrame, clip: bool) -> np.ndarray:
    """Mediana entre indices de la posicion de cada valor entre ancla sana (0) y enferma (1)."""
    v, s, e = values.to_numpy(float), sana.to_numpy(float), enferma.to_numpy(float)
    den = e - s
    with np.errstate(divide="ignore", invalid="ignore"):
        norm = np.where(den != 0, (v - s) / den, np.nan)
    if clip:
        norm = np.clip(norm, 0.0, 1.0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # filas sin ningun indice valido -> NaN
        return np.nanmedian(norm, axis=1)


def severity_timeseries(files: pd.DataFrame, anchors: dict, clip: bool = True) -> pd.DataFrame:
    """Severidad por hoja y fecha con anclas S1 (congeladas) y S2 (leave-one-campaign-out).

    Igual que la pagina 4: score por archivo (mediana de los 8 indices normalizados), despues
    media de repeticiones por punto y media de puntos por hoja.
    """
    f = files[files["species"].isin(anchors["sana"].index)].copy()
    vals = f[INDICES]
    sana = anchors["sana"].reindex(f["species"])[INDICES]
    enf = anchors["enferma"].reindex(f["species"])[INDICES]
    loco_key = pd.MultiIndex.from_arrays([f["species"], f["campaign_date"]])
    enf_loco = anchors["enferma_loco"].reindex(loco_key)[INDICES]

    f["sev_S1"] = _scores(vals, sana, enf, clip)
    f["sev_S2"] = _scores(vals, sana, enf_loco, clip)

    claves = [*LEAF_KEYS, "campaign_id", "campaign_date"]
    por_punto = f.groupby([*claves, "point"])[["sev_S1", "sev_S2"]].mean()
    return por_punto.groupby(claves)[["sev_S1", "sev_S2"]].mean().reset_index()


def _lag1(res: np.ndarray) -> float:
    if len(res) < 4 or np.std(res[:-1]) == 0 or np.std(res[1:]) == 0:
        return np.nan
    return float(np.corrcoef(res[:-1], res[1:])[0, 1])


def leaf_trends(ts: pd.DataFrame, columnas: list[str], familia: str) -> pd.DataFrame:
    """Pendiente de Theil-Sen (por semana) + Mann-Kendall por hoja y variable, con FDR de BH.

    La correccion se aplica sobre toda la familia recibida (todas las especies y hojas), no
    sobre lo filtrado en pantalla, para que el p corregido no cambie al mover un filtro.
    """
    filas = []
    for (species, lid, leaf, leaf_type), g in ts.groupby(["species", "leaf_id", "leaf", "leaf_type"]):
        g = g.sort_values("campaign_date")
        for col in columnas:
            ok = g[col].notna()
            x = g.loc[ok, "dia"].to_numpy(float) / 7.0
            y = g.loc[ok, col].to_numpy(float)
            base = {"Especie": species, "Hoja": leaf, "Tipo": leaf_type, "leaf_id": lid,
                    "Variable": col, "Familia": familia, "n fechas": int(ok.sum())}
            if len(y) < TEMPORAL_MIN_FECHAS_TENDENCIA:
                filas.append({**base, "Motivo omision": f"menos de {TEMPORAL_MIN_FECHAS_TENDENCIA} fechas"})
                continue
            if np.allclose(y, y[0]):
                filas.append({**base, "Motivo omision": "serie constante"})
                continue
            pend, inter, lo, hi = theilslopes(y, x, 0.95)
            tau, p = kendalltau(x, y)
            filas.append({
                **base,
                "Pendiente / semana": pend, "IC95 inf": lo, "IC95 sup": hi,
                "tau": tau, "p": p,
                "r1 residuos": _lag1(y - (inter + pend * x)),
            })

    out = pd.DataFrame(filas)
    if out.empty:
        return out
    evaluables = out["p"].notna() if "p" in out else pd.Series(False, index=out.index)
    out["p FDR"] = np.nan
    if evaluables.any():
        out.loc[evaluables, "p FDR"] = multipletests(out.loc[evaluables, "p"], method="fdr_bh")[1]
    out["Significativa"] = out["p FDR"] < ALPHA_SIGNIFICANCE
    return out


def distance_to_rust(files: pd.DataFrame, ts: pd.DataFrame) -> pd.DataFrame:
    """Distancia RMS en z-scores entre cada hoja M/T y la hoja R1 de su especie, fecha a fecha.

    El z-score usa media y SD de los valores por punto de las hojas T en las primeras
    TEMPORAL_BASELINE_CAMPAIGNS fechas (12 valores en Bourbon/Pacamara). Se excluye FSR.
    Mas baja = el espectro de la hoja se parece mas al de la hoja con roya ese dia.
    """
    puntos = point_table(files)
    filas = []
    for species, g in ts.groupby("species"):
        r = g[g["leaf_type"] == "R"]
        if r.empty:
            continue
        pt = puntos[(puntos["species"] == species) & (puntos["leaf_type"] == "T")]
        primeras = sorted(pt["campaign_date"].unique())[:TEMPORAL_BASELINE_CAMPAIGNS]
        ref = pt[pt["campaign_date"].isin(primeras)][DIST_INDICES]
        mu, sd = ref.mean(), ref.std(ddof=1).replace(0, np.nan)

        z_r = ((r.set_index("campaign_date")[DIST_INDICES] - mu) / sd)
        for _, fila in g[g["leaf_type"] != "R"].iterrows():
            fecha = fila["campaign_date"]
            if fecha not in z_r.index:
                continue
            z = (fila[DIST_INDICES].astype(float) - mu) / sd
            dif = (z - z_r.loc[fecha]).to_numpy(float)
            dif = dif[~np.isnan(dif)]
            if dif.size == 0:
                continue
            filas.append({
                **{k: fila[k] for k in LEAF_KEYS}, "campaign_date": fecha, "dia": fila["dia"],
                "distancia": float(np.sqrt(np.mean(dif ** 2))), "n_indices": int(dif.size),
            })
    return pd.DataFrame(filas)


_SPECTRA_CACHE_DIR = Path(__file__).resolve().parent.parent / ".state" / "spectra_cache"


def _spectra_signature(files: pd.DataFrame, wl_min: float, wl_max: float, n_points: int) -> str:
    """Huella de los archivos (ruta + mtime) y de los parametros: cambia si se toca data/."""
    h = hashlib.sha1(f"{wl_min}|{wl_max}|{n_points}".encode())
    for row in sorted(zip(files["leaf_id"], files["campaign_date"].astype(str), files["point"], files["path"])):
        try:
            mtime = os.stat(row[3]).st_mtime_ns
        except OSError:
            mtime = 0
        h.update(f"{row}|{mtime}".encode("utf-8", "surrogateescape"))
    return h.hexdigest()


def _load_spectra_cache(firma: str) -> pd.DataFrame | None:
    """Cache en disco de los espectros medios: leerlos otra vez tarda ~9 s con el dataset actual."""
    archivo = _SPECTRA_CACHE_DIR / f"{firma}.pkl"
    if not archivo.exists():
        return None
    try:
        return pd.read_pickle(archivo)
    except Exception:  # noqa: BLE001 (cache corrupto: se recalcula)
        return None


def _save_spectra_cache(firma: str, df: pd.DataFrame) -> None:
    try:
        _SPECTRA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        existentes = sorted(_SPECTRA_CACHE_DIR.glob("*.pkl"), key=lambda p: p.stat().st_mtime)
        for viejo in existentes[:-11]:  # conserva solo las ultimas huellas
            viejo.unlink(missing_ok=True)
        df.to_pickle(_SPECTRA_CACHE_DIR / f"{firma}.pkl")
    except OSError:
        pass  # es una optimizacion, no algo critico


@st.cache_data(show_spinner="Calculando espectros medios por hoja y fecha...")
def leaf_mean_spectra(files: pd.DataFrame, wl_min: float = TEMPORAL_WL_MIN, wl_max: float = X_MAX,
                      n_points: int = TEMPORAL_GRID_POINTS) -> pd.DataFrame:
    """Espectro medio por hoja y fecha sobre una grilla comun a todas las fechas.

    La grilla es la misma en todos los frames de la animacion: si cambiara entre fechas, parte
    del cambio visible seria artefacto de la interpolacion. Mismos dos pasos que los indices.
    """
    firma = _spectra_signature(files, wl_min, wl_max, n_points)
    guardado = _load_spectra_cache(firma)
    if guardado is not None:
        return guardado
    resultado = _leaf_mean_spectra_compute(files, wl_min, wl_max, n_points)
    _save_spectra_cache(firma, resultado)
    return resultado


def _leaf_mean_spectra_compute(files: pd.DataFrame, wl_min: float, wl_max: float,
                               n_points: int) -> pd.DataFrame:
    grid = np.linspace(wl_min, wl_max, n_points)
    curvas = []
    for row in files.itertuples():
        spec = prepare_spectrum(load_spectrum(row.path))
        y = np.interp(grid, spec["wavelength"], spec["smooth"], left=np.nan, right=np.nan)
        curvas.append(((row.leaf_id, row.campaign_date, row.point), y))

    # Recorta la grilla a la cobertura comun: el ultimo pixel del espectrometro cae apenas
    # antes de X_MAX y dejaria un NaN en el borde de cada curva.
    cubierto = ~np.isnan(np.array([y for _, y in curvas])).any(axis=0)
    grid = grid[cubierto]
    n_points = len(grid)
    curvas = [(clave, y[cubierto]) for clave, y in curvas]

    por_punto: dict[tuple, list] = {}
    for clave, y in curvas:
        por_punto.setdefault(clave, []).append(y)

    por_hoja: dict[tuple, list] = {}
    for (lid, fecha, _), ys in por_punto.items():
        por_hoja.setdefault((lid, fecha), []).append(np.mean(ys, axis=0))

    partes = []
    for (lid, fecha), ys in por_hoja.items():
        m = np.array(ys)
        partes.append(pd.DataFrame({
            "leaf_id": lid, "campaign_date": fecha, "wavelength": grid,
            "mean": m.mean(axis=0),
            "sd": m.std(axis=0, ddof=1) if len(ys) > 1 else np.full(n_points, np.nan),
            "n_puntos": len(ys),
        }))
    return pd.concat(partes, ignore_index=True)


PEOR = "peor "
SD = "sd "


def point_series(files: pd.DataFrame, t_cero: pd.Timestamp) -> pd.DataFrame:
    """Valores por punto (media de repeticiones) con su dia, para graficar la dispersion interna."""
    pt = point_table(files)
    pt["dia"] = (pt["campaign_date"] - t_cero).dt.days
    return pt


def worst_point(files: pd.DataFrame, anchors: dict) -> pd.DataFrame:
    """Por hoja, fecha e indice, el punto mas desplazado hacia el ancla con roya.

    La roya aparece en manchas: si un solo punto cae sobre una pustula, el promedio de la hoja
    diluye la señal. La direccion "hacia la roya" de cada indice es el signo de
    (ancla con roya - ancla sana) de la especie. Con 3 puntos elegidos a ojo, el extremo es
    ruidoso: sirve como señal complementaria, no como reemplazo del promedio.
    """
    pt = point_table(files)
    signo = np.sign(anchors["enferma"] - anchors["sana"])
    claves = [*LEAF_KEYS, "campaign_id", "campaign_date"]
    out = pt[claves].drop_duplicates().set_index(claves)
    for idx in INDICES:
        s = pt["species"].map(signo[idx])
        dirigido = pt[idx] * s
        pos = dirigido.groupby([pt[c] for c in claves]).idxmax().dropna()
        out[PEOR + idx] = pt.loc[pos.astype(int).to_numpy(), idx].set_axis(pos.index)
    return out.reset_index()


def _theil_sen_matrix(x: np.ndarray, Y: np.ndarray) -> np.ndarray:
    """Pendiente de Theil-Sen de cada columna de Y (fechas x variables) contra x, vectorizada."""
    i, j = np.triu_indices(len(x), k=1)
    dx = x[j] - x[i]
    ok = dx != 0
    pendientes = (Y[j[ok]] - Y[i[ok]]) / dx[ok, None]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmedian(pendientes, axis=0)


@st.cache_data(show_spinner="Calculando la tendencia de cada longitud de onda...")
def spectral_trends(spectra: pd.DataFrame, meta: pd.DataFrame, t_cero: pd.Timestamp,
                    normalizar_nir: bool = False) -> pd.DataFrame:
    """Pendiente de Theil-Sen (puntos de reflectancia por semana) por hoja y longitud de onda.

    `normalizar_nir` divide cada espectro por su media en 750-900 nm (x100): elimina cambios
    multiplicativos de nivel entre dias (acople de la sonda, referencia de blanco), a costa de
    esconder tambien los cambios reales de la meseta NIR.
    """
    filas = []
    for lid, g in spectra.groupby("leaf_id"):
        m = g.pivot_table(index="campaign_date", columns="wavelength", values="mean").sort_index()
        if len(m) < TEMPORAL_MIN_FECHAS_TENDENCIA:
            continue
        Y = m.to_numpy(float)
        if normalizar_nir:
            wl = m.columns.to_numpy(float)
            nir = Y[:, (wl >= 750) & (wl <= 900)].mean(axis=1, keepdims=True)
            Y = Y / nir * 100
        x = (m.index - t_cero).days.to_numpy(float) / 7.0
        pend = _theil_sen_matrix(x, Y)
        filas.append(pd.DataFrame({"leaf_id": lid, "wavelength": m.columns.to_numpy(float),
                                   "pendiente": pend, "n_fechas": len(m)}))
    if not filas:
        return pd.DataFrame(columns=["leaf_id", "wavelength", "pendiente", "n_fechas"])
    out = pd.concat(filas, ignore_index=True)
    return out.merge(meta[LEAF_KEYS].drop_duplicates(), on="leaf_id", how="left")


def trend_groups(species_with_rust: set) -> dict:
    """Grupos de hojas para comparar tendencias: quien envejece, quien tiene roya, quien es control."""
    return {
        "T (tierna al inicio), todas las especies": lambda d: d["Tipo"] == "T",
        "M, especies susceptibles": lambda d: (d["Tipo"] == "M") & d["Especie"].isin(species_with_rust),
        "M, controles sin roya": lambda d: (d["Tipo"] == "M") & ~d["Especie"].isin(species_with_rust),
        "R1 (con roya)": lambda d: d["Tipo"] == "R",
    }


def index_change_summary(trends: pd.DataFrame, species_with_rust: set) -> pd.DataFrame:
    """Que indices cambian con el tiempo y en que grupo de hojas, con una lectura por reglas fijas.

    Reglas (en este orden, se acumulan):
    - R1 significativa sin tendencia del mismo signo en T ni en M de controles -> propio de la roya.
    - M susceptible y M control significativas con el mismo signo -> envejecimiento de hoja madura.
    - M susceptible significativa sin igual en controles -> candidata (solo susceptibles).
    - Alguna T significativa -> maduracion de la hoja tierna.
    """
    grupos = trend_groups(species_with_rust)
    ev = trends[trends["p"].notna()] if "p" in trends else trends.iloc[0:0]
    filas = []
    for var, g in ev.groupby("Variable"):
        fila = {"Índice": var}
        signos = {}
        for nombre, sel in grupos.items():
            gg = g[sel(g)]
            sig = gg[gg["Significativa"] == True]  # noqa: E712
            fila[f"{nombre}: ↑/↓ sig. de n"] = f"{int((sig['Pendiente / semana'] > 0).sum())}/{int((sig['Pendiente / semana'] < 0).sum())} de {len(gg)}"
            fila[f"{nombre}: mediana pendiente"] = gg["Pendiente / semana"].median() if len(gg) else np.nan
            signos[nombre] = set(np.sign(sig["Pendiente / semana"]).astype(int))
        t, ms, mc, r = (signos[k] for k in grupos)
        lecturas = []
        if r and not (r & (t | mc)):
            lecturas.append("Cambia solo en la hoja con roya")
        if ms & mc:
            lecturas.append("Envejecimiento de la hoja madura (también en controles)")
        if ms - mc:
            lecturas.append("Solo en M susceptibles: candidata")
        if t:
            lecturas.append("Cambia al madurar la hoja tierna")
        fila["Lectura"] = "; ".join(lecturas) or "Sin cambio temporal detectable"
        filas.append(fila)
    return pd.DataFrame(filas)
