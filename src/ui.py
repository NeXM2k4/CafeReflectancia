"""Sistema visual compartido: encabezados, notas, leyendas, filtros comunes y plantilla de graficos.

Toda la app pasa por aqui para que una misma cosa se vea igual en todas las vistas. Colores con
significado (tipo de hoja, especie) viven en `src.config`; aqui solo se usan.
"""

from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from src.config import INDEX_SHEET, LEAF_TYPE_COLORS, LEAF_TYPE_HELP, LEAF_TYPE_LABELS

APP_TITLE = "Reflectancia foliar y roya del café"
APP_SHORT = "Reflectancia · Roya"

# Tinta y superficies (tema oscuro de .streamlit/config.toml).
INK = "#ECEBE6"
INK_2 = "#C3C2B7"
INK_MUTED = "#8E8C85"
GRID = "#262725"
AXIS = "#3A3B38"
SURFACE = "#1B1C1B"

# Orden fijo de tipos de hoja en toda la app: por edad/estado, nunca alfabetico.
LEAF_ORDER = ["T", "M", "V", "R"]


def leaf_sort(codes) -> list:
    return sorted(codes, key=lambda c: LEAF_ORDER.index(c) if c in LEAF_ORDER else 99)


# --------------------------------------------------------------------------------------------
# Plantilla Plotly
# --------------------------------------------------------------------------------------------
_axis = dict(
    gridcolor=GRID, gridwidth=1, linecolor=AXIS, linewidth=1, zeroline=False,
    ticks="outside", tickcolor=AXIS, ticklen=4, tickfont=dict(size=11, color=INK_MUTED),
    title=dict(font=dict(size=12, color=INK_2), standoff=10), automargin=True,
)
pio.templates["reflec"] = go.layout.Template(
    layout=dict(
        font=dict(family="IBM Plex Sans, system-ui, sans-serif", size=12, color=INK_2),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=["#3987E5", "#D95926", "#199E70", "#C98500", "#D55181", "#008300", "#9085E9", "#E66767"],
        xaxis=_axis, yaxis=_axis,
        legend=dict(font=dict(size=11, color=INK_2), bgcolor="rgba(0,0,0,0)", itemsizing="constant",
                    orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
        hoverlabel=dict(bgcolor="#222322", bordercolor=AXIS, font=dict(family="IBM Plex Sans", size=12, color=INK)),
        margin=dict(l=10, r=16, t=36, b=10),
        title=dict(font=dict(size=13, color=INK), x=0, xanchor="left", y=0.98),
        coloraxis=dict(colorbar=dict(outlinewidth=0, thickness=10, tickfont=dict(size=11, color=INK_MUTED))),
    )
)
pio.templates.default = "plotly_dark+reflec"

PLOT_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
    "toImageButtonOptions": {"format": "png", "scale": 3},
}


def chart(fig, height: int | None = None, key: str | None = None):
    """`st.plotly_chart` con la plantilla de la app (no la de Streamlit) y exportacion a PNG x3."""
    if height is not None:
        fig.update_layout(height=height)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch", theme=None, config=PLOT_CONFIG, key=key)


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


# Escala secuencial de similitud (un solo tono, oscuro = bajo, se funde con el fondo).
SIMILARITY_SCALE = [
    [0.0, "#1E2020"], [0.2, "#3A2B24"], [0.45, "#7A3E25"], [0.7, "#C25424"], [1.0, "#F08A5D"],
]
# Divergente para efectos con signo: azul (negativo) - gris - rojo (positivo).
DIVERGING_SCALE = [[0.0, "#3987E5"], [0.5, "#383835"], [1.0, "#E66767"]]


