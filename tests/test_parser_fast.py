"""El lector rapido de SpectraSuite debe dar exactamente lo mismo que el lector original.

`_lector_original` es una copia literal del parser anterior a 2026-11-16 (bucle linea por
linea). Se compara contra todos los .txt de data/: igualdad exacta, no aproximada.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.parser import parse_spectrasuite_text

ROOT = Path(__file__).resolve().parent.parent
ARCHIVOS = sorted((ROOT / "data").rglob("*.txt"))


def _lector_original(texto: str) -> pd.DataFrame:
    lineas = texto.splitlines()
    inicio = None
    for i, linea in enumerate(lineas):
        if "Comienza Data" in linea or "Begin Spectral" in linea:
            inicio = i + 1
            break
    if inicio is None:
        raise ValueError("sin marcador")
    filas = []
    for linea in lineas[inicio:]:
        linea = linea.strip()
        if not linea:
            continue
        partes = linea.replace(",", ".").split()
        if len(partes) >= 2:
            try:
                filas.append((float(partes[0]), float(partes[1])))
            except ValueError:
                continue
    if not filas:
        raise ValueError("sin datos")
    df = pd.DataFrame(filas, columns=["wavelength", "reflectance"])
    return df.drop_duplicates(subset="wavelength").sort_values("wavelength").reset_index(drop=True)


def test_hay_archivos():
    assert len(ARCHIVOS) > 1000


def test_lector_rapido_identico_en_todo_data():
    distintos = []
    for p in ARCHIVOS:
        texto = p.read_text(encoding="latin-1", errors="replace")
        try:
            viejo = _lector_original(texto)
        except ValueError:
            with pytest.raises(ValueError):
                parse_spectrasuite_text(texto, str(p))
            continue
        nuevo = parse_spectrasuite_text(texto, str(p))
        if not (np.array_equal(viejo.to_numpy(), nuevo.to_numpy()) and list(viejo.columns) == list(nuevo.columns)):
            distintos.append(p.name)
    assert not distintos, distintos[:10]


def test_camino_lento_con_lineas_raras():
    texto = "cabecera\n>>>>> Comienza Data<<<<<\n400,0\t10,5\nbasura\n401,0\t11,0\t99\n\n402,0\t12,0\n"
    assert parse_spectrasuite_text(texto).to_numpy().tolist() == [[400.0, 10.5], [401.0, 11.0], [402.0, 12.0]]
