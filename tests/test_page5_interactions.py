"""La pagina 5 se probo antes con una sola interaccion por instancia; aqui se encadenan varias
(cambio de especie, control de calidad, indice y modo) porque un KeyError de session_state solo
aparecia en la tercera."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent


def test_page5_survives_repeated_interactions():
    at = AppTest.from_file(str(ROOT / "views/evolucion.py"), default_timeout=180)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    for especie in ["Pacamara", "Canefora", "Cuscatleco", "Bourbon"]:
        at.selectbox(key="sp_sel").set_value(especie).run()
        assert not at.exception, (especie, [str(e) for e in at.exception])
    at.toggle(key="excl_qc").set_value(True).run()
    assert not at.exception, [str(e) for e in at.exception]
    at.selectbox(key="index_sel").set_value("NDRE").run()
    at.radio(key="modo_sel").set_value("Cambio desde la primera fecha (Δ)").run()
    assert not at.exception, [str(e) for e in at.exception]
    assert len(at.tabs) >= 5
