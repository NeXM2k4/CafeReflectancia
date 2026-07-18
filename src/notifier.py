"""Envio de notificaciones por Telegram cuando termina el analisis de datos nuevos.

Requiere credenciales en .streamlit/secrets.toml (ver .streamlit/secrets.toml.example):

    [telegram]
    bot_token = "123456:ABC-DEF..."
    chat_id = "123456789"
"""

from __future__ import annotations

import math

import requests
import streamlit as st

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

INDICES_ORDER = ["NDVI", "PRI", "PSRI", "CARI", "RCI", "EDI", "FSR"]


def _fmt(v) -> str:
    """Valor numerico con 3 decimales, o '–' si es nulo o NaN."""
    try:
        f = float(v)
        if math.isnan(f):
            return "–"
        return f"{f:.3f}"
    except (TypeError, ValueError):
        return "–"


def _severity_label(score: float) -> str:
    """Etiqueta simple en lenguaje llano para que un trabajador de campo la entienda de un vistazo."""
    if score < 0.33:
        return "🟢 riesgo bajo"
    if score < 0.66:
        return "🟡 riesgo medio"
    return "🔴 riesgo alto"


def format_severity_summary(species_scores: dict) -> str:
    """Promedio de indicio de roya por especie (0% sana - 100% enferma), para la alerta de Telegram."""
    return "\n".join(
        f"- {especie}: {score * 100:.0f}% {_severity_label(score)}"
        for especie, score in species_scores.items()
    )


def format_species_index_comparison(
    species_scores: dict,
    species_avg_indices: dict,
    baselines: dict,
    global_range: dict,
) -> str:
    """Bloque por especie: valores promedio de cada indice vs. referencia sana (T), enferma (R) y rango global."""
    blocks = []
    for species, score in species_scores.items():
        label = _severity_label(score)
        ref_propia = baselines.get(species, {}).get("referencia_propia", True)
        nota_ref = "" if ref_propia else " _(ref. estimada)_"
        idx_baseline = baselines.get(species, {}).get("indices", {})
        avg = species_avg_indices.get(species, {})

        lines = [f"*{species} — {score * 100:.0f}% {label}{nota_ref}*"]
        for idx_name in INDICES_ORDER:
            val = avg.get(idx_name)
            ref = idx_baseline.get(idx_name, {})
            sana_val = ref.get("sana")
            enf_val = ref.get("enferma")
            gr = global_range.get(idx_name, {})
            min_val = gr.get("min")
            max_val = gr.get("max")
            rango = (
                f"[{_fmt(min_val)} – {_fmt(max_val)}]"
                if min_val is not None and max_val is not None
                else "–"
            )
            lines.append(
                f"  • {idx_name}: {_fmt(val)}"
                f" | sana(T): {_fmt(sana_val)}"
                f" | roya(R): {_fmt(enf_val)}"
                f" | rango: {rango}"
            )
        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


def format_severity_detail(file_scores: list) -> str:
    """Detalle de indicio de roya por hoja/archivo nuevo, para la alerta de Telegram."""
    lineas = []
    for item in file_scores:
        nota = "" if item["referencia_propia"] else " (referencia estimada: esta especie aun no tiene roya propia registrada)"
        lineas.append(
            f"- {item['species']} hoja {item['hoja']}, punto {item['punto']}: "
            f"{item['score'] * 100:.0f}% {_severity_label(item['score'])} "
            f"({item['n_indices']}/7 indices){nota}"
        )
    return "\n".join(lineas)


def _get_credentials() -> tuple[str, str] | None:
    try:
        cfg = st.secrets["telegram"]
        return cfg["bot_token"], cfg["chat_id"]
    except Exception:
        return None


def send_telegram_message(text: str) -> tuple[bool, str]:
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
            data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        resp.raise_for_status()
        return True, "Mensaje enviado por Telegram."
    except requests.RequestException as e:
        return False, f"No se pudo enviar el mensaje de Telegram: {e}"
