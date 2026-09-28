"""Helpers de graficos de la pagina 5 (evolucion temporal).

Se sacaron de la pagina para que esta se lea de arriba abajo. Las funciones puras estan a nivel de
modulo; las que dependen del estado de la pagina (eje X elegido, especies susceptibles, puntos)
viven en `TimePlots`, que se construye una vez con ese estado.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import (
    LEAF_NUM_DASH,
    LEAF_TYPE_COLORS,
    LEAF_TYPE_LABELS,
    RUST_RISK_CLASSES,
)

TEXT_MUTED = "#C9CDD3"
GRID = "rgba(255,255,255,0.08)"
SPECIES_ORDER = ["Bourbon", "Pacamara", "Canefora", "Cuscatleco"]
TYPE_ORDER = {"M": 0, "T": 1, "R": 2}


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


def leaf_sort_key(leaf: str):
    return TYPE_ORDER.get(leaf[0], 9), leaf


def leaf_style(leaf: str) -> tuple[str, str]:
    return LEAF_TYPE_COLORS[leaf[0]], LEAF_NUM_DASH.get(int(leaf[1:]), "dot")


def leaf_name(leaf: str) -> str:
    return f"{leaf} · {LEAF_TYPE_LABELS[leaf[0]]}"


def date_color(hex_color: str, t: float) -> str:
    """Rampa de un solo tono: apagado (primera fecha) a brillante (ultima), sobre el fondo oscuro."""
    h = hex_color.lstrip("#")
    c = np.array([int(h[k:k + 2], 16) for k in (0, 2, 4)], float)
    lo = c * 0.35 + np.array([14, 17, 23]) * 0.65
    hi = c * 0.7 + 255 * 0.3
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

    def add_leaf_lines(self, fig, data, ycol, sdcol=None, row=None, col=None, showlegend=True,
                       direct_labels=True, scale=1.0, mark_qc=True):
        """Una linea por hoja: color por tipo, trazo por numero, huecos sin unir."""
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
                    x=g[self.xcol], y=y, mode="lines+markers", name=leaf_name(leaf), legendgroup=leaf,
                    legendrank=rank, showlegend=showlegend, connectgaps=False, error_y=err,
                    line=dict(color=color, width=2, dash=dash),
                    marker=dict(size=8, color=color, line=dict(width=2, color="#0E1117")),
                    customdata=custom,
                    hovertemplate=(
                        f"<b>{leaf}</b> · %{{customdata[0]}} (día %{{customdata[1]}})<br>"
                        "%{y:.4f}<br>n puntos: %{customdata[2]}<extra></extra>"
                    ),
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
                            marker=dict(size=16, symbol="circle-open", color="#FAFAFA", line=dict(width=2)),
                            hoverinfo="skip",
                        ),
                        row=row, col=col,
                    )
            if direct_labels:
                last = g.dropna(subset=[ycol]).tail(1)
                if not last.empty:
                    etiquetas.append([last[self.xcol].iloc[0], float(last[ycol].iloc[0] * scale), leaf])

        if etiquetas:
            # Separa verticalmente las etiquetas finales que caerian encimadas.
            vals = (data[ycol] * scale).dropna()
            gap = 0.06 * ((vals.max() - vals.min()) or 1.0)
            etiquetas.sort(key=lambda e: e[1])
            for i in range(1, len(etiquetas)):
                etiquetas[i][1] = max(etiquetas[i][1], etiquetas[i - 1][1] + gap)
            for x, y, leaf in etiquetas:
                fig.add_annotation(
                    x=x, y=y, text=leaf, showarrow=False, xanchor="left", xshift=9,
                    font=dict(size=11, color=TEXT_MUTED), row=row, col=col,
                )


    def style_time_axis(self, fig, height, **kw):
        fig.update_layout(
            height=height, margin=dict(t=30, b=10, r=40), hovermode="closest",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)), **kw,
        )
        fig.update_xaxes(title_text=self.x_title, gridcolor=GRID, zeroline=False)
        if self.xcol == "campaign_date":
            fig.update_xaxes(tickformat="%d/%m")
        fig.update_yaxes(gridcolor=GRID, zeroline=False)


    def m_panels(self, data, ycol, y_title, sdcol=None, scale=1.0, risk_lines=False, zero_line=False,
                 show_rust=True, rows=1, row=1, fig=None, show_titles=True, pts_col=None, worst_col=None):
        """Bourbon | Pacamara: hojas M en primer plano, rango de hojas T y R1 como referencias tenues."""
        own_fig = fig is None
        if own_fig:
            fig = make_subplots(rows=rows, cols=len(self.SUSCEPTIBLES), shared_yaxes=True,
                                subplot_titles=self.SUSCEPTIBLES if show_titles else None, horizontal_spacing=0.04)
        for j, sp in enumerate(self.SUSCEPTIBLES, start=1):
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
                    x=r[self.xcol], y=r[ycol] * scale, mode="lines+markers", connectgaps=False,
                    name="R1 · con roya (referencia)", legendgroup="rref", legendrank=950, showlegend=leyenda,
                    line=dict(color=rgba(LEAF_TYPE_COLORS["R"], 0.6), width=1.5, dash="dot"),
                    marker=dict(size=5, color=rgba(LEAF_TYPE_COLORS["R"], 0.6)),
                    hovertemplate="R1 · %{x}<br>%{y:.4f}<extra></extra>",
                ), row=row, col=j)
            m = d[d["leaf_type"] == "M"]
            if pts_col is not None:
                pm = self.pts[(self.pts["species"] == sp) & (self.pts["leaf_type"] == "M")]
                for leaf, g in pm.groupby("leaf"):
                    fig.add_trace(go.Scatter(
                        x=g[self.xcol], y=g[pts_col] * scale, mode="markers", name="Puntos individuales (p1–p3)",
                        legendgroup="self.pts", legendrank=800, showlegend=leyenda and leaf == pm["leaf"].min(),
                        marker=dict(size=7, color=rgba(LEAF_TYPE_COLORS["M"], 0.65), symbol="circle",
                                    line=dict(width=1, color="#0E1117")),
                        customdata=g["point"],
                        hovertemplate=f"{leaf} · p%{{customdata}}<br>%{{x}}<br>%{{y:.4f}}<extra></extra>",
                    ), row=row, col=j)
            if worst_col is not None and not m.empty:
                for leaf in sorted(m["leaf"].unique(), key=leaf_sort_key):
                    g = m[m["leaf"] == leaf].sort_values("campaign_date")
                    _, dash = leaf_style(leaf)
                    fig.add_trace(go.Scatter(
                        x=g[self.xcol], y=g[worst_col] * scale, mode="lines+markers", connectgaps=False,
                        name=f"{leaf} · peor punto", legendgroup=f"w{leaf}", legendrank=850, showlegend=leyenda,
                        line=dict(color=rgba(LEAF_TYPE_COLORS["M"], 0.75), width=1, dash=dash),
                        marker=dict(size=8, symbol="diamond-open", color=LEAF_TYPE_COLORS["M"]),
                        hovertemplate=f"{leaf} peor punto<br>%{{x}}<br>%{{y:.4f}}<extra></extra>",
                    ), row=row, col=j)
            if not m.empty:
                self.add_leaf_lines(fig, m, ycol, sdcol=sdcol, row=row, col=j, showlegend=leyenda, scale=scale)
            if zero_line:
                fig.add_hline(y=0, line_width=1, line_color="rgba(200,200,200,0.4)", row=row, col=j)
            if risk_lines:
                for nivel, nombre_clase, _, _ in RUST_RISK_CLASSES:
                    if nivel in (0.0, 1.0):
                        continue
                    etiqueta = nombre_clase if j == 1 else ""
                    fig.add_hline(y=nivel * 100, line_dash="dot", line_width=1, line_color="rgba(180,180,180,0.3)",
                                  annotation_text=etiqueta, annotation_font_size=9,
                                  annotation_font_color=TEXT_MUTED, annotation_position="top left", row=row, col=j)
        if own_fig:
            self.style_time_axis(fig, 500)
            fig.update_layout(margin=dict(t=85), legend=dict(y=1.09))
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
