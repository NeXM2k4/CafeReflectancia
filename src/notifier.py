"""Envio de notificaciones por Telegram cuando termina el analisis de datos nuevos.

Requiere credenciales en .streamlit/secrets.toml (ver .streamlit/secrets.toml.example):

    [telegram]
    bot_token = "123456:ABC-DEF..."
    chat_id = "123456789"
"""

from __future__ import annotations

import requests
import streamlit as st

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


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
