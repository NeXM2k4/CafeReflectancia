"""Analisis de reflectancia foliar en cafe - deteccion de roya. Pagina de inicio.

Orden de la pagina (F2 de plan_mejora_app.md): 1) que datos hay, 2) calidad de datos
(que se excluye/marca y por que), 3) novedades y alerta de Telegram, 4) glosario y que
responde cada pagina. Antes la alerta iba primero y el resto quedaba mezclado sin un orden
claro; esta pagina es la puerta de entrada, asi que es la que mas necesita ese orden.
"""

import re
from pathlib import Path

import streamlit as st

from src.config import DATA_DIR, LEAF_TYPE_HELP, LEAF_TYPE_LABELS, ROYA_LABEL, SPECIES_PENDING_LABEL
from src.indices import file_index_table, leaf_date_table, quality_flags
from src.notifier import build_notification, send_telegram_messages
from src.parser import campaign_options, get_dataset, raw_dataset, sorted_campaigns
from src.severity import leaf_severity_reports, severity_baselines
from src.state import file_key, load_last_run, save_last_run
from src.ui import inject_base_css, render_header, render_styled_pivot

st.set_page_config(page_title="Reflectancia Café - Roya", page_icon="🍃", layout="wide")
inject_base_css()
render_header("Inicio — qué datos hay, su calidad, y novedades")

