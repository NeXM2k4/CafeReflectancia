"""Envio de notificaciones por Telegram cuando termina el analisis de datos nuevos.

Requiere credenciales en .streamlit/secrets.toml (ver .streamlit/secrets.toml.example):

    [telegram]
    bot_token = "123456:ABC-DEF..."
    chat_id = "123456789"

El mensaje se arma por hoja (una tarjeta de riesgo por hoja) y se parte en varios envios,
porque la API de Telegram rechaza cualquier texto de mas de 4096 caracteres.
"""

from __future__ import annotations

import html
import math
import time

import requests
import streamlit as st

from src.config import RUST_RISK_CLASSES, rust_risk_action, rust_risk_class

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# Limite duro de la API de Telegram por mensaje. Un texto mas largo devuelve
# 400 "message is too long" y NO se entrega nada.
TELEGRAM_MAX_CHARS = 4096

# Pausa entre envios consecutivos, para no chocar con el limite de rate de Telegram
# (~20 mensajes por minuto al mismo chat).
SEND_DELAY_S = 0.4

INDICES_ORDER = ["NDVI", "PRI", "PSRI", "RCI", "EDI", "NDRE", "mNDVI705"]
# FSR se quito de la alerta (2026-09-28): usa las mismas bandas que NDVI (WL_FSR = WL_NDVI en
# config.py), asi que su valor es identico y no aporta informacion propia — ver X8 de
# plan_mejora_app.md.

# Un indice se considera "en rango de alerta" (y se resalta en negrita) cuando su valor
# normalizado entre la referencia sana y la referencia con roya llega a este umbral. Con la
# escala de 4 clases (F3.3), 0.66 practicamente coincide con el nivel de "Revisar en campo"
# (2/3 = 0.667), asi que no hizo falta ajustarlo al reducir de 11 a 4 clases.
ALERT_THRESHOLD = 0.66

BLOCK_SEPARATOR = "\n\n———\n\n"


def _esc(text) -> str:
    """Escapa el texto para parse_mode=HTML de Telegram (solo & < > son especiales)."""
    return html.escape(str(text), quote=False)


def _fecha(valor) -> str:
    """Fecha de la campaña en dd/mm/yyyy; el dataset la guarda como 'yyyy-mm-dd'."""
    try:
        anio, mes, dia = str(valor).split("-")
        return f"{dia}/{mes}/{anio}"
    except (AttributeError, ValueError):
        return "–"


def _fmt(v, decimals: int = 3) -> str:
    """Valor numerico con decimales fijos, o '–' si es nulo o NaN."""
    try:
        f = float(v)
        if math.isnan(f):
            return "–"
        return f"{f:.{decimals}f}"
    except (TypeError, ValueError):
        return "–"


def _class_bounds(indice: int) -> tuple[float, float]:
    """Tramo de similitud que cae en esa clase: como se asigna por cercania (no por umbral

    fijo), el limite entre dos clases es el punto medio entre sus niveles nominales. Antes se
    usaba un margen fijo de +-5 %, valido solo cuando las clases estaban espaciadas cada 10 %
    (las 11 clases viejas); con las 4 clases actuales (espaciado desigual: 0, 1/3, 2/3, 1) un
    margen fijo dejaria huecos o superposiciones en el texto de `format_risk_scale()`.
    """
    niveles = [c[0] for c in RUST_RISK_CLASSES]
    nivel = niveles[indice]
    bajo = 0.0 if indice == 0 else (niveles[indice - 1] + nivel) / 2
    alto = 1.0 if indice == len(RUST_RISK_CLASSES) - 1 else (nivel + niveles[indice + 1]) / 2
    return bajo, alto


def format_risk_scale() -> str:
    """Que significa cada clase y en que tramo de similitud cae, para leer las tarjetas."""
    lineas = ["📋 <b>Que significa cada clase</b>", ""]
    for i, (_, nombre, emoji, descripcion) in enumerate(RUST_RISK_CLASSES):
        bajo, alto = _class_bounds(i)
        lineas.append(
            f"{emoji} <b>{nombre}</b> ({bajo * 100:.0f}–{alto * 100:.0f} %) — {_esc(descripcion)}"
        )
    return "\n".join(lineas)


