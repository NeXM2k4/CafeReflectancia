"""Imagen del mensaje de alerta de Telegram para el paper (Fig. 7), SIN el indice ND705/EDI.

Datos reales de las 5 campanas: hoja R1 de Bourbon del 27/07/2026 (promedio de p1-p3).
Anclas por variedad (como el codigo de la app): 0 = media de las hojas tiernas (H), 1 = media de la
hoja con roya (R); cada indice se normaliza, se recorta a [0,1] y el score es la MEDIANA. El nivel es
el mas cercano de los 11 (0, 10, ..., 100 %).
NOTA: es una reconstruccion del formato (formato_mensaje.txt) con numeros reales, no una captura del
bot actual (la app ya usa 4 clases en espanol).

Uso (desde la raiz del repo):  python PAPER/FINAL_VERSION/make_alert_message.py
"""
from __future__ import annotations
import sys, warnings
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1])); sys.path.insert(0, str(HERE)); warnings.filterwarnings("ignore")

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch
import make_final_figures as m

SPECIES, CAMP, LEAF = "Bourbon", "Roya_27_07", ("R", 1.0)
SHOW = [n for n in m.ORDER if n != "ND705"]           # 7 indices, sin ND705 (EDI)
ALERT_THRESHOLD = 0.66
LEVELS = [(0.0, "Healthy", "#2E8B57"), (0.1, "Incipient", "#2E8B57"), (0.2, "Very light", "#E0B000"),
          (0.3, "Light", "#E0B000"), (0.4, "Beginning of moderate", "#E0B000"), (0.5, "Moderate", "#E67E22"),
          (0.6, "Beginning of severe", "#E67E22"), (0.7, "Severe", "#D03B3B"), (0.8, "Very severe", "#D03B3B"),
          (0.9, "Critical", "#D03B3B"), (1.0, "Very critical", "#222222")]
ACTIONS = [(0.15, "No action needed: keep the usual monitoring routine."),
           (0.35, "Scout the lower third of the plant and repeat the measurement in the coming days."),
           (0.55, "Apply preventive control and check neighbouring plants for spread."),
           (0.75, "Treat this plant as soon as possible; the infection is already established."),
           (1.01, "Treat urgently and assess whether the plant can still be recovered.")]


# Tema claro, para que la imagen se integre en la pagina blanca del paper
FONDO = "#FFFFFF"            # lienzo
BURBUJA = "#F3F6F9"          # mensaje: gris azulado muy suave
BORDE = "#D9E1E8"
TEXTO = "#1F2933"            # texto principal
SECUNDARIO = "#52606D"       # fecha, encabezado de la tabla
REFERENCIA = "#6B7C8D"       # valores de referencia sana y accion recomendada
NOTA = "#8A97A3"             # nota al pie


def main() -> None:
    p = m.points(m.build_files())
    s = p[p.species == SPECIES]
    cols = [m.NAMES[n] for n in SHOW]
    H, R = s[s.sess == "T"][cols].mean(), s[s.sess == "R"][cols].mean()
    leaf = s[(s.camp == CAMP) & (s.sess == LEAF[0]) & (s.num == LEAF[1]) & s.pt.isin([1, 2, 3])][cols].mean()
    norm = ((leaf - H) / (R - H)).clip(0, 1)
    score = float(norm.median())
    level, name, color = min(LEVELS, key=lambda c: abs(c[0] - score))
    action = next(t for lim, t in ACTIONS if score < lim)
    print(f"score = {score:.3f} -> {name} ({level:.0%}); indices:\n{norm.round(2).to_string()}")

    plt.rcParams["font.family"] = "DejaVu Sans"
    Wd, Ht = 4.6, 5.2
    fig = plt.figure(figsize=(Wd, Ht), dpi=300); fig.patch.set_facecolor("white")
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, Wd); ax.set_ylim(0, Ht); ax.axis("off")
    W, SUB, DIM = "#111111", "#444444", "#666666"
    x0, x1 = 0.22, Wd - 0.22                      # margenes laterales: el texto ocupa todo el ancho
    y = Ht - 0.34
    ax.add_patch(Circle((x0 + 0.11, y), 0.11, fc=color, ec="none"))
    ax.text(x0 + 0.34, y, name, color=W, fontsize=15, fontweight="bold", va="center")
    ax.text(x1, y, f"{score * 100:.0f} %", color=color if color != "#222222" else "#111111", fontsize=15, fontweight="bold", va="center", ha="right")
    y -= 0.40
    ax.text(x0, y, f"Date: 27/07/2026 - {SPECIES} - R1", color=SUB, fontsize=10.5, va="center")
    y -= 0.40
    ax.text(x0, y, f"Estimated severity: {score * 100:.0f} % compared to a", color=W, fontsize=11.5, va="center"); y -= 0.25
    ax.text(x0, y, "healthy reference.", color=W, fontsize=11.5, va="center"); y -= 0.30
    for ln in _wrap(action, 46):
        ax.text(x0, y, ln, color=DIM, fontsize=10.2, style="italic", va="center"); y -= 0.23
    y -= 0.12
    ax.plot([x0, x1], [y + 0.1, y + 0.1], color="#BBBBBB", lw=0.8)
    ax.text(x0, y - 0.08, "Index", color=SUB, fontsize=9.6, va="center")
    ax.text(x0 + 1.75, y - 0.08, "Value", color=SUB, fontsize=9.6, va="center", ha="right")
    ax.text(x0 + 2.95, y - 0.08, "Healthy ref.", color=SUB, fontsize=9.6, va="center", ha="right")
    ax.text(x1, y - 0.08, "Similarity", color=SUB, fontsize=9.6, va="center", ha="right")
    y -= 0.38
    for n, c in zip(SHOW, cols):
        v = leaf[c]; h = H[c]; alert = norm[c] >= ALERT_THRESHOLD
        d = 2 if n == "CRI1" else 3
        wt = "bold" if alert else "normal"
        ax.text(x0, y, n, color=W, fontsize=11.5, fontweight=wt, va="center")
        ax.text(x0 + 1.75, y, f"{v:.{d}f}", color=W, fontsize=11.5, fontweight=wt, va="center", ha="right", family="DejaVu Sans Mono")
        ax.text(x0 + 2.95, y, f"{h:.{d}f}", color=DIM, fontsize=11.5, va="center", ha="right", family="DejaVu Sans Mono")
        ax.text(x1, y, f"{norm[c] * 100:.0f} %", color=W, fontsize=11.5, fontweight=wt, va="center", ha="right", family="DejaVu Sans Mono")
        y -= 0.31
    ax.text(x0, 0.34, "Similarity: 0 % = like the healthy reference, 100 % = like the rust reference.", color="#666666", fontsize=7.6, va="center")
    ax.text(x0, 0.15, "Bold: index in the alert range (similarity >= 66 %).", color="#666666", fontsize=7.6, va="center")
    fig.savefig(HERE / "fig_alert_message_telegram.png", dpi=300, facecolor=fig.get_facecolor()); plt.close(fig)


def _wrap(t: str, n: int) -> list[str]:
    out, cur = [], ""
    for w in t.split():
        if len(cur) + len(w) + 1 > n and cur:
            out.append(cur); cur = w
        else:
            cur = f"{cur} {w}".strip()
    return out + [cur]


if __name__ == "__main__":
    main()