# --------------------------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------------------------
_CSS = f"""
<style>
.block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1320px; }}
section[data-testid="stSidebar"] .block-container {{ padding-top: 1rem; }}
[data-testid="stSidebarNav"] {{ padding-top: .25rem; }}
h1, h2, h3 {{ letter-spacing: -0.005em; }}
hr {{ margin: 1.4rem 0 1rem 0 !important; border-color: {GRID} !important; }}

div[data-testid="stMetric"] {{
  background: {SURFACE}; border: 1px solid #2A2B29; border-radius: 6px; padding: .8rem 1rem .7rem;
}}
div[data-testid="stMetricLabel"] p {{ color: {INK_MUTED}; font-size: .78rem; text-transform: uppercase; letter-spacing: .04em; }}
div[data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; }}

.rf-kicker {{ font-size: .72rem; font-weight: 600; letter-spacing: .09em; text-transform: uppercase;
  color: {INK_MUTED}; margin-bottom: .25rem; }}
.rf-title {{ font-size: 1.85rem; font-weight: 600; color: {INK}; line-height: 1.2; margin: 0 0 .45rem 0; }}
.rf-lede {{ font-size: 1rem; color: {INK_2}; max-width: 62rem; line-height: 1.55; margin: 0; }}
.rf-header {{ padding-bottom: 1.1rem; margin-bottom: 1.2rem; border-bottom: 1px solid {GRID}; }}

.rf-section {{ margin: 1.6rem 0 .6rem 0; }}
.rf-section h3 {{ font-size: 1.15rem; font-weight: 600; color: {INK}; margin: 0 0 .2rem 0; }}
.rf-section p {{ color: {INK_MUTED}; font-size: .9rem; margin: 0; max-width: 62rem; line-height: 1.5; }}

.rf-note {{ border-left: 2px solid var(--c); background: {SURFACE}; padding: .65rem .9rem;
  border-radius: 0 6px 6px 0; margin: .35rem 0 .8rem 0; font-size: .9rem; line-height: 1.5; color: {INK_2}; }}
.rf-note b.rf-note-k {{ color: var(--c); font-weight: 600; font-size: .72rem; letter-spacing: .07em;
  text-transform: uppercase; display: block; margin-bottom: .15rem; }}
.rf-note p {{ margin: 0; }}

.rf-legend {{ display: flex; flex-wrap: wrap; gap: .4rem 1.4rem; margin: .1rem 0 .6rem 0; }}
.rf-legend span {{ display: inline-flex; align-items: center; gap: .45rem; font-size: .86rem; color: {INK_2}; }}
.rf-legend i {{ width: 10px; height: 10px; border-radius: 2px; display: inline-block; background: var(--c); }}

.rf-kv {{ display: grid; grid-template-columns: max-content 1fr; gap: .25rem 1.2rem; font-size: .88rem; }}
.rf-kv dt {{ color: {INK_MUTED}; }} .rf-kv dd {{ margin: 0; color: {INK_2}; }}

.rf-foot {{ font-size: .76rem; color: {INK_MUTED}; line-height: 1.55; border-top: 1px solid {GRID};
  padding-top: .7rem; margin-top: 1rem; }}
.rf-foot b {{ color: {INK_2}; font-weight: 500; }}

.rf-card {{ border: 1px solid #2A2B29; border-radius: 6px; padding: .9rem 1rem; background: {SURFACE}; height: 100%; }}
.rf-card-k {{ font-size: .7rem; letter-spacing: .08em; text-transform: uppercase; color: {INK_MUTED}; }}
.rf-card-t {{ font-size: 1rem; font-weight: 600; color: {INK}; margin: .15rem 0 .1rem 0; }}
.rf-card .rf-card-k {{ font-size: .7rem; letter-spacing: .08em; text-transform: uppercase; color: {INK_MUTED}; }}
.rf-card .rf-card-t {{ font-size: 1rem; font-weight: 600; color: {INK}; margin: .15rem 0 .3rem 0; }}
.rf-card .rf-card-b {{ font-size: .87rem; color: {INK_2}; line-height: 1.5; }}

table.rf-table {{ width: 100%; border-collapse: collapse; font-size: .87rem; }}
table.rf-table th {{ text-align: left; font-weight: 500; color: {INK_MUTED}; font-size: .74rem;
  letter-spacing: .05em; text-transform: uppercase; padding: .45rem .6rem; border-bottom: 1px solid {AXIS}; }}
table.rf-table td {{ padding: .45rem .6rem; border-bottom: 1px solid {GRID}; color: {INK_2}; vertical-align: top; }}
table.rf-table td.num, table.rf-table th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
table.rf-table td.mono {{ font-family: 'IBM Plex Mono', monospace; font-size: .82rem; color: {INK}; }}
table.rf-table tr:last-child td {{ border-bottom: none; }}
table.rf-table td.strong {{ color: {INK}; font-weight: 500; }}
.rf-scroll {{ overflow-x: auto; }}

div[data-testid="stExpander"] details summary p {{ font-size: .92rem; }}
button[aria-pressed="true"], button[aria-checked="true"] {{
  background: {INK} !important; border-color: {INK} !important; color: #111211 !important; }}
button[aria-pressed="true"] p, button[aria-checked="true"] p {{
  color: #111211 !important; font-weight: 500; }}
button[aria-pressed="false"] p {{ color: {INK_MUTED}; }}
</style>
"""