def format_index_ranges(index_ranges: dict) -> str:
    """Informe de los valores minimo y maximo observados de cada indice.

    Es la referencia contra la que se lee el valor de cada indice en las tarjetas, que ademas
    muestran el porcentaje de similitud de ese indice en particular.
    """
    lineas = [
        "📊 <b>Rangos de referencia de cada indice</b>",
        "",
        "Minimo y maximo observado en todas las hojas de referencia (tiernas + con roya):",
    ]
    for name in INDICES_ORDER:
        rango = index_ranges.get(name, {})
        lineas.append(
            f"{name:<9}min {_fmt(rango.get('min')):>9}   max {_fmt(rango.get('max')):>9}"
        )
    return "\n".join(lineas)


def format_leaf_report(reporte: dict) -> str:
    """Tarjeta de una hoja: clase, ubicacion, similitud estimada y detalle de los 7 indices.

    `reporte` es un elemento de `leaf_severity_reports()` (src/severity.py). Los indices cuyo
    valor normalizado llega a ALERT_THRESHOLD se muestran en negrita.
    """
    score = reporte["score"]
    _, etiqueta, emoji, descripcion = rust_risk_class(score)
    hoja = reporte.get("hoja") or ""

    partes = [f"Fecha: {_fecha(reporte.get('campaign_date'))}"]
    if reporte.get("species"):
        partes.append(_esc(reporte["species"]))
    if hoja:
        partes.append(_esc(hoja))
    ubicacion = " - ".join(partes)

    nota_ref = (
        ""
        if reporte.get("referencia_propia", True)
        else " <i>(referencia estimada: esta especie todavia no tiene medidas de roya propias)</i>"
    )
    # F3.1: las hojas Tierna/Con roya que llegan en el mismo lote son la referencia que define
    # las anclas (deberian salir ~0 % y ~100 % por construccion), no una alerta para actuar.
    nota_tipo = ""
    if hoja[:1] == "T":
        nota_tipo = " <i>(hoja de referencia sana — no requiere accion en si misma)</i>"
    elif hoja[:1] == "R":
        nota_tipo = " <i>(hoja de referencia con roya confirmada — no requiere accion en si misma)</i>"
    # F3.5: menos de 3 puntos ese dia es una medicion mas fragil que de costumbre.
    nota_calidad = (
        f" ⚠️ <i>medida con solo {reporte['n_puntos']} punto(s) esa fecha</i>"
        if reporte.get("n_puntos", 3) < 3 else ""
    )

    lineas = [
        f"{emoji} <b>{etiqueta}</b>",
        "",
        ubicacion,
        "",
        f"Similitud con la hoja con roya: <b>{score * 100:.0f} %</b> (0 % = como una hoja "
        f"tierna sana; 100 % = como la hoja con roya confirmada de referencia).",
        f"<i>{_esc(descripcion)}</i>{nota_tipo}{nota_calidad}",
        f"{rust_risk_action(score)}{nota_ref}",
        "",
        f"Indices — valor y similitud de ese indice por si solo "
        f"({reporte['n_indices']}/{len(INDICES_ORDER)} comparables):",
    ]

    for name in INDICES_ORDER:
        info = reporte["indices"].get(name, {})
        norm = info.get("normalizado")
        pct = "–" if norm is None else f"{norm * 100:.0f} %"
        linea = f"{name:<9}{_fmt(info.get('valor')):>10}{pct:>8}"
        if norm is not None and norm >= ALERT_THRESHOLD:
            lineas.append(f"<b>{_esc(linea)}</b>")
        else:
            lineas.append(_esc(linea))

    return "\n".join(lineas)


def format_header(n_archivos: int, archivos_por_especie: dict, n_roya: int, reportes: list) -> str:
    """Primer mensaje: cuantos archivos nuevos hay, por especie, y como leer lo que sigue."""
    lineas = [
        "🍃 <b>Analisis de reflectancia actualizado</b>",
        f"{n_archivos} archivo(s) nuevo(s) detectado(s) en data/"
        + (f" — {len(reportes)} hoja(s) analizada(s)." if reportes else "."),
    ]
    lineas += [f"- {_esc(especie)}: {n} archivo(s)" for especie, n in archivos_por_especie.items()]
    if n_roya:
        lineas.append(f"⚠️ {n_roya} archivo(s) marcado(s) como roya en el nombre.")

    if reportes:
        lineas += [
            "",
            "Cada hoja se reporta como el promedio de sus puntos de medicion y se asigna a la "
            f"clase mas cercana de las {len(RUST_RISK_CLASSES)}. Los indices en <b>negrita</b> "
            f"estan en rango de alerta (≥ {ALERT_THRESHOLD * 100:.0f} % del camino hacia la "
            "referencia con roya). Las hojas Tierna/Con roya que aparezcan son la referencia, "
            "no una alerta.",
        ]
        if any(not r.get("referencia_propia", True) for r in reportes):
            lineas += [
                "",
                "ℹ️ <i>Algunas de estas especies todavia no tienen medidas de roya propias, asi "
                "que su similitud usa la referencia combinada de las que si tienen.</i>",
            ]

    return "\n".join(lineas)