with st.sidebar:
    st.header("Datos")
    if st.button("🔄 Recargar datos", width='stretch'):
        st.cache_data.clear()
        st.rerun()
    st.caption(
        "El escaneo de la carpeta `data/` se actualiza automáticamente "
        "cuando se agregan o modifican archivos, pero puedes forzarlo aquí."
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
raw = raw_dataset()

# ============================================================================
# 1. Que datos hay
# ============================================================================
st.subheader("1. Qué datos hay")
n_hojas_fisicas = recognized.groupby(["species", "session", "session_num"]).ngroups

c1, c2, c3, c4 = st.columns(4)
c1.metric("Archivos analizados", len(df), border=True, help="Tras aplicar los filtros de la sección 2.")
c2.metric(
    "Especies", df.loc[df["species"] != SPECIES_PENDING_LABEL, "species"].nunique(), border=True,
    help="No cuenta la categoría 'especie pendiente' (ver sección 2): esa no es una especie real.",
)
c3.metric("Campañas", df["campaign_id"].nunique(), border=True)
c4.metric(
    "Hojas fisicas con serie", n_hojas_fisicas, border=True,
    help="Combinaciones especie + tipo de hoja + número distintas (M1, M2, T1, T2, R1...).",
)

tab_especie, tab_hoja = st.tabs(["Por especie y campaña", "Por tipo de hoja"])

with tab_especie:
    st.caption(
        "Número de archivos (mediciones individuales) por especie y fecha de campaña. "
        "Las columnas van en orden cronologico real, no alfabetico."
    )
    labels = campaign_options(df)
    pivot = (
        df.pivot_table(index="species", columns="campaign_id", values="filename", aggfunc="count", fill_value=0)
        .reindex(columns=sorted_campaigns(df))
        .assign(Total=lambda d: d.sum(axis=1))
        .sort_index()
    )
    pivot = pivot.rename(columns={cid: labels.get(cid, cid) for cid in pivot.columns if cid != "Total"})
    render_styled_pivot(pivot, decimals=0)

with tab_hoja:
    st.caption(
        "**Tipo de hoja**, no estado sanitario: Madura y Tierna no tienen síntomas visibles, "
        "pero su estado sanitario real **no se conoce** — es justo lo que el resto de la app "
        "trata de estimar. Solo 'Con roya' es un diagnostico confirmado visualmente."
    )
    tipo_pivot = recognized.pivot_table(
        index="species", columns="session", values="filename", aggfunc="count", fill_value=0
    )
    tipo_pivot = tipo_pivot.rename(columns=LEAF_TYPE_LABELS)
    orden_cols = [c for c in ["Madura", "Tierna", "Vieja", "Con roya"] if c in tipo_pivot.columns]
    render_styled_pivot(tipo_pivot[orden_cols], decimals=0)
    for code, texto in LEAF_TYPE_HELP.items():
        if LEAF_TYPE_LABELS[code] in tipo_pivot.columns:
            st.caption(f"**{LEAF_TYPE_LABELS[code]}**: {texto}")
    susc = df[df["susceptibility"].notna()]
    if not susc.empty:
        with st.expander("Susceptibilidad de variedad (hoy solo Pacamara)"):
            st.caption(
                "Propiedad de la **planta** (variedad), distinta del tipo de hoja o de si esa "
                "hoja tiene roya activa ahora mismo."
            )
            susc_pivot = susc.pivot_table(
                index="species", columns="susceptibility", values="filename", aggfunc="count", fill_value=0
            )
            render_styled_pivot(susc_pivot, decimals=0)

with st.expander(f"Detalle de campañas detectadas ({df['campaign_id'].nunique()})"):
    campaigns = df[["campaign_id", "campaign_date"]].drop_duplicates().set_index("campaign_id")
    campaigns = campaigns.loc[sorted_campaigns(df)].reset_index()
    st.dataframe(campaigns, width='stretch', hide_index=True)

st.divider()

# ============================================================================
# 2. Calidad de datos
# ============================================================================
st.subheader("2. Calidad de datos")
st.caption(
    "Que se excluye o se marca antes de analizar, y por que. Nada se borra: todo sigue en "
    "`data/` y puede revisarse en las tablas de abajo."
)

n_no_susceptible = int(((raw["species"] == "Pacamara") & (raw["susceptibility"] == "No susceptible")).sum())
n_pendiente = int((df["species"] == SPECIES_PENDING_LABEL).sum())
files_all, read_errors = file_index_table(df)
ld_all = quality_flags(leaf_date_table(files_all))
n_qc_atipico = int(ld_all["qc_atipico"].sum())
n_qc_implausible = int(ld_all["qc_implausible"].sum())
# file_index_table() ya excluye no-reconocidos y especie pendiente, asi que lo que le falta
# frente a p1-p3 es exactamente los archivos con punto p4+ (nunca se filtra por punto ahi).
n_fuera_p1p3 = int((~files_all["point"].isin([1, 2, 3])).sum())

filas_calidad = [
    ("Pacamara \"No susceptible\"", n_no_susceptible,
     "Variedad no susceptible a roya: fuera de foco del proyecto. Excluidas de todas las páginas."),
    ("Especie pendiente (hoja \"vieja\" sin especie)", n_pendiente,
     "No se sabe a que especie corresponden (ver docs/bitacora.md §4/§12). Agrupadas aparte, "
     "nunca mezcladas con las 4 especies reales."),
    ("Nombre de archivo no reconocido", len(unrecognized),
     "No siguen el patron {M|T|R|V}{n}p{punto}{especie}{repeticion}. Visibles en el expander de abajo."),
    ("Puntos fuera de p1-p3 (p4-p6)", n_fuera_p1p3,
     "Los puntos no son ubicaciones fijas entre campañas; solo p1-p3 se usan en índices, "
     "estadística y similitud (decisión confirmada con el equipo de campo)."),
    ("Hojas-fecha marcadas por control de calidad", n_qc_atipico,
     "Outlier respecto de la propia historia de esa hoja (4+ de 7 índices con |z robusto| > 3.5). "
     "Excluidas solo de las anclas de similitud, nunca borradas ni ocultas."),
    ("Hojas-fecha con mNDVI705 fuera de rango físico", n_qc_implausible,
     "mNDVI705 < -0.05 o > 1.05: indicio de reflejo especular en la banda azul (445 nm), no una "
     "diferencia biologica real."),
]

st.dataframe(
    filas_calidad, width="stretch", hide_index=True,
    column_config={0: "Que se marca/excluye", 1: st.column_config.NumberColumn("Archivos/hojas-fecha"), 2: "Por que"},
)

if n_qc_atipico or n_qc_implausible:
    with st.expander("Ver el detalle de las hojas-fecha marcadas"):
        cols = ["species", "leaf", "campaign_date", "qc_n_atipicos", "qc_atipico", "mNDVI705", "qc_implausible"]
        st.dataframe(
            ld_all[ld_all["qc_atipico"] | ld_all["qc_implausible"]][cols],
            width="stretch", hide_index=True,
        )

if not unrecognized.empty:
    with st.expander(f"⚠️ Archivos con nombre no reconocido ({len(unrecognized)})", expanded=False):
        st.dataframe(unrecognized[["path", "species", "susceptibility"]], width='stretch', hide_index=True)

if read_errors:
    with st.expander(f"⚠️ Archivos con error de lectura ({len(read_errors)})", expanded=False):
        for name, err in read_errors:
            st.write(f"- **{name}**: {err}")

st.divider()

# ============================================================================
# 3. Novedades y alerta de Telegram
# ============================================================================
st.subheader("3. Novedades y alerta de Telegram")
st.caption(
    "Compara los archivos actuales de `data/` contra la última verificación y, si hay "
    "mediciones nuevas, permite avisar por Telegram — pero primero muestra una vista previa: "
    "nada sale sin que la revises. La identidad de cada archivo es su ruta relativa a `data/` "
    "+ un hash de su contenido, así que mover o clonar el proyecto no genera novedades falsas."
)
col_verif, col_reset = st.columns([2, 1])
with col_verif:
    verificar = st.button("Verificar novedades", width="stretch")
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
        "Telegram. La próxima verificación solo avisará de lo que se agregue de aquí en adelante."
    )

