"""Metodo y glosario. El texto del metodo se lee de METODOLOGIA.md: una sola fuente de verdad."""

import re
from pathlib import Path

import streamlit as st

from src.indices import DISPLAY_INDICES
from src.parser import get_dataset
from src.ui import html_table, index_sheet_table, page_header, section, sidebar_footer

import pandas as pd

page_header(
    "Resumen",
    "Método y glosario",
    "Cómo se procesa cada espectro, cómo se agregan los datos y qué significa cada término que "
    "aparece en la aplicación. El texto se lee de <code>METODOLOGIA.md</code>, el mismo documento "
    "que sirve de base al artículo.",
)
sidebar_footer(get_dataset())

GLOSARIO = [
    ("Hoja-fecha", "Una hoja física en una campaña (p. ej. Bourbon M1 el 21/07). Es la unidad de análisis: se promedian las repeticiones de cada punto y luego los puntos p1–p3."),
    ("Tipo de hoja", "Tierna (T), Madura (M), Vieja (V) o Con roya (R), según el prefijo del archivo. Tierna y madura significan «sin síntomas visibles», no «sana»."),
    ("Hoja longitudinal", "M1, M2, T1, T2 y R1 son las mismas hojas en todas las campañas; por eso se puede seguir su trayectoria."),
    ("Punto", "Zona de la hoja donde se apoya la sonda. No es una ubicación fija entre fechas, así que nunca se sigue un punto en el tiempo."),
    ("Índice espectral", "Combinación de reflectancias en bandas concretas que resume un rasgo fisiológico (clorofila, carotenoides, senescencia)."),
    ("Anclas", "Valores de referencia por variedad e índice: la hoja tierna (0) y la hoja con roya (1). Se promedian por fecha y sin hojas-fecha dudosas."),
    ("Similitud con roya", "Mediana, entre índices, de la posición de la hoja entre sus dos anclas (0–100 %). Relativa a los propios datos; no es severidad ni diagnóstico."),
    ("S1 / S2 / U", "Tres variantes de anclas para la similitud en el tiempo: S1 congela el ancla sana en las 2 primeras campañas, S2 además deja fuera la fecha evaluada, U es la de toda la aplicación."),
    ("Δ y Δ*", "Δ: cambio de una hoja desde su primera medición. Δ*: Δ menos el cambio mediano de las hojas tiernas ese día (corrige deriva común y maduración)."),
    ("δ de Cliff", "Tamaño de efecto no paramétrico entre dos grupos (−1 a +1): proporción de pares en que un grupo supera al otro, menos la inversa."),
    ("Holm / FDR", "Correcciones por pruebas múltiples: Holm controla la probabilidad de algún falso positivo; Benjamini–Hochberg (FDR) la proporción esperada de falsos positivos."),
    ("Theil–Sen / Mann–Kendall", "Pendiente robusta (mediana de las pendientes entre pares de fechas) y prueba de tendencia monótona."),
    ("Control de calidad", "Marca una hoja-fecha como atípica (≥ 4 de 7 índices con |z robusto| > 3.5 respecto de su propia serie) o implausible (mNDVI705 fuera de [−0.05; 1.05]). Nunca borra datos."),
    ("Control sin roya", "Canefora y Cuscatleco: variedades sin hoja con roya, que sirven para reconocer cambios por edad o por estación."),
]

tab_met, tab_glo, tab_idx = st.tabs(["Método", "Glosario", "Índices"])

with tab_glo:
    html_table(pd.DataFrame(GLOSARIO, columns=["Término", "Definición"]), strong_cols=("Término",))

with tab_idx:
    section("Índices activos", "Siete índices; los nombres de la aplicación se conservan por continuidad con versiones anteriores.")
    index_sheet_table(DISPLAY_INDICES)
    st.caption(
        "Rn = reflectancia (%) a n nm, tomada del espectro suavizado (valor más cercano dentro de ±5 nm). "
        "Los rangos absolutos de la literatura (satélite, dosel) no son comparables con medición de "
        "contacto a nivel de hoja; por eso la aplicación compara siempre contra referencias propias."
    )

with tab_met:
    texto = (Path(__file__).resolve().parent.parent / "METODOLOGIA.md").read_text(encoding="utf-8")
    cuerpo = texto.split("\n---\n", 1)[-1]
    partes = re.split(r"(?m)^## ", cuerpo)
    secciones = [p for p in partes if p.strip()]
    titulos_completos = [p.splitlines()[0].strip() for p in secciones]
    titulos = [re.sub(r"\s*\(.*\)\s*$", "", t) for t in titulos_completos]
    nav, contenido = st.columns([1, 3.2], gap="large")
    with nav:
        elegido = st.radio("Sección", titulos, label_visibility="collapsed", key="met_sec")
    with contenido:
        k = titulos.index(elegido)
        s = secciones[k]
        st.markdown(f"### {titulos[k]}")
        modulo = re.search(r"\((.*)\)\s*$", titulos_completos[k])
        if modulo:
            st.caption(f"Implementación: {modulo.group(1)}")
        st.markdown("\n".join(s.splitlines()[1:]))
