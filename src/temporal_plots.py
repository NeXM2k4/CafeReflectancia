"""Helpers de graficos de la pagina 5 (evolucion temporal).

Se sacaron de la pagina para que esta se lea de arriba abajo. Las funciones puras estan a nivel de
modulo; las que dependen del estado de la pagina (eje X elegido, especies susceptibles, puntos)
viven en `TimePlots`, que se construye una vez con ese estado.
"""

import re
import warnings

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from statsmodels.nonparametric.smoothers_lowess import lowess

from src.config import (
    LEAF_NUM_DASH,
    LEAF_NUM_SYMBOL,
    LEAF_TYPE_COLORS,
    LEAF_TYPE_LABELS,
    RUST_RISK_CLASSES,
    TEMPORAL_MIN_FECHAS_TENDENCIA,
)
from src.config import SPECIES_ORDER as CONFIG_SPECIES_ORDER
from src.stats_utils import stars
from src.ui import defer_layout_items, subplot_refs

# Tendencia suavizada (descriptiva): LOWESS local lineal sobre los mismos valores graficados.
# frac = 2/3 es el valor clasico de Cleveland (1979); 3 iteraciones robustas atenuan un dia
# atipico sin borrarlo. Ver docs/plan_fondo_blanco_tendencias_rendimiento.md.
LOWESS_FRAC = 2 / 3
LOWESS_IT = 3
LOWESS_PUNTOS = 60

TEXT_MUTED = "#6B6A64"
GRID = "#ECEBE7"
BG = "#FFFFFF"
SPECIES_ORDER = CONFIG_SPECIES_ORDER  # fuente unica en config.py (incluye Pacamara no susceptible)
TYPE_ORDER = {"M": 0, "T": 1, "R": 2, "V": 3}


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


