"""Anclas de referencia sana/enferma por especie e indice, para el score de severidad de roya."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import INDEX_DEFINITIONS
from src.parser import load_spectrum
from src.processing import calcular_indices, prepare_spectrum

_INDICES = list(INDEX_DEFINITIONS)


@st.cache_data(show_spinner="Calculando referencias de severidad de roya...")
def severity_baselines(dataset: pd.DataFrame) -> dict:
    """Ancla sana (hoja Tierna) y ancla enferma (hoja Con roya) por especie e indice.

    La hoja Tierna se usa como ancla sana porque la roya no ha tenido tiempo de manifestarse
    en tejido nuevo. Las especies sin muestras de roya propias (Canefora, Cuscatleco) usan
    como ancla enferma el promedio combinado de Bourbon y Pacamara; el dict resultante marca
    esos casos con referencia_propia=False.

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
        baselines[species] = {
            "referencia_propia": tiene_referencia_propia,
            "indices": {
                idx_name: {"sana": sana.loc[species, idx_name], "enferma": enferma[idx_name]}
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
