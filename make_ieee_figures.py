"""Genera las figuras del paper (IEEE / CONCAPAN) en figures_ieee/.

Todo el contenido de las figuras esta en INGLES (titulos, ejes, leyendas, nombres de archivo)
porque el paper se presenta en ingles.

Son 29 figuras (8 indices: NDVI, PRI, PSRI, RCI, EDI, FSR, NDRE, mNDVI705):
  - 16 boxplots: 8 indices x 2 especies, Healthy vs. Rust-infected.
  - 8 boxplots de comparacion entre especies (uno por indice).
  - 2 curvas de reflectancia media +- 1 SE + espectro de diferencia (Bourbon y Pacamara).
  - 3 figuras resumen para un paper de 4 paginas (ver `figures_ieee/README.md`).

Las especies se toman de `get_dataset()`, que filtra por `config.EXCLUDED_SPECIES` (vacia desde
el 2026-09-11: las 4 especies vuelven a incluirse). El script no las nombra en ningun lado:
recorre las especies que efectivamente vengan en el dataset. La categoria
`SPECIES_PENDING_LABEL` ("hoja vieja" sin especie identificada, ver `config.py`) nunca aparece
aqui porque solo trae hojas Vieja: ninguna es Tierna (Healthy) ni Con roya (Rust), los unicos
dos grupos que entran en estas figuras.

Decisiones de analisis (acordadas con el usuario, 2026-08-02):

- **Unidad de observacion: el punto de medicion.** Se promedian las medidas repetidas de
  cada punto (3 en las hojas M/T, 10 en las hojas R). No se agrega hasta el nivel de hoja
  porque las campañas de roya tienen **una sola hoja R por campaña**: a nivel hoja el grupo
  con roya quedaria en n=2, sin cuartiles ni test valido.
- **Grupo "Healthy" = hojas tiernas (T) unicamente.** Es la misma referencia sana que usa el
  score de severidad: la roya no tuvo tiempo de manifestarse en tejido nuevo. Las hojas
  maduras (M) son de estado sanitario desconocido, asi que no entran en ningun grupo.

Uso:
    python make_ieee_figures.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin backend interactivo: el script corre fuera de Streamlit

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

from src.config import INDEX_DEFINITIONS, X_MAX, X_MIN  # noqa: E402
from src.parser import get_dataset, leaf_label, load_spectrum  # noqa: E402
from src.processing import average_group, calcular_indices, prepare_spectrum  # noqa: E402
from src.stats_utils import compare_groups  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "figures_ieee"

INDICES = list(INDEX_DEFINITIONS)

# Etiquetas en ingles para el paper. "Canephora" es la grafia correcta de Coffea canephora.
# Los mapeos cubren las 4 especies que el parser reconoce, no las que se grafican: las que
# esten en `config.EXCLUDED_SPECIES` nunca llegan aqui porque `get_dataset()` ya las filtro.
# Se dejan completos para que reactivar una especie sea solo tocar esa tupla.
SPECIES_DISPLAY = {
    "Bourbon": "Bourbon",
    "Canefora": "Canephora",
    "Cuscatleco": "Cuscatleco",
    "Pacamara": "Pacamara",
}
# El grupo sano son las hojas tiernas (T): misma referencia sana que usa el score de severidad.
# Las hojas maduras (M) tienen estado sanitario desconocido y quedan fuera de las figuras.
GROUP_HEALTHY = "Healthy (young)"
GROUP_RUST = "Rust-infected"
GROUP_ORDER = [GROUP_HEALTHY, GROUP_RUST]

GROUP_COLORS = {GROUP_HEALTHY: "#2E8B57", GROUP_RUST: "#C0392B"}

# Por debajo de ~440 nm la señal del espectrometro es tan baja que un 13 % de los espectros
# con roya da reflectancia negativa (hasta -365 %), lo que deforma la banda de SD. Ningun
# indice usa bandas por debajo de 500 nm, asi que recortar la figura no afecta el analisis.
SPECTRA_MIN_NM = 440
SPECIES_COLORS_PRINT = {
    "Bourbon": "#2C6FBB",
    "Canephora": "#2E8B57",
    "Cuscatleco": "#B5497F",
    "Pacamara": "#C98500",
}

# Abreviaturas para el eje X de la figura resumen de cultivares (la leyenda las expande).
SPECIES_SHORT = {
    "Bourbon": "B",
    "Canephora": "Ca",
    "Cuscatleco": "C",
    "Pacamara": "P",
}

# Titulo dentro de la figura: IEEE normalmente usa el caption de LaTeX en su lugar.
# Poner en False si se prefiere la figura sin titulo.
SHOW_TITLES = True
# Anotacion del p-valor del test automatico (Shapiro -> ANOVA o Kruskal-Wallis).
SHOW_PVALUE = True

FIG_W, FIG_H = 3.5, 2.6  # ancho de una columna IEEE en pulgadas
FIG_W2 = 7.16  # ancho de dos columnas IEEE, para las figuras resumen multipanel
DPI = 600

# Especies con muestras de roya: las unicas donde existe la comparacion sana vs. enferma.
SUSCEPTIBLE_DISPLAY = ["Bourbon", "Pacamara"]

# Tipografia de las figuras resumen: van a dos columnas y se leen impresas, asi que usan
# cuerpos mayores que los paneles individuales.
SUMMARY_TICK_SIZE = 8.5
SUMMARY_TITLE_SIZE = 10.5
SUMMARY_XLABEL_SIZE = 9.5
# Los asteriscos son glifos pequeños y elevados: necesitan bastante mas cuerpo que el resto
# del texto (y negrita) para leerse impresos a tamaño de figura.
SUMMARY_STAR_SIZE = 14
SUMMARY_LEGEND_SIZE = 9.5
SUMMARY_FOOTNOTE_SIZE = 9.5
RNG = np.random.default_rng(20260802)  # jitter reproducible entre corridas


def apply_style() -> None:
    """Estilo de publicacion: fondo blanco, tipografia serif, lineas finas, sin ruido visual."""
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 7,
        "axes.linewidth": 0.7,
        "axes.edgecolor": "#000000",
        "xtick.major.width": 0.7,
        "ytick.major.width": 0.7,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "lines.linewidth": 1.0,
        "legend.frameon": False,
    })


def _group_of(row) -> str | None:
    """Grupo de la figura: hoja tierna sana, hoja con roya, o fuera de analisis (hoja madura)."""
    if row.health_status == "Con roya":
        return GROUP_RUST
    if row.leaf_maturity == "Tierna":
        return GROUP_HEALTHY
    return None


def point_level_indices(df: pd.DataFrame) -> pd.DataFrame:
    """Tabla de indices con una fila por punto de medicion (promedio de sus medidas repetidas).

    Promediar las repeticiones tecnicas quita el ruido del espectrometro sin colapsar la
    variabilidad entre puntos, que es la que sostiene el n del grupo con roya.
    """
    filas = []
    for row in df[df["name_recognized"]].itertuples():
        grupo = _group_of(row)
        if grupo is None:
            continue
        try:
            idx = calcular_indices(prepare_spectrum(load_spectrum(row.path)))
        except ValueError:
            continue
        filas.append({
            "species": SPECIES_DISPLAY.get(row.species, row.species),
            "campaign": row.campaign_id,
            "group": grupo,
            "leaf": leaf_label(row.session, row.session_num),
            "point": row.point,
            **idx,
        })

    medidas = pd.DataFrame(filas)
    claves = ["species", "campaign", "group", "leaf", "point"]
    return medidas.groupby(claves, dropna=False)[INDICES].mean().reset_index()


def _pvalue_text(grupos: dict[str, list]) -> str | None:
    """Test automatico (parametrico o no segun Shapiro) formateado para anotar en la figura."""
    if not SHOW_PVALUE or len(grupos) < 2:
        return None
    res = compare_groups(grupos)
    p = res.get("p_value")
    if p is None or np.isnan(p):
        return None
    nombre = "ANOVA" if res["test_name"] == "ANOVA" else "Kruskal-Wallis"
    return f"{nombre}: p < 0.001" if p < 0.001 else f"{nombre}: p = {p:.3f}"


def _draw_boxplot(ax, grupos: dict[str, list], colores: dict[str, str], ylabel: str) -> None:
    """Boxplot con los puntos individuales superpuestos (n chico: conviene mostrar cada hoja)."""
    labels = list(grupos)
    datos = [grupos[k] for k in labels]

    bp = ax.boxplot(
        datos,
        widths=0.5,
        patch_artist=True,
        showfliers=False,  # los outliers ya se ven en la capa de puntos individuales
        medianprops=dict(color="black", linewidth=1.1),
        boxprops=dict(linewidth=0.7, edgecolor="black"),
        whiskerprops=dict(linewidth=0.7, color="black"),
        capprops=dict(linewidth=0.7, color="black"),
    )
    for parche, etiqueta in zip(bp["boxes"], labels):
        parche.set_facecolor(colores.get(etiqueta, "#999999"))
        parche.set_alpha(0.35)

    for i, (etiqueta, valores) in enumerate(grupos.items(), start=1):
        if not valores:
            continue
        jitter = RNG.uniform(-0.13, 0.13, size=len(valores))
        ax.scatter(
            np.full(len(valores), i) + jitter,
            valores,
            s=7,
            facecolors="none",
            edgecolors=colores.get(etiqueta, "#999999"),
            linewidths=0.6,
            alpha=0.85,
            zorder=3,
        )

    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels([f"{k}\n(n = {len(grupos[k])})" for k in labels])
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.4, alpha=0.9)
    ax.set_axisbelow(True)
    ax.margins(y=0.16)

    texto = _pvalue_text({k: v for k, v in grupos.items() if len(v) >= 2})
    if texto:
        ax.text(0.98, 0.97, texto, transform=ax.transAxes, ha="right", va="top", fontsize=7)


def figure_species_boxplots(points: pd.DataFrame) -> list[tuple[str, str]]:
    """8 indices x cada especie del dataset: hojas tiernas sanas vs. hojas con roya."""
    generadas = []
    for species in sorted(points["species"].unique()):
        sub = points[points["species"] == species]
        for index_name in INDICES:
            grupos = {
                grupo: sub.loc[sub["group"] == grupo, index_name].dropna().tolist()
                for grupo in GROUP_ORDER
                if (sub["group"] == grupo).any()
            }
            fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
            _draw_boxplot(ax, grupos, GROUP_COLORS, index_name)
            ax.tick_params(axis="x", labelsize=7)
            if SHOW_TITLES:
                ax.set_title(f"{species} — {index_name}")
            nombre = f"boxplot_{species.lower()}_{index_name.lower()}.png"
            fig.savefig(OUT_DIR / nombre, dpi=DPI)
            plt.close(fig)
            detalle = ", ".join(f"{g} n = {len(v)}" for g, v in grupos.items())
            generadas.append((nombre, f"{species}, {index_name} ({detalle} points)"))
    return generadas


def figure_species_comparison(points: pd.DataFrame) -> list[tuple[str, str]]:
    """8 figuras: los cultivares del dataset comparados entre si, un indice por figura.

    Se comparan solo hojas tiernas sanas: mismo tipo de tejido en todas las especies, para que
    la diferencia entre cultivares no quede mezclada con la presencia de roya.
    """
    generadas = []
    sanas = points[points["group"] == GROUP_HEALTHY]
    orden = [s for s in SPECIES_DISPLAY.values() if s in set(sanas["species"])]
    for index_name in INDICES:
        grupos = {
            species: sanas.loc[sanas["species"] == species, index_name].dropna().tolist()
            for species in orden
        }
        fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
        _draw_boxplot(ax, grupos, SPECIES_COLORS_PRINT, index_name)
        ax.tick_params(axis="x", labelsize=7)
        if SHOW_TITLES:
            ax.set_title(f"Cultivar comparison — {index_name}")
        nombre = f"species_comparison_{index_name.lower()}.png"
        fig.savefig(OUT_DIR / nombre, dpi=DPI)
        plt.close(fig)
        detalle = ", ".join(f"{s} n = {len(v)}" for s, v in grupos.items())
        generadas.append((nombre, f"{index_name}, healthy young leaves ({detalle} points)"))
    return generadas


def _bh_significant(pvals: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """Benjamini-Hochberg: controla la tasa de falsos descubrimientos al testear miles de bandas.

    Sin correccion, testear ~3000 longitudes de onda daria ~150 "significativas" solo por azar.

    Ya no se usa en las figuras (se quito el sombreado de bandas significativas a pedido del
    usuario); se conserva por si se quiere volver a marcar las regiones significativas.
    """
    n = len(pvals)
    orden = np.argsort(pvals)
    umbral = alpha * np.arange(1, n + 1) / n
    pasa = pvals[orden] <= umbral
    if not pasa.any():
        return np.zeros(n, dtype=bool)
    corte = np.max(np.flatnonzero(pasa))
    significativo = np.zeros(n, dtype=bool)
    significativo[orden[: corte + 1]] = True
    return significativo


def _spectra_matrix(filas: pd.DataFrame, grid: np.ndarray | None) -> tuple[np.ndarray, np.ndarray] | None:
    """Matriz (mediciones x longitudes de onda) interpolada a una grilla comun."""
    curvas, malla = [], grid
    for row in filas.itertuples():
        try:
            espectro = prepare_spectrum(load_spectrum(row.path))
        except ValueError:
            continue
        espectro = espectro[espectro["wavelength"] >= SPECTRA_MIN_NM]
        if malla is None:
            malla = espectro["wavelength"].to_numpy()
        curvas.append(np.interp(malla, espectro["wavelength"], espectro["smooth"]))
    if not curvas:
        return None
    return np.asarray(curvas), malla


def figure_spectra(df: pd.DataFrame, species: str) -> tuple[str, str] | None:
    """Reflectancia sana vs. con roya, en dos paneles.

    (a) media +- 1 SE. Se usa el error estandar de la media y no la SD porque lo que se compara
        son las medias de grupo: la SD entre mediciones (12-16 puntos de reflectancia, por
        variacion de acoplamiento sonda-hoja y entre hojas) es varias veces mayor que la
        diferencia entre grupos y tapaba por completo el efecto.
    (b) diferencia espectral (roya - sana), en puntos de reflectancia.
    """
    sub = df[(df["species"] == species) & df["name_recognized"]]
    display = SPECIES_DISPLAY.get(species, species)

    subconjuntos = {
        GROUP_HEALTHY: sub[sub["leaf_maturity"] == "Tierna"],
        GROUP_RUST: sub[sub["health_status"] == "Con roya"],
    }

    matrices: dict[str, np.ndarray] = {}
    grid = None
    for grupo, filas in subconjuntos.items():
        resultado = _spectra_matrix(filas, grid)
        if resultado is None:
            continue
        matrices[grupo], grid = resultado

    if len(matrices) < 2:
        print(f"  ! {display}: falta uno de los dos grupos, se omite")
        return None

    sana, roya = matrices[GROUP_HEALTHY], matrices[GROUP_RUST]
    diferencia = roya.mean(axis=0) - sana.mean(axis=0)

    fig, (ax, ax_d) = plt.subplots(
        2, 1, figsize=(FIG_W, FIG_H * 1.45), sharex=True,
        gridspec_kw={"height_ratios": [2.4, 1], "hspace": 0.12},
    )

    for grupo in GROUP_ORDER:
        datos, color = matrices[grupo], GROUP_COLORS[grupo]
        media = datos.mean(axis=0)
        se = datos.std(axis=0, ddof=1) / np.sqrt(len(datos))
        ax.fill_between(grid, media - se, media + se, color=color, alpha=0.30, linewidth=0)
        ax.plot(grid, media, color=color, linewidth=1.2, label=f"{grupo} (n = {len(datos)})")

    ax.set_ylabel("Reflectance (%)")
    ax.set_ylim(bottom=0)
    ax.grid(color="#DDDDDD", linewidth=0.4, alpha=0.9)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left")
    if SHOW_TITLES:
        ax.set_title(f"{display} — mean reflectance ± 1 SE")

    ax_d.axhline(0, color="#666666", linewidth=0.6)
    ax_d.plot(grid, diferencia, color="#333333", linewidth=1.0)
    ax_d.set_xlabel("Wavelength (nm)")
    ax_d.set_ylabel("Δ reflectance\n(rust − healthy)")
    ax_d.set_xlim(SPECTRA_MIN_NM, X_MAX)
    ax_d.grid(color="#DDDDDD", linewidth=0.4, alpha=0.9)
    ax_d.set_axisbelow(True)

    nombre = f"spectra_{display.lower()}_healthy_vs_rust.png"
    fig.savefig(OUT_DIR / nombre, dpi=DPI)
    plt.close(fig)
    detalle = ", ".join(f"{g} n = {len(m)}" for g, m in matrices.items())
    return nombre, f"{display}, mean ± SE + difference spectrum ({detalle} measurements)"


def _stars(p: float | None) -> str:
    """Notacion de significancia habitual en figuras de paper."""
    if p is None or np.isnan(p):
        return "n/a"
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


def _pairwise_pvalues(res: dict, labels: list[str]) -> dict[frozenset, float]:
    """P-valores por pares del post-hoc, unificando el formato de Tukey y el de Dunn.

    `compare_groups()` solo corre el post-hoc si el test global dio significativo; si no lo
    corrio, se devuelve vacio y todos los grupos quedan sin diferencias entre si.

    Ya no se usa en las figuras (se quito la anotacion estadistica de summary_cultivars);
    se conserva junto con `_compact_letters()` por si se quiere volver a mostrarla.
    """
    posthoc = res.get("posthoc")
    if posthoc is None:
        return {}

    pares: dict[frozenset, float] = {}
    if (res.get("posthoc_name") or "").startswith("Tukey"):
        # Tabla de statsmodels: group1 | group2 | meandiff | p-adj | lower | upper | reject.
        # Se accede por nombre porque 'p-adj' no es un identificador valido para itertuples.
        col_p = next(c for c in posthoc.columns if str(c).startswith("p-adj"))
        for _, fila in posthoc.iterrows():
            pares[frozenset((fila["group1"], fila["group2"]))] = float(fila[col_p])
    else:  # Dunn: matriz cuadrada label x label
        for a in labels:
            for b in labels:
                if a != b and a in posthoc.index and b in posthoc.columns:
                    pares[frozenset((a, b))] = float(posthoc.loc[a, b])
    return pares


def _compact_letters(labels: list[str], pares: dict[frozenset, float], alpha: float = 0.05) -> dict[str, str]:
    """Letras de agrupamiento: dos grupos que comparten letra no difieren significativamente.

    Es la notacion habitual en papers agronomicos, y responde lo que un p global no puede
    responder con 4 cultivares: cual es distinto de cual.
    """
    if not pares:
        return {etiqueta: "a" for etiqueta in labels}

    def sin_diferencia(a: str, b: str) -> bool:
        p = pares.get(frozenset((a, b)))
        return p is None or np.isnan(p) or p >= alpha

    # Cliques maximales del grafo "no difieren": con 4 cultivares alcanza la fuerza bruta.
    cliques: list[set] = []
    for mascara in range(1, 1 << len(labels)):
        grupo = {labels[i] for i in range(len(labels)) if mascara >> i & 1}
        if all(sin_diferencia(a, b) for a in grupo for b in grupo if a < b):
            cliques.append(grupo)
    maximales = [c for c in cliques if not any(c < otro for otro in cliques)]
    maximales.sort(key=lambda c: sorted(labels.index(x) for x in c))

    letras = {etiqueta: "" for etiqueta in labels}
    for i, clique in enumerate(maximales):
        for etiqueta in clique:
            letras[etiqueta] += chr(ord("a") + i)
    return letras


def _panel_box(ax, cajas: list[tuple[list, str]], posiciones: list[float]) -> None:
    """Boxplot compacto para un panel de figura resumen (sin etiquetas de eje X)."""
    bp = ax.boxplot(
        [c[0] for c in cajas],
        positions=posiciones,
        widths=0.62,
        patch_artist=True,
        showfliers=False,
        medianprops=dict(color="black", linewidth=0.9),
        boxprops=dict(linewidth=0.5, edgecolor="black"),
        whiskerprops=dict(linewidth=0.5, color="black"),
        capprops=dict(linewidth=0.5, color="black"),
    )
    for parche, (_, color) in zip(bp["boxes"], cajas):
        parche.set_facecolor(color)
        parche.set_alpha(0.38)
    for pos, (valores, color) in zip(posiciones, cajas):
        if not valores:
            continue
        jitter = RNG.uniform(-0.15, 0.15, size=len(valores))
        ax.scatter(
            np.full(len(valores), pos) + jitter, valores,
            s=4, facecolors="none", edgecolors=color, linewidths=0.45, alpha=0.8, zorder=3,
        )
    ax.grid(axis="y", color="#DDDDDD", linewidth=0.4, alpha=0.9)
    ax.set_axisbelow(True)
    ax.margins(y=0.26)
    ax.tick_params(labelsize=SUMMARY_TICK_SIZE)
    # Menos marcas en Y: con la tipografia mas grande, 5 alcanzan y liberan ancho entre paneles.
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5))


def _summary_grid():
    """Grilla cuadrada: un panel por indice + el hueco final reservado para la leyenda."""
    lado = int(np.ceil(np.sqrt(len(INDICES) + 1)))
    filas = int(np.ceil((len(INDICES) + 1) / lado))
    fig, axes = plt.subplots(filas, lado, figsize=(FIG_W2, 2.05 * filas))
    # Paneles mas juntos para aprovechar el ancho de las dos columnas IEEE.
    fig.subplots_adjust(hspace=0.30, wspace=0.20, left=0.055, right=0.995, top=0.94, bottom=0.06)
    ejes = axes.ravel()
    for sobrante in ejes[len(INDICES) + 1:]:  # celdas de mas cuando la grilla no cierra justo
        sobrante.axis("off")
    return fig, ejes


def figure_summary_rust(points: pd.DataFrame) -> tuple[str, str]:
    """UNA figura que reemplaza los 16 boxplots de las especies susceptibles.

    8 paneles (uno por indice); en cada panel, sana vs. roya para Bourbon y para Pacamara.
    """
    fig, axes = _summary_grid()
    especies = [s for s in SUSCEPTIBLE_DISPLAY if s in set(points["species"])]

    for ax, index_name in zip(axes, INDICES):
        cajas, posiciones, centros = [], [], []
        for i, species in enumerate(especies):
            base = i * 2.6
            for j, grupo in enumerate(GROUP_ORDER):
                valores = points.loc[
                    (points["species"] == species) & (points["group"] == grupo), index_name
                ].dropna().tolist()
                cajas.append((valores, GROUP_COLORS[grupo]))
                posiciones.append(base + j)
            centros.append(base + 0.5)

        _panel_box(ax, cajas, posiciones)
        ax.set_xticks(centros)
        ax.set_xticklabels(especies, fontsize=SUMMARY_XLABEL_SIZE)
        ax.set_title(index_name, fontsize=SUMMARY_TITLE_SIZE, pad=3)

        # Asterisco de significancia sobre cada par sana/roya.
        for i, species in enumerate(especies):
            sub = points[points["species"] == species]
            grupos = {
                g: sub.loc[sub["group"] == g, index_name].dropna().tolist() for g in GROUP_ORDER
            }
            if all(len(v) >= 2 for v in grupos.values()):
                res = compare_groups(grupos)
                ax.text(
                    i * 2.6 + 0.5, 0.97, _stars(res.get("p_value")),
                    transform=ax.get_xaxis_transform(), ha="center", va="top",
                    fontsize=SUMMARY_STAR_SIZE, fontweight="bold",
                )

    leyenda = axes[len(INDICES)]
    leyenda.axis("off")
    leyenda.legend(
        handles=[Patch(facecolor=GROUP_COLORS[g], alpha=0.38, edgecolor="black", linewidth=0.5, label=g)
                 for g in GROUP_ORDER],
        loc="center", fontsize=SUMMARY_LEGEND_SIZE, frameon=False,
    )
    leyenda.text(
        0.5, 0.18, "*** p<0.001   ** p<0.01\n* p<0.05   ns: not significant",
        transform=leyenda.transAxes, ha="center", va="center",
        fontsize=SUMMARY_FOOTNOTE_SIZE, color="#555555", linespacing=1.5,
    )

    nombre = "summary_rust_vs_healthy.png"
    fig.savefig(OUT_DIR / nombre, dpi=DPI)
    plt.close(fig)
    return nombre, "All 8 indices, healthy young vs. rust-infected, Bourbon and Pacamara (replaces the 16 single-species boxplots)"


def figure_summary_cultivars(points: pd.DataFrame) -> tuple[str, str]:
    """UNA figura que reemplaza los 8 boxplots de comparacion entre cultivares."""
    fig, axes = _summary_grid()
    sanas = points[points["group"] == GROUP_HEALTHY]
    orden = [s for s in SPECIES_DISPLAY.values() if s in set(sanas["species"])]

    for ax, index_name in zip(axes, INDICES):
        cajas, posiciones = [], list(range(len(orden)))
        grupos = {}
        for species in orden:
            valores = sanas.loc[sanas["species"] == species, index_name].dropna().tolist()
            grupos[species] = valores
            cajas.append((valores, SPECIES_COLORS_PRINT[species]))

        _panel_box(ax, cajas, posiciones)
        ax.set_xticks(posiciones)
        ax.set_xticklabels([SPECIES_SHORT.get(s, s[:2]) for s in orden], fontsize=SUMMARY_XLABEL_SIZE)
        ax.set_title(index_name, fontsize=SUMMARY_TITLE_SIZE, pad=3)

        # Solo el asterisco del test global entre los 4 cultivares. Sin letras de agrupamiento
        # post-hoc: se probaron y resultaron dificiles de leer. El asterisco dice si algun
        # cultivar difiere; identificar cual queda para el texto del paper.
        res = compare_groups({k: v for k, v in grupos.items() if len(v) >= 2})
        ax.text(
            0.97, 0.97, _stars(res.get("p_value")), transform=ax.transAxes,
            ha="right", va="top", fontsize=SUMMARY_STAR_SIZE, fontweight="bold",
        )

    leyenda = axes[len(INDICES)]
    leyenda.axis("off")
    leyenda.legend(
        handles=[Patch(facecolor=SPECIES_COLORS_PRINT[s], alpha=0.38, edgecolor="black",
                       linewidth=0.5, label=f"{SPECIES_SHORT.get(s, s)}: {s}") for s in orden],
        loc="upper center", fontsize=SUMMARY_LEGEND_SIZE, frameon=False,
    )
    leyenda.text(
        0.5, 0.16, "*** p<0.001   ** p<0.01\n* p<0.05   ns: not significant",
        transform=leyenda.transAxes, ha="center", va="center",
        fontsize=SUMMARY_FOOTNOTE_SIZE, color="#555555", linespacing=1.5,
    )

    nombre = "summary_cultivars.png"
    fig.savefig(OUT_DIR / nombre, dpi=DPI)
    plt.close(fig)
    return nombre, "All 8 indices across the cultivars analysed, healthy young leaves (replaces the 8 cultivar-comparison boxplots)"


def _cliffs_delta(a: list[float], b: list[float]) -> float:
    """Tamaño de efecto no parametrico: -1 a +1, independiente de la escala del indice."""
    x, y = np.asarray(a)[:, None], np.asarray(b)[None, :]
    return float((np.sign(y - x)).mean())


def figure_effect_size(points: pd.DataFrame) -> tuple[str, str]:
    """Alternativa de UNA sola figura: tamaño de efecto de los 8 indices en las 2 especies.

    Cliff's delta (roya vs. sana) con intervalo bootstrap: resume todas las comparaciones sin
    depender de la escala de cada indice, que varia en varios ordenes de magnitud entre ellos.
    """
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H * 1.55))
    especies = [s for s in SUSCEPTIBLE_DISPLAY if s in set(points["species"])]
    etiquetas, y = [], 0

    for index_name in reversed(INDICES):
        for species in reversed(especies):
            sub = points[points["species"] == species]
            sana = sub.loc[sub["group"] == GROUP_HEALTHY, index_name].dropna().tolist()
            roya = sub.loc[sub["group"] == GROUP_RUST, index_name].dropna().tolist()
            if len(sana) < 2 or len(roya) < 2:
                continue
            delta = _cliffs_delta(sana, roya)
            boot = [
                _cliffs_delta(
                    list(RNG.choice(sana, len(sana), replace=True)),
                    list(RNG.choice(roya, len(roya), replace=True)),
                )
                for _ in range(400)
            ]
            lo, hi = np.percentile(boot, [2.5, 97.5])
            color = SPECIES_COLORS_PRINT[species]
            ax.plot([lo, hi], [y, y], color=color, linewidth=1.0, solid_capstyle="round")
            ax.plot(delta, y, "o", color=color, markersize=3.5)
            etiquetas.append((y, f"{index_name} · {species}"))
            y += 1

    ax.axvline(0, color="#666666", linewidth=0.7, linestyle="--")
    ax.set_yticks([p for p, _ in etiquetas])
    ax.set_yticklabels([t for _, t in etiquetas], fontsize=6)
    ax.set_xlabel("Cliff's δ  (rust vs. healthy, 95 % bootstrap CI)")
    ax.set_xlim(-1.05, 1.05)
    ax.grid(axis="x", color="#DDDDDD", linewidth=0.4, alpha=0.9)
    ax.set_axisbelow(True)
    if SHOW_TITLES:
        ax.set_title("Effect size per index and cultivar", fontsize=8)

    nombre = "summary_effect_size.png"
    fig.savefig(OUT_DIR / nombre, dpi=DPI)
    plt.close(fig)
    return nombre, "Cliff's delta with bootstrap CI, 8 indices x 2 cultivars (single-figure alternative to all boxplots)"


def write_index(entradas: list[tuple[str, str]]) -> None:
    """Indice de figuras en ingles, para copiar los captions al paper."""
    lineas = [
        "# IEEE / CONCAPAN figures",
        "",
        "Generated by `make_ieee_figures.py` (run it again to refresh after adding new data).",
        "White background, Times New Roman, single-column width (3.5 in), 600 dpi PNG.",
        "",
        "## How the groups are defined",
        "",
        "- **Healthy (young):** young leaves (`T` prefix). Rust has not had time to develop in new",
        "  tissue, so these are the healthy reference — the same anchor the severity score uses.",
        "- **Rust-infected:** leaves with confirmed rust (`R` prefix).",
        "- **Mature leaves (`M`) are excluded** from every figure: their health status is unknown,",
        "  which is precisely what the severity model is meant to estimate.",
        "",
        "**Observation unit: the measurement point.** Repeated measurements of the same point are",
        "averaged first (3 per point on M/T leaves, 10 per point on R leaves). Data are not",
        "aggregated up to the leaf because each rust campaign sampled a single rust leaf, which",
        "would leave the rust group at n = 2. Individual points are overlaid as open circles.",
        "",
        "**Statistics:** the annotated p-value comes from the same automatic pipeline used in the",
        "dashboard (Shapiro-Wilk per group, then ANOVA if all groups are normal, otherwise",
        "Kruskal-Wallis).",
        "",
        "**Spectra figures** start at 440 nm: below that the signal-to-noise ratio of the",
        "spectrometer is so low that ~13 % of the rust spectra return negative reflectance. No",
        "spectral index uses bands below 500 nm, so the analysis is unaffected. They show the",
        "**standard error of the mean**, not the standard deviation: the SD between individual",
        "measurements (12-16 reflectance points, driven by probe-leaf coupling and between-leaf",
        "variation) is several times larger than the between-group difference and hid the effect.",
        "The lower panel shows the difference spectrum (rust - healthy) in reflectance points.",
        "",
        "## Summary figures (for a 4-page paper)",
        "",
        "`summary_rust_vs_healthy.png` and `summary_cultivars.png` condense the single-index",
        "boxplots into two two-column figures. `summary_effect_size.png` is a single-figure",
        "alternative if only one can fit. Note that **FSR is numerically identical to NDVI**",
        "(same bands), so both panels look the same; consider dropping FSR from the paper.",
        "",
        "In `summary_cultivars.png` the cultivars are abbreviated on the x-axis (B: Bourbon,",
        "P: Pacamara), and the legend expands the abbreviations. With only two cultivars the",
        "annotated test is a direct Bourbon-vs-Pacamara comparison, so no post-hoc test is",
        "needed to know which pair differs.",
        "",
        "## Data excluded from every figure",
        "",
        "Both exclusions are applied upstream by `get_dataset()`, so no figure can contain them:",
        "",
        "- **Canephora and Cuscatleco:** the permissions to use their data were not obtained, so",
        "  the analysis covers Bourbon and Pacamara only — which are also the two rust-susceptible",
        "  cultivars, the ones the healthy-vs-rust comparison needs.",
        "- **Pacamara plants of the non-susceptible variety.**",
        "",
        "| File | Content |",
        "|---|---|",
    ]
    lineas += [f"| `{nombre}` | {detalle} |" for nombre, detalle in entradas]
    (OUT_DIR / "README.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main() -> None:
    apply_style()
    OUT_DIR.mkdir(exist_ok=True)

    df = get_dataset()
    print(f"dataset: {len(df)} archivos")

    print("calculando indices por punto de medicion...")
    points = point_level_indices(df)
    print(f"  {len(points)} puntos (hojas maduras excluidas)")
    print(points.groupby(["species", "group"]).size().to_string())

    entradas = []
    print("figuras por especie...")
    entradas += figure_species_boxplots(points)
    print("figuras de comparacion entre especies (8)...")
    entradas += figure_species_comparison(points)
    print("figuras de reflectancia (2)...")
    for species in ("Bourbon", "Pacamara"):
        resultado = figure_spectra(df, species)
        if resultado:
            entradas.append(resultado)
    print("figuras resumen para el paper (3)...")
    entradas.append(figure_summary_rust(points))
    entradas.append(figure_summary_cultivars(points))
    entradas.append(figure_effect_size(points))

    write_index(entradas)
    print(f"\nlisto: {len(entradas)} figuras en {OUT_DIR}")


if __name__ == "__main__":
    main()