def lowess_curve(dias: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    """Curva LOWESS sobre una grilla de dias entre la primera y la ultima medicion.

    Devuelve None con menos de `TEMPORAL_MIN_FECHAS_TENDENCIA` fechas validas: el mismo minimo
    que los tests de tendencia, para no dibujar una tendencia que no se evalua.
    """
    dias, y = np.asarray(dias, float), np.asarray(y, float)
    ok = np.isfinite(dias) & np.isfinite(y)
    dias, y = dias[ok], y[ok]
    if len(np.unique(dias)) < TEMPORAL_MIN_FECHAS_TENDENCIA:
        return None
    grilla = np.linspace(dias.min(), dias.max(), LOWESS_PUNTOS)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        curva = lowess(y, dias, frac=LOWESS_FRAC, it=LOWESS_IT, xvals=grilla)
        if not np.all(np.isfinite(curva)):
            # Con pocas fechas las iteraciones robustas pueden anular todos los pesos de una
            # ventana; en ese caso se usa el ajuste sin iteraciones.
            curva = lowess(y, dias, frac=LOWESS_FRAC, it=0, xvals=grilla)
    if not np.all(np.isfinite(curva)):
        return None
    return grilla, curva


TREND_CAPTION = (
    "Puntos: una hoja-fecha (media de p1–p3), sin unir. Línea: tendencia suavizada (LOWESS, descriptiva; "
    f"solo con {TEMPORAL_MIN_FECHAS_TENDENCIA} fechas o más). Al final de cada línea, la significancia de la "
    "tendencia: Mann–Kendall con corrección de Benjamini–Hochberg sobre todas las variedades y hojas a la "
    r"vez (mismo p FDR de la tabla de tendencias): \*\*\* p < 0.001 · \*\* p < 0.01 · \* p < 0.05 · ns no "
    "significativa. Las mediciones sucesivas de una hoja no son independientes: el p es optimista."
)


def leaf_sort_key(leaf: str):
    return TYPE_ORDER.get(leaf[0], 9), leaf


def _leaf_num(leaf: str) -> int | None:
    """Numero de hoja de una etiqueta ("M1" -> 1; "T2-NS" -> 2, sufijo de Pacamara no susceptible)."""
    m = re.match(r"^[A-Za-z](\d+)", leaf)
    return int(m.group(1)) if m else None


def leaf_style(leaf: str) -> tuple[str, str]:
    return LEAF_TYPE_COLORS[leaf[0]], LEAF_NUM_DASH.get(_leaf_num(leaf), "dot")


def leaf_symbol(leaf: str) -> str:
    return LEAF_NUM_SYMBOL.get(_leaf_num(leaf), "diamond")


def leaf_name(leaf: str) -> str:
    return f"{leaf} · {LEAF_TYPE_LABELS[leaf[0]]}"


def date_color(hex_color: str, t: float) -> str:
    """Rampa de un solo tono: claro (primera fecha) a oscuro (ultima), sobre el fondo blanco."""
    h = hex_color.lstrip("#")
    c = np.array([int(h[k:k + 2], 16) for k in (0, 2, 4)], float)
    lo = c * 0.35 + 255 * 0.65
    hi = c * 0.75
    r, g, b = (lo + (hi - lo) * float(np.clip(t, 0, 1))).round().astype(int)
    return f"rgb({r},{g},{b})"


def region_slopes(spec_tr: pd.DataFrame, sel, a: float, z: float) -> pd.Series:
    """Pendiente media de cada hoja del grupo dentro de una region espectral."""
    g = spec_tr[sel(spec_tr) & spec_tr["wavelength"].between(a, z)]
    return g.groupby("leaf_id")["pendiente"].mean()


def region_table(spec_tr: pd.DataFrame, grupos, regiones) -> pd.DataFrame:
    filas = {}
    for nombre, _, _, _, sel in grupos:
        fila = {}
        for reg, (a, z) in regiones.items():
            s = region_slopes(spec_tr, sel, a, z)
            fila[reg] = f"{s.median():+.2f}  ({int((s > 0).sum())}/{len(s)} suben)" if len(s) else "—"
        filas[nombre] = fila
    return pd.DataFrame(filas).T



class TimePlots:
    """Graficos de series por hoja que comparten eje X, especies susceptibles y puntos."""

    def __init__(self, xcol, x_title, susceptibles, species_with_rust, pts):
        self.xcol = xcol
        self.x_title = x_title
        self.SUSCEPTIBLES = susceptibles
        self.species_with_rust = species_with_rust
        self.pts = pts

    def _x_from_days(self, g: pd.DataFrame, dias: np.ndarray):
        """Convierte dias (desde el dia 0 del dataset) al eje elegido (fecha o dias)."""
        if self.xcol == "dia":
            return dias
        t0 = g["campaign_date"].iloc[0] - pd.Timedelta(days=float(g["dia"].iloc[0]))
        return t0 + pd.to_timedelta(dias, unit="D")

    def add_leaf_lines(self, fig, data, ycol, sdcol=None, row=None, col=None, showlegend=True,
                       direct_labels=True, scale=1.0, mark_qc=True, trend_q=None, smooth=True, y_span=None):
        """Una serie por hoja: puntos sin unir (color por tipo) y tendencia suavizada (trazo por numero).

        `trend_q` (Serie indexada por `leaf_id` con el p FDR de la tendencia de cada hoja) agrega
        la significancia al final de la linea: ``M1 **``. Las etiquetas se agregan al final, en
        una sola operacion (agregarlas de a una revalida todas las anteriores y es lento).
        `y_span` es el rango del eje del panel (si incluye otras series, como R1 o la banda de T),
        para separar las etiquetas en proporcion a lo que realmente se ve.
        """
        etiquetas = []
        for rank, leaf in enumerate(sorted(data["leaf"].unique(), key=leaf_sort_key)):
            g = data[data["leaf"] == leaf].sort_values("campaign_date")
            color, dash = leaf_style(leaf)
            y = g[ycol] * scale
            err = None
            if sdcol is not None and sdcol in g:
                err = dict(type="data", array=(g[sdcol] * scale).to_numpy(), thickness=1, width=3,
                           color=rgba(color, 0.55), visible=True)
            custom = np.stack([
                g["campaign_date"].dt.strftime("%d/%m/%Y"), g["dia"].fillna(-1).astype(int),
                g["n_puntos"].fillna(0).astype(int),
            ], axis=-1)
            fig.add_trace(
                go.Scatter(
                    x=g[self.xcol], y=y, mode="markers", name=leaf_name(leaf), legendgroup=leaf,
                    legendrank=rank, showlegend=showlegend, error_y=err,
                    marker=dict(size=8, color=color, symbol=leaf_symbol(leaf), line=dict(width=1.5, color=BG)),
                    customdata=custom,
                    hovertemplate=(
                        f"<b>{leaf}</b> · %{{customdata[0]}} (día %{{customdata[1]}})<br>"
                        "%{y:.4f}<br>n puntos: %{customdata[2]}<extra></extra>"
                    ),
                ),
                row=row, col=col,
            )
            curva = lowess_curve(g["dia"].to_numpy(), y.to_numpy()) if smooth else None
            if curva is not None:
                xs = self._x_from_days(g, curva[0])
                fig.add_trace(
                    go.Scatter(
                        x=xs, y=curva[1], mode="lines", name=f"{leaf} · tendencia", legendgroup=leaf,
                        showlegend=False, line=dict(color=color, width=2, dash=dash, shape="spline"),
                        opacity=0.85, hoverinfo="skip",
                    ),
                    row=row, col=col,
                )
            if mark_qc and "qc_atipico" in g:
                q = g[g["qc_atipico"] == True]  # noqa: E712 (columna con NaN en huecos)
                if not q.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=q[self.xcol], y=q[ycol] * scale, mode="markers", name="Atípico (QC)",
                            legendgroup="qc", legendrank=1000,
                            showlegend=showlegend and not any(t.name == "Atípico (QC)" for t in fig.data),
                            marker=dict(size=16, symbol="circle-open", color="#1F201E", line=dict(width=1.5)),
                            hoverinfo="skip",
                        ),
                        row=row, col=col,
                    )

            marca = ""
            if trend_q is not None and "leaf_id" in g and g["leaf_id"].iloc[0] in trend_q.index:
                marca = stars(trend_q.loc[g["leaf_id"].iloc[0]])
            texto = f"{leaf} {marca}".strip() if direct_labels else marca
            if texto:
                if curva is not None:
                    etiquetas.append([self._x_from_days(g, curva[0][-1:])[0], float(curva[1][-1]), texto])
                else:
                    last = g.dropna(subset=[ycol]).tail(1)
                    if not last.empty:
                        etiquetas.append([last[self.xcol].iloc[0], float(last[ycol].iloc[0] * scale), texto])

        if showlegend and not any(t.name == "Tendencia suavizada (LOWESS)" for t in fig.data):
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name="Tendencia suavizada (LOWESS)",
                                     legendgroup="lowess", legendrank=990, line=dict(color=TEXT_MUTED, width=2),
                                     hoverinfo="skip"), row=row, col=col)

        if etiquetas:
            # Separa verticalmente las etiquetas finales que caerian encimadas.
            vals = (data[ycol] * scale).dropna()
            gap = 0.06 * (y_span or (vals.max() - vals.min()) or 1.0)
            etiquetas.sort(key=lambda e: e[1])
            for i in range(1, len(etiquetas)):
                etiquetas[i][1] = max(etiquetas[i][1], etiquetas[i - 1][1] + gap)
            xref, yref = subplot_refs(fig, row, col)
            nuevas = [dict(x=x, y=y, xref=xref, yref=yref, text=t, showarrow=False, xanchor="left", xshift=7,
                           font=dict(size=11, color=TEXT_MUTED)) for x, y, t in etiquetas]
            defer_layout_items(fig, annotations=nuevas)


    def style_time_axis(self, fig, height, **kw):
        fig.update_layout(
            height=height, margin=dict(t=70, b=10, r=60), hovermode="closest",
            legend=dict(orientation="h", yanchor="bottom", y=1.04, x=0, font=dict(size=11)), **kw,
        )
        fig.update_xaxes(title_text=self.x_title, gridcolor=GRID, zeroline=False)
        if self.xcol == "campaign_date":
            fig.update_xaxes(tickformat="%d/%m")
        fig.update_yaxes(gridcolor=GRID, zeroline=False)


    def m_panels(self, data, ycol, y_title, sdcol=None, scale=1.0, risk_lines=False, zero_line=False,
                 show_rust=True, rows=1, row=1, fig=None, show_titles=True, pts_col=None, worst_col=None,
                 trend_q=None):
        """Bourbon | Pacamara: hojas M en primer plano, rango de hojas T y R1 como referencias tenues."""
        own_fig = fig is None
        if own_fig:
            fig = make_subplots(rows=rows, cols=len(self.SUSCEPTIBLES), shared_yaxes=True,
                                subplot_titles=self.SUSCEPTIBLES if show_titles else None, horizontal_spacing=0.04)
        formas, notas = [], []
        for j, sp in enumerate(self.SUSCEPTIBLES, start=1):
            xref, yref = subplot_refs(fig, row, j)
            d = data[data["species"] == sp]
            leyenda = j == 1 and row == 1
            t = (d[(d["leaf_type"] == "T")].dropna(subset=[ycol])
                 .groupby("campaign_date").agg(lo=(ycol, "min"), hi=(ycol, "max"), dia=("dia", "first"))
                 .reset_index())
            if not t.empty:
                xs = t[self.xcol]
                fig.add_trace(go.Scatter(x=xs, y=t["hi"] * scale, mode="lines", line=dict(width=0),
                                         legendgroup="tband", showlegend=False, hoverinfo="skip"), row=row, col=j)
                fig.add_trace(go.Scatter(
                    x=xs, y=t["lo"] * scale, mode="lines", line=dict(width=0), fill="tonexty",
                    fillcolor=rgba(LEAF_TYPE_COLORS["T"], 0.2), name="Rango de hojas T (sanas al inicio)",
                    legendgroup="tband", legendrank=900, showlegend=leyenda, hoverinfo="skip",
                ), row=row, col=j)
            r = d[d["leaf_type"] == "R"].sort_values("campaign_date")
            if show_rust and not r.empty:
                fig.add_trace(go.Scatter(
                    x=r[self.xcol], y=r[ycol] * scale, mode="markers",
                    name="R1 · con roya (referencia)", legendgroup="rref", legendrank=950, showlegend=leyenda,
                    marker=dict(size=6, color=rgba(LEAF_TYPE_COLORS["R"], 0.6)),
                    hovertemplate="R1 · %{x}<br>%{y:.4f}<extra></extra>",
                ), row=row, col=j)
                curva_r = lowess_curve(r["dia"].to_numpy(), (r[ycol] * scale).to_numpy())
                if curva_r is not None:
                    fig.add_trace(go.Scatter(
                        x=self._x_from_days(r, curva_r[0]), y=curva_r[1], mode="lines", legendgroup="rref",
                        showlegend=False, line=dict(color=rgba(LEAF_TYPE_COLORS["R"], 0.55), width=1.5, dash="dot",
                                                    shape="spline"), hoverinfo="skip",
                    ), row=row, col=j)
            m = d[d["leaf_type"] == "M"]
            if pts_col is not None:
                pm = self.pts[(self.pts["species"] == sp) & (self.pts["leaf_type"] == "M")]
                for leaf, g in pm.groupby("leaf"):
                    fig.add_trace(go.Scatter(
                        x=g[self.xcol], y=g[pts_col] * scale, mode="markers", name="Puntos individuales (p1–p3)",
                        legendgroup="self.pts", legendrank=800, showlegend=leyenda and leaf == pm["leaf"].min(),
                        marker=dict(size=7, color=rgba(LEAF_TYPE_COLORS["M"], 0.65), symbol=leaf_symbol(leaf),
                                    line=dict(width=1, color=BG)),
                        customdata=g["point"],
                        hovertemplate=f"{leaf} · p%{{customdata}}<br>%{{x}}<br>%{{y:.4f}}<extra></extra>",
                    ), row=row, col=j)
            if worst_col is not None and not m.empty:
                for leaf in sorted(m["leaf"].unique(), key=leaf_sort_key):
                    g = m[m["leaf"] == leaf].sort_values("campaign_date")
                    fig.add_trace(go.Scatter(
                        x=g[self.xcol], y=g[worst_col] * scale, mode="markers",
                        name=f"{leaf} · peor punto", legendgroup=f"w{leaf}", legendrank=850, showlegend=leyenda,
                        marker=dict(size=8, symbol="diamond-open", color=LEAF_TYPE_COLORS["M"]),
                        hovertemplate=f"{leaf} peor punto<br>%{{x}}<br>%{{y:.4f}}<extra></extra>",
                    ), row=row, col=j)
            if not m.empty:
                # Los paneles de una fila comparten el eje Y: el rango visible es el de todas las variedades.
                vals_panel = (data.loc[data["species"].isin(self.SUSCEPTIBLES), ycol] * scale).dropna()
                self.add_leaf_lines(fig, m, ycol, sdcol=sdcol, row=row, col=j, showlegend=leyenda, scale=scale,
                                    trend_q=trend_q, y_span=float(vals_panel.max() - vals_panel.min()) or None)
            # Lineas horizontales: se juntan y se agregan una sola vez al final (add_hline por
            # subgrafico revalida todas las formas anteriores y con 14 subgraficos tardaba segundos).
            if zero_line:
                formas.append(dict(type="line", xref=f"{xref} domain", yref=yref, x0=0, x1=1, y0=0, y1=0,
                                   line=dict(color="rgba(40,40,35,0.35)", width=1), layer="below"))
            if risk_lines:
                for nivel, nombre_clase, _, _ in RUST_RISK_CLASSES:
                    if nivel in (0.0, 1.0):
                        continue
                    formas.append(dict(type="line", xref=f"{xref} domain", yref=yref, x0=0, x1=1,
                                       y0=nivel * 100, y1=nivel * 100, layer="below",
                                       line=dict(color="rgba(60,60,55,0.3)", width=1, dash="dot")))
                    if j == 1:
                        notas.append(dict(x=0, xref=f"{xref} domain", y=nivel * 100, yref=yref, text=nombre_clase,
                                          showarrow=False, xanchor="left", yanchor="bottom",
                                          font=dict(size=9, color=TEXT_MUTED)))
        defer_layout_items(fig, shapes=formas, annotations=notas)
        if own_fig:
            self.style_time_axis(fig, 540)
            fig.update_layout(margin=dict(t=125), legend=dict(y=1.16))
            fig.update_yaxes(title_text=y_title, col=1)
        return fig


    def m_trend_table(self, trends: pd.DataFrame) -> pd.DataFrame:
        """Tendencias de las hojas M susceptibles, contrastadas con las hojas M de los controles."""
        ev = trends[trends["Tipo"] == "M"]
        ctrl = ev[~ev["Especie"].isin(self.species_with_rust) & (ev["Significativa"] == True)]  # noqa: E712
        filas = []
        for _, r in ev[ev["Especie"].isin(self.SUSCEPTIBLES)].iterrows():
            pend = r.get("Pendiente / semana", np.nan)
            sig = bool(r.get("Significativa", False) is True or r.get("Significativa", False) == True)  # noqa: E712
            iguales = ""
            if pd.isna(r.get("p", np.nan)):
                lectura = f"Sin test ({r.get('Motivo omision') or 'pocas fechas'})"
            else:
                mismos = ctrl[(ctrl["Variable"] == r["Variable"]) & (np.sign(ctrl["Pendiente / semana"]) == np.sign(pend))]
                iguales = ", ".join(mismos["Especie"] + " " + mismos["Hoja"])
                if not sig:
                    lectura = "Sin tendencia"
                elif iguales:
                    lectura = "Compatible con envejecimiento (también en control sin roya)"
                else:
                    lectura = "Candidata: ausente en controles — revisar en campo"
            filas.append({
                "Especie": r["Especie"], "Hoja": r["Hoja"], "Índice": r["Variable"], "n fechas": r["n fechas"],
                "Pendiente / semana": pend, "p FDR": r.get("p FDR", np.nan), "Significativa": sig,
                "Controles M con igual tendencia": iguales, "Lectura": lectura,
            })
        orden = {"Candidata: ausente en controles — revisar en campo": 0,
                 "Compatible con envejecimiento (también en control sin roya)": 1, "Sin tendencia": 2}
        out = pd.DataFrame(filas)
        if out.empty:
            return out
        return out.assign(_o=out["Lectura"].map(orden).fillna(3)).sort_values(["_o", "Especie", "Hoja", "Índice"]).drop(columns="_o")
