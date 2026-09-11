"""Anclas de referencia sana/enferma por especie e indice, para el score de severidad de roya."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from src.config import INDEX_DEFINITIONS
from src.parser import leaf_label, load_spectrum
from src.processing import calcular_indices, prepare_spectrum, severity_score

_INDICES = list(INDEX_DEFINITIONS)


def _min_max(col: pd.Series) -> tuple[float | None, float | None]:
    """Min y max de una columna de indice, o (None, None) si no hay datos validos."""
    limpio = col.dropna()
    if limpio.empty:
        return None, None
    return float(limpio.min()), float(limpio.max())


@st.cache_data(show_spinner="Calculando referencias de severidad de roya...")
def severity_baselines(dataset: pd.DataFrame) -> dict:
    """Ancla sana (hoja Tierna) y ancla enferma (hoja Con roya) por especie e indice.

    La hoja Tierna se usa como ancla sana porque la roya no ha tenido tiempo de manifestarse
    en tejido nuevo. Una especie sin muestras de roya propias usa como ancla enferma el
    promedio combinado de todas las que si las tienen, y el dict la marca con
    referencia_propia=False. Hoy el dataset solo trae Bourbon y Pacamara, que tienen ancla
    propia, asi que ese respaldo no se activa; se conserva para cuando entren especies nuevas.

    Incluye ademas la clave especial '__global_range__' con el min/max de cada indice
    calculado sobre todas las filas de referencia (Tierna + Con roya).
    """
    recognized = dataset[dataset["name_recognized"]]
    reference_rows = recognized[
        (recognized["leaf_maturity"] == "Tierna") | (recognized["health_status"] == "Con roya")
    ]

    calculado = []
    for row in reference_rows.itertuples():
        try:
            raw = load_spectrum(row.path)
            idx = calcular_indices(prepare_spectrum(raw))
        except ValueError:
            continue
        calculado.append({
            "species": row.species,
            "leaf_maturity": row.leaf_maturity,
            "health_status": row.health_status,
            **idx,
        })

    if not calculado:
        return {}

    calc_df = pd.DataFrame(calculado)
    sana = calc_df[calc_df["leaf_maturity"] == "Tierna"].groupby("species")[_INDICES].mean()
    enferma_especie = calc_df[calc_df["health_status"] == "Con roya"].groupby("species")[_INDICES].mean()
    enferma_global = calc_df[calc_df["health_status"] == "Con roya"][_INDICES].mean()

    baselines: dict = {}
    for species in sana.index:
        tiene_referencia_propia = species in enferma_especie.index
        enferma = enferma_especie.loc[species] if tiene_referencia_propia else enferma_global
        # Rango observado del indice en las hojas de referencia de esa especie: es lo que la
        # alerta muestra al lado del valor, para saber si esta alto o bajo para su especie.
        filas_especie = calc_df[calc_df["species"] == species]
        baselines[species] = {
            "referencia_propia": tiene_referencia_propia,
            "indices": {
                idx_name: {
                    "sana": sana.loc[species, idx_name],
                    "enferma": enferma[idx_name],
                    "min": _min_max(filas_especie[idx_name])[0],
                    "max": _min_max(filas_especie[idx_name])[1],
                }
                for idx_name in _INDICES
            },
        }

    global_range = {}
    for idx_name in _INDICES:
        col = calc_df[idx_name].dropna()
        if not col.empty:
            global_range[idx_name] = {"min": float(col.min()), "max": float(col.max())}
        else:
            global_range[idx_name] = {"min": None, "max": None}
    baselines["__global_range__"] = global_range

    return baselines


def _normalizado(valor, sana, enferma) -> float | None:
    """Posicion del valor entre la referencia sana (0) y la de roya (1), recortada a 0-1."""
    if valor is None or sana is None or enferma is None:
        return None
    if np.isnan(valor) or np.isnan(sana) or np.isnan(enferma) or sana == enferma:
        return None
    return float(np.clip((valor - sana) / (enferma - sana), 0.0, 1.0))


def leaf_severity_reports(new_df: pd.DataFrame, baselines: dict) -> list[dict]:
    """Agrega las mediciones nuevas a nivel de hoja, que es la unidad que se reporta en Telegram.

    Se promedia en dos pasos —primero las medidas repetidas de cada punto, despues los puntos
    de la hoja— para que una hoja con puntos incompletos no quede sesgada hacia el punto que
    tenga mas repeticiones. Se promedia tanto la severidad como cada indice.

    Devuelve una lista de dicts (una por hoja) ordenada de mayor a menor severidad, con el
    valor de cada indice, su referencia sana y su posicion normalizada hacia la referencia
    con roya (lo que `notifier` usa para decidir que indices van en negrita).
    """
    filas = []
    for row in new_df[new_df["name_recognized"]].itertuples():
        especie_baseline = baselines.get(row.species)
        if especie_baseline is None:
            continue
        try:
            idx = calcular_indices(prepare_spectrum(load_spectrum(row.path)))
        except ValueError:
            continue
        sev = severity_score(idx, especie_baseline["indices"])
        if sev is None:
            continue
        filas.append({
            "species": row.species,
            "campaign": row.campaign_id,
            "campaign_date": row.campaign_date,
            "hoja": leaf_label(row.session, row.session_num),
            "punto": row.point,
            "score": sev["score"],
            **idx,
        })

    if not filas:
        return []

    medidas = pd.DataFrame(filas)
    valores = ["score", *_INDICES]
    claves_punto = ["species", "campaign", "hoja", "punto"]
    claves_hoja = ["species", "campaign", "hoja"]

    por_punto = medidas.groupby(claves_punto, dropna=False)[valores].mean().reset_index()
    por_hoja = por_punto.groupby(claves_hoja, dropna=False)[valores].mean()
    n_puntos = por_punto.groupby(claves_hoja, dropna=False).size()
    # La fecha es constante dentro de cada campaña, asi que basta con mapearla una vez.
    fecha_por_campana = dict(zip(medidas["campaign"], medidas["campaign_date"]))

    reportes = []
    for clave, fila in por_hoja.iterrows():
        species, campaign, hoja = clave
        especie_baseline = baselines.get(species, {})
        idx_baseline = especie_baseline.get("indices", {})

        indices = {}
        for idx_name in _INDICES:
            ref = idx_baseline.get(idx_name, {})
            valor = fila[idx_name]
            indices[idx_name] = {
                "valor": valor,
                "sana": ref.get("sana"),
                "enferma": ref.get("enferma"),
                "min": ref.get("min"),
                "max": ref.get("max"),
                "normalizado": _normalizado(valor, ref.get("sana"), ref.get("enferma")),
            }

        reportes.append({
            "species": species,
            "campaign": campaign if pd.notna(campaign) else None,
            "campaign_date": fecha_por_campana.get(campaign),
            "hoja": hoja,
            "score": float(fila["score"]),
            "n_indices": sum(1 for v in indices.values() if v["normalizado"] is not None),
            "n_puntos": int(n_puntos.loc[clave]),
            "referencia_propia": especie_baseline.get("referencia_propia", True),
            "indices": indices,
        })

    reportes.sort(key=lambda r: (-r["score"], r["species"], str(r["campaign"]), r["hoja"]))
    return reportes
