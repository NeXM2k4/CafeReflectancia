# Estado del proyecto — vigente

Última actualización: 2026-11-24 (análisis espectral por hoja: `docs/plan_analisis_espectral.md`).
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

## 2026-11-24: análisis espectral por hoja (`docs/plan_analisis_espectral.md`)
Pedido en `PROMPT-noviembre24/prompt.txt`. Cuatro vistas nuevas bajo *Evolución temporal*: *Derivadas
espectrales*, *Correlación con el tiempo*, *Cambio espectral y PCA* y *Rasgos espectrales*. Una hoja a la
vez, cruda y normalizada, con estadística (Spearman + FDR por λ; Theil–Sen + Mann–Kendall + FDR para Δ por
región, puntajes de PCA y rasgos). Método en `METODOLOGIA.md` §10. 45 pruebas pasan; recarga ≤ 0,3 s por
página con caché (primera visita ~5 s). Las vistas existentes no cambian sus números.
Primer hallazgo: el patrón de Bourbon M1 en ρ vs tiempo (visible ↑, NIR normalizado ↓) aparece también en
Canefora M1 y Cuscatleco M1/M2 (controles sin roya): es compatible con envejecimiento.
Pendiente de decisión: informe Excel + figuras y su sincronización con Drive (opinión en el plan, §9).
El paper ya se entregó; `plan_mejora_paper.md` y `PAPER/` son historia.

Cómo se hizo: plan en `docs/plan_analisis_espectral.md` → F1 núcleo (`src/spectral.py`, `spectral_page.py`,
`spectral_plots.py`, `tests/test_spectral.py`, 12 pruebas) → F2 (`plots_forma.py`, `views/derivadas.py`,
`views/correlacion_tiempo.py`) y F3 (`plots_cambio.py`, `views/cambio_pca.py`, `views/rasgos.py`) en
paralelo → integración (`app.py`, `tests/test_smoke_pages.py`), revisión visual y ajustes (colores de las
franjas, espacio entre títulos, leyenda de regiones en la PCA). Se mostró al usuario en local el 2026-11-24.

Diferencias con las imágenes de ejemplo (a propósito): la primera fecha va arriba en los mapas de Δ; la
línea base es de 2 fechas por defecto (el ejemplo usa 1; hay selector); los espectros sin firma de hoja
(NDVI < 0,05) se excluyen por defecto en estas 4 vistas, por eso desaparece la franja del 24/08 de Bourbon M1.

### Siguiente sesión
1. Recoger la opinión del usuario sobre las 4 vistas (las vio en el navegador; aún no dio comentarios).
2. **Nada está commiteado.** El árbol tiene dos trabajos juntos: rendimiento P1/P2 (2026-11-19) y este
   análisis espectral. Preguntar si van en uno o dos commits (sin `Co-Authored-By`).
3. Decidir el informe Excel + figuras / Drive (plan §9; recomendación: script `scripts/export_report.py`
   y después una GitHub Action que sincronice a Drive).
4. Sigue pendiente lo anterior: medir el rendimiento en Streamlit Cloud y reescribir `plan_subida_datos.md`.
5. `PROMPT-noviembre24/` (pedido + imágenes) no está versionado: decidir si se guarda en `docs/`.

## 2026-11-16: fondo blanco, tendencias y arranque rápido
- Tema claro (fondo blanco) en toda la app; paleta revalidada sobre blanco (Pacamara pasa a `#B97A00`).
- Evolución temporal: puntos sin unir, tendencia LOWESS por hoja y significancia (Mann–Kendall + FDR)
  al final de cada línea. Cajas de *Índices* y *Variedades*: corchetes con asteriscos (p de Holm).
- Arranque: almacén precalculado versionado (`data_cache/`, `src/store.py`), lector de `.txt` más
  rápido y líneas de referencia de Plotly agregadas en bloque. Medido en local: arranque en frío
  ~36 s → ~11 s; *Evolución temporal* ~19 s → ~4 s por recarga.
- Corregido: la huella de `data/` nunca invalidaba el caché (parámetro con guion bajo); ahora los
  archivos nuevos aparecen solos en menos de un minuto.
- Subido a `main` en `f1d26d4` (incluye `data_cache/`, al día con `data/`: 3471 archivos, 0 por recalcular).

## Rendimiento (2026-11-19): P1 y P2 hechos, falta medir en la nube
Detalle y números en `docs/plan_rendimiento.md` § 6. En *Evolución temporal* cada clic pasó de
~3,9 s a 0,6–1,3 s: plantilla de Plotly combinada una vez, `leaf_trends` en caché y pestañas que
solo dibujan la abierta. Costo: cambiar de pestaña ya no es instantáneo (~0,6–1,3 s). La app ya no
lee los 212 MB de `.txt` al arrancar (verifica `data_cache/` por ruta + tamaño; si se reemplaza un
`.txt`, correr `build_cache.py`, ver `README.md`). Mismos números: 29 pruebas pasan.
**Siguiente:** medir en Streamlit Cloud (hace falta la URL) y decidir P3 con esos números.

Aparte, en pausa: `plan_subida_datos.md` (subir campañas desde la app con un zip). El usuario no
quedó convencido; hay que reescribirlo antes de implementar nada.

### Lista anterior (2026-11-16)
El equipo reporta que la app en Streamlit Cloud sigue tardando en arrancar. **Primero medir**, después
optimizar:

1. **Medir en la nube** (después del push de `f1d26d4`): cuánto tarda y en qué pantalla se queda.
   - Pantalla de Streamlit antes de la app («in the oven» / «waking up»): es el contenedor de la
     plataforma; no se arregla desde el código. Opción: otro hosting (`DEPLOY.md` §C).
   - «Running…» dentro de la app: es nuestro código; seguir con 2 y 3.
2. **(Recomendada) No releer los ~192 MB de `.txt` al arrancar.** Hoy `store.build_store` calcula el
   sha1 de cada archivo para verificar el almacén; en el disco de la nube puede ser lo más lento.
   Propuesta: verificar por ruta + tamaño y dejar la verificación por contenido en
   `scripts/build_cache.py` y en `tests/test_store.py::test_almacen_versionado_esta_al_dia` (que ya
   detecta un almacén desactualizado antes de commitear). Riesgo a declarar: un archivo reemplazado
   por otro del mismo tamaño sin regenerar el almacén pasaría sin detectarse en la app.
3. **Guardar también resultados derivados** en `data_cache/` (tablas hoja-fecha, tendencias de
   `leaf_trends`, espectros medios y tendencias espectrales), con la misma huella de método, para que
   *Evolución temporal* no los recalcule en la primera visita de cada arranque.
4. Opcional: leer del parquet solo las columnas de índices en las páginas que no usan espectros
   (Panorama, Estado actual) y cargar los 300 puntos de espectro solo en *Espectros* y *Evolución*.

Referencias de tiempos (local, `AppTest`): imports ~2–3 s; carga del almacén ~1–1.5 s; cálculo por
página ~1–4 s. Detalle en `docs/plan_fondo_blanco_tendencias_rendimiento.md`.

También pendiente (fuera de rendimiento): *Panorama* todavía dice «semanal, 29/06 a 21/09» y algunas
notas hablan de «12 semanas»; hay que generar esos textos a partir de los datos.

## Abierto (no es trabajo de la app)
- **Datos nuevos (oct–nov):** 18 archivos `Validacion1p*bourbon*.txt` (26/10 y 05/11) no se reconocen
  y no entran al análisis; falta saber qué hoja es. Los `p*roya*` de Pacamara del 19/10 están en una
  carpeta `suceptible/vieja/` y hoy se leen como R1.
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
