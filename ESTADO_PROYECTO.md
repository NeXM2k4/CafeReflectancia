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
Reiniciar el proceso tras cambiar código en `src/` o `pages/`. "🔄 Recargar datos" (Inicio) fuerza
un nuevo escaneo de `data/`. Pruebas: `pip install -r requirements-dev.txt && python -m pytest tests -q`.

## Estructura
```
app.py                     Inicio: inventario, calidad de datos, novedades y alerta, glosario
pages/1_Espectros.py       ¿Cómo se ve la reflectancia?
pages/2_Indices_Espectrales.py   ¿Qué índices separan tipos de hoja?
pages/3_Comparacion_Especies.py  ¿Difieren las variedades (mismo tipo de hoja)?
pages/4_Estado_Hojas.py    ¿Cómo está hoy cada hoja madura? (similitud con roya)
pages/5_Evolucion_Temporal.py    ¿Cómo cambia cada hoja en el tiempo? (5 pestañas)
src/parser.py              descubre y parsea los .txt de data/
src/processing.py          suavizado + fórmulas de índices
src/indices.py             tabla única de índices por archivo/punto/hoja-fecha + control de calidad
src/severity.py            anclas y similitud con roya
src/stats_utils.py         estadística con veredicto
src/temporal.py            series por hoja, Δ/Δ*, tendencias, distancia a R1
src/temporal_plots.py      helpers de gráficos de la página 5
src/notifier.py, state.py  alerta de Telegram y registro de novedades
tests/                     humo de las 6 páginas + interacciones repetidas de la página 5
```
Agregar una campaña = copiar la carpeta a `data/`; no requiere tocar código si sigue la convención
de nombres (`docs/bitacora.md` §4).

## Qué se hizo en la mejora de la app
Todo el plan `plan_mejora_app.md` (F0–F6). Detalle por tarea en `PROGRESO_MEJORA_APP.md`.

## Abierto (no es trabajo de la app)
- **Datos:** 45 archivos de "hoja vieja" sin especie confirmada; 3 archivos `araña*.txt` sin
  significado; solo 1 hoja con roya por especie; no hay etiqueta de hoja asintomática infectada.
- **Prueba en navegador real** de la página 5 (la extensión de Chrome no respondió en las sesiones
  de desarrollo): abrir cada pestaña, cambiar de especie varias veces y darle "Reproducir" a la
  animación.
- **Paper (CONCAPAN):** pausado; se retoma con `plan_mejora_paper.md` a partir de `METODOLOGIA.md`.
  Las figuras de `figures_ieee/` y las tablas de `docs/bitacora.md` §14 son anteriores a las
  7 campañas nuevas y a los cambios de similitud: hay que regenerarlas.
- **Telegram en producción:** el registro de archivos vistos vive en `.state/` (no se versiona).
  En un hosting con disco efímero se pierde al reiniciar (ver `DEPLOY.md`).
