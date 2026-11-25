"""Las optimizaciones de rendimiento (docs/plan_rendimiento.md) no cambian ningun numero ni el aspecto."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import pytest

import src.ui  # noqa: F401 (registra la plantilla de la app)
from src.parser import get_dataset
from src.temporal import (
    DELTA_STAR,
    DIST_INDICES,
    _leaf_trends_compute,
    add_deltas,
    file_indices,
    leaf_timeseries,
    leaf_trends,
)


def test_plantilla_precombinada_es_igual_a_la_cadena():
    precombinada = go.Figure().layout.template.to_plotly_json()
    cadena = pio.templates.merge_templates("plotly_white", "reflec").to_plotly_json()
    assert pio.templates.default == "reflec_full"
    assert precombinada == cadena


@pytest.fixture(scope="module")
def ts() -> pd.DataFrame:
    files, _ = file_indices(get_dataset())
    return add_deltas(leaf_timeseries(files))


@pytest.mark.parametrize("prefijo", ["", DELTA_STAR])
def test_leaf_trends_con_cache_da_lo_mismo(ts, prefijo):
    columnas = [prefijo + i for i in DIST_INDICES]
    esperado = _leaf_trends_compute(ts, columnas, "familia")  # tabla completa, sin cache
    pd.testing.assert_frame_equal(leaf_trends(ts, columnas, "familia"), esperado)
    pd.testing.assert_frame_equal(leaf_trends(ts, columnas, "familia"), esperado)  # desde el cache
