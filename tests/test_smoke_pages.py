"""Prueba de humo: abre todas las vistas con los filtros por defecto y falla si hay excepciones.

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

# app.py es el enrutador (st.navigation) y abre "Panorama"; el resto de vistas se prueban solas.
PAGES = [
    "app.py",
    "views/metodo.py",
    "views/espectros.py",
    "views/indices.py",
    "views/variedades.py",
    "views/estado_actual.py",
    "views/evolucion.py",
    "views/datos_calidad.py",
    "views/alerta.py",
]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_without_exception(page):
    at = AppTest.from_file(str(ROOT / page), default_timeout=120)
    at.run()
    assert not at.exception, f"{page} lanzo una excepcion: {[str(e) for e in at.exception]}"
