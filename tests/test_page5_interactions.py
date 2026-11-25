"""La pagina 5 se probo antes con una sola interaccion por instancia; aqui se encadenan varias
(cambio de especie, control de calidad, indice y modo) porque un KeyError de session_state solo
aparecia en la tercera.

Desde 2026-11-19 las pestañas son perezosas (solo se dibuja la abierta): para tocar un control hay
que abrir antes su pestaña, y se comprueba que cada pestaña y subpestaña se dibuja sin errores."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent

PESTANAS = ["Resumen", "Hojas maduras", "¿Roya o edad?", "Detalle por hoja", "Datos y calidad"]
SUBPESTANAS = {
    "Hojas maduras": ("tabs_mad", None),  # la primera etiqueta depende del indice elegido
    "¿Roya o edad?": ("tabs_edad", ["Firma espectral por grupo", "Cada hoja (mapa de calor)", "¿Qué índices cambian?"]),
    "Detalle por hoja": ("tabs_det", ["Un índice", "Los 7 índices"]),
}


def _abrir(at, clave, etiqueta):
    at.session_state[clave] = etiqueta
    at.run()
    assert not at.exception, (etiqueta, [str(e) for e in at.exception])


def test_page5_survives_repeated_interactions():
    at = AppTest.from_file(str(ROOT / "views/evolucion.py"), default_timeout=180)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    for especie in ["Pacamara", "Canefora", "Cuscatleco", "Bourbon"]:
        at.selectbox(key="sp_sel").set_value(especie).run()
        assert not at.exception, (especie, [str(e) for e in at.exception])
    at.toggle(key="excl_qc").set_value(True).run()
    assert not at.exception, [str(e) for e in at.exception]
    _abrir(at, "tabs_evol", "Hojas maduras")
    at.selectbox(key="index_sel").set_value("NDRE").run()
    at.radio(key="modo_sel").set_value("Cambio desde la primera fecha (Δ)").run()
    assert not at.exception, [str(e) for e in at.exception]
    assert len(at.tabs) >= 5

    # La seleccion de «Hojas maduras» llega a «Detalle por hoja» y sobrevive al volver.
    _abrir(at, "tabs_evol", "Detalle por hoja")
    assert any("**NDRE**" in c.value and "Cambio desde la primera fecha" in c.value for c in at.caption)
    _abrir(at, "tabs_evol", "Hojas maduras")
    assert at.selectbox(key="index_sel").value == "NDRE"
    assert at.radio(key="modo_sel").value == "Cambio desde la primera fecha (Δ)"


def test_page5_cada_pestana_se_dibuja():
    at = AppTest.from_file(str(ROOT / "views/evolucion.py"), default_timeout=180)
    at.run()
    for pestana in PESTANAS:
        _abrir(at, "tabs_evol", pestana)
        clave, subs = SUBPESTANAS.get(pestana, (None, []))
        if clave is None:
            continue
        if subs is None:  # «Hojas maduras»: etiquetas tomadas de la pagina
            subs = [f"{at.selectbox(key='index_sel').value} en el tiempo", "Similitud relativa con roya",
                    "Distancia a R1", "Los 7 índices"]
        for sub in subs:
            _abrir(at, clave, sub)