NOTE_KINDS = {
    "leer": ("Cómo leer", "#8FB8E8"),
    "limite": ("Limitación", "#D9A441"),
    "metodo": ("Método", "#9A9890"),
    "aviso": ("Atención", "#E66767"),
    "hallazgo": ("Hallazgo", "#4FB88F"),
}


def inject_base_css():
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(kicker: str, title: str, lede: str | None = None):
    """Encabezado de vista: seccion, pregunta que responde y una linea de contexto."""
    inject_base_css()
    lede_html = f'<p class="rf-lede">{lede}</p>' if lede else ""
    st.markdown(
        f'<div class="rf-header"><div class="rf-kicker">{kicker}</div>'
        f'<div class="rf-title">{title}</div>{lede_html}</div>',
        unsafe_allow_html=True,
    )


def render_header(subtitle: str = None):
    """Compatibilidad con vistas antiguas: encabezado simple."""
    page_header(APP_SHORT, subtitle or APP_TITLE)


def section(title: str, desc: str | None = None):
    desc_html = f"<p>{desc}</p>" if desc else ""
    st.markdown(f'<div class="rf-section"><h3>{title}</h3>{desc_html}</div>', unsafe_allow_html=True)


def note(kind: str, body: str):
    """Nota tipificada. `body` admite **negrita** y `codigo` de Markdown sencillo."""
    label, color = NOTE_KINDS[kind]
    st.markdown(
        f'<div class="rf-note" style="--c:{color}"><b class="rf-note-k">{label}</b><p>{_md_inline(body)}</p></div>',
        unsafe_allow_html=True,
    )


def _md_inline(text: str) -> str:
    import re
    t = html.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


def leaf_legend(codes, with_help: bool = False):
    """Leyenda compacta de tipos de hoja presentes, en el orden de la app."""
    items = []
    for c in leaf_sort(codes):
        tip = f' title="{html.escape(LEAF_TYPE_HELP.get(c, ""))}"'
        items.append(f'<span{tip}><i style="--c:{LEAF_TYPE_COLORS[c]}"></i>{LEAF_TYPE_LABELS[c]}</span>')
    st.markdown(f'<div class="rf-legend">{"".join(items)}</div>', unsafe_allow_html=True)
    if with_help:
        st.caption(" · ".join(f"**{LEAF_TYPE_LABELS[c]}**: {LEAF_TYPE_HELP[c]}" for c in leaf_sort(codes)))


