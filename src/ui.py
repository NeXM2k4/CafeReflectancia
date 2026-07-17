"""Componentes de UI compartidos entre las 4 paginas: header, estilos globales y helpers de presentacion."""

import pandas as pd
import streamlit as st

APP_TITLE = "Analisis de Reflectancia Foliar - Cafe"
APP_SUBTITLE = "Bourbon · Canefora · Cuscatleco · Pacamara — deteccion de roya por espectroscopia"
LOGO_EMOJI = "🍃"

# Color de "tag" por tipo de filtro, consistente en las 4 paginas.
FILTER_TAG_COLORS = {
    "Especie": "#199E70",
    "Campana": "#3987E5",
    "Especies": "#3987E5",
    "Estado sanitario": "#D03B3B",
    "Susceptibilidad": "#C98500",
    "Madurez de hoja": "#9085E9",
    "Punto": "#7A7E85",
    "Agrupar / comparar por": "#199E70",
}


def inject_base_css():
    """CSS global: densidad de espacio, tarjetas de metricas y tags de filtro. No afecta logica."""
    st.markdown(
        """
        <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        section[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
        div[data-testid="stVerticalBlock"] { gap: 0.55rem; }
        hr { margin: 0.5rem 0 !important; }
        h2, h3 { margin-top: 0.3rem !important; margin-bottom: 0.3rem !important; }

        div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.35);
            padding: 0.75rem 1rem 0.6rem 1rem;
        }

        .app-header { display:flex; align-items:center; gap:0.65rem; margin-bottom:0.3rem; }
        .app-header .logo { font-size: 2.1rem; line-height:1; }
        .app-header .titles { display:flex; flex-direction:column; }
        .app-header .titles .title { font-size:1.4rem; font-weight:700; margin:0; color:#FAFAFA; }
        .app-header .titles .subtitle { font-size:0.82rem; color:#9CA3AF; margin:0; }

        .filter-tag {
            display:inline-block; font-size:0.65rem; font-weight:700; letter-spacing:0.03em;
            text-transform:uppercase; padding:1px 9px; border-radius:999px; margin-bottom:3px;
            color:#0E1117; background:var(--tag-color, #199E70);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(subtitle: str = None):
    """Header reutilizable (logo + titulo + subtitulo), identico en las 4 paginas."""
    sub = subtitle or APP_SUBTITLE
    st.markdown(
        f"""
        <div class="app-header">
            <div class="logo">{LOGO_EMOJI}</div>
            <div class="titles">
                <p class="title">{APP_TITLE}</p>
                <p class="subtitle">{sub}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def filter_tag(label: str):
    """Badge de color por tipo de filtro, para usar antes de cada widget en el sidebar."""
    color = FILTER_TAG_COLORS.get(label, "#199E70")
    st.markdown(
        f'<span class="filter-tag" style="--tag-color:{color}">{label}</span>',
        unsafe_allow_html=True,
    )


def index_column_config(indices, decimals: int = 3):
    """Column config de st.dataframe para mostrar decimales consistentes en columnas de indices."""
    fmt = f"%.{decimals}f"
    return {name: st.column_config.NumberColumn(name, format=fmt) for name in indices}


def numeric_column_config(df: pd.DataFrame, decimals: int = 4, exclude: tuple = ()):
    """Column config que fija el mismo numero de decimales para cada columna numerica (float)
    de un DataFrame, dejando enteros/booleanos/texto sin tocar. Util para tablas de estadistica
    (summary, Shapiro, post-hoc) donde las columnas varian segun el resultado."""
    fmt = f"%.{decimals}f"
    return {
        col: st.column_config.NumberColumn(str(col), format=fmt)
        for col in df.columns
        if col not in exclude and pd.api.types.is_float_dtype(df[col])
    }


def render_index_legend(index_definitions: dict, expanded: bool = False):
    """Leyenda breve de que mide cada indice espectral."""
    with st.expander("ℹ️ Que mide cada indice", expanded=expanded):
        for name, desc in index_definitions.items():
            st.markdown(f"**{name}** — {desc}")


def render_styled_pivot(df: pd.DataFrame, decimals: int = 0):
    """Tabla pivote pequeña (HTML estatico) con encabezado diferenciado y numeros alineados
    a la derecha. Usa pandas Styler en vez de st.dataframe porque esta ultima se dibuja en un
    canvas y no admite CSS por celda; solo apta para tablas chicas (no reemplaza st.dataframe
    en tablas grandes con miles de filas)."""
    fmt = f"{{:.{decimals}f}}"
    styler = (
        df.style.format(fmt)
        .set_table_styles(
            [
                {
                    "selector": "thead th.col_heading",
                    "props": [
                        ("background-color", "#1C2128"),
                        ("color", "#9CA3AF"),
                        ("text-transform", "uppercase"),
                        ("font-size", "0.72rem"),
                        ("letter-spacing", "0.03em"),
                        ("text-align", "right"),
                        ("padding", "6px 12px"),
                        ("border-bottom", "2px solid #199E70"),
                    ],
                },
                {
                    "selector": "thead th.blank",
                    "props": [
                        ("background-color", "#1C2128"),
                        ("border-bottom", "2px solid #199E70"),
                    ],
                },
                {
                    "selector": "tbody th.row_heading",
                    "props": [
                        ("text-align", "left"),
                        ("padding", "4px 12px"),
                        ("color", "#FAFAFA"),
                        ("font-weight", "600"),
                        ("border-bottom", "1px solid rgba(255,255,255,0.06)"),
                    ],
                },
                {
                    "selector": "td",
                    "props": [
                        ("text-align", "right"),
                        ("padding", "4px 12px"),
                        ("font-variant-numeric", "tabular-nums"),
                        ("border-bottom", "1px solid rgba(255,255,255,0.06)"),
                    ],
                },
                {"selector": "table", "props": [("width", "100%"), ("border-collapse", "collapse")]},
            ]
        )
    )
    st.markdown(styler.to_html(), unsafe_allow_html=True)
