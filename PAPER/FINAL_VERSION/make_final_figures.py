"""Tablas, estadistica y figuras del paper CONCAPAN (version final), SOLO con las 5 campanas del envio.

Campanas del paper: C1_29_06, C2_06_07, Roya_15_07, Roya_21_07, Roya_27_07 (julio de 2026).
Las 7 campanas posteriores (agosto-septiembre) NO entran: no estaban en el paper enviado.

Decisiones (todas verificables en el codigo):
- Grupo H = hojas tiernas (T) ["healthy (H, young)" del texto]. Grupo R = hoja R1 (15/07 y 27/07).
- Unidad = punto de medicion (se promedian sus repeticiones), igual que en el paper enviado.
- Reflectancia en FRACCION (0-1) para CRI1: SpectraSuite entrega % (0-100), y CRI1 = 1/R510 - 1/R550
  no es invariante a la escala (con % sale 100 veces menor). Los demas indices son cocientes: no cambian.
- FSR se calcula con 850 nm (como dice Metodos); en el codigo de la app usa 800 nm y sale igual a NDVI.
- Nombres: los de la seccion Metodos del paper (CRI1, ND705, mND705), no los internos de la app.

Uso (desde la raiz del repo):  python PAPER/FINAL_VERSION/make_final_figures.py
"""
from __future__ import annotations
import sys, warnings
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
from matplotlib.patches import Patch
from scipy import stats
from statsmodels.stats.multitest import multipletests

from src.parser import get_dataset, load_spectrum
from src.processing import calcular_indices, prepare_spectrum, reflectance_at

CAMPAIGNS = ["C1_29_06", "C2_06_07", "Roya_15_07", "Roya_21_07", "Roya_27_07"]
SPECIES = ["Bourbon", "Pacamara"]
# nombre en el paper -> columna interna
NAMES = {"CRI1": "RCI", "PRI": "PRI", "PSRI": "PSRI", "NDVI": "NDVI", "FSR": "FSR850",
         "ND705": "EDI", "mND705": "mNDVI705", "NDRE": "NDRE"}
ORDER = list(NAMES)
COL = {"H": "#2E8B57", "R": "#C0392B"}


def build_files() -> pd.DataFrame:
    df = get_dataset()
    d = df[df.campaign_id.isin(CAMPAIGNS) & df.name_recognized & df.species.isin(SPECIES)]
    rows = []
    for r in d.itertuples():
        s = prepare_spectrum(load_spectrum(r.path))
        idx = calcular_indices(s)
        nir, red = reflectance_at(s, 850), reflectance_at(s, 670)
        idx["FSR850"] = (nir - red) / (nir + red)
        idx["RCI"] = idx["RCI"] * 100.0  # reflectancia % -> fraccion: 1/(R/100) = 100/R
        rows.append(dict(species=r.species, camp=r.campaign_id, sess=r.session, num=r.session_num,
                         pt=r.point, rep=r.repetition, **idx))
    return pd.DataFrame(rows)


def points(files: pd.DataFrame) -> pd.DataFrame:
    return files.groupby(["species", "camp", "sess", "num", "pt"])[list(NAMES.values())].mean().reset_index()


def cliff(a, b):
    d = np.asarray(a)[:, None] - np.asarray(b)[None, :]
    return float(((d > 0).sum() - (d < 0).sum()) / d.size)


def analyse(p: pd.DataFrame, healthy: set[str], label: str) -> pd.DataFrame:
    out = []
    for sp in SPECIES:
        s = p[p.species == sp]
        h, r = s[s.sess.isin(healthy)], s[s.sess == "R"]
        for nm, c in NAMES.items():
            a, b = h[c].dropna().values, r[c].dropna().values
            pv = stats.mannwhitneyu(a, b, alternative="two-sided").pvalue
            out.append(dict(grupoH=label, species=sp, index=nm, nH=len(a), nR=len(b),
                            H_mean=a.mean(), H_sd=a.std(ddof=1), R_mean=b.mean(), R_sd=b.std(ddof=1),
                            change_pct=100 * (b.mean() - a.mean()) / abs(a.mean()),
                            cliff_delta=cliff(b, a), p_raw=pv))
    t = pd.DataFrame(out)
    for sp in SPECIES:  # Holm sobre los 8 indices de cada especie
        m = t.species == sp
        t.loc[m, "p_holm"] = multipletests(t.loc[m, "p_raw"], method="holm")[1]
    return t


def stars(p):
    return "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "ns"