def html_table(df: pd.DataFrame, num_cols=(), mono_cols=(), strong_cols=(), index: bool = False):
    """Tabla estatica sobria para tablas chicas de lectura (no reemplaza st.dataframe)."""
    d = df.reset_index() if index else df
    head = "".join(f'<th class="{"num" if c in num_cols else ""}">{html.escape(str(c))}</th>' for c in d.columns)
    rows = []
    for _, r in d.iterrows():
        cells = []
        for c in d.columns:
            v = r[c]
            cls = " ".join(k for k, cols in (("num", num_cols), ("mono", mono_cols), ("strong", strong_cols)) if c in cols)
            txt = "—" if (v is None or (isinstance(v, float) and pd.isna(v))) else str(v)
            cells.append(f'<td class="{cls}">{txt}</td>')
        rows.append(f"<tr>{''.join(cells)}</tr>")
    st.markdown(
        f'<div class="rf-scroll"><table class="rf-table"><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def card(kicker: str, title: str, body: str):
    st.markdown(
        f'<div class="rf-card"><div class="rf-card-k">{kicker}</div><div class="rf-card-t">{title}</div>'
        f'<div class="rf-card-b">{body}</div></div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------------------------
# Filtros comunes
# --------------------------------------------------------------------------------------------
def campaign_range(df: pd.DataFrame, key: str, label: str = "Campañas") -> list:
    """Rango de campañas (desde / hasta) en vez de una lista de 12 fechas. Devuelve los ids."""
    from src.parser import campaign_options, sorted_campaigns

    ids = sorted_campaigns(df)
    if not ids:
        return []
    etiquetas = campaign_options(df)
    corto = {cid: etiquetas[cid][:5] for cid in ids}
    if len(ids) == 1:
        st.caption(f"{label}: {etiquetas[ids[0]]}")
        return ids
    desde, hasta = st.select_slider(
        label, options=ids, value=(ids[0], ids[-1]), format_func=corto.get, key=key,
        help="Rango de fechas de campaña incluido en esta vista (ambos extremos incluidos).",
    )
    i, j = ids.index(desde), ids.index(hasta)
    sel = ids[i:j + 1]
    st.caption(f"{len(sel)} de {len(ids)} campañas · {etiquetas[desde]} a {etiquetas[hasta]}")
    return sel


def sidebar_footer(df: pd.DataFrame):
    """Pie de la barra lateral: que datos esta viendo la app."""
    if df is None or df.empty:
        return
    fechas = pd.to_datetime(df["campaign_date"].dropna())
    st.sidebar.markdown(
        f'<div class="rf-foot"><b>{len(df):,}</b> espectros · <b>{df["campaign_id"].nunique()}</b> campañas<br>'
        f'{fechas.min():%d/%m/%Y} a {fechas.max():%d/%m/%Y}<br>'
        f'Solo p1–p3 en índices y similitud. Método en <b>Método y glosario</b>.</div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------------------------
# Tablas
# --------------------------------------------------------------------------------------------
def index_column_config(indices, decimals: int = 3):
    fmt = f"%.{decimals}f"
    return {name: st.column_config.NumberColumn(name, format=fmt) for name in indices}


def numeric_column_config(df: pd.DataFrame, decimals: int = 4, exclude: tuple = ()):
    fmt = f"%.{decimals}f"
    return {
        col: st.column_config.NumberColumn(str(col), format=fmt)
        for col in df.columns
        if col not in exclude and pd.api.types.is_float_dtype(df[col])
    }


def index_sheet_table(indices):
    """Ficha de indices: nombre en la app, nombre estandar, formula, que mide y referencia."""
    filas = []
    for i in indices:
        std, formula, mide, ref = INDEX_SHEET[i]
        filas.append({"Índice": i, "Nombre estándar": std, "Fórmula": formula, "Qué mide": mide, "Referencia": ref})
    html_table(pd.DataFrame(filas), mono_cols=("Fórmula",), strong_cols=("Índice",))


def render_index_legend(index_definitions=None, expanded: bool = False):
    from src.indices import DISPLAY_INDICES

    with st.expander("Ficha de los índices espectrales", expanded=expanded):
        index_sheet_table(DISPLAY_INDICES)
        st.caption("R*n* = reflectancia (%) a *n* nm tras el suavizado Savitzky–Golay. FSR se retiró: "
                   "usa las mismas bandas que NDVI y da el mismo valor.")


def render_styled_pivot(df: pd.DataFrame, decimals: int = 0):
    """Tabla de conteos: enteros alineados, ceros atenuados."""
    d = df.copy()
    d.index.name = None
    d.columns.name = None
    fmt = lambda v: "" if pd.isna(v) else (f'<span style="color:{INK_MUTED}">0</span>' if v == 0 else f"{v:,.{decimals}f}")
    out = d.map(fmt) if hasattr(d, "map") else d.applymap(fmt)
    out.insert(0, "", d.index)
    html_table(out, num_cols=tuple(out.columns[1:]), strong_cols=("",))
