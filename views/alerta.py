"""Alerta de campo: revisar las mediciones nuevas y enviar el aviso por Telegram (siempre con vista previa)."""

import re
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import DATA_DIR, ROYA_LABEL, RUST_RISK_CLASSES
from src.notifier import build_notification, send_telegram_messages
from src.parser import get_dataset
from src.severity import leaf_severity_reports, severity_baselines
from src.state import file_key, load_last_run, save_last_run
from src.ui import html_table, note, page_header, section, sidebar_footer

page_header(
    "Datos y operación",
    "Alerta de campo",
    "Compara los espectros de <code>data/</code> con la última verificación y prepara un aviso por "
    "Telegram con la similitud de cada hoja nueva. Nada se envía sin revisar antes la vista previa.",
)

df = get_dataset()
if df.empty:
    st.warning("No se encontraron espectros en `data/`.")
    st.stop()
sidebar_footer(df)

PREVIEW_KEYS = ("preview_new_df", "preview_resumen", "preview_n_roya", "preview_reportes", "preview_current_keys")


def _limpiar_preview():
    for k in PREVIEW_KEYS:
        st.session_state.pop(k, None)


previos = load_last_run()
current_keys = {file_key(row.path, row.mtime_ns) for row in df.itertuples()}
pendientes = len(current_keys - previos) if previos else None

c1, c2, c3 = st.columns(3)
c1.metric("Espectros registrados", f"{len(previos):,}" if previos else "—",
          help="Espectros que ya se consideran vistos (registro local en .state/).")
c2.metric("Espectros en data/", f"{len(current_keys):,}")
c3.metric("Pendientes de revisar", "—" if pendientes is None else pendientes,
          help="Diferencia entre lo que hay en data/ y el registro. Cada espectro se identifica por su ruta relativa y un hash de su contenido.")

if pendientes and pendientes > 300:
    note("aviso", f"Hay **{pendientes} espectros pendientes**, más de lo que suele traer una campaña. Si el registro "
                  "se perdió (por ejemplo, tras reiniciar un servidor en la nube), conviene «Marcar todo como visto» "
                  "en lugar de enviar un aviso masivo.")

b1, b2, _ = st.columns([1.2, 1.2, 2])
verificar = b1.button("Revisar novedades", type="primary", icon=":material/search:", width="stretch")
reset = b2.button("Marcar todo como visto", icon=":material/done_all:", width="stretch",
                  help="Actualiza el registro al estado actual de data/ sin enviar nada.")

if reset:
    save_last_run(current_keys)
    _limpiar_preview()
    st.success(f"Registro actualizado: {len(current_keys)} espectros marcados como vistos. No se envió nada.")

if verificar:
    if not previos:
        save_last_run(current_keys)
        st.info(f"Primera verificación: se registraron {len(current_keys)} espectros como línea base. "
                "La próxima revisión mostrará solo lo que se agregue desde ahora.")
    else:
        nuevos = current_keys - previos
        if not nuevos:
            _limpiar_preview()
            st.info("No hay espectros nuevos desde la última verificación.")
        else:
            rutas = {k.rsplit("|", 1)[0] for k in nuevos}
            rel = df["path"].apply(lambda p: Path(p).resolve().relative_to(DATA_DIR.resolve()).as_posix())
            new_df = df[rel.isin(rutas)]
            st.session_state["preview_new_df"] = new_df
            st.session_state["preview_resumen"] = new_df.groupby("species").size().sort_values(ascending=False)
            st.session_state["preview_n_roya"] = int((new_df["health_status"] == ROYA_LABEL).sum())
            st.session_state["preview_reportes"] = leaf_severity_reports(new_df, severity_baselines(df))
            st.session_state["preview_current_keys"] = current_keys

if st.session_state.get("preview_reportes") is not None:
    new_df = st.session_state["preview_new_df"]
    resumen = st.session_state["preview_resumen"]
    reportes = st.session_state["preview_reportes"]

    section("Vista previa", f"{len(new_df)} espectros nuevos en {len(reportes)} hojas.")
    filas = [{
        "Fecha": f"{pd.Timestamp(r.get('campaign_date')):%d/%m/%Y}" if r.get("campaign_date") is not None else "—",
        "Variedad": r.get("species", ""), "Hoja": r.get("hoja", ""),
        "Similitud": f"{r['score'] * 100:.0f} %" if r.get("score") is not None else "—",
        "Puntos": r.get("n_puntos", "—"), "Índices": f"{r.get('n_indices', '—')}/7",
    } for r in reportes]
    html_table(pd.DataFrame(filas), num_cols=("Similitud", "Puntos", "Índices"))

    mensajes = build_notification(len(new_df), resumen.to_dict(), st.session_state["preview_n_roya"], reportes)
    with st.expander(f"Texto exacto que se enviará ({len(mensajes)} mensajes)"):
        for i, msg in enumerate(mensajes, start=1):
            st.caption(f"Mensaje {i} de {len(mensajes)} · {len(msg)} caracteres (límite 4096)")
            st.code(re.sub(r"</?[bi]>", "", msg), language=None)

    s1, s2, _ = st.columns([1.2, 1.2, 2])
    if s1.button("Enviar a Telegram", type="primary", icon=":material/send:", width="stretch"):
        ok, detalle = send_telegram_messages(mensajes)
        if ok:
            save_last_run(st.session_state["preview_current_keys"])
            _limpiar_preview()
            st.success(f"Enviado. {detalle}")
        else:
            st.error(f"No se pudo enviar: {detalle}. El registro no cambió; las novedades seguirán pendientes.")
    if s2.button("Descartar", icon=":material/close:", width="stretch"):
        _limpiar_preview()
        st.rerun()

section("Cómo se lee cada tarjeta")
html_table(pd.DataFrame(
    [(c[1], f"{c[0] * 100:.0f} %", c[3]) for c in RUST_RISK_CLASSES],
    columns=["Clase", "Nivel nominal", "Significado"],
), num_cols=("Nivel nominal",), strong_cols=("Clase",))
st.caption("Cada hoja se asigna a la clase de nivel más cercano (límites en 17 %, 50 % y 83 %). Las hojas "
           "tiernas y con roya del mismo lote son las referencias: una tierna alta o una con roya baja "
           "indican una medición dudosa ese día.")
