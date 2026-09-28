"""Analisis de reflectancia foliar en cafe - deteccion de roya. Pagina de inicio."""

import re
from pathlib import Path

import streamlit as st

from src.config import DATA_DIR
from src.notifier import build_notification, send_telegram_messages
from src.parser import get_dataset, sorted_campaigns
from src.severity import leaf_severity_reports, severity_baselines
from src.state import file_key, load_last_run, save_last_run
from src.ui import inject_base_css, render_header, render_styled_pivot


st.set_page_config(page_title="Reflectancia Cafe - Roya", page_icon="🍃", layout="wide")
inject_base_css()
render_header("Inicio — resumen general de archivos, especies y campañas")

with st.sidebar:
    st.header("Datos")
    if st.button("🔄 Recargar datos", width='stretch'):
        st.cache_data.clear()
        st.rerun()
    st.caption(
        "El escaneo de la carpeta `data/` se actualiza automaticamente "
        "cuando se agregan o modifican archivos, pero puedes forzarlo aqui."
    )

df = get_dataset()

if df.empty:
    st.warning(
        "No se encontraron archivos .txt en `data/`. Verifica que la carpeta exista "
        "y que contenga subcarpetas por especie (Bourbon, Canefora, Cuscatleco, Pacamara)."
    )
    st.stop()

recognized = df[df["name_recognized"]]
unrecognized = df[~df["name_recognized"]]

st.subheader("📲 Verificar y notificar nueva data")
st.caption(
    "Compara los archivos actuales de `data/` contra la ultima verificacion y, si hay "
    "mediciones nuevas, te avisa por Telegram. La identidad de cada archivo es su ruta "
    "relativa a `data/` + un hash de su contenido, asi que mover o clonar el proyecto no "
    "genera novedades falsas."
)
col_verif, col_reset = st.columns([2, 1])
with col_verif:
    verificar = st.button("Verificar y analizar nueva data", width="stretch")
with col_reset:
    reset = st.button(
        "🧹 Marcar todo como visto (sin avisar)", width="stretch",
        help=(
            "Actualiza la linea base al estado actual de `data/` sin enviar nada a Telegram. "
            "Usalo si el registro quedo desactualizado (por ejemplo, tras agregar muchas "
            "campañas sin haber verificado antes) para no disparar una notificacion masiva."
        ),
    )

if reset:
    current_keys = {file_key(row.path, row.mtime_ns) for row in df.itertuples()}
    save_last_run(current_keys)
    st.success(
        f"Listo: se marcaron {len(current_keys)} archivo(s) como vistos, sin enviar nada a "
        "Telegram. La proxima verificacion solo avisara de lo que se agregue de aqui en adelante."
    )

if verificar:
    current_keys = {file_key(row.path, row.mtime_ns) for row in df.itertuples()}
    previous_keys = load_last_run()
    new_keys = current_keys - previous_keys

    if not previous_keys:
        st.info(
            f"Primera verificacion: se registraron {len(current_keys)} archivo(s) como linea base. "
            "La proxima vez que agregues mediciones, se te notificara solo lo nuevo."
        )
        save_last_run(current_keys)
    elif not new_keys:
        st.info("No hay archivos nuevos desde la ultima verificacion.")
    else:
        new_paths = {k.rsplit("|", 1)[0] for k in new_keys}
        # Las claves nuevas guardan la ruta RELATIVA a data/ (ver src/state.py); el DataFrame
        # trae la ruta absoluta, asi que se compara contra la version relativa de esa columna.
        rel_paths = df["path"].apply(lambda p: Path(p).resolve().relative_to(DATA_DIR.resolve()).as_posix())
        new_df = df[rel_paths.isin(new_paths)]
        resumen = new_df.groupby("species").size().sort_values(ascending=False)
        n_roya = int((new_df["health_status"] == "Con roya").sum())

        # --- indicio de roya por indices espectrales, agregado por hoja (0% sana - 100% enferma) ---
        baselines = severity_baselines(df)
        reportes = leaf_severity_reports(new_df, baselines)

        # Vista previa SIEMPRE antes de enviar: nada sale a Telegram sin que se vea primero
        # (F2, pagina de Inicio). Se guarda en session_state para sobrevivir al rerun del boton.
        st.session_state["preview_new_df"] = new_df
        st.session_state["preview_resumen"] = resumen
        st.session_state["preview_n_roya"] = n_roya
        st.session_state["preview_reportes"] = reportes
        st.session_state["preview_current_keys"] = current_keys

