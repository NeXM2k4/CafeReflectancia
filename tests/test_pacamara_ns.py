"""Pacamara «No susceptible» (planta resistente) como grupo propio (docs/plan_pacamara_no_susceptible.md)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.config import PACAMARA_NS, RUST_ANCHOR_FROM
from src.parser import _discover_records, get_dataset, leaf_label
from src.temporal import file_indices, leaf_timeseries, severity_anchors

TXT = "Data>>>>>Begin Spectral Data<<<<<\n500.0\t10.0\n600.0\t20.0\n"


def _toca(base: Path, rel: str) -> None:
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(TXT, encoding="latin-1")


def test_parser_separa_las_dos_plantas_de_pacamara(tmp_path):
    _toca(tmp_path, "10_08_2026/pacamara/no suceptible/M1p1pacamara1.txt")
    _toca(tmp_path, "10_08_2026/pacamara/suceptible/M1p1pacamara1.txt")
    _toca(tmp_path, "05_10_2026/Pacamara/Roya/R1p1pacamara1.txt")
    _toca(tmp_path, "05_10_2026/Pacamara/No Susceptible/T2p3pacamara2.txt")
    recs = {Path(r.path).relative_to(tmp_path).as_posix(): r for r in _discover_records(tmp_path)}
    assert recs["10_08_2026/pacamara/no suceptible/M1p1pacamara1.txt"].species == PACAMARA_NS
    assert recs["05_10_2026/Pacamara/No Susceptible/T2p3pacamara2.txt"].species == PACAMARA_NS
    assert recs["10_08_2026/pacamara/suceptible/M1p1pacamara1.txt"].species == "Pacamara"
    # la roya es solo de la planta susceptible
    assert recs["05_10_2026/Pacamara/Roya/R1p1pacamara1.txt"].species == "Pacamara"


def test_etiqueta_de_hoja_con_sufijo():
    assert leaf_label("M", 1, PACAMARA_NS) == "M1-NS"
    assert leaf_label("T", 2.0, PACAMARA_NS) == "T2-NS"
    assert leaf_label("M", 1, "Pacamara") == "M1"


@pytest.fixture(scope="module")
def ts() -> pd.DataFrame:
    files, _ = file_indices(get_dataset())
    return leaf_timeseries(files)


def test_hojas_de_las_dos_plantas_no_se_mezclan(ts):
    ns = ts[ts["species"] == PACAMARA_NS]
    assert set(ns["leaf"]) == {"M1-NS", "M2-NS", "T1-NS", "T2-NS"}
    assert ns["campaign_date"].nunique() == 20
    pac = ts[ts["species"] == "Pacamara"]
    assert set(pac["leaf"]) == {"M1", "M2", "T1", "T2", "R1"}
    assert not set(ns["leaf_id"]) & set(pac["leaf_id"])


def test_ancla_con_roya_de_la_misma_variedad(ts):
    a = severity_anchors(ts)
    fuente = RUST_ANCHOR_FROM[PACAMARA_NS]
    assert a["referencia_de"][PACAMARA_NS] == fuente
    assert not a["referencia_propia"][PACAMARA_NS]
    pd.testing.assert_series_equal(a["enferma"].loc[PACAMARA_NS], a["enferma"].loc[fuente], check_names=False)


def test_distancia_y_sam_contra_r1_de_pacamara(ts):
    from src.parser import get_dataset
    from src.spectral import F_SAM_R1, features_table
    from src.temporal import distance_to_rust, leaf_mean_spectra

    files, _ = file_indices(get_dataset())
    d = distance_to_rust(files, ts)
    assert (d["species"] == PACAMARA_NS).any()
    spectra = leaf_mean_spectra(files[["leaf_id", "campaign_date", "point", "path"]])
    f = features_table(spectra, ts)
    assert f.loc[f["species"] == PACAMARA_NS, F_SAM_R1].notna().any()