if verificar:
    current_keys = {file_key(row.path, row.mtime_ns) for row in df.itertuples()}
    previous_keys = load_last_run()
    new_keys = current_keys - previous_keys

    if not previous_keys:
        st.info(
            f"Primera verificación: se registraron {len(current_keys)} archivo(s) como línea base. "
            "La próxima vez que agregues mediciones, se te notificará solo lo nuevo."
        )
        save_last_run(current_keys)
    elif not new_keys:
        st.info("No hay archivos nuevos desde la última verificación.")
    else:
        new_paths = {k.rsplit("|", 1)[0] for k in new_keys}
        # Las claves nuevas guardan la ruta RELATIVA a data/ (ver src/state.py); el DataFrame
        # trae la ruta absoluta, asi que se compara contra la version relativa de esa columna.
        rel_paths = df["path"].apply(lambda p: Path(p).resolve().relative_to(DATA_DIR.resolve()).as_posix())
        new_df = df[rel_paths.isin(new_paths)]
        resumen = new_df.groupby("species").size().sort_values(ascending=False)
        n_roya = int((new_df["health_status"] == ROYA_LABEL).sum())

        baselines = severity_baselines(df)
        reportes = leaf_severity_reports(new_df, baselines)

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
                save_last_run(current_keys)
                st.success(f"Enviado. {detalle}")
                for k in ("preview_new_df", "preview_resumen", "preview_n_roya", "preview_reportes", "preview_current_keys"):
                    st.session_state.pop(k, None)
                st.rerun()
            else:
                st.error(f"No se pudo enviar: {detalle}. El registro no se actualizó — se reintenta la próxima vez.")
    with c_discard:
        if st.button("Descartar vista previa", width="stretch"):
            for k in ("preview_new_df", "preview_resumen", "preview_n_roya", "preview_reportes", "preview_current_keys"):
                st.session_state.pop(k, None)
            st.rerun()

st.divider()

# ============================================================================
# 4. Glosario y que responde cada pagina
# ============================================================================
st.subheader("4. Glosario y navegacion")

col_mapa, col_glosario = st.columns(2)
with col_mapa:
    st.markdown("**Qué responde cada página**")
    st.markdown(
        "- **Inicio** — qué datos hay, su calidad, y novedades (esta página).\n"
        "- **1. Espectros** — cómo se ve la reflectancia de estas hojas.\n"
        "- **2. Índices espectrales** — qué índices separan hojas con roya de las que no.\n"
        "- **3. Comparación de especies** — cómo difieren las variedades entre sí.\n"
        "- **4. Estado de las hojas** — qué tan parecida es cada hoja madura a una hoja con roya, hoy.\n"
        "- **5. Evolución Temporal** — cómo cambia cada hoja física en el tiempo, y si es por "
        "roya o por envejecimiento."
    )
with col_glosario:
    st.markdown("**Terminos clave**")
    st.markdown(
        "- **Hoja-fecha**: una hoja física (ej. Bourbon M1) en una campaña concreta. Es la "
        "unidad de análisis: primero se promedian las repeticiones de cada punto, después los "
        "puntos (solo p1-p3), nunca se trata un punto o una repetición como observación "
        "independiente.\n"
        "- **Tipo de hoja** (M/T/R/V): Madura, Tierna, Con roya, Vieja — ver la tabla de la "
        "sección 1. Madura/Tierna **no** son 'sanas', son de estado sanitario desconocido.\n"
        "- **Similitud con roya**: qué tan parecido es el espectro de una hoja al de una hoja "
        "con roya confirmada de su misma especie, frente a una hoja tierna sana. No es un "
        "diagnostico.\n"
        "- **Control de calidad**: hojas-fecha marcadas por medición dudosa (ver sección 2)."
    )