if st.session_state.get("preview_reportes") is not None:
    new_df = st.session_state["preview_new_df"]
    resumen = st.session_state["preview_resumen"]
    n_roya = st.session_state["preview_n_roya"]
    reportes = st.session_state["preview_reportes"]
    current_keys = st.session_state["preview_current_keys"]

    st.info(f"Hay {len(new_df)} archivo(s) nuevo(s) en {len(reportes)} hoja(s). Revisa antes de enviar:")
    st.dataframe(resumen.rename("Archivos nuevos"), width="stretch")

    mensajes = build_notification(len(new_df), resumen.to_dict(), n_roya, reportes)
    with st.expander(f"Vista previa del mensaje ({len(mensajes)} mensaje(s) de Telegram)", expanded=True):
        for i, msg in enumerate(mensajes, start=1):
            st.caption(f"Mensaje {i}/{len(mensajes)} — {len(msg)} caracteres")
            st.text(re.sub(r"</?[bi]>", "", msg))

    c_send, c_discard = st.columns([2, 1])
    with c_send:
        if st.button("✅ Enviar a Telegram", type="primary", width="stretch"):
            ok, detalle = send_telegram_messages(mensajes)
            if ok:
                # El registro solo se actualiza si el envio funciono: si falla, estas
                # mismas novedades se vuelven a mostrar la proxima vez en vez de perderse.
                save_last_run(current_keys)
                st.success(f"Enviado. {detalle}")
                for k in ("preview_new_df", "preview_resumen", "preview_n_roya", "preview_reportes", "preview_current_keys"):
                    st.session_state.pop(k, None)
                st.rerun()
            else:
                st.error(f"No se pudo enviar: {detalle}. El registro no se actualizo — se reintenta la proxima vez.")
    with c_discard:
        if st.button("Descartar vista previa", width="stretch"):
            for k in ("preview_new_df", "preview_resumen", "preview_n_roya", "preview_reportes", "preview_current_keys"):
                st.session_state.pop(k, None)
            st.rerun()

st.divider()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Archivos encontrados", len(df), border=True)
c2.metric("Especies", df["species"].nunique(), border=True)
c3.metric("Campañas", df["campaign_id"].nunique(), border=True)
c4.metric("Nombres no reconocidos", len(unrecognized), border=True)

st.subheader("Archivos por especie y campaña")
# Las columnas del pivote van en orden cronologico real (campaign_date), no alfabetico:
# el id de campaña ("Campaña_07_09" vs. "Campaña_10_08") no ordena igual que la fecha real.
pivot = (
    df.pivot_table(index="species", columns="campaign_id", values="filename", aggfunc="count", fill_value=0)
    .reindex(columns=sorted_campaigns(df))
    .assign(Total=lambda d: d.sum(axis=1))
    .sort_index()
)
render_styled_pivot(pivot, decimals=0)

st.subheader("🍃 Estado sanitario (deteccion de roya)")
st.caption(
    "Archivos cuyo nombre empieza con **R/r** se registran como 'Con roya'; los que empiezan "
    "con M (hoja madura) o T (hoja tierna) se registran como 'Sana'. Tanto Bourbon como Pacamara "
    "tienen muestras con roya confirmada."
)
health = df[df["health_status"].notna()]
if health.empty:
    st.info("Ningun archivo tiene aun estado sanitario reconocido.")
else:
    health_pivot = health.pivot_table(
        index="species", columns="health_status", values="filename", aggfunc="count", fill_value=0
    )
    render_styled_pivot(health_pivot, decimals=0)

st.subheader("Susceptibilidad de variedad")
st.caption(
    "Por ahora solo **Pacamara** tiene la variedad clasificada como Susceptible / No susceptible "
    "(es una propiedad de la planta, distinta de si esa hoja tiene roya activa ahora mismo)."
)
susc = df[df["susceptibility"].notna()]
if susc.empty:
    st.info("Ninguna especie tiene aun la susceptibilidad de variedad registrada.")
else:
    susc_pivot = (
        susc.pivot_table(index="species", columns="susceptibility", values="filename", aggfunc="count", fill_value=0)
    )
    render_styled_pivot(susc_pivot, decimals=0)

with st.expander(f"Detalle de campañas detectadas ({df['campaign_id'].nunique()})"):
    campaigns = df[["campaign_id", "campaign_date"]].drop_duplicates().set_index("campaign_id")
    campaigns = campaigns.loc[sorted_campaigns(df)].reset_index()
    st.dataframe(campaigns, width='stretch', hide_index=True)

if not unrecognized.empty:
    with st.expander(f"⚠️ Archivos con nombre no reconocido ({len(unrecognized)})", expanded=False):
        st.caption(
            "Estos archivos se detectaron por su carpeta (especie/susceptibilidad) pero su "
            "nombre no sigue el patron `{M|T|R}{n}p{punto}{especie}{repeticion}`. Se excluyen del "
            "agrupamiento por madurez/estado sanitario hasta que se revisen."
        )
        st.dataframe(
            unrecognized[["path", "species", "susceptibility"]],
            width='stretch',
            hide_index=True,
        )

st.divider()
st.markdown(
    "Usa el menu lateral para ver **Espectros**, **Indices Espectrales** por especie, "
    "o la **Comparacion entre especies**."
)
