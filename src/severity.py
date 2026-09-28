"""Anclas de referencia sana/con-roya por especie e indice, para la similitud espectral con roya.

Hasta el 2026-09-28 este modulo promediaba **archivos** para armar las anclas, lo que sobre-
pesaba las campañas con mas repeticiones (las de julio, con hasta 10 repeticiones por punto en
las hojas con roya, pesaban ~3 veces mas que las de septiembre, con 3). Ver `plan_mejora_app.md`
fase F1.3. Ahora las anclas se calculan sobre la tabla **hoja-fecha** (cada fecha pesa igual,
sin importar cuantas repeticiones tuvo) y excluyen las hojas-fecha marcadas por el control de
calidad (`src.indices.quality_flags`): outliers respecto de la propia historia de la hoja, o
valores fisicamente imposibles (mNDVI705 fuera de rango). FSR se excluye siempre: usa las
mismas bandas que NDVI (`config.WL_FSR`) y duplicaria su peso en la mediana.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from src.config import TEMPORAL_VALID_POINTS
from src.indices import DISPLAY_INDICES, file_index_table, leaf_date_table, quality_flags
from src.parser import leaf_label
from src.processing import calcular_indices, prepare_spectrum, severity_score
from src.parser import load_spectrum


def _min_max(col: pd.Series) -> tuple[float | None, float | None]:
    """Min y max de una columna de indice, o (None, None) si no hay datos validos."""
    limpio = col.dropna()
    if limpio.empty:
        return None, None
    return float(limpio.min()), float(limpio.max())


@st.cache_data(show_spinner="Calculando referencias de similitud con roya...")
def severity_baselines(dataset: pd.DataFrame) -> dict:
    """Ancla sana (hoja Tierna) y ancla con roya (hoja Con roya) por especie e indice.

    La hoja Tierna se usa como ancla sana porque la roya no ha tenido tiempo de manifestarse
    en tejido nuevo. Una especie sin muestras de roya propias usa como ancla con roya el
    promedio combinado de todas las que si las tienen, y el dict la marca con
    `referencia_propia=False` (hoy eso aplica a Canefora y Cuscatleco).

    **Unidad: hoja-fecha, no archivo** (cada fecha pesa igual) y sin las hojas-fecha marcadas
    por control de calidad. Solo p1-p3 (`leaf_date_table`). FSR queda fuera de las anclas: no
    aparece en `baselines[especie]["indices"]`, asi que `severity_score()` lo ignora solo.

    Incluye ademas la clave especial '__global_range__' con el min/max de cada indice sobre
    todas las hojas-fecha de referencia (Tierna + Con roya) usadas para las anclas.
    """
    files, _ = file_index_table(dataset)
    ld = quality_flags(leaf_date_table(files, TEMPORAL_VALID_POINTS))
    limpio = ld[~ld["qc_flag"]]

    sana = limpio[limpio["leaf_type"] == "T"].groupby("species")[DISPLAY_INDICES].mean()
    if sana.empty:
        return {}
    enferma_especie = limpio[limpio["leaf_type"] == "R"].groupby("species")[DISPLAY_INDICES].mean()
    enferma_global = limpio[limpio["leaf_type"] == "R"][DISPLAY_INDICES].mean()

    baselines: dict = {}
    for species in sana.index:
        tiene_referencia_propia = species in enferma_especie.index
        enferma = enferma_especie.loc[species] if tiene_referencia_propia else enferma_global
        # Rango observado del indice en las hojas-fecha de referencia de esa especie: es lo
        # que la alerta muestra al lado del valor, para saber si esta alto o bajo para su especie.
        filas_especie = limpio[limpio["species"] == species]
        baselines[species] = {
            "referencia_propia": tiene_referencia_propia,
            "indices": {
                idx_name: {
                    "sana": sana.loc[species, idx_name],
                    "enferma": enferma[idx_name],
                    "min": _min_max(filas_especie[idx_name])[0],
                    "max": _min_max(filas_especie[idx_name])[1],
                }
                for idx_name in DISPLAY_INDICES
            },
        }

    global_range = {}
    for idx_name in DISPLAY_INDICES:
        col = limpio[idx_name].dropna()
        if not col.empty:
            global_range[idx_name] = {"min": float(col.min()), "max": float(col.max())}
        else:
            global_range[idx_name] = {"min": None, "max": None}
    baselines["__global_range__"] = global_range

    return baselines


def leaf_date_similarity(leaf_dates: pd.DataFrame, baselines: dict) -> pd.DataFrame:
    """Similitud con roya (0-1) para cada fila de una tabla hoja-fecha (`leaf_date_table`).

    Usa las mismas anclas que `leaf_severity_reports()` (la alerta de Telegram), asi que una
    hoja-fecha muestra el mismo numero en la pagina 4 y en la pagina 5 (X5 de
    `plan_mejora_app.md`: "una sola definicion de similitud con roya en toda la app").
    """
    out = leaf_dates.copy()
    scores, n_indices = [], []
    for row in out.itertuples():
        baseline = baselines.get(row.species)
        if baseline is None:
            scores.append(np.nan)
            n_indices.append(0)
            continue
        values = {idx: getattr(row, idx) for idx in DISPLAY_INDICES}
        sev = severity_score(values, baseline["indices"])
        if sev is None:
            scores.append(np.nan)
            n_indices.append(0)
        else:
            scores.append(sev["score"])
            n_indices.append(sev["n_indices"])
    out["similitud"] = scores
    out["similitud_n_indices"] = n_indices
    return out


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
    tenga mas repeticiones. Solo p1-p3 (mismo criterio que el resto de la app, ver
    `TEMPORAL_VALID_POINTS`). **La similitud se calcula una sola vez, sobre el promedio final de
    cada indice** (no se promedia una similitud calculada por archivo): es exactamente el mismo
    orden de operaciones que `leaf_date_similarity()`, para que una hoja-fecha muestre el mismo
    numero en Telegram, en la pagina 4 y en la pagina 5 (X5 de `plan_mejora_app.md`). Antes de
    esta correccion (2026-09-28) el orden era distinto (mediana de normalizados por archivo,
    despues promedio) y daba un numero ligeramente distinto al de las paginas 4/5 para la misma
    hoja-fecha.

    Devuelve una lista de dicts (una por hoja) ordenada de mayor a menor similitud, con el
    valor de cada indice, su referencia sana y su posicion normalizada hacia la referencia
    con roya (lo que `notifier` usa para decidir que indices resaltar).
    """
    filas = []
    sel = new_df[new_df["name_recognized"] & new_df["point"].isin(TEMPORAL_VALID_POINTS)]
    for row in sel.itertuples():
        if baselines.get(row.species) is None:
            continue
        try:
            idx = calcular_indices(prepare_spectrum(load_spectrum(row.path)))
        except ValueError:
            continue
        filas.append({
            "species": row.species,
            "campaign": row.campaign_id,
            "campaign_date": row.campaign_date,
            "hoja": leaf_label(row.session, row.session_num),
            "punto": row.point,
            **idx,
        })

    if not filas:
        return []

    medidas = pd.DataFrame(filas)
    claves_punto = ["species", "campaign", "hoja", "punto"]
    claves_hoja = ["species", "campaign", "hoja"]

    por_punto = medidas.groupby(claves_punto, dropna=False)[DISPLAY_INDICES].mean().reset_index()
    por_hoja = por_punto.groupby(claves_hoja, dropna=False)[DISPLAY_INDICES].mean()
    n_puntos = por_punto.groupby(claves_hoja, dropna=False).size()
    # La fecha es constante dentro de cada campaña, asi que basta con mapearla una vez.
    fecha_por_campana = dict(zip(medidas["campaign"], medidas["campaign_date"]))

    reportes = []
    for clave, fila in por_hoja.iterrows():
        species, campaign, hoja = clave
        especie_baseline = baselines.get(species, {})
        idx_baseline = especie_baseline.get("indices", {})

        indices = {}
        for idx_name in DISPLAY_INDICES:
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

        # Un solo calculo de similitud, sobre el promedio final de cada indice (no una mediana
        # por archivo que despues se promedia): mismo orden que `leaf_date_similarity()`.
        sev = severity_score({idx: fila[idx] for idx in DISPLAY_INDICES}, idx_baseline)
        if sev is None:
            continue

        reportes.append({
            "species": species,
            "campaign": campaign if pd.notna(campaign) else None,
            "campaign_date": fecha_por_campana.get(campaign),
            "hoja": hoja,
            "score": sev["score"],
            "n_indices": sev["n_indices"],
            "n_puntos": int(n_puntos.loc[clave]),
            "referencia_propia": especie_baseline.get("referencia_propia", True),
            "indices": indices,
        })

    reportes.sort(key=lambda r: (-r["score"], r["species"], str(r["campaign"]), r["hoja"]))
    return reportes
