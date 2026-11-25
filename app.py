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
            st.Page(V / "derivadas.py", title="Derivadas espectrales", icon=":material/ssid_chart:"),
            st.Page(V / "correlacion_tiempo.py", title="Correlación con el tiempo", icon=":material/trending_up:"),
            st.Page(V / "cambio_pca.py", title="Cambio espectral y PCA", icon=":material/scatter_plot:"),
            st.Page(V / "rasgos.py", title="Rasgos espectrales", icon=":material/insights:"),
        ],
        "Datos y operación": [
            st.Page(V / "datos_calidad.py", title="Datos y calidad", icon=":material/fact_check:"),
            # Alerta de campo (Telegram) oculta desde 2026-11-24 a pedido del usuario: al sumar la planta
            # resistente de Pacamara, sus 711 archivos saldrian todos como «novedad». El codigo sigue en
            # views/alerta.py; para volver a mostrarla, descomentar la linea de abajo.
            # st.Page(V / "alerta.py", title="Alerta de campo", icon=":material/notifications:"),
        ],
    }
)
nav.run()
