"""Analisis de reflectancia foliar en cafe - deteccion de roya. Pagina de inicio."""

import streamlit as st

from src.notifier import send_telegram_message
from src.parser import get_dataset
from src.state import file_key, load_last_run, save_last_run
from src.ui import inject_base_css, render_header, render_styled_pivot

st.set_page_config(page_title="Reflectancia Cafe - Roya", page_icon="🍃", layout="wide")
inject_base_css()
render_header("Inicio — resumen general de archivos, especies y campanas")

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
    "mediciones nuevas, te avisa por Telegram."
)
if st.button("Verificar y analizar nueva data"):
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
        new_df = df[df["path"].isin(new_paths)]
        resumen = new_df.groupby("species").size().sort_values(ascending=False)
        lineas = [f"- {especie}: {n} archivo(s)" for especie, n in resumen.items()]
        n_roya = int((new_df["health_status"] == "Con roya").sum())
        roya_linea = f"\n⚠️ {n_roya} archivo(s) con roya detectada." if n_roya else ""
        mensaje = (
            "🍃 *Analisis de reflectancia actualizado*\n"
            f"Se detectaron {len(new_df)} archivo(s) nuevo(s) en data/:\n"
            + "\n".join(lineas)
            + roya_linea
        )
        ok, detalle = send_telegram_message(mensaje)
        save_last_run(current_keys)
        if ok:
            st.success(f"Se detectaron {len(new_df)} archivo(s) nuevo(s) y se notifico por Telegram.")
        else:
            st.warning(f"Se detectaron {len(new_df)} archivo(s) nuevo(s), pero: {detalle}")
        st.dataframe(resumen.rename("Archivos nuevos"), width="stretch")

st.divider()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Archivos encontrados", len(df), border=True)
c2.metric("Especies", df["species"].nunique(), border=True)
c3.metric("Campanas", df["campaign_id"].nunique(), border=True)
c4.metric("Nombres no reconocidos", len(unrecognized), border=True)

st.subheader("Archivos por especie y campana")
pivot = (
    df.pivot_table(index="species", columns="campaign_id", values="filename", aggfunc="count", fill_value=0)
    .assign(Total=lambda d: d.sum(axis=1))
    .sort_index()
)
render_styled_pivot(pivot, decimals=0)

st.subheader("🍃 Estado sanitario (deteccion de roya)")
st.caption(
    "Archivos cuyo nombre empieza con **R/r** se registran como 'Con roya'; los que empiezan "
    "con M (hoja madura) o T (hoja tierna) se registran como 'Sana'. Por ahora Bourbon y Pacamara "
    "ya tienen muestras con roya confirmada; Canefora y Cuscatleco todavia solo tienen hojas sanas."
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

with st.expander(f"Detalle de campanas detectadas ({df['campaign_id'].nunique()})"):
    campaigns = df[["campaign_id", "campaign_date"]].drop_duplicates().sort_values("campaign_id")
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