def fig_boxplots(p: pd.DataFrame, st_: pd.DataFrame) -> None:
    plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"]})
    fig, axes = plt.subplots(2, 4, figsize=(7.16, 4.9))
    fig.subplots_adjust(left=0.065, right=0.995, top=0.90, bottom=0.17, wspace=0.42, hspace=0.42)
    rng = np.random.default_rng(20260802)
    for ax, nm in zip(axes.ravel(), ORDER):
        c = NAMES[nm]; pos, data, cols = [], [], []
        for i, sp in enumerate(SPECIES):
            s = p[p.species == sp]
            for j, (g, mask) in enumerate([("H", s.sess == "T"), ("R", s.sess == "R")]):
                pos.append(i * 3 + j); data.append(s.loc[mask, c].dropna().values); cols.append(COL[g])
        bp = ax.boxplot(data, positions=pos, widths=0.8, patch_artist=True, showfliers=False,
                        medianprops=dict(color="black", lw=2.0), boxprops=dict(lw=1.5),
                        whiskerprops=dict(lw=1.5), capprops=dict(lw=1.5))
        for b, col in zip(bp["boxes"], cols):
            b.set_facecolor(col); b.set_alpha(0.40); b.set_edgecolor("black")
        for x, v, col in zip(pos, data, cols):
            ax.scatter(x + rng.uniform(-.2, .2, len(v)), v, s=9, facecolors="none", edgecolors=col, lw=0.8, zorder=3)
        ax.set_xticks([0.5, 3.5]); ax.set_xticklabels(["Bourbon", "Pacamara"], fontsize=9)
        ax.set_title(nm, fontsize=12, fontweight="bold", pad=14)
        ax.tick_params(axis="y", labelsize=9); ax.margins(y=0.12)
        ax.grid(axis="y", color="#DDD", lw=0.5); ax.set_axisbelow(True)
        for sp, x0 in zip(SPECIES, (0.5, 3.5)):
            row = st_[(st_.species == sp) & (st_["index"] == nm)].iloc[0]
            ax.text(x0, 1.01, stars(row.p_holm), transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                    fontsize=12 if row.p_holm < .05 else 9, fontweight="bold")
        ax.spines[["top", "right"]].set_visible(False)
    n = {sp: (int((p[(p.species == sp) & (p.sess == 'T')].shape[0])), int((p[(p.species == sp) & (p.sess == 'R')].shape[0]))) for sp in SPECIES}
    fig.legend(handles=[Patch(facecolor=COL["H"], alpha=.4, edgecolor="black", label=f"H: healthy young leaves (n = {n['Bourbon'][0]} points per variety)"),
                        Patch(facecolor=COL["R"], alpha=.4, edgecolor="black", label=f"R: rust-infected leaf (n = {n['Bourbon'][1]} points per variety)")],
               loc="lower center", ncol=2, fontsize=9, frameon=False, bbox_to_anchor=(0.5, 0.045))
    fig.text(0.5, 0.012, "Mann-Whitney U, Holm-adjusted over the 8 indices: *** p<0.001, ** p<0.01, * p<0.05, ns not significant.",
             ha="center", fontsize=8.5, color="#444")
    fig.savefig(OUT / "fig_boxplots_indices.png", dpi=600); plt.close(fig)


def fig_cultivars(p: pd.DataFrame) -> pd.DataFrame:
    """Bourbon vs Pacamara, solo hojas tiernas (H), 8 indices. Mann-Whitney + Holm sobre los 8 indices."""
    plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"]})
    CC = {"Bourbon": "#2C6FBB", "Pacamara": "#C98500"}
    h = p[p.sess == "T"]
    res = []
    for nm, c in NAMES.items():
        a, b = h.loc[h.species == "Bourbon", c].dropna().values, h.loc[h.species == "Pacamara", c].dropna().values
        res.append(dict(index=nm, nB=len(a), nP=len(b), B_mean=a.mean(), B_sd=a.std(ddof=1), P_mean=b.mean(), P_sd=b.std(ddof=1),
                        cliff_delta_P_vs_B=cliff(b, a), p_raw=stats.mannwhitneyu(a, b, alternative="two-sided").pvalue))
    t = pd.DataFrame(res); t["p_holm"] = multipletests(t.p_raw, method="holm")[1]
    t.to_csv(OUT / "estadistica_cultivares_5campanas.csv", index=False, float_format="%.6g")
    fig, axes = plt.subplots(2, 4, figsize=(7.16, 4.9))
    fig.subplots_adjust(left=0.065, right=0.995, top=0.90, bottom=0.14, wspace=0.42, hspace=0.42)
    rng = np.random.default_rng(20260803)
    for ax, nm in zip(axes.ravel(), ORDER):
        c = NAMES[nm]; data = [h.loc[h.species == sp, c].dropna().values for sp in SPECIES]
        bp = ax.boxplot(data, positions=[0, 1], widths=0.6, patch_artist=True, showfliers=False,
                        medianprops=dict(color="black", lw=2.0), boxprops=dict(lw=1.5), whiskerprops=dict(lw=1.5), capprops=dict(lw=1.5))
        for b, sp in zip(bp["boxes"], SPECIES):
            b.set_facecolor(CC[sp]); b.set_alpha(0.40); b.set_edgecolor("black")
        for x, v, sp in zip([0, 1], data, SPECIES):
            ax.scatter(x + rng.uniform(-.16, .16, len(v)), v, s=9, facecolors="none", edgecolors=CC[sp], lw=0.8, zorder=3)
        ax.set_xticks([0, 1]); ax.set_xticklabels(["Bourbon", "Pacamara"], fontsize=9)
        ax.set_title(nm, fontsize=12, fontweight="bold", pad=14); ax.tick_params(axis="y", labelsize=9); ax.margins(y=0.12)
        ax.grid(axis="y", color="#DDD", lw=0.5); ax.set_axisbelow(True); ax.spines[["top", "right"]].set_visible(False)
        ph = t.loc[t["index"] == nm, "p_holm"].iloc[0]
        ax.text(0.5, 1.01, stars(ph), transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                fontsize=12 if ph < .05 else 9, fontweight="bold")
    fig.text(0.5, 0.045, f"Healthy young leaves only (n = {len(data[0])} points per variety).", ha="center", fontsize=9)
    fig.text(0.5, 0.012, "Mann-Whitney U, Holm-adjusted over the 8 indices: *** p<0.001, ** p<0.01, * p<0.05, ns not significant.",
             ha="center", fontsize=8.5, color="#444")
    fig.savefig(OUT / "fig_boxplots_cultivares.png", dpi=600); plt.close(fig)
    return t


