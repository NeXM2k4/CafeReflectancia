"""Punto de entrada: configuracion de la pagina, tema y navegacion agrupada por proposito.

Cada vista vive en `views/`. Se ejecuta con `streamlit run app.py`.
"""

from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Reflectancia foliar · Roya del café",
    page_icon=":material/eco:",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.logo(str(ROOT / "assets" / "logo.svg"), size="large")

V = ROOT / "views"
nav = st.navigation(
    {
        "Resumen": [
            st.Page(V / "panorama.py", title="Panorama", icon=":material/space_dashboard:", default=True),
            st.Page(V / "metodo.py", title="Método y glosario", icon=":material/menu_book:"),
        ],
        "Análisis exploratorio": [
            st.Page(V / "espectros.py", title="Espectros", icon=":material/show_chart:"),
            st.Page(V / "indices.py", title="Índices por tipo de hoja", icon=":material/stacked_bar_chart:"),
            st.Page(V / "variedades.py", title="Comparación entre variedades", icon=":material/compare_arrows:"),
        ],
        "Seguimiento de hojas": [
            st.Page(V / "estado_actual.py", title="Estado actual", icon=":material/grid_view:"),
            st.Page(V / "evolucion.py", title="Evolución temporal", icon=":material/timeline:"),
        ],
        "Datos y operación": [
            st.Page(V / "datos_calidad.py", title="Datos y calidad", icon=":material/fact_check:"),
            st.Page(V / "alerta.py", title="Alerta de campo", icon=":material/notifications:"),
        ],
    }
)
nav.run()
