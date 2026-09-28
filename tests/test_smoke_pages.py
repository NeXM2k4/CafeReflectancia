"""Prueba de humo: abre las 5 paginas con los filtros por defecto y falla si hay excepciones.

No verifica valores (eso lo hacen los chequeos de coherencia numerica, F6), solo que cada
pagina renderiza sin lanzar una excepcion no capturada. Se corre con:

    python -m pytest tests/test_smoke_pages.py -v

Requiere que `data/` tenga contenido real (usa el dataset del proyecto, no fixtures).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent

PAGES = [
    "app.py",
    "pages/1_Espectros.py",
    "pages/2_Indices_Espectrales.py",
    "pages/3_Comparacion_Especies.py",
    "pages/4_Estado_Hojas.py",
    "pages/5_Evolucion_Temporal.py",
]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_without_exception(page):
    at = AppTest.from_file(str(ROOT / page), default_timeout=120)
    at.run()
    assert not at.exception, f"{page} lanzo una excepcion: {[str(e) for e in at.exception]}"
