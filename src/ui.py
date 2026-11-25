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

# Tinta y superficies (tema claro de .streamlit/config.toml; fondo blanco desde 2026-11-16).
INK = "#1F201E"
INK_2 = "#3F403C"
INK_MUTED = "#6B6A64"
GRID = "#ECEBE7"
AXIS = "#BDBCB5"
SURFACE = "#F6F6F3"
BORDER = "#E2E1DC"
BG = "#FFFFFF"

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
        hoverlabel=dict(bgcolor=BG, bordercolor=AXIS, font=dict(family="IBM Plex Sans", size=12, color=INK)),
        margin=dict(l=10, r=16, t=36, b=10),
        title=dict(font=dict(size=13, color=INK), x=0, xanchor="left", y=0.98),
        coloraxis=dict(colorbar=dict(outlinewidth=0, thickness=10, tickfont=dict(size=11, color=INK_MUTED))),
    )
)
# Se combina una sola vez y se registra ya combinada: con la cadena "plotly_white+reflec" como
# predeterminada, Plotly vuelve a combinar y validar ambas plantillas en cada `go.Figure` (~32 ms
# por figura; ~0,9 s por recarga de *Evolucion temporal*). El resultado es identico.
pio.templates["reflec_full"] = pio.templates.merge_templates("plotly_white", "reflec")
pio.templates.default = "reflec_full"

PLOT_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
    "toImageButtonOptions": {"format": "png", "scale": 3},
}


def defer_layout_items(fig, shapes=(), annotations=()):
    """Acumula formas y anotaciones para agregarlas a la figura de una sola vez (en `chart`).

    Plotly revalida *todas* las formas/anotaciones existentes cada vez que se agrega una o se
    reasigna la lista: en una grilla de 14 paneles, agregarlas panel por panel costaba ~8 s por
    recarga. Los helpers de graficos acumulan aqui y `chart()` (o `flush_layout_items`) aplica.
    """
    pend = getattr(fig, "_rf_pending", None)
    if pend is None:
        pend = {"shapes": [], "annotations": []}
        fig._rf_pending = pend  # plotly admite atributos privados (con guion bajo) en la figura
    pend["shapes"].extend(shapes)
    pend["annotations"].extend(annotations)


def flush_layout_items(fig):
    """Agrega a la figura lo acumulado con `defer_layout_items` (una sola validacion)."""
    pend = getattr(fig, "_rf_pending", None)
    if pend and (pend["shapes"] or pend["annotations"]):
        fig.update_layout(shapes=list(fig.layout.shapes) + pend["shapes"],
                          annotations=list(fig.layout.annotations) + pend["annotations"])
        pend["shapes"], pend["annotations"] = [], []


def chart(fig, height: int | None = None, key: str | None = None):
    """`st.plotly_chart` con la plantilla de la app (no la de Streamlit) y exportacion a PNG x3."""
    flush_layout_items(fig)
    if height is not None:
        fig.update_layout(height=height)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch", theme=None, config=PLOT_CONFIG, key=key)


def _subplot_axes(fig) -> list[tuple[str, str]]:
    """Pares (x, y) de cada subgrafico, p. ej. [('x', 'y'), ('x2', 'y2'), ...]."""
    pares = []
    for clave in fig.layout:
        if clave.startswith("xaxis"):
            x = "x" + clave[len("xaxis"):]
            ancla = fig.layout[clave].anchor
            pares.append((x, ancla if ancla and ancla != "free" else "y" + clave[len("xaxis"):]))
    return pares or [("x", "y")]


def subplot_refs(fig, row, col) -> tuple[str, str]:
    """Referencias ('x2', 'y2') del subgrafico (row, col) de `make_subplots`; ('x', 'y') sin subgraficos."""
    if row is None or col is None:
        return "x", "y"
    ref = fig._grid_ref[row - 1][col - 1][0]  # noqa: SLF001 (no hay API publica equivalente)
    x_key, y_key = ref.layout_keys
    return x_key.replace("axis", ""), y_key.replace("axis", "")


def add_vlines(fig, xs, color: str, width: float = 1, dash: str | None = None):
    """Lineas verticales en todos los subgraficos, agregadas en una sola operacion.

    `fig.add_vline` agrega las formas de a una y Plotly revalida todas las anteriores en cada
    llamada: con subgraficos y una docena de bandas tardaba ~8 s por recarga de pagina.
    """
    nuevas = [dict(type="line", xref=x, yref=f"{y} domain", x0=w, x1=w, y0=0, y1=1, layer="below",
                   line=dict(color=color, width=width, dash=dash))
              for x, y in _subplot_axes(fig) for w in xs]
    defer_layout_items(fig, shapes=nuevas)


def add_hlines_all(fig, y: float, color: str = "rgba(40,40,35,0.35)", width: float = 1):
    """Linea horizontal en `y` en todos los subgraficos, en una sola operacion (ver `add_vlines`)."""
    nuevas = [dict(type="line", xref=f"{x} domain", yref=yy, x0=0, x1=1, y0=y, y1=y, layer="below",
                   line=dict(color=color, width=width))
              for x, yy in _subplot_axes(fig)]
    defer_layout_items(fig, shapes=nuevas)


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


# Escala secuencial de similitud (un solo tono, claro = bajo, se funde con el fondo blanco).
SIMILARITY_SCALE = [
    [0.0, "#F7F4F0"], [0.2, "#F5DCCB"], [0.45, "#EBA37E"], [0.7, "#D2622E"], [1.0, "#9A3A12"],
]
# Divergente para efectos con signo: azul (negativo) - gris claro - rojo (positivo).
DIVERGING_SCALE = [[0.0, "#2F6DB5"], [0.5, "#EFEFEC"], [1.0, "#C8402F"]]



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
  background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 6px; padding: .8rem 1rem .7rem;
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

.rf-card {{ border: 1px solid {BORDER}; border-radius: 6px; padding: .9rem 1rem; background: {SURFACE}; height: 100%; }}
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
  background: {INK} !important; border-color: {INK} !important; color: {BG} !important; }}
button[aria-pressed="true"] p, button[aria-checked="true"] p {{
  color: {BG} !important; font-weight: 500; }}
button[aria-pressed="false"] p {{ color: {INK_MUTED}; }}
</style>
"""

NOTE_KINDS = {
    "leer": ("Cómo leer", "#1F5FAD"),
    "limite": ("Limitación", "#946200"),
    "metodo": ("Método", "#6B6A64"),
    "aviso": ("Atención", "#B83227"),
    "hallazgo": ("Hallazgo", "#1D7A57"),
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


def keep_widget_state(keys=(), prefixes=()):
    """Conserva el valor de controles que no se dibujan en esta recarga (pestañas perezosas).

    Streamlit borra el estado de un control que no se dibuja en una recarga; con pestañas que solo
    dibujan la abierta, eso reiniciaba los controles de las demás al cambiar de pestaña. Reasignar
    la clave al principio de la página la conserva (patrón documentado por Streamlit). Llamar
    antes de crear cualquier control.
    """
    for k in list(st.session_state.keys()):
        if k in keys or any(k.startswith(p) for p in prefixes):
            st.session_state[k] = st.session_state[k]


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
