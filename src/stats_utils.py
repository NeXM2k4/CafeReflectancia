"""Comparacion estadistica automatica entre grupos.

`summarize_indices()` es la funcion nueva (F1.4 de `plan_mejora_app.md`) y la que deberian usar
las paginas: una fila por indice con mediana por grupo, tamaño de efecto, p ajustado por
comparaciones multiples (Holm) y un **veredicto en palabras**. Esta pensada para trabajar sobre
datos ya agregados a hoja-fecha (`src.indices.leaf_date_table`), asi que cada fila de entrada es
una observacion biologica y no una pseudo-replica de puntos o repeticiones.

`compare_groups()` es la funcion vieja (Shapiro -> ANOVA/Tukey o Kruskal-Wallis/Dunn), con mas
detalle tecnico pero sin veredicto ni correccion por comparaciones multiples. Se mantiene para
quien quiera ver ese detalle (paginas 2 y 3 la muestran plegada en "Detalle tecnico").
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

from src.config import ALPHA_SIGNIFICANCE

# Umbrales de |delta de Cliff| para el veredicto en palabras (Romano et al. 2006: 0.11/0.28/0.43
# para pequeño/mediano/grande: se redondea a un criterio mas simple de comunicar, sin cambiar el
# orden de magnitud: "clara" ~ grande, "moderada" ~ mediana, "debil" ~ pequeña).
_DELTA_CLARA = 0.66
_DELTA_MODERADA = 0.33


def cliffs_delta(a, b) -> float:
    """Tamaño de efecto no parametrico entre dos muestras, -1 a +1, independiente de la escala
    del indice. +1 = todo `a` es mayor que todo `b`; 0 = se solapan por completo."""
    a = np.asarray([v for v in a if v is not None and not (isinstance(v, float) and np.isnan(v))], dtype=float)
    b = np.asarray([v for v in b if v is not None and not (isinstance(v, float) and np.isnan(v))], dtype=float)
    if len(a) == 0 or len(b) == 0:
        return np.nan
    diff = a[:, None] - b[None, :]
    return float(((diff > 0).sum() - (diff < 0).sum()) / (len(a) * len(b)))


def _verdict(p: float | None, delta: float | None, n_groups: int, alpha: float) -> str:
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "Datos insuficientes"
    if p >= alpha:
        return "No separa los grupos"
    if n_groups != 2 or delta is None or np.isnan(delta):
        return "Diferencia significativa (grupo distinto sin identificar cual)"
    mag = abs(delta)
    if mag >= _DELTA_CLARA:
        return "Separa claramente los grupos"
    if mag >= _DELTA_MODERADA:
        return "Diferencia moderada"
    return "Diferencia débil (estadísticamente significativa, pero el solape es grande)"


def summarize_indices(
    data: pd.DataFrame, group_col: str, indices: list[str], alpha: float = ALPHA_SIGNIFICANCE,
) -> pd.DataFrame:
    """Resumen por indice: mediana por grupo, tamaño de efecto, test, p crudo, p ajustado por
    Holm (entre todos los indices de esta tabla) y un veredicto en palabras.

    Con 2 grupos usa Mann-Whitney U + delta de Cliff (con su signo: positivo si el primer grupo
    -orden alfabetico- tiende a ser mayor). Con 3+ grupos usa Kruskal-Wallis (sin tamaño de
    efecto por pares: para eso esta `compare_groups()` con su post-hoc).
    """
    groups_present = sorted(data[group_col].dropna().unique())
    filas = []
    for idx in indices:
        vals = {}
        for g in groups_present:
            serie = data.loc[data[group_col] == g, idx].dropna()
            if len(serie) >= 2:
                vals[g] = serie.to_numpy(dtype=float)
        row: dict = {"Índice": idx}
        for g in groups_present:
            v = vals.get(g)
            row[f"n ({g})"] = 0 if v is None else len(v)
            row[f"Mediana ({g})"] = float(np.median(v)) if v is not None else np.nan
        if len(vals) < 2:
            row.update({"Efecto (δ Cliff)": np.nan, "Test": None, "p": np.nan, "_n_grupos": len(vals)})
            filas.append(row)
            continue
        samples = list(vals.values())
        if len(samples) == 2:
            delta = cliffs_delta(samples[0], samples[1])
            try:
                _, p = stats.mannwhitneyu(samples[0], samples[1], alternative="two-sided")
            except ValueError:
                p = np.nan
            test_name = "Mann-Whitney U"
        else:
            delta = np.nan
            try:
                _, p = stats.kruskal(*samples)
            except ValueError:
                p = np.nan
            test_name = "Kruskal-Wallis"
        row.update({
            "Efecto (δ Cliff)": delta, "Test": test_name, "p": float(p) if p is not None and not np.isnan(p) else np.nan,
            "_n_grupos": len(vals),
        })
        filas.append(row)

    out = pd.DataFrame(filas)
    valid = out["p"].notna()
    out["p (Holm)"] = np.nan
    if valid.sum() > 0:
        _, p_adj, _, _ = multipletests(out.loc[valid, "p"], method="holm")
        out.loc[valid, "p (Holm)"] = p_adj
    out["Veredicto"] = [
        _verdict(p_holm, delta, n_g, alpha)
        for p_holm, delta, n_g in zip(out["p (Holm)"], out["Efecto (δ Cliff)"], out["_n_grupos"])
    ]
    return out.drop(columns="_n_grupos")


def compare_groups(groups: dict[str, list[float]], alpha: float = ALPHA_SIGNIFICANCE) -> dict:
    """Compara 2+ grupos de valores numericos (ej. un indice espectral por grupo).

    Decide automaticamente el test parametrico o no parametrico segun Shapiro-Wilk,
    y corre el post-hoc correspondiente si el resultado es significativo.
    """
    clean = {g: [float(v) for v in vals if v is not None and not np.isnan(v)] for g, vals in groups.items()}
    summary = {
        g: {
            "n": len(v),
            "mean": float(np.mean(v)) if v else np.nan,
            "sd": float(np.std(v, ddof=1)) if len(v) > 1 else np.nan,
        }
        for g, v in clean.items()
    }

    usable = {g: v for g, v in clean.items() if len(v) >= 2}
    if len(usable) < 2:
        return {
            "summary": summary,
            "shapiro": {},
            "test_name": None,
            "stat": None,
            "p_value": None,
            "significant": False,
            "posthoc_name": None,
            "posthoc": None,
            "message": "Se necesitan al menos 2 grupos con 2 o más observaciones para comparar.",
        }

    shapiro_results = {}
    normal = True
    for g, v in usable.items():
        if len(v) >= 3:
            stat, p = stats.shapiro(v)
            shapiro_results[g] = {"stat": float(stat), "p": float(p), "normal": p > alpha}
            if p <= alpha:
                normal = False
        else:
            shapiro_results[g] = {"stat": np.nan, "p": np.nan, "normal": None}
            normal = False  # sin suficientes datos para confirmar normalidad -> se asume conservador

    labels = list(usable.keys())
    samples = list(usable.values())

    if normal:
        stat, p = stats.f_oneway(*samples)
        test_name = "ANOVA"
    else:
        stat, p = stats.kruskal(*samples)
        test_name = "Kruskal-Wallis"

    posthoc = None
    posthoc_name = None
    if p is not None and not np.isnan(p) and p < alpha:
        if normal:
            from statsmodels.stats.multicomp import pairwise_tukeyhsd

            all_vals = [v for s in samples for v in s]
            all_labels = [g for g, s in zip(labels, samples) for _ in s]
            tukey = pairwise_tukeyhsd(all_vals, all_labels, alpha=alpha)
            table = tukey._results_table.data
            posthoc = pd.DataFrame(table[1:], columns=table[0])
            posthoc_name = "Tukey HSD"
        else:
            from scikit_posthocs import posthoc_dunn

            dunn = posthoc_dunn(samples, p_adjust="bonferroni")
            dunn.index = labels
            dunn.columns = labels
            posthoc = dunn
            posthoc_name = "Dunn (Bonferroni)"

    return {
        "summary": summary,
        "shapiro": shapiro_results,
        "test_name": test_name,
        "stat": float(stat) if stat is not None else None,
        "p_value": float(p) if p is not None else None,
        "significant": bool(p is not None and not np.isnan(p) and p < alpha),
        "posthoc_name": posthoc_name,
        "posthoc": posthoc,
        "message": None,
    }
