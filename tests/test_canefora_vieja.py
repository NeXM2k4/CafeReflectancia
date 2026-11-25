"""Hoja vieja de Canefora (V1) en el analisis (agregado 2026-11-24)."""

from __future__ import annotations

from pathlib import Path

from src.config import SPECIES_PENDING_LABEL, VIEJA_SPECIES
from src.parser import _discover_records, get_dataset
from src.temporal import file_indices, leaf_timeseries

TXT = "Data>>>>>Begin Spectral Data<<<<<\n500.0\t10.0\n600.0\t20.0\n"


def test_carpeta_vieja_suelta_es_canefora(tmp_path):
    p = tmp_path / "24_08_2026/24_08_2026/vieja/p2vieja3.txt"
    p.parent.mkdir(parents=True)
    p.write_text(TXT, encoding="latin-1")
    (r,) = _discover_records(tmp_path)
    assert r.species == VIEJA_SPECIES == "Canefora"
    assert (r.session, r.session_num, r.point, r.repetition) == ("V", 1, 2, 3)


def test_canefora_v1_tiene_serie_temporal():
    df = get_dataset()
    assert not (df["species"] == SPECIES_PENDING_LABEL).any()
    files, _ = file_indices(df)
    ts = leaf_timeseries(files)
    v1 = ts[(ts["species"] == "Canefora") & (ts["leaf"] == "V1")]
    assert v1["campaign_date"].nunique() == 9
    assert v1["campaign_date"].min().strftime("%d/%m") == "17/08"
