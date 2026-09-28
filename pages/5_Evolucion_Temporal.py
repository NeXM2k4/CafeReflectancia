"""Evolucion temporal de cada hoja fisica: indices, severidad relativa, tendencias y espectro animado."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.config import (
    INDEX_DEFINITIONS,
    INDEX_WAVELENGTHS,
    LEAF_NUM_DASH,
    LEAF_TYPE_COLORS,
    LEAF_TYPE_LABELS,
    RUST_RISK_CLASSES,
    TEMPORAL_BASELINE_CAMPAIGNS,
    TEMPORAL_MIN_FECHAS_TENDENCIA,
    TEMPORAL_VALID_POINTS,
)
from src.parser import get_dataset
from src.temporal import (
    DELTA,
    DELTA_STAR,
    DIST_INDICES,
    INDICES,
    PEOR,
    QC_MIN_INDICES,
    SD,
    QC_Z_UMBRAL,
    add_deltas,
    distance_to_rust,
    file_indices,
    leaf_mean_spectra,
    leaf_timeseries,
    leaf_trends,
    index_change_summary,
    point_series,
    qc_flags,
    spectral_trends,
    worst_point,
    severity_anchors,
    severity_timeseries,
    temporal_selection,
    with_gaps,
)
from src.ui import filter_tag, index_column_config, inject_base_css, render_header, render_index_legend

TEXT_MUTED = "#C9CDD3"
GRID = "rgba(255,255,255,0.08)"
SPECIES_ORDER = ["Bourbon", "Pacamara", "Canefora", "Cuscatleco"]
TYPE_ORDER = {"M": 0, "T": 1, "R": 2}

st.set_page_config(page_title="Evolucion Temporal", page_icon="⏳", layout="wide")
inject_base_css()
render_header("Evolución temporal — la misma hoja física a lo largo de las campañas")

df = get_dataset()
if df.empty:
    st.warning("No hay datos en `data/`. Ve a la pagina de inicio.")
    st.stop()

files_all, read_errors = file_indices(df)
if files_all.empty:
    st.warning("No hay archivos validos para el analisis temporal.")
    st.stop()

ts_qc = qc_flags(leaf_timeseries(files_all))
flagged = ts_qc[ts_qc["qc_atipico"]]
species_with_rust = set(files_all.loc[files_all["leaf_type"] == "R", "species"])


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


def _leaf_sort_key(leaf: str):
    return TYPE_ORDER.get(leaf[0], 9), leaf


def _leaf_style(leaf: str) -> tuple[str, str]:
    return LEAF_TYPE_COLORS[leaf[0]], LEAF_NUM_DASH.get(int(leaf[1:]), "dot")


def _leaf_name(leaf: str) -> str:
    return f"{leaf} · {LEAF_TYPE_LABELS[leaf[0]]}"


def _species_label(sp: str) -> str:
    return sp if sp in species_with_rust else f"{sp} (control, sin roya)"


with st.sidebar:
    st.markdown("**Filtros**")
    with st.container(border=True):
        present = [s for s in SPECIES_ORDER if s in set(files_all["species"])]
        filter_tag("Especie")
        species = st.selectbox("Especie", present, format_func=_species_label, label_visibility="collapsed")
        leaves_all = sorted(files_all.loc[files_all["species"] == species, "leaf"].unique(), key=_leaf_sort_key)
        filter_tag("Hoja")
        sel_leaves = st.multiselect("Hojas", leaves_all, default=leaves_all, label_visibility="collapsed")
        filter_tag("Eje temporal")
        x_mode = st.radio(
            "Eje X", ["Fecha", "Días desde la primera campaña"], label_visibility="collapsed"
        )
    with st.container(border=True):
        filter_tag("Control de calidad")
        exclude_qc = st.toggle(
            "Excluir hojas-fecha atípicas",
            value=False,
            help=(
                f"Una hoja-fecha es atípica si {QC_MIN_INDICES} o más de los 7 índices (sin FSR) "
                f"tienen |robust z| > {QC_Z_UMBRAL} respecto de la propia serie de esa hoja. "
                "Excluirlas recalcula todo: series, anclas, tendencias y espectros."
            ),
        )

if not sel_leaves:
    st.info("Selecciona al menos una hoja.")
    st.stop()

if exclude_qc and not flagged.empty:
    claves_fuera = set(zip(flagged["leaf_id"], flagged["campaign_date"]))
    mask = [(l, d) not in claves_fuera for l, d in zip(files_all["leaf_id"], files_all["campaign_date"])]
    files = files_all[mask]
else:
    files = files_all

ts = add_deltas(leaf_timeseries(files))
ts = ts.merge(
    ts_qc[["leaf_id", "campaign_date", "qc_n_atipicos", "qc_atipico"]],
    on=["leaf_id", "campaign_date"], how="left",
)
T_CERO = ts["campaign_date"].min()
ts_gaps = with_gaps(ts, T_CERO)

sp_ts = ts_gaps[(ts_gaps["species"] == species) & ts_gaps["leaf"].isin(sel_leaves)]
xcol = "campaign_date" if x_mode == "Fecha" else "dia"
x_title = "Fecha de campaña" if x_mode == "Fecha" else f"Días desde {ts['campaign_date'].min():%d/%m/%Y}"

st.caption(
    "Cada hoja (M1, M2, T1, T2, R1) es **la misma hoja física en todas las campañas**. "
    "Los puntos de medición no son ubicaciones fijas, así que la unidad es la hoja: se promedian "
    f"las repeticiones de cada punto y después los puntos (solo p{TEMPORAL_VALID_POINTS[0]}–"
    f"p{TEMPORAL_VALID_POINTS[-1]}). Las barras muestran ±1 SD **entre puntos** (heterogeneidad "
    "de la hoja ese día). Metodología completa en `evoluciontemporal.md`."
)

with st.expander("ℹ️ Cómo leer esta página y qué NO se puede concluir"):
    st.markdown(
        f"""
- **n = 1 hoja con roya por especie.** Todo lo que se ve de R1 describe la trayectoria de *esa*
  hoja, no un efecto de la roya en la población.
- **La fecha de infección no se conoce.** "Día 0" de R1 es su primera medición (15/07), no el
  inicio de la roya.
- **Las hojas envejecen.** T1/T2 eran tiernas el 29/06 y son las mismas hojas 12 semanas después.
  Una tendencia en M o T puede ser maduración, no roya: por eso existen **Δ\\*** y los
  **controles** (Canefora y Cuscatleco, sin roya).
- **Mediciones sucesivas de una misma hoja no son independientes.** Los p-valores de tendencia
  son optimistas; se reporta la autocorrelación de residuos como diagnóstico.
- **Severidad temporal ≠ severidad de la página 4.** Aquí el ancla sana son las hojas T en las
  {TEMPORAL_BASELINE_CAMPAIGNS} primeras campañas y cada fecha pesa igual en el ancla con roya
  (ver sección 7).
- **FSR ≡ NDVI** (mismas bandas): se grafica, pero no entra en tendencias, distancia ni control
  de calidad.
