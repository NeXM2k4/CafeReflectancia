# Estado del proyecto — vigente

Última actualización: 2026-09-28 (cierre de `plan_mejora_app.md`, rama `mejora-app`).
Historia y decisiones antiguas: `docs/bitacora.md`. Método: `METODOLOGIA.md`. Cómo desplegar: `DEPLOY.md`.

## Qué es
App Streamlit que analiza reflectancia foliar de café (SpectraSuite) para estudiar la roya en 4
especies (Bourbon, Pacamara, Canefora, Cuscatleco). Solo Bourbon y Pacamara son susceptibles y
tienen una hoja con roya confirmada (R1); las otras dos son controles sin roya.

## Cómo correrla
```bash
pip install -r requirements.txt
streamlit run app.py
```
Reiniciar el proceso tras cambiar código en `src/`. «Volver a escanear data/» (en *Datos y calidad*)
fuerza un nuevo escaneo. Pruebas: `pip install -r requirements-dev.txt && python -m pytest tests -q`.

## Estructura
Ver la tabla de vistas y el árbol del repositorio en `README.md`. `app.py` es el enrutador
(`st.navigation`); cada vista vive en `views/`; el sistema visual común en `src/ui.py`.
Agregar una campaña = copiar la carpeta a `data/`; no requiere tocar código si sigue la convención
de nombres (`docs/bitacora.md` §4).

## Qué se hizo en la mejora de la app
Todo el plan `plan_mejora_app.md` (F0–F6) y la presentación de `plan_presentacion.md`
(navegación agrupada, sistema visual único, estadística por pares). Detalle en `PROGRESO_MEJORA_APP.md`.

## Abierto (no es trabajo de la app)
- **Datos:** 45 archivos de "hoja vieja" sin especie confirmada; 3 archivos `araña*.txt` sin
  significado; solo 1 hoja con roya por especie; no hay etiqueta de hoja asintomática infectada.
- **Espectros sin firma de hoja:** 4 espectros con NDVI ≈ 0 (reflectancia plana, probable referencia
  blanca): Bourbon M1 p3 del 24/08 (las 3 repeticiones) y Cuscatleco M1 p3 del 17/08 (1 repetición).
  Hoy entran en los promedios y explican la caída de Bourbon M1 el 24/08. Están marcados en
  *Datos y calidad*; falta decidir si se excluyen (cambia números).
- **Animación de espectros** (Evolución temporal → Detalle por hoja): verificada en Chrome headless
  que se dibuja; conviene darle «Reproducir» a mano una vez.
- **Paper (CONCAPAN):** pausado; se retoma con `plan_mejora_paper.md` a partir de `METODOLOGIA.md`.
  Las figuras de `figures_ieee/` y las tablas de `docs/bitacora.md` §14 son anteriores a las
  7 campañas nuevas y a los cambios de similitud: hay que regenerarlas.
- **Telegram en producción:** el registro de archivos vistos vive en `.state/` (no se versiona).
  En un hosting con disco efímero se pierde al reiniciar (ver `DEPLOY.md`).
