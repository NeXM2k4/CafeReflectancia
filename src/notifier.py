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

INDICES_ORDER = ["NDVI", "PRI", "PSRI", "RCI", "EDI", "FSR", "NDRE", "mNDVI705"]

# Un indice se considera "en rango de alerta" (y se resalta en negrita) cuando su valor
# normalizado entre la referencia sana y la referencia con roya llega al mismo umbral
# que la app usa para riesgo alto.
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
    """Que significa cada color y en que tramo de severidad cae, para leer las tarjetas."""
    lineas = ["📋 <b>What each colour means</b>", ""]
    for i, (_, nombre, emoji, descripcion) in enumerate(RUST_RISK_CLASSES):
        bajo, alto = _class_bounds(i)
        lineas.append(
            f"{emoji} <b>{nombre}</b> ({bajo * 100:.0f}–{alto * 100:.0f} %) — {_esc(descripcion)}"
        )
    return "\n".join(lineas)


def format_index_ranges(index_ranges: dict) -> str:
    """Informe de los valores minimo y maximo observados de cada indice.

    Es la referencia contra la que se lee el valor de cada indice en las tarjetas, que ahora
    muestran el porcentaje de severidad de ese indice en vez del rango.
    """
    lineas = [
        "📊 <b>Index reference ranges</b>",
        "",
        "Min and max observed across all reference leaves (young + rust-infected):",
    ]
    for name in INDICES_ORDER:
        rango = index_ranges.get(name, {})
        lineas.append(
            f"{name:<9}min {_fmt(rango.get('min')):>9}   max {_fmt(rango.get('max')):>9}"
        )
    return "\n".join(lineas)


def format_leaf_report(reporte: dict) -> str:
    """Tarjeta de una hoja: riesgo, ubicacion, severidad estimada y detalle de los 7 indices.

    `reporte` es un elemento de `leaf_severity_reports()` (src/severity.py). Los indices cuyo
    valor normalizado llega a ALERT_THRESHOLD se muestran en negrita.
    """
    score = reporte["score"]
    _, etiqueta, emoji, descripcion = rust_risk_class(score)

    partes = [f"Date: {_fecha(reporte.get('campaign_date'))}"]
    if reporte.get("species"):
        partes.append(_esc(reporte["species"]))
    if reporte.get("hoja"):
        partes.append(_esc(reporte["hoja"]))
    ubicacion = " - ".join(partes)

    nota_ref = (
        ""
        if reporte.get("referencia_propia", True)
        else " <i>(estimated reference: this species has no rust measurements of its own yet)</i>"
    )

    lineas = [
        f"{emoji} <b>{etiqueta}</b>",
        "",
        ubicacion,
        "",
        f"Estimated severity: <b>{score * 100:.0f} %</b> compared to a healthy reference leaf.",
        f"<i>{_esc(descripcion)}</i>",
        f"{rust_risk_action(score)}{nota_ref}",
        "",
        f"Indices — value and severity of that single index "
        f"({reporte['n_indices']}/{len(INDICES_ORDER)} comparable):",
    ]

    for name in INDICES_ORDER:
        info = reporte["indices"].get(name, {})
        norm = info.get("normalizado")
        pct = "–" if norm is None else f"{norm * 100:.0f} %"
        linea = f"{name:<9}{_fmt(info.get('valor')):>10}{pct:>8}"
        norm = info.get("normalizado")
        if norm is not None and norm >= ALERT_THRESHOLD:
            lineas.append(f"<b>{_esc(linea)}</b>")
        else:
            lineas.append(_esc(linea))

    return "\n".join(lineas)


def format_header(n_archivos: int, archivos_por_especie: dict, n_roya: int, reportes: list) -> str:
    """Primer mensaje: cuantos archivos nuevos hay, por especie, y como leer lo que sigue."""
    lineas = [
        "🍃 <b>Reflectance analysis updated</b>",
        f"{n_archivos} new file(s) detected in data/"
        + (f" — {len(reportes)} leaf(s) analysed." if reportes else "."),
    ]
    lineas += [f"- {_esc(especie)}: {n} file(s)" for especie, n in archivos_por_especie.items()]
    if n_roya:
        lineas.append(f"⚠️ {n_roya} file(s) flagged as rust in the filename.")

    if reportes:
        lineas += [
            "",
            "Each leaf is reported as the average of its measurement points and assigned to the "
            f"closest of the {len(RUST_RISK_CLASSES)} risk classes. Indices shown in <b>bold</b> "
            f"are in the alert range (≥ {ALERT_THRESHOLD * 100:.0f} % of the way towards the "
            "rust reference).",
        ]
        if any(not r.get("referencia_propia", True) for r in reportes):
            lineas += [
                "",
                "ℹ️ <i>Some of these species have no rust measurements of their own yet, so their "
                "score uses the combined reference of the species that do.</i>",
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