"""
    )

def add_leaf_lines(fig, data, ycol, sdcol=None, row=None, col=None, showlegend=True,
                   direct_labels=True, scale=1.0, mark_qc=True):
    """Una linea por hoja: color por tipo, trazo por numero, huecos sin unir."""
    etiquetas = []
    for rank, leaf in enumerate(sorted(data["leaf"].unique(), key=_leaf_sort_key)):
        g = data[data["leaf"] == leaf].sort_values("campaign_date")
        color, dash = _leaf_style(leaf)
        y = g[ycol] * scale
        err = None
        if sdcol is not None and sdcol in g:
            err = dict(type="data", array=(g[sdcol] * scale).to_numpy(), thickness=1, width=3,
                       color=_rgba(color, 0.55), visible=True)
        custom = np.stack([
            g["campaign_date"].dt.strftime("%d/%m/%Y"), g["dia"].fillna(-1).astype(int),
            g["n_puntos"].fillna(0).astype(int),
        ], axis=-1)
        fig.add_trace(
            go.Scatter(
                x=g[xcol], y=y, mode="lines+markers", name=_leaf_name(leaf), legendgroup=leaf,
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
                        x=q[xcol], y=q[ycol] * scale, mode="markers", name="Atípico (QC)",
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
                etiquetas.append([last[xcol].iloc[0], float(last[ycol].iloc[0] * scale), leaf])

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


def style_time_axis(fig, height, **kw):
    fig.update_layout(
        height=height, margin=dict(t=30, b=10, r=40), hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)), **kw,
    )
    fig.update_xaxes(title_text=x_title, gridcolor=GRID, zeroline=False)
    if xcol == "campaign_date":
        fig.update_xaxes(tickformat="%d/%m")
    fig.update_yaxes(gridcolor=GRID, zeroline=False)


# ---------- calculos compartidos ----------
anchors = severity_anchors(ts)
sev_all = severity_timeseries(files, anchors, clip=True)
ts = ts.merge(worst_point(files, anchors)[["leaf_id", "campaign_date", *[PEOR + i for i in INDICES]]],
              on=["leaf_id", "campaign_date"], how="left")
ts_gaps = with_gaps(ts, T_CERO)
sp_ts = ts_gaps[(ts_gaps["species"] == species) & ts_gaps["leaf"].isin(sel_leaves)]
pts = point_series(files, T_CERO)


def _familia(cols_prefijo: str, nombre: str) -> pd.DataFrame:
    tr = leaf_trends(ts, [cols_prefijo + i for i in DIST_INDICES], nombre)
    if cols_prefijo:
        tr["Variable"] = tr["Variable"].str.replace(cols_prefijo, "", regex=False)
    return tr


FAMILIAS = {
    "Δ* corregido por hojas T": (DELTA_STAR, "Δ*"),
    "Valor (promedio de la hoja)": ("", "valor"),
    "Peor punto (hacia la roya)": (PEOR, "peor punto"),
    "Heterogeneidad (SD entre puntos)": (SD, "SD entre puntos"),
}
FAM_AYUDA = (
    "Δ*: promedio de la hoja menos la deriva de las hojas T ese día (lo más conservador). "
    "Valor: promedio de la hoja. Peor punto: el punto más desplazado hacia la roya ese día (la roya "
    "aparece en manchas y el promedio la diluye). Heterogeneidad: qué tan distintos son los 3 puntos "
    "(una hoja que empieza a enfermarse debería volverse más desigual)."
)
trends_fam = {k: _familia(pref, nombre) for k, (pref, nombre) in FAMILIAS.items()}
trends_star = trends_fam["Δ* corregido por hojas T"]
trends_val = trends_fam["Valor (promedio de la hoja)"]
dist_all = distance_to_rust(files, ts)

spectra_all = leaf_mean_spectra(files[["leaf_id", "campaign_date", "point", "path"]])
spec_tr_raw = spectral_trends(spectra_all, ts, T_CERO, False)
spec_tr_norm = spectral_trends(spectra_all, ts, T_CERO, True)

GRUPOS_ESP = [
    ("T (tierna al inicio), todas las especies", "T", LEAF_TYPE_COLORS["T"], "solid",
     lambda d: d["leaf_type"] == "T"),
    ("M, especies susceptibles", "M susc.", LEAF_TYPE_COLORS["M"], "solid",
     lambda d: (d["leaf_type"] == "M") & d["species"].isin(species_with_rust)),
    ("M, controles sin roya", "M control", "#9AA0A6", "dash",
     lambda d: (d["leaf_type"] == "M") & ~d["species"].isin(species_with_rust)),
    ("R1 (con roya)", "R1", LEAF_TYPE_COLORS["R"], "solid", lambda d: d["leaf_type"] == "R"),
]
REGIONES = {"Azul-verde 450–600": (450, 600), "Rojo 650–690": (650, 690),
            "Borde rojo 700–740": (700, 740), "NIR 760–950": (760, 950)}


def region_slopes(spec_tr: pd.DataFrame, sel, a: float, z: float) -> pd.Series:
    """Pendiente media de cada hoja del grupo dentro de una region espectral."""
    g = spec_tr[sel(spec_tr) & spec_tr["wavelength"].between(a, z)]
    return g.groupby("leaf_id")["pendiente"].mean()


def region_table(spec_tr: pd.DataFrame) -> pd.DataFrame:
    filas = {}
    for nombre, _, _, _, sel in GRUPOS_ESP:
        fila = {}
        for reg, (a, z) in REGIONES.items():
            s = region_slopes(spec_tr, sel, a, z)
            fila[reg] = f"{s.median():+.2f}  ({int((s > 0).sum())}/{len(s)} suben)" if len(s) else "—"
        filas[nombre] = fila
    return pd.DataFrame(filas).T


def date_color(hex_color: str, t: float) -> str:
    """Rampa de un solo tono: apagado (primera fecha) a brillante (ultima), sobre el fondo oscuro."""
    h = hex_color.lstrip("#")
    c = np.array([int(h[k:k + 2], 16) for k in (0, 2, 4)], float)
    lo = c * 0.35 + np.array([14, 17, 23]) * 0.65
    hi = c * 0.7 + 255 * 0.3
    r, g, b = (lo + (hi - lo) * float(np.clip(t, 0, 1))).round().astype(int)
    return f"rgb({r},{g},{b})"


SUSCEPTIBLES = [s for s in SPECIES_ORDER if s in species_with_rust]
BASE_COLS = ["species", "leaf_id", "leaf", "leaf_type", "leaf_num", "campaign_id", "campaign_date",
             "dia", "n_puntos", "qc_atipico"]
sev_gaps = with_gaps(
    ts[BASE_COLS].merge(sev_all[["leaf_id", "campaign_date", "sev_S1", "sev_S2"]], on=["leaf_id", "campaign_date"]),
    T_CERO,
)
dist_gaps = with_gaps(
    dist_all.merge(ts[["leaf_id", "campaign_date", "n_puntos", "qc_atipico"]], on=["leaf_id", "campaign_date"], how="left"),
    T_CERO,
) if not dist_all.empty else dist_all


def m_panels(data, ycol, y_title, sdcol=None, scale=1.0, risk_lines=False, zero_line=False,
             show_rust=True, rows=1, row=1, fig=None, show_titles=True, pts_col=None, worst_col=None):
    """Bourbon | Pacamara: hojas M en primer plano, rango de hojas T y R1 como referencias tenues."""
    own_fig = fig is None
    if own_fig:
        fig = make_subplots(rows=rows, cols=len(SUSCEPTIBLES), shared_yaxes=True,
                            subplot_titles=SUSCEPTIBLES if show_titles else None, horizontal_spacing=0.04)
    for j, sp in enumerate(SUSCEPTIBLES, start=1):
        d = data[data["species"] == sp]
        leyenda = j == 1 and row == 1
        t = (d[(d["leaf_type"] == "T")].dropna(subset=[ycol])
             .groupby("campaign_date").agg(lo=(ycol, "min"), hi=(ycol, "max"), dia=("dia", "first"))
             .reset_index())
        if not t.empty:
            xs = t[xcol]
            fig.add_trace(go.Scatter(x=xs, y=t["hi"] * scale, mode="lines", line=dict(width=0),
                                     legendgroup="tband", showlegend=False, hoverinfo="skip"), row=row, col=j)
            fig.add_trace(go.Scatter(
                x=xs, y=t["lo"] * scale, mode="lines", line=dict(width=0), fill="tonexty",
                fillcolor=_rgba(LEAF_TYPE_COLORS["T"], 0.2), name="Rango de hojas T (sanas al inicio)",
                legendgroup="tband", legendrank=900, showlegend=leyenda, hoverinfo="skip",
            ), row=row, col=j)
        r = d[d["leaf_type"] == "R"].sort_values("campaign_date")
        if show_rust and not r.empty:
            fig.add_trace(go.Scatter(
                x=r[xcol], y=r[ycol] * scale, mode="lines+markers", connectgaps=False,
                name="R1 · con roya (referencia)", legendgroup="rref", legendrank=950, showlegend=leyenda,
                line=dict(color=_rgba(LEAF_TYPE_COLORS["R"], 0.6), width=1.5, dash="dot"),
                marker=dict(size=5, color=_rgba(LEAF_TYPE_COLORS["R"], 0.6)),
                hovertemplate="R1 · %{x}<br>%{y:.4f}<extra></extra>",
            ), row=row, col=j)
        m = d[d["leaf_type"] == "M"]
        if pts_col is not None:
            pm = pts[(pts["species"] == sp) & (pts["leaf_type"] == "M")]
            for leaf, g in pm.groupby("leaf"):
                fig.add_trace(go.Scatter(
                    x=g[xcol], y=g[pts_col] * scale, mode="markers", name="Puntos individuales (p1–p3)",
                    legendgroup="pts", legendrank=800, showlegend=leyenda and leaf == pm["leaf"].min(),
                    marker=dict(size=7, color=_rgba(LEAF_TYPE_COLORS["M"], 0.65), symbol="circle",
                                line=dict(width=1, color="#0E1117")),
                    customdata=g["point"],
                    hovertemplate=f"{leaf} · p%{{customdata}}<br>%{{x}}<br>%{{y:.4f}}<extra></extra>",
                ), row=row, col=j)
        if worst_col is not None and not m.empty:
            for leaf in sorted(m["leaf"].unique(), key=_leaf_sort_key):
                g = m[m["leaf"] == leaf].sort_values("campaign_date")
                _, dash = _leaf_style(leaf)
                fig.add_trace(go.Scatter(
                    x=g[xcol], y=g[worst_col] * scale, mode="lines+markers", connectgaps=False,
                    name=f"{leaf} · peor punto", legendgroup=f"w{leaf}", legendrank=850, showlegend=leyenda,
                    line=dict(color=_rgba(LEAF_TYPE_COLORS["M"], 0.75), width=1, dash=dash),
                    marker=dict(size=8, symbol="diamond-open", color=LEAF_TYPE_COLORS["M"]),
                    hovertemplate=f"{leaf} peor punto<br>%{{x}}<br>%{{y:.4f}}<extra></extra>",
                ), row=row, col=j)
        if not m.empty:
            add_leaf_lines(fig, m, ycol, sdcol=sdcol, row=row, col=j, showlegend=leyenda, scale=scale)
        if zero_line:
            fig.add_hline(y=0, line_width=1, line_color="rgba(200,200,200,0.4)", row=row, col=j)
        if risk_lines:
            for nivel, nombre_clase, _, _ in RUST_RISK_CLASSES:
                if nivel in (0.0, 1.0):
                    continue
                etiqueta = nombre_clase if (j == 1 and round(nivel * 10) % 2 == 0) else ""
                fig.add_hline(y=nivel * 100, line_dash="dot", line_width=1, line_color="rgba(180,180,180,0.3)",
                              annotation_text=etiqueta, annotation_font_size=9,
                              annotation_font_color=TEXT_MUTED, annotation_position="top left", row=row, col=j)
    if own_fig:
        style_time_axis(fig, 500)
        fig.update_layout(margin=dict(t=85), legend=dict(y=1.09))
        fig.update_yaxes(title_text=y_title, col=1)
    return fig


def m_trend_table(trends: pd.DataFrame) -> pd.DataFrame:
    """Tendencias de las hojas M susceptibles, contrastadas con las hojas M de los controles."""
    ev = trends[trends["Tipo"] == "M"]
    ctrl = ev[~ev["Especie"].isin(species_with_rust) & (ev["Significativa"] == True)]  # noqa: E712
    filas = []
    for _, r in ev[ev["Especie"].isin(SUSCEPTIBLES)].iterrows():
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


# ---------- resumen de hallazgos ----------
with st.container(border=True):
    st.markdown("**Hallazgos principales** — se recalculan solos cuando entran datos nuevos")
    bullets = []
    vis_t = region_slopes(spec_tr_raw, GRUPOS_ESP[0][4], 450, 690)
    vis_r = region_slopes(spec_tr_raw, GRUPOS_ESP[3][4], 450, 690)
    vis_tn = region_slopes(spec_tr_norm, GRUPOS_ESP[0][4], 450, 690)
    vis_rn = region_slopes(spec_tr_norm, GRUPOS_ESP[3][4], 450, 690)
    if len(vis_t) and len(vis_r):
        robusto = np.sign(vis_t.median()) == np.sign(vis_tn.median()) and np.sign(vis_r.median()) == np.sign(vis_rn.median())
        bullets.append(
            f"**Visible (450–690 nm):** las hojas tiernas cambian {vis_t.median():+.2f} pp/semana "
            f"({int((vis_t < 0).sum())}/{len(vis_t)} bajan) y R1 {vis_r.median():+.2f} pp/semana "
            f"({int((vis_r > 0).sum())}/{len(vis_r)} suben). "
            + ("Direcciones opuestas: la maduración oscurece el visible y la roya lo aclara. "
               if vis_t.median() < 0 < vis_r.median() else "")
            + ("Se mantiene al normalizar por el NIR." if robusto else "**No** se mantiene al normalizar por el NIR: leer con cautela.")
        )
    res_star = index_change_summary(trends_star, species_with_rust)
    env = res_star[res_star["Lectura"].str.contains("Envejecimiento")]["Índice"].tolist()
    solo_r = res_star[res_star["Lectura"].str.contains("solo en la hoja con roya")]["Índice"].tolist()
    if env:
        bullets.append(f"**Índices que cambian con la edad de la hoja madura** (también en controles sin roya, Δ*): {', '.join(env)}.")
    bullets.append(
        f"**Índices que cambian solo en la hoja con roya** (Δ*): {', '.join(solo_r)}." if solo_r
        else "**Ningún índice cambia de forma significativa solo en la hoja con roya** (Δ*, FDR 5 %)."
    )
    tm = m_trend_table(trends_star)
    if not tm.empty:
        cand = tm[tm["Lectura"].str.startswith("Candidata")]
        compat = tm[tm["Lectura"].str.startswith("Compatible")]
        hojas_c = sorted(set(compat["Especie"] + " " + compat["Hoja"]))
        bullets.append(
            f"**Hojas maduras susceptibles:** {len(cand)} tendencia(s) candidata(s) a roya y {len(compat)} "
            f"compatible(s) con envejecimiento" + (f" ({', '.join(hojas_c)})" if hojas_c else "") + " (Δ*)."
        )
    bullets.append(
        "**Límites:** una sola hoja con roya por especie, ya infectada en su primera medición; la fecha de "
        "infección no se conoce. Esto describe trayectorias, no permite todavía predecir la roya."
    )
    for b in bullets:
        st.markdown(f"- {b}")

# ---------- 1. hojas maduras de las especies susceptibles ----------
st.subheader(f"1. Hojas maduras (M) de las especies susceptibles: {' y '.join(SUSCEPTIBLES)}")
st.caption(
    "**Es el foco de la página.** La hoja madura es la de estado sanitario desconocido: es donde "
    "una infección todavía sin síntomas tendría que aparecer. M1 y M2 van en primer plano; como "
    "referencia, la banda verde es el rango de las hojas T de la misma especie (sanas al inicio) y "
    "la línea naranja punteada es R1 (hoja con roya). Esta sección muestra siempre las dos especies "
    "susceptibles, sin importar la especie elegida en la barra lateral."
)

MODOS = {
    "Valor": ("", "Valor del índice, sin anclas ni modelos. Es la vista más defendible."),
    "Δ desde la primera fecha": (
        DELTA, "Cambio respecto de la primera medición de cada hoja: cada hoja es su propio control."
    ),
    "Δ* corregido por hojas T": (
        DELTA_STAR,
        "Δ menos la mediana de Δ de las hojas T de la misma especie ese día. Resta la deriva común "
        "(luz, calibración, estación) y también la maduración normal: es conservador a propósito.",
    ),
}

c1, c2 = st.columns([1, 2])
index_sel = c1.selectbox("Índice", INDICES, index=INDICES.index("mNDVI705"))
modo = c2.radio("Modo", list(MODOS), horizontal=True)
prefijo, explicacion = MODOS[modo]
st.caption(explicacion)

tiles = st.columns(sum(len(ts[(ts["species"] == sp) & (ts["leaf_type"] == "M")]["leaf"].unique()) for sp in SUSCEPTIBLES) or 1)
k = 0
for sp in SUSCEPTIBLES:
    for leaf in sorted(ts[(ts["species"] == sp) & (ts["leaf_type"] == "M")]["leaf"].unique(), key=_leaf_sort_key):
        s = sev_all[(sev_all["species"] == sp) & (sev_all["leaf"] == leaf)].sort_values("campaign_date")
        if s.empty:
            continue
        first, last = s.iloc[0], s.iloc[-1]
        tiles[k].metric(
            f"{sp} · {leaf}", f"{last['sev_S1'] * 100:.0f} %",
            delta=f"{(last['sev_S1'] - first['sev_S1']) * 100:+.0f} pp desde {first['campaign_date']:%d/%m}",
            delta_color="inverse", border=True,
            help=f"Severidad relativa (anclas S1) el {last['campaign_date']:%d/%m}. Comparable entre hojas, "
                 "no absoluta: ver la sección 7.",
        )
        k += 1

tab_idx, tab_sev, tab_dist, tab_all = st.tabs(
    [f"{index_sel} en el tiempo", "Severidad relativa", "Distancia a R1", "Los 8 índices"]
)
with tab_idx:
    if prefijo:
        st.caption("Los puntos individuales y el peor punto se muestran en el modo **Valor**.")
        ver_pts = ver_peor = False
    else:
        cc1, cc2 = st.columns(2)
        ver_pts = cc1.toggle("Puntos individuales (p1–p3)", value=True,
                             help="Cada punto es la media de sus repeticiones. Muestra cuánto varía la hoja por dentro.")
        ver_peor = cc2.toggle("Peor punto (hacia la roya)", value=False,
                              help="El punto más desplazado hacia la hoja con roya ese día. Con 3 puntos es ruidoso: "
                                   "sirve como señal complementaria, no como reemplazo del promedio.")
    fig = m_panels(ts_gaps, prefijo + index_sel, f"{modo}: {index_sel}",
                   sdcol=f"sd {index_sel}" if not (prefijo or ver_pts) else None, zero_line=bool(prefijo),
                   pts_col=index_sel if ver_pts else None, worst_col=PEOR + index_sel if ver_peor else None)
    st.plotly_chart(fig, width="stretch")
with tab_sev:
    st.caption(
        "Severidad relativa con anclas S1: 0 % = hojas T en las primeras campañas, 100 % = promedio de "
        "R1. Sirve para comparar hojas entre sí; ver la advertencia de circularidad en la sección 7."
    )
    fig = m_panels(sev_gaps, "sev_S1", "Severidad relativa (%)", scale=100, risk_lines=True)
    fig.update_yaxes(range=[-3, 105])
    st.plotly_chart(fig, width="stretch")
with tab_dist:
    st.caption(
        "Distancia RMS en z-scores (sin FSR) entre cada hoja y R1 **el mismo día**. Más baja = más "
        "parecida a la hoja con roya. Una M que baja de forma sostenida y sale de la banda de las T es "
        "la señal a revisar en campo. El pico del 10/08 en Pacamara es R1 atípica ese día, no las M."
    )
    if dist_gaps.empty:
        st.info("No hay datos de distancia.")
    else:
        fig = m_panels(dist_gaps, "distancia", "Distancia a R1 (z RMS)", show_rust=False)
        fig.update_yaxes(rangemode="tozero")
        st.plotly_chart(fig, width="stretch")
with tab_all:
    fig = make_subplots(rows=len(INDICES), cols=len(SUSCEPTIBLES), shared_xaxes=True, shared_yaxes=True,
                        subplot_titles=[f"{sp} · {idx}" for idx in INDICES for sp in SUSCEPTIBLES],
                        vertical_spacing=0.035, horizontal_spacing=0.04)
    for i, idx in enumerate(INDICES, start=1):
        m_panels(ts_gaps, prefijo + idx, idx, zero_line=bool(prefijo), rows=len(INDICES), row=i, fig=fig)
    style_time_axis(fig, 1900)
    fig.update_xaxes(title_text=None)
    for ann in fig.layout.annotations:
        ann.font.size = 11
    st.plotly_chart(fig, width="stretch")

st.markdown("**¿Las hojas maduras cambian con el tiempo, y ese cambio es propio de la especie susceptible?**")
fam_m = st.radio("Tendencia calculada sobre", list(FAMILIAS), horizontal=True, help=FAM_AYUDA)
tabla_m = m_trend_table(trends_fam[fam_m])
if fam_m != "Δ* corregido por hojas T":
    st.caption(
        "⚠ Una \"candidata\" en esta familia debe contrastarse con Δ* y con el promedio: si la misma hoja "
        "ya coincide con un control en el promedio (p. ej. Bourbon M1 en NDVI), la explicación más simple "
        "sigue siendo el envejecimiento."
    )
if not tabla_m.empty:
    n_cand = int((tabla_m["Lectura"].str.startswith("Candidata")).sum())
    n_env = int((tabla_m["Lectura"].str.startswith("Compatible")).sum())
    t1, t2, t3 = st.columns(3)
    t1.metric("Series M evaluadas", int(tabla_m["Lectura"].isin(["Sin tendencia"]).sum() + n_cand + n_env), border=True)
    t2.metric("Candidatas (solo en susceptibles)", n_cand, border=True,
              help="Tendencia significativa (FDR 5 %) que no aparece con el mismo signo en ninguna hoja M de Canefora o Cuscatleco.")
    t3.metric("Compatibles con envejecimiento", n_env, border=True,
              help="Tendencia significativa que también muestra una hoja M sin roya: no se puede atribuir a la roya.")
    st.dataframe(
        tabla_m, hide_index=True, width="stretch",
        column_config={
            "Pendiente / semana": st.column_config.NumberColumn("Pendiente / semana", format="%.5f"),
            "p FDR": st.column_config.NumberColumn("p FDR", format="%.4f"),
        },
    )
st.caption(
    "La tabla cruza cada tendencia de una hoja M de Bourbon/Pacamara con las hojas M de Canefora y "
    "Cuscatleco, que no tienen roya. Si el control muestra la misma tendencia, la explicación más "
    "simple es la maduración de la hoja o la estación, no la roya. Sin FSR (idéntico a NDVI)."
)

# ---------- 2. que cambia con el tiempo ----------
st.subheader("2. ¿Qué cambia con el tiempo? Envejecimiento frente a roya")
st.caption(
    "Tendencia de **cada longitud de onda** (pendiente de Theil-Sen, en puntos de reflectancia por "
    "semana) calculada hoja por hoja sobre su espectro medio, y resumida por grupo con la mediana "
    "entre hojas (banda = rango intercuartil cuando el grupo tiene 3 hojas o más). Por encima de 0, "
    "esa región del espectro sube con las semanas; por debajo, baja. No depende de los 8 índices: "
    "muestra dónde ocurre el cambio."
)
c1, c2 = st.columns(2)
norm_nir = c1.toggle(
    "Normalizar por la meseta NIR (750–900 nm)", value=False, key="norm_s2",
    help="Divide cada espectro por su media en 750–900 nm. Quita cambios de nivel de un día a otro "
         "(contacto de la sonda, referencia de blanco), pero también esconde cambios reales del NIR. "
         "Si una conclusión se mantiene con y sin normalizar, es robusta a esos efectos.",
)
ver_cada_hoja = c2.toggle("Mostrar cada hoja", value=False, key="hojas_s2")
spec_tr = spec_tr_norm if norm_nir else spec_tr_raw
unidad = "% de la meseta NIR por semana" if norm_nir else "pp de reflectancia por semana"

tab_firma, tab_mapa, tab_idx_cambio = st.tabs(
    ["Firma espectral por grupo", "Cada hoja (mapa de calor)", "¿Qué índices cambian?"]
)
with tab_firma:
    fig = go.Figure()
    etiquetas = []
    for nombre, corto, color, dash, sel in GRUPOS_ESP:
        g = spec_tr[sel(spec_tr)]
        if g.empty:
            continue
        n_h = g["leaf_id"].nunique()
        if ver_cada_hoja:
            for lid, gl in g.groupby("leaf_id"):
                fig.add_trace(go.Scatter(
                    x=gl["wavelength"], y=gl["pendiente"], mode="lines", showlegend=False, legendgroup=nombre,
                    line=dict(color=_rgba(color, 0.3), width=1),
                    hovertemplate=f"{lid.replace('|', ' ')}<br>%{{x:.0f}} nm · %{{y:+.2f}}<extra></extra>",
                ))
        q = g.groupby("wavelength")["pendiente"]
        med = q.median()
        if n_h >= 3:
            fig.add_trace(go.Scatter(x=med.index, y=q.quantile(0.75).to_numpy(), mode="lines", line=dict(width=0),
                                     showlegend=False, legendgroup=nombre, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=med.index, y=q.quantile(0.25).to_numpy(), mode="lines", line=dict(width=0),
                                     fill="tonexty", fillcolor=_rgba(color, 0.15), showlegend=False,
                                     legendgroup=nombre, hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=med.index, y=med.to_numpy(), mode="lines", name=f"{nombre} (n = {n_h} hojas)", legendgroup=nombre,
            line=dict(color=color, width=2.5, dash=dash),
            hovertemplate=f"{corto}<br>%{{x:.0f}} nm · %{{y:+.2f}} {unidad}<extra></extra>",
        ))
        etiquetas.append([med.index[-1], float(med.iloc[-1]), corto])
    if etiquetas:
        vals = spec_tr["pendiente"].dropna()
        gap = 0.05 * ((vals.quantile(0.95) - vals.quantile(0.05)) or 1.0)
        etiquetas.sort(key=lambda e: e[1])
        for i in range(1, len(etiquetas)):
            etiquetas[i][1] = max(etiquetas[i][1], etiquetas[i - 1][1] + gap)
        for x, y, texto in etiquetas:
            fig.add_annotation(x=x, y=y, text=texto, showarrow=False, xanchor="left", xshift=6,
                               font=dict(size=11, color=TEXT_MUTED))
    for w in INDEX_WAVELENGTHS:
        fig.add_vline(x=w, line_width=1, line_dash="dot", line_color="rgba(160,160,160,0.18)")
    fig.add_hline(y=0, line_width=1, line_color="rgba(220,220,220,0.55)")
    fig.update_layout(height=480, margin=dict(t=30, b=10, r=70), hovermode="x unified",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)),
                      xaxis_title="Longitud de onda (nm)", yaxis_title=f"Tendencia ({unidad})")
    fig.update_xaxes(gridcolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    st.plotly_chart(fig, width="stretch")

    st.markdown("**Resumen por región del espectro**")
    st.dataframe(region_table(spec_tr), width="stretch")
    st.caption(
        "Cada celda: mediana de la pendiente de las hojas del grupo en esa región, y cuántas hojas "
        "suben de cuántas. Es descriptivo: por región y grupo hay pocas hojas (R1 son 2), así que no "
        "se reporta un p-valor. La coincidencia de signo entre hojas es lo que da solidez."
    )

with tab_mapa:
    orden = []
    for _, _, _, _, sel in GRUPOS_ESP:
        ids = spec_tr[sel(spec_tr)][["leaf_id", "species", "leaf"]].drop_duplicates()
        ids = ids.assign(_o=ids["species"].map({s: i for i, s in enumerate(SPECIES_ORDER)})).sort_values(["_o", "leaf"])
        orden += [i for i in ids["leaf_id"] if i not in orden]
    mat = spec_tr.pivot_table(index="leaf_id", columns="wavelength", values="pendiente").reindex(orden)
    zmax = float(np.nanpercentile(np.abs(mat.to_numpy()), 98)) or 1.0
    fig = go.Figure(go.Heatmap(
        z=mat.to_numpy(), x=mat.columns.to_numpy(), y=[i.replace("|", " · ") for i in mat.index],
        zmin=-zmax, zmax=zmax, zmid=0,
        colorscale=[[0, "#2F6DB5"], [0.5, "#3A3F47"], [1, "#C8553D"]],
        colorbar=dict(title=dict(text="por semana", side="top"), thickness=14),
        hovertemplate="%{y}<br>%{x:.0f} nm · %{z:+.2f}<extra></extra>",
    ))
    fig.update_layout(height=max(360, 26 * len(mat) + 100), margin=dict(t=20, b=10),
                      xaxis_title="Longitud de onda (nm)",
                      yaxis=dict(autorange="reversed", tickfont=dict(size=11)))
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Una fila por hoja con al menos "
        f"{TEMPORAL_MIN_FECHAS_TENDENCIA} fechas, ordenadas por grupo: tiernas, maduras susceptibles, "
        "maduras de control y hojas con roya. Naranja = esa longitud de onda sube con las semanas; azul = "
        f"baja; gris = sin cambio. Unidad: {unidad}. La escala se recorta al percentil 98 para que un "
        "extremo no apague el resto."
    )

with tab_idx_cambio:
    fam_idx = st.radio("Tendencia calculada sobre", list(FAMILIAS), horizontal=True, help=FAM_AYUDA, key="fam_idx")
    resumen_idx = index_change_summary(trends_fam[fam_idx], species_with_rust)
    st.dataframe(resumen_idx, hide_index=True, width="stretch",
                 column_config={c: st.column_config.NumberColumn(c, format="%.5f")
                                for c in resumen_idx.columns if "mediana" in c})
    st.caption(
        "Por índice y grupo: tendencias significativas (FDR 5 %) que suben / bajan, de cuántas hojas "
        "evaluadas, y la mediana de la pendiente por semana. La lectura sigue reglas fijas: "
        "**propio de la roya** si R1 cambia y ni las T ni las M de control cambian en el mismo sentido; "
        "**envejecimiento de hoja madura** si M susceptibles y M de control cambian igual; **candidata** si "
        "una M susceptible cambia y ningún control lo hace; **maduración** si cambia alguna T. "
        "En la familia Δ*, las hojas T son la referencia y su tendencia es ~0 por construcción."
    )

# ---------- 3. roya frente a envejecimiento ----------
st.subheader("3. La misma hoja semana a semana: roya (R1) frente a envejecimiento (hoja tierna)")
st.caption(
    "Todos los espectros medios de una misma hoja, uno por fecha, con el color de más apagado (primera "
    "fecha) a más brillante (última). Abajo, el cambio de cada fecha respecto de la primera medición. "
    "**R1 ya tenía roya el 15/07, su primera medición:** se ve cómo sigue cambiando una hoja infectada, "
    "no cómo empieza la infección. La hoja tierna sí muestra su maduración completa desde el 29/06. "
    "La curva hundida de Pacamara R1 es el 10/08 atípico: el control de calidad de la barra lateral la excluye."
)
c1, c2 = st.columns(2)
t_leaf = c1.radio("Hoja tierna a comparar", ["T1", "T2"], horizontal=True, key="t_leaf_s3")
norm3 = c2.toggle("Normalizar por la meseta NIR (750–900 nm)", value=False, key="norm_s3")

fechas_glob = sorted(ts["campaign_date"].unique())
f0, f1 = pd.Timestamp(fechas_glob[0]), pd.Timestamp(fechas_glob[-1])
span = max((f1 - f0).days, 1)
paneles = [("R1", "R", "con roya"), (t_leaf, "T", "tierna al inicio")]
titulos = []
for sp in SUSCEPTIBLES:
    titulos += [f"{sp} · {leaf} ({desc})" for leaf, _, desc in paneles]
    titulos += ["Cambio respecto de la 1ª medición", "Cambio respecto de la 1ª medición"]
fig = make_subplots(rows=2 * len(SUSCEPTIBLES), cols=2, shared_xaxes=True, shared_yaxes=True,
                    row_heights=[0.34, 0.16] * len(SUSCEPTIBLES), subplot_titles=titulos,
                    vertical_spacing=0.06, horizontal_spacing=0.04)
for i, sp in enumerate(SUSCEPTIBLES):
    for j, (leaf, tipo, _) in enumerate(paneles, start=1):
        g = spectra_all[spectra_all["leaf_id"] == f"{sp}|{leaf}"]
        if g.empty:
            continue
        curvas = {pd.Timestamp(f): c.sort_values("wavelength") for f, c in g.groupby("campaign_date")}
        base = None
        for f in sorted(curvas):
            c = curvas[f]
            y = c["mean"].to_numpy()
            if norm3:
                wl = c["wavelength"].to_numpy()
                y = y / y[(wl >= 750) & (wl <= 900)].mean() * 100
            if base is None:
                base = y
            color = date_color(LEAF_TYPE_COLORS[tipo], (f - f0).days / span)
            hover = f"{leaf} · {f:%d/%m/%Y}<br>%{{x:.0f}} nm · %{{y:.1f}}<extra></extra>"
            fig.add_trace(go.Scatter(x=c["wavelength"], y=y, mode="lines", showlegend=False,
                                     line=dict(color=color, width=1.6), hovertemplate=hover),
                          row=2 * i + 1, col=j)
            fig.add_trace(go.Scatter(x=c["wavelength"], y=y - base, mode="lines", showlegend=False,
                                     line=dict(color=color, width=1.4), hovertemplate=hover),
                          row=2 * i + 2, col=j)
        fig.add_hline(y=0, line_width=1, line_color="rgba(220,220,220,0.5)", row=2 * i + 2, col=j)

ticks = [0, 0.25, 0.5, 0.75, 1]
for j, (leaf, tipo, _) in enumerate(paneles):
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", showlegend=False, hoverinfo="skip",
        marker=dict(
            color=[0], cmin=0, cmax=1, showscale=True,
            colorscale=[[k, date_color(LEAF_TYPE_COLORS[tipo], k)] for k in np.linspace(0, 1, 6)],
            colorbar=dict(orientation="h", x=0.24 + 0.52 * j, xanchor="center", y=-0.06, yanchor="top",
                          len=0.42, thickness=10, title=dict(text=f"Fecha ({leaf})", side="top"),
                          tickvals=ticks,
                          ticktext=[f"{(f0 + pd.Timedelta(days=round(t * span))):%d/%m}" for t in ticks]),
        ),
    ), row=1, col=1)
for w in INDEX_WAVELENGTHS:
    fig.add_vline(x=w, line_width=1, line_dash="dot", line_color="rgba(160,160,160,0.15)")
fig.update_layout(height=1180, margin=dict(t=40, b=90), hovermode="closest")
fig.update_xaxes(gridcolor=GRID)
fig.update_yaxes(gridcolor=GRID, zeroline=False)
for i in range(len(SUSCEPTIBLES)):
    fig.update_yaxes(title_text="% de la meseta NIR" if norm3 else "Reflectancia (%)", row=2 * i + 1, col=1)
    fig.update_yaxes(title_text="Δ (pp)", row=2 * i + 2, col=1)
fig.update_xaxes(title_text="Longitud de onda (nm)", row=2 * len(SUSCEPTIBLES), col=1)
fig.update_xaxes(title_text="Longitud de onda (nm)", row=2 * len(SUSCEPTIBLES), col=2)
for ann in fig.layout.annotations:
    ann.font.size = 12
st.plotly_chart(fig, width="stretch")

lectura_s3 = []
for sp in SUSCEPTIBLES:
    for leaf, tipo, desc in paneles:
        g = spec_tr_raw[(spec_tr_raw["species"] == sp) & (spec_tr_raw["leaf"] == leaf)]
        vis = g[g["wavelength"].between(450, 690)]["pendiente"].median()
        ro = g[g["wavelength"].between(700, 740)]["pendiente"].median()
        if pd.notna(vis):
            lectura_s3.append(f"{sp} {leaf}: visible {vis:+.2f} pp/semana, borde rojo {ro:+.2f} pp/semana")
if lectura_s3:
    st.caption("Tendencia (Theil-Sen, sin normalizar): " + " · ".join(lectura_s3) + ".")

st.divider()
st.markdown(f"### Detalle por especie: {_species_label(species)}")
st.caption("Las secciones siguientes usan la especie y las hojas elegidas en la barra lateral.")

# ---------- 2. ficha de datos ----------
st.subheader("4. Ficha de datos")
st.caption(
    "Puntos válidos por hoja y fecha. **—** = la especie tuvo campaña pero la hoja no se midió "
    "(hueco, no se interpola). **⚠** = hoja-fecha marcada por el control de calidad."
)

ficha_src = ts_gaps[ts_gaps["species"] == species]
fechas_sp = sorted(ficha_src["campaign_date"].unique())
ficha = pd.DataFrame(index=sorted(ficha_src["leaf"].unique(), key=_leaf_sort_key),
                     columns=[f"{pd.Timestamp(f):%d/%m}" for f in fechas_sp], dtype=object).fillna("")
for r in ficha_src.itertuples():
    col = f"{r.campaign_date:%d/%m}"
    if r.hueco:
        ficha.loc[r.leaf, col] = "—"
    else:
        txt = str(int(r.n_puntos))
        if r.qc_atipico is True:
            txt += " ⚠"
        ficha.loc[r.leaf, col] = txt
st.dataframe(ficha, width="stretch")

sel_sp = temporal_selection(df[df["species"] == species])
excl = sel_sp["motivo_exclusion"].value_counts()
notas = [f"**{n}** archivo(s) excluido(s): {m}" for m, n in excl.items()]
qc_sp = ts_qc[(ts_qc["species"] == species) & ts_qc["qc_atipico"]]
for r in qc_sp.itertuples():
    notas.append(
        f"⚠ **{r.leaf} el {r.campaign_date:%d/%m}**: {int(r.qc_n_atipicos)} de 7 índices atípicos "
        f"respecto de su propia serie — {'**excluida**' if exclude_qc else 'incluida (activa el control de calidad para excluirla)'}."
    )
incompletas = ts[(ts["species"] == species) & (ts["n_puntos"] < len(TEMPORAL_VALID_POINTS))]
for r in incompletas.itertuples():
    notas.append(f"{r.leaf} el {r.campaign_date:%d/%m}: solo {int(r.n_puntos)} punto(s) medido(s).")
if read_errors:
    notas.append(f"{len(read_errors)} archivo(s) con error de lectura en todo el dataset.")
if notas:
    with st.container(border=True):
        for n in notas:
            st.markdown(f"- {n}")

if sp_ts.empty:
    st.info("No hay datos para las hojas seleccionadas.")
    st.stop()


# ---------- 3. indices en el tiempo ----------
st.subheader("5. Índices en el tiempo")
st.caption(f"Índice y modo elegidos en la sección 1: **{index_sel}**, **{modo}**. {explicacion}")
if prefijo == DELTA_STAR and species == "Canefora":
    st.info("Canefora tiene una sola hoja T en la mayoría de las fechas: su Δ* es 0 por definición.")

tab_uno, tab_todos = st.tabs(["Un índice", "Los 8 índices"])
with tab_uno:
    fig = go.Figure()
    add_leaf_lines(fig, sp_ts, prefijo + index_sel, sdcol=f"sd {index_sel}")
    if prefijo:
        fig.add_hline(y=0, line_width=1, line_color="rgba(200,200,200,0.4)")
    style_time_axis(fig, 460, yaxis_title=f"{modo}: {index_sel}")
    st.plotly_chart(fig, width="stretch")

with tab_todos:
    fig = make_subplots(rows=4, cols=2, shared_xaxes=True, subplot_titles=INDICES,
                        vertical_spacing=0.07, horizontal_spacing=0.07)
    for i, idx in enumerate(INDICES):
        add_leaf_lines(fig, sp_ts, prefijo + idx, row=i // 2 + 1, col=i % 2 + 1,
                       showlegend=(i == 0), direct_labels=False)
        if prefijo:
            fig.add_hline(y=0, line_width=1, line_color="rgba(200,200,200,0.4)", row=i // 2 + 1, col=i % 2 + 1)
    style_time_axis(fig, 1000)
    fig.update_xaxes(title_text=None)
    st.plotly_chart(fig, width="stretch")

# ---------- 4. tendencias ----------
st.subheader("6. Tendencias por hoja")
st.caption(
    f"Pendiente de Theil-Sen (unidades del índice por semana, IC 95 %) y test de Mann-Kendall, "
    f"por hoja e índice, con al menos {TEMPORAL_MIN_FECHAS_TENDENCIA} fechas. La corrección de "
    "Benjamini-Hochberg se aplica sobre **todas las especies y hojas a la vez**, así que el p "
    "corregido no cambia al mover los filtros. Sin FSR (idéntico a NDVI)."
)

familia = st.radio("Variable analizada", list(FAMILIAS), horizontal=True, help=FAM_AYUDA, key="fam_detalle")
trends = trends_fam[familia]

evaluadas = trends[trends["p"].notna()]
ctrl = evaluadas[~evaluadas["Especie"].isin(species_with_rust)]
m1, m2, m3 = st.columns(3)
m1.metric("Series evaluadas (todas las especies)", len(evaluadas), border=True)
m2.metric("Con tendencia significativa (FDR 5 %)", int(evaluadas["Significativa"].sum()), border=True)
m3.metric(
    "Controles sin roya con tendencia",
    f"{int(ctrl['Significativa'].sum())} / {len(ctrl)}",
    help="Canefora y Cuscatleco no tienen roya: una tendencia ahí no puede atribuirse a la roya. "
         "Si una hoja de Bourbon/Pacamara muestra la misma tendencia que un control del mismo tipo, "
         "lo más probable es maduración o estación.",
    border=True,
)

forest = evaluadas[evaluadas["Variable"] == index_sel] if index_sel in DIST_INDICES else pd.DataFrame()
if not forest.empty:
    forest = forest.assign(
        _o=forest["Especie"].map({s: i for i, s in enumerate(SPECIES_ORDER)}),
        _l=forest["Hoja"].map(_leaf_sort_key),
    ).sort_values(["_o", "_l"], ascending=False)
    forest["etiqueta"] = forest["Especie"] + " · " + forest["Hoja"]
    fig = go.Figure()
    # Leyenda neutra: el color de cada punto es el tipo de hoja, no la significancia.
    for simbolo, nombre in [("circle", "Significativa (FDR 5 %)"), ("circle-open", "No significativa")]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=nombre,
                                 marker=dict(size=10, symbol=simbolo, color=TEXT_MUTED, line=dict(width=2, color=TEXT_MUTED))))
    for sig, simbolo in [(True, "circle"), (False, "circle-open")]:
        g = forest[forest["Significativa"] == sig]
        if g.empty:
            continue
        fig.add_trace(go.Scatter(
            x=g["Pendiente / semana"], y=g["etiqueta"], mode="markers", showlegend=False,
            error_x=dict(type="data", symmetric=False,
                         array=g["IC95 sup"] - g["Pendiente / semana"],
                         arrayminus=g["Pendiente / semana"] - g["IC95 inf"],
                         thickness=1.5, width=0, color="rgba(200,200,200,0.6)"),
            marker=dict(size=10, symbol=simbolo, color=[LEAF_TYPE_COLORS[h[0]] for h in g["Hoja"]],
                        line=dict(width=2, color=[LEAF_TYPE_COLORS[h[0]] for h in g["Hoja"]])),
            customdata=np.stack([g["p FDR"], g["n fechas"]], axis=-1),
            hovertemplate="%{y}<br>%{x:.5f} / semana<br>p FDR %{customdata[0]:.4f} · n %{customdata[1]}<extra></extra>",
        ))
    fig.add_vline(x=0, line_width=1, line_color="rgba(200,200,200,0.5)")
    fig.update_layout(
        height=max(340, 26 * len(forest) + 110), margin=dict(t=80, b=10),
        title=dict(text=f"Pendiente de {index_sel} ({familia}) por hoja — color = tipo de hoja",
                   font=dict(size=13), y=0.985, yref="container", yanchor="top"),
        xaxis_title="Pendiente por semana (IC 95 %)",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0),
        yaxis=dict(type="category", categoryorder="array", categoryarray=forest["etiqueta"].tolist()),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    st.plotly_chart(fig, width="stretch")
elif index_sel == "FSR":
    st.caption("FSR no tiene tendencia propia (es idéntico a NDVI): elige otro índice para el gráfico de pendientes.")

solo_especie = st.checkbox(f"Mostrar solo {species} en la tabla", value=True)
tabla = trends[trends["Especie"] == species] if solo_especie else trends
tabla = tabla.assign(**{"Autocorrelación alta": tabla["r1 residuos"].abs() > 0.5})
cols = ["Especie", "Hoja", "Variable", "n fechas", "Pendiente / semana", "IC95 inf", "IC95 sup",
        "tau", "p", "p FDR", "Significativa", "r1 residuos", "Autocorrelación alta", "Motivo omision"]
st.dataframe(
    tabla[[c for c in cols if c in tabla]].sort_values(["Especie", "Hoja", "Variable"]),
    width="stretch", hide_index=True,
    column_config={
        **{c: st.column_config.NumberColumn(c, format="%.5f") for c in ["Pendiente / semana", "IC95 inf", "IC95 sup"]},
        **{c: st.column_config.NumberColumn(c, format="%.4f") for c in ["tau", "p", "p FDR", "r1 residuos"]},
    },
)
st.caption(
    "**Se puede decir:** \"la hoja R1 de Bourbon muestra una tendencia monótona en X, ausente en "
    "sus hojas T y en los controles\". **No se puede decir:** \"la roya cambia X a razón de Y por "
    "semana\" (n = 1 hoja enferma, mediciones autocorrelacionadas). `r1 residuos` > 0,5 marca "
    "series con autocorrelación fuerte, donde el p-valor es especialmente optimista."
)

# ---------- 5. severidad relativa ----------
st.subheader("7. Severidad relativa en el tiempo")
c1, c2 = st.columns([2, 1])
ancla = c1.radio(
    "Anclas",
    ["S1 — congeladas", "S2 — sin la fecha evaluada (sensibilidad)"],
    horizontal=True,
    help="S1: ancla con roya = media de todas las fechas de R. S2: para cada fecha, el ancla con "
         "roya se calcula sin esa fecha (leave-one-campaign-out).",
)
sin_recorte = c2.toggle("Sin recorte a 0–100 %", value=False)
sev_col = "sev_S1" if ancla.startswith("S1") else "sev_S2"

st.warning(
    "**Circularidad:** en Bourbon y Pacamara la única hoja con roya es R1, así que el ancla "
    "\"con roya\" *es* el promedio de R1 en el tiempo. La severidad de R1 contra su propio promedio "
    "tiende a quedar alrededor del 100 % por construcción. S2 lo atenúa pero no lo elimina. "
    "Úsala para comparar hojas entre sí, no como medida absoluta de progresión."
)
if species not in species_with_rust:
    st.info(f"{species} no tiene hoja con roya: el ancla con roya es la media de las especies que sí tienen (referencia estimada).")

sev = severity_timeseries(files, anchors, clip=not sin_recorte)
sev_sp = sev[(sev["species"] == species) & sev["leaf"].isin(sel_leaves)]
sev_plot = with_gaps(
    ts[["species", "leaf_id", "leaf", "leaf_type", "leaf_num", "campaign_id", "campaign_date",
        "dia", "n_puntos", "qc_atipico"]]
    .merge(sev_sp[["leaf_id", "campaign_date", "sev_S1", "sev_S2"]], on=["leaf_id", "campaign_date"]),
    T_CERO,
)
fig = go.Figure()
add_leaf_lines(fig, sev_plot, sev_col, scale=100)
if not sin_recorte:
    for nivel, nombre_clase, _, _ in RUST_RISK_CLASSES:
        if nivel in (0.0, 1.0):
            continue
        fig.add_hline(
            y=nivel * 100, line_dash="dot", line_width=1, line_color="rgba(180,180,180,0.3)",
            annotation_text=nombre_clase if round(nivel * 10) % 2 == 0 else "",
            annotation_font_size=9, annotation_font_color=TEXT_MUTED, annotation_position="top left",
        )
else:
    for y, t in [(0, "ancla sana"), (100, "ancla con roya")]:
        fig.add_hline(y=y, line_width=1, line_color="rgba(200,200,200,0.5)", annotation_text=t,
                      annotation_font_size=10, annotation_font_color=TEXT_MUTED, annotation_position="top left")
style_time_axis(fig, 440, yaxis_title="Severidad relativa (%)")
if not sin_recorte:
    fig.update_yaxes(range=[-3, 105])
st.plotly_chart(fig, width="stretch")

r1 = sev_sp[sev_sp["leaf_type"] == "R"].sort_values("campaign_date")
if not r1.empty:
    comp = pd.DataFrame({
        "Fecha": r1["campaign_date"].dt.strftime("%d/%m/%Y"),
        "Hoja": r1["leaf"],
        "S1 (%)": r1["sev_S1"] * 100,
        "S2 (%)": r1["sev_S2"] * 100,
        "S2 − S1 (pp)": (r1["sev_S2"] - r1["sev_S1"]) * 100,
    })
    with st.expander("Sensibilidad de la hoja con roya a las anclas (S1 vs S2)"):
        st.dataframe(comp, hide_index=True, width="stretch",
                     column_config={c: st.column_config.NumberColumn(c, format="%.1f") for c in comp.columns[2:]})

with st.expander("Anclas usadas para esta especie"):
    fechas_sana = anchors["fechas_ancla_sana"].get(species, [])
    st.markdown(
        f"Ancla sana: hojas T en {', '.join(f'{pd.Timestamp(f):%d/%m}' for f in fechas_sana)}. "
        f"Ancla con roya: {'hoja R propia' if anchors['referencia_propia'].get(species) else 'media de las especies con roya'} "
        "(cada fecha pesa igual)."
    )
    if species in anchors["sana"].index:
        st.dataframe(
            pd.DataFrame({"Ancla sana": anchors["sana"].loc[species], "Ancla con roya (S1)": anchors["enferma"].loc[species]}),
            width="stretch", column_config=index_column_config(["Ancla sana", "Ancla con roya (S1)"], 4),
        )

# ---------- 6. distancia a R1 ----------
st.subheader("8. Distancia espectral a la hoja con roya")
if species not in species_with_rust:
    st.info(f"{species} no tiene hoja con roya: no hay contra qué medir la distancia.")
else:
    st.caption(
        "Distancia RMS en z-scores (7 índices, sin FSR) entre cada hoja M/T y R1 **el mismo día**. "
        f"El z-score usa media y SD de las hojas T en las {TEMPORAL_BASELINE_CAMPAIGNS} primeras "
        "campañas, a nivel punto. **Más baja = más parecida a la hoja con roya.** Una hoja M que baja "
        "de forma sostenida mientras las T no, es candidata a revisión en campo — no un diagnóstico."
    )
    dist = dist_all
    dist_sp = dist[(dist["species"] == species) & dist["leaf"].isin(sel_leaves)]
    if dist_sp.empty:
        st.info("Selecciona alguna hoja M o T.")
    else:
        dist_plot = with_gaps(
            dist_sp.merge(ts[["leaf_id", "campaign_date", "n_puntos", "qc_atipico"]],
                          on=["leaf_id", "campaign_date"], how="left"),
            T_CERO,
        )
        fig = go.Figure()
        add_leaf_lines(fig, dist_plot, "distancia")
        style_time_axis(fig, 400, yaxis_title="Distancia a R1 (z RMS)")
        fig.update_yaxes(rangemode="tozero")
        st.plotly_chart(fig, width="stretch")
        qc_r = ts_qc[(ts_qc["species"] == species) & (ts_qc["leaf_type"] == "R") & ts_qc["qc_atipico"]]
        if not qc_r.empty and not exclude_qc:
            fechas_r = ", ".join(f"{d:%d/%m}" for d in qc_r["campaign_date"])
            st.caption(
                f"⚠ R1 está marcada como atípica el {fechas_r}: ese día **todas** las hojas se alejan de "
                "R1 a la vez, lo que indica un problema de R1, no de las demás. Activa el control de "
                "calidad para excluirla."
            )

# ---------- 7. animacion del espectro ----------
st.subheader("9. Espectro de reflectancia a lo largo de las semanas")
st.caption(
    "Espectro medio de cada hoja por fecha (media de repeticiones por punto, luego media de "
    "puntos) sobre una grilla común a todas las fechas. La curva gris punteada es la misma hoja en "
    "su primera medición; el panel inferior muestra la diferencia respecto de esa primera medición. "
    "El eje Y es fijo en todos los cuadros para que el cambio sea comparable. Las líneas "
    "verticales marcan las bandas que usan los índices."
)
default_anim = [l for l in sel_leaves if l.startswith("M")]
c1, c2, c3 = st.columns([2, 1, 1])
anim_leaves = c1.multiselect("Hojas en la animación", sel_leaves, default=default_anim or sel_leaves[:2])
show_band = c2.toggle("Banda ±1 SD entre puntos", value=False)
frame_ms = c3.slider("ms por cuadro", 300, 2000, 900, step=100)

if anim_leaves:
    anim_files = files[(files["species"] == species) & files["leaf"].isin(anim_leaves)]
    spectra = leaf_mean_spectra(anim_files[["leaf_id", "campaign_date", "point", "path"]])
    fechas = sorted(ts.loc[ts["species"] == species, "campaign_date"].unique())
    grid = np.sort(spectra["wavelength"].unique())
    nan_curve = np.full(len(grid), np.nan)

    curva = {(lid.split("|")[1], pd.Timestamp(fecha)): g.sort_values("wavelength")
             for (lid, fecha), g in spectra.groupby(["leaf_id", "campaign_date"])}
    t0 = {leaf: min(d for (l, d) in curva if l == leaf) for leaf in anim_leaves if any(l == leaf for l, _ in curva)}
    leaves_ok = [l for l in sorted(anim_leaves, key=_leaf_sort_key) if l in t0]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.66, 0.34], vertical_spacing=0.05)
    dinamicas = []

    def _dyn(leaf, fecha):
        c = curva.get((leaf, pd.Timestamp(fecha)))
        base = curva[(leaf, t0[leaf])]["mean"].to_numpy()
        if c is None:
            return nan_curve, nan_curve, nan_curve
        m, s = c["mean"].to_numpy(), c["sd"].to_numpy()
        return m, s, m - base

    for leaf in leaves_ok:
        color, dash = _leaf_style(leaf)
        m, s, d = _dyn(leaf, fechas[0])
        if show_band:
            dinamicas.append(len(fig.data))
            fig.add_trace(go.Scatter(x=grid, y=m + s, mode="lines", line=dict(width=0), showlegend=False,
                                     hoverinfo="skip", legendgroup=leaf), row=1, col=1)
            dinamicas.append(len(fig.data))
            fig.add_trace(go.Scatter(x=grid, y=m - s, mode="lines", line=dict(width=0), fill="tonexty",
                                     fillcolor=_rgba(color, 0.18), showlegend=False, hoverinfo="skip",
                                     legendgroup=leaf), row=1, col=1)
        dinamicas.append(len(fig.data))
        fig.add_trace(go.Scatter(x=grid, y=m, mode="lines", name=_leaf_name(leaf), legendgroup=leaf,
                                 line=dict(color=color, width=2.5, dash=dash),
                                 hovertemplate=f"{leaf}<br>%{{x:.0f}} nm · %{{y:.1f}} %<extra></extra>"),
                      row=1, col=1)
        fig.add_trace(go.Scatter(x=grid, y=curva[(leaf, t0[leaf])]["mean"], mode="lines",
                                 name=f"{leaf} en {t0[leaf]:%d/%m} (primera medición)", legendgroup=leaf,
                                 line=dict(color=_rgba(color, 0.5), width=1.5, dash="dot"),
                                 hovertemplate=f"{leaf} {t0[leaf]:%d/%m}<br>%{{x:.0f}} nm · %{{y:.1f}} %<extra></extra>"),
                      row=1, col=1)
        dinamicas.append(len(fig.data))
        fig.add_trace(go.Scatter(x=grid, y=d, mode="lines", showlegend=False, legendgroup=leaf,
                                 line=dict(color=color, width=2, dash=dash),
                                 hovertemplate=f"{leaf}<br>%{{x:.0f}} nm · %{{y:+.1f}} pp<extra></extra>"),
                      row=2, col=1)

    def _titulo(fecha):
        f = pd.Timestamp(fecha)
        dia = (f - T_CERO).days
        faltan = [l for l in leaves_ok if (l, f) not in curva]
        extra = f" · sin medición: {', '.join(faltan)}" if faltan else ""
        return f"{f:%d/%m/%Y} · día {dia}{extra}"

    frames = []
    for fecha in fechas:
        data = []
        for leaf in leaves_ok:
            m, s, d = _dyn(leaf, fecha)
            if show_band:
                data += [go.Scatter(y=m + s), go.Scatter(y=m - s)]
            data += [go.Scatter(y=m), go.Scatter(y=d)]
        frames.append(go.Frame(name=f"{pd.Timestamp(fecha):%d/%m}", data=data, traces=dinamicas,
                               layout=go.Layout(title_text=_titulo(fecha))))
    fig.frames = frames

    means = np.concatenate([c["mean"].to_numpy() + (c["sd"].fillna(0).to_numpy() if show_band else 0)
                            for c in curva.values()])
    lows = np.concatenate([c["mean"].to_numpy() - (c["sd"].fillna(0).to_numpy() if show_band else 0)
                           for c in curva.values()])
    diffs = np.concatenate([np.abs(_dyn(l, f)[2]) for l in leaves_ok for f in fechas])
    dmax = np.nanmax(diffs) * 1.1 if np.isfinite(np.nanmax(diffs)) and np.nanmax(diffs) > 0 else 1

    for w in INDEX_WAVELENGTHS:
        fig.add_vline(x=w, line_width=1, line_dash="dot", line_color="rgba(160,160,160,0.22)")
    fig.add_hline(y=0, line_width=1, line_color="rgba(200,200,200,0.5)", row=2, col=1)

    play = dict(frame=dict(duration=frame_ms, redraw=True), fromcurrent=True, transition=dict(duration=0))
    fig.update_layout(
        height=740, margin=dict(t=110, b=10),
        title=dict(text=_titulo(fechas[0]), font=dict(size=14), y=0.985, yref="container", yanchor="top"),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0, font=dict(size=11)),
        updatemenus=[dict(
            type="buttons", direction="left", x=0, y=-0.08, xanchor="left", yanchor="top", showactive=False,
            buttons=[
                dict(label="▶ Reproducir", method="animate", args=[None, play]),
                dict(label="⏸ Pausa", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")]),
            ],
        )],
        sliders=[dict(
            active=0, x=0.2, y=-0.06, len=0.8, currentvalue=dict(prefix="Fecha: ", font=dict(size=12)),
            steps=[dict(label=fr.name, method="animate",
                        args=[[fr.name], dict(mode="immediate", frame=dict(duration=0, redraw=True),
                                               transition=dict(duration=0))])
                   for fr in frames],
        )],
    )
    fig.update_yaxes(title_text="Reflectancia (%)", range=[max(np.nanmin(lows) - 3, -5), np.nanmax(means) + 3],
                     gridcolor=GRID, row=1, col=1)
    fig.update_yaxes(title_text="Δ vs. 1ª medición (pp)", range=[-dmax, dmax], gridcolor=GRID, row=2, col=1)
    fig.update_xaxes(gridcolor=GRID)
    fig.update_xaxes(title_text="Longitud de onda (nm)", row=2, col=1)
    st.plotly_chart(fig, width="stretch")
else:
    st.info("Elige al menos una hoja para la animación.")

# ---------- 8. tabla y descarga ----------
with st.container(border=True):
    render_index_legend(INDEX_DEFINITIONS)
    st.subheader("10. Serie por hoja y fecha")
    st.caption("Una fila por hoja y fecha (media de puntos). Incluye Δ, Δ*, severidad S1/S2 y el control de calidad.")
    sev_full = severity_timeseries(files, anchors, clip=True)
    out = ts.merge(sev_full[["leaf_id", "campaign_date", "sev_S1", "sev_S2"]], on=["leaf_id", "campaign_date"], how="left")
    out_sp = out[(out["species"] == species) & out["leaf"].isin(sel_leaves)].copy()
    out_sp["campaign_date"] = out_sp["campaign_date"].dt.strftime("%Y-%m-%d")
    base_cols = ["species", "leaf", "campaign_id", "campaign_date", "dia", "dia_roya", "n_puntos",
                 "n_archivos", "qc_atipico", "sev_S1", "sev_S2"]
    st.dataframe(
        out_sp[base_cols + INDICES],
        width="stretch", hide_index=True,
        column_config={
            **index_column_config(INDICES),
            "sev_S1": st.column_config.NumberColumn("sev_S1", format="%.3f"),
            "sev_S2": st.column_config.NumberColumn("sev_S2", format="%.3f"),
        },
    )
    out_all = out.copy()
    out_all["campaign_date"] = out_all["campaign_date"].dt.strftime("%Y-%m-%d")
    st.download_button(
        "Descargar CSV (todas las especies, todas las columnas)",
        out_all.to_csv(index=False).encode("utf-8"),
        file_name="evolucion_temporal_hojas.csv",
        mime="text/csv",
        icon="⬇️",
    )
