"""Comparacion estadistica automatica entre grupos (Shapiro -> ANOVA/Tukey o Kruskal-Wallis/Dunn)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from src.config import ALPHA_SIGNIFICANCE


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
            "message": "Se necesitan al menos 2 grupos con 2 o mas observaciones para comparar.",
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
