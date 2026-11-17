"""Actualiza el almacen precalculado `data_cache/` (indices + espectros suavizados por archivo).

Uso, desde la raiz del repo, despues de copiar una campaña nueva a `data/`:

    python scripts/build_cache.py            # completa lo que falta y reutiliza el resto
    python scripts/build_cache.py --desde-cero   # descarta el almacen y recalcula todo

Despues: `git add data/ data_cache/ && git commit`. Si se olvida este paso la app funciona igual
(calcula lo que falta al arrancar), solo que ese primer arranque tarda mas.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore", message=".*No runtime found.*")

import streamlit.logger  # noqa: E402

streamlit.logger.set_log_level("error")  # fuera de la app, los caches avisan "No runtime found"

from src.store import STORE_DIR, build_store  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde-cero", action="store_true", help="borra data_cache/ y recalcula todo")
    args = ap.parse_args()
    if args.desde_cero and STORE_DIR.exists():
        shutil.rmtree(STORE_DIR)

    t = time.perf_counter()

    def avance(k, n):
        if k % 250 == 0 or k == n:
            print(f"  {k}/{n} archivos", flush=True)

    tabla, r = build_store(progress=avance)
    errores = tabla[tabla["error"] != ""]
    print(f"Listo en {time.perf_counter() - t:.1f} s: {r['archivos']} archivos, {r['calculados']} calculados, "
          f"{r['reutilizados']} reutilizados, {r['quitados']} quitados (metodo {r['metodo']}).")
    if len(errores):
        print(f"{len(errores)} archivos ilegibles (quedan con NaN y se listan en «Datos y calidad»):")
        for rel, e in zip(errores["rel_path"], errores["error"]):
            print(f"  {rel}: {e}")


if __name__ == "__main__":
    main()