def fig_spectra() -> pd.DataFrame:
    """Reflectancia media +- 1 SE (H joven vs R) y espectro diferencia, por variedad. n = espectros."""
    df = get_dataset()
    d = df[df.campaign_id.isin(CAMPAIGNS) & df.name_recognized & df.species.isin(SPECIES)]
    grid = np.arange(440, 1000, 1.0)
    res = []
    for sp in SPECIES:
        mats = {}
        for g, mask in [("H", d.session == "T"), ("R", d.session == "R")]:
            cur = []
            for r in d[(d.species == sp) & mask].itertuples():
                s_ = prepare_spectrum(load_spectrum(r.path))
                cur.append(np.interp(grid, s_["wavelength"], s_["smooth"]))
            mats[g] = np.asarray(cur)
        diff = mats["R"].mean(0) - mats["H"].mean(0)
        for wl in (500, 550, 680, 700, 720, 750, 800, 850, 900):
            res.append(dict(species=sp, wl=wl, H=mats["H"].mean(0)[wl - 440], R=mats["R"].mean(0)[wl - 440], diff=diff[wl - 440]))
        i_max = int(np.argmax(np.abs(diff))); res.append(dict(species=sp, wl="max|diff|", H=mats["H"].mean(0)[i_max], R=mats["R"].mean(0)[i_max], diff=diff[i_max], at_nm=grid[i_max]))
        plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"]})
        fig, (ax, ad) = plt.subplots(2, 1, figsize=(3.5, 4.3), sharex=True, gridspec_kw={"height_ratios": [2.4, 1], "hspace": 0.1})
        for g, lab in [("H", "H: healthy young"), ("R", "R: rust-infected")]:
            m = mats[g]; mu = m.mean(0); se = m.std(0, ddof=1) / np.sqrt(len(m))
            ax.fill_between(grid, mu - se, mu + se, color=COL[g], alpha=.3, lw=0)
            ax.plot(grid, mu, color=COL[g], lw=1.6, label=f"{lab} (n = {len(m)} spectra)")
        ax.set_ylabel("Reflectance (%)", fontsize=10); ax.set_ylim(0, 118); ax.set_yticks([0, 20, 40, 60, 80, 100]); ax.legend(fontsize=8, loc="upper left", frameon=False)
        ax.grid(color="#DDD", lw=.5); ax.tick_params(labelsize=9); ax.set_title(f"{sp}: mean reflectance $\pm$ 1 SE", fontsize=10)
        ad.axhline(0, color="#666", lw=.7); ad.plot(grid, diff, color="#222", lw=1.3)
        ad.set_xlabel("Wavelength (nm)", fontsize=10); ad.set_ylabel("R $-$ H (%)", fontsize=10); ad.set_xlim(440, 1000)
        ad.grid(color="#DDD", lw=.5); ad.tick_params(labelsize=9)
        for a in (ax, ad): a.spines[["top", "right"]].set_visible(False)
        fig.savefig(OUT / f"fig_spectra_{sp.lower()}.png", dpi=600, bbox_inches="tight"); plt.close(fig)
    return pd.DataFrame(res)


def main() -> None:
    files = build_files(); p = points(files)
    print("espectros:", len(files), "| puntos:", len(p))
    print(p.groupby(["species", "sess"]).size().unstack().to_string())
    main_t = analyse(p, {"T"}, "T (young)")
    sens = pd.concat([analyse(p, {"M"}, "M (mature)"), analyse(p, {"M", "T"}, "M+T pooled")])
    pd.concat([main_t, sens]).to_csv(OUT / "estadistica_5campanas.csv", index=False, float_format="%.6g")
    fig_boxplots(p, main_t)
    cult = fig_cultivars(p); print(cult.round(4).to_string())
    sp_tab = fig_spectra(); sp_tab.to_csv(OUT / 'espectros_diferencia_5campanas.csv', index=False, float_format='%.4g'); print(sp_tab.round(2).to_string())
    pd.set_option("display.width", 250, "display.max_columns", 30)
    print(main_t.round(4).to_string())
    print("\nSENSIBILIDAD\n", sens.round(4)[["grupoH","species","index","nH","H_mean","R_mean","change_pct","cliff_delta","p_raw","p_holm"]].to_string())


if __name__ == "__main__":
    main()