def _hard_split(text: str, max_chars: int) -> list[str]:
    """Parte un bloque unico demasiado largo por saltos de linea (nunca a mitad de una etiqueta)."""
    partes, actual = [], ""
    for linea in text.split("\n"):
        candidato = f"{actual}\n{linea}" if actual else linea
        if len(candidato) <= max_chars:
            actual = candidato
            continue
        if actual:
            partes.append(actual)
        actual = linea[:max_chars]
    if actual:
        partes.append(actual)
    return partes


def pack_messages(blocks: list[str], max_chars: int = TELEGRAM_MAX_CHARS) -> list[str]:
    """Agrupa bloques en la menor cantidad de mensajes posible sin pasar el limite de Telegram.

    Nunca corta un bloque por la mitad salvo que ese bloque solo no entre en un mensaje.
    """
    mensajes: list[str] = []
    actual = ""
    for block in blocks:
        if not block:
            continue
        candidato = f"{actual}{BLOCK_SEPARATOR}{block}" if actual else block
        if len(candidato) <= max_chars:
            actual = candidato
            continue
        if actual:
            mensajes.append(actual)
            actual = ""
        if len(block) <= max_chars:
            actual = block
        else:
            partes = _hard_split(block, max_chars)
            mensajes.extend(partes[:-1])
            actual = partes[-1]
    if actual:
        mensajes.append(actual)
    return mensajes


def build_notification(
    n_archivos: int, archivos_por_especie: dict, n_roya: int, reportes: list
) -> list[str]:
    """Arma la notificacion completa (encabezado + una tarjeta por hoja) ya partida en mensajes."""
    blocks = [format_header(n_archivos, archivos_por_especie, n_roya, reportes)]
    blocks += [format_leaf_report(r) for r in reportes]
    return pack_messages(blocks)


def _get_credentials() -> tuple[str, str] | None:
    try:
        cfg = st.secrets["telegram"]
        return cfg["bot_token"], cfg["chat_id"]
    except Exception:
        return None


def send_telegram_message(text: str, parse_mode: str = "HTML") -> tuple[bool, str]:
    """Envia un mensaje de texto al chat configurado. Devuelve (ok, detalle)."""
    creds = _get_credentials()
    if creds is None:
        return False, (
            "Faltan las credenciales de Telegram. Crea .streamlit/secrets.toml "
            "a partir de .streamlit/secrets.toml.example con tu bot_token y chat_id."
        )
    bot_token, chat_id = creds

    try:
        resp = requests.post(
            TELEGRAM_API.format(token=bot_token),
            data={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            timeout=15,
        )
    except requests.RequestException as e:
        return False, f"No se pudo enviar el mensaje de Telegram: {e}"

    if resp.status_code != 200:
        # La descripcion de la API dice exactamente que fallo (texto muy largo, HTML mal
        # formado, chat_id invalido...); sin ella el error es imposible de diagnosticar.
        try:
            detalle = resp.json().get("description", resp.text[:300])
        except ValueError:
            detalle = resp.text[:300]
        return False, f"Telegram respondió {resp.status_code}: {detalle}"

    return True, "Mensaje enviado por Telegram."


def send_telegram_messages(messages: list[str]) -> tuple[bool, str]:
    """Envia varios mensajes en orden. Se detiene en el primer fallo e informa cuantos salieron."""
    if not messages:
        return False, "No hay nada que enviar."

    for i, msg in enumerate(messages):
        ok, detalle = send_telegram_message(msg)
        if not ok:
            return False, f"Se enviaron {i} de {len(messages)} mensaje(s). {detalle}"
        if i < len(messages) - 1:
            time.sleep(SEND_DELAY_S)

    return True, f"{len(messages)} mensaje(s) enviados por Telegram."
