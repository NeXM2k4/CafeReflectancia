# Plan: análisis espectral por hoja (derivadas, correlación con el tiempo, Δ + PCA, rasgos)

Fecha: 2026-11-24. Origen: `PROMPT-noviembre24/prompt.txt` (+ 3 imágenes de ejemplo en esa carpeta).
Estado: **implementado el 2026-11-24** (F0–F5). La parte de Drive (§9) es solo una opinión: no se implementa.

## 1. Para qué

Los 7 índices usan 2–3 bandas cada uno; lo que pasa entre esas bandas (forma del borde rojo, posición
del pico verde, cambios de forma vs. cambios de nivel) no se ve. Se agregan **cuatro vistas nuevas**
que trabajan con el **espectro completo de cada hoja física**, una hoja a la vez, a lo largo de las
20 campañas, cada una con su análisis estadístico.

**Nunca se promedian hojas distintas** (ni de la misma variedad): es seguimiento longitudinal a campo
abierto. La unidad es la **hoja-fecha** de siempre: archivo → punto (media de repeticiones) → hoja-fecha
(media de p1–p3) = `temporal.leaf_mean_spectra` (grilla del almacén, 440–1000 nm, paso ≈1,87 nm).

Éxito = para cualquier hoja (18 hojas: Bourbon M1 M2 T1 T2 R1, Pacamara ídem, Canefora M1 M2 T1 T2,
Cuscatleco M1 M2 T1 T2) se ven las figuras de las 3 imágenes de ejemplo, en versión cruda y
normalizada, con una tabla estadística debajo, y ninguna vista existente cambia sus números.

## 2. Navegación

En `app.py`, sección **«Seguimiento de hojas»**, debajo de *Evolución temporal*, en este orden:

| Página | Archivo | Ítem del prompt |
|---|---|---|
| Derivadas espectrales | `views/derivadas.py` | 1 |
| Correlación con el tiempo | `views/correlacion_tiempo.py` | 2 |
| Cambio espectral y PCA | `views/cambio_pca.py` | 3 |
| Rasgos espectrales | `views/rasgos.py` | 4 |

## 3. Decisiones de método (fijas; se documentan en `METODOLOGIA.md` §10)

### 3.1 Datos de entrada
- Hojas M, T y R de las 4 variedades, puntos p1–p3 (lo mismo que *Evolución temporal*:
  `temporal.temporal_selection` + `temporal.file_indices`).
- **Rango de análisis 440–900 nm** (`SPECTRAL_WL = (440, 900)`): por debajo de 440 hay reflectancia
  negativa en R; por encima de 900 el detector es ruidoso. ~246 puntos de grilla.
- **Espectros sin firma de hoja** (NDVI < 0,05 a nivel archivo, p. ej. referencia blanca: Bourbon M1 p3
  24/08 ×3, Cuscatleco M1 p3 17/08 ×1): **se excluyen por defecto** en estas 4 vistas porque destruyen
  cualquier análisis de forma (son la franja roja del 24/08 en la imagen de ejemplo). Interruptor en la
  barra lateral para incluirlos. La constante `NDVI_SIN_HOJA = 0.05` pasa de `views/datos_calidad.py` a
  `src/config.py` (datos_calidad la importa de ahí; mismo valor). Las vistas existentes no cambian.
- Interruptor **«Excluir hojas-fecha atípicas»** (misma regla `temporal.qc_flags` que *Evolución
  temporal*), apagado por defecto. Las fechas atípicas se marcan con «⚠» en etiquetas y tablas.
- Tiempo: `dia` = días desde la primera campaña del dataset (`T_CERO`), igual que *Evolución temporal*.

### 3.2 Normalización («forma»)
- **Cruda:** reflectancia en % (0–100).
- **Normalizada por área (por defecto):** `R(λ) / media(R, 440–900 nm)`. Quita los cambios
  multiplicativos de nivel (acople de la sonda, referencia de blanco, distancia) y deja la forma.
  Es la que reproduce los ejemplos (correlación negativa en NIR al normalizar).
- **Alternativa (sensibilidad):** normalizada por meseta NIR `R / media(R, 750–900)` — la misma que ya usa
  `temporal.spectral_trends`. Selector en la barra lateral: «Normalización: área 440–900 | meseta NIR».
- Toda figura y tabla se muestra **en las dos versiones, cruda y normalizada, lado a lado** (como en
  los ejemplos), nunca solo una.

### 3.3 Derivadas
- Savitzky–Golay sobre la grilla uniforme del espectro medio hoja-fecha:
  `savgol_filter(R, window_length=SPECTRAL_DERIV_WINDOW, polyorder=SPECTRAL_DERIV_POLY, deriv=k, delta=Δλ)`
  con ventana **7 puntos (≈13 nm)** y polinomio **3**, k = 1 y 2. Unidades: %/nm y %/nm² (crudas);
  1/nm y 1/nm² (normalizadas).
- Sensibilidad: en «Avanzado», ventana 5 / 7 / 11.
- Regiones (como el ejemplo): **azul-verde 440–600 nm** (carotenoides/clorofila) y **borde rojo
  650–780 nm**.

### 3.4 Correlación con el tiempo (ítem 2)
- Por hoja y por λ: **ρ de Spearman** entre R(λ) y `dia`, con p bilateral (`scipy.stats.spearmanr`).
- **FDR de Benjamini–Hochberg sobre las λ de esa hoja** (válido con dependencia positiva entre λ
  vecinas). Se dibuja la curva de ρ; puntos rellenos donde p_FDR < 0,05 y huecos donde solo
  p sin corregir < 0,05 (el ejemplo usa sin corregir; se muestran los dos).
- Mínimo 5 fechas (`TEMPORAL_MIN_FECHAS_TENDENCIA`); con menos (Canefora M2/T2: 4) se dibuja ρ sin p.
- Franjas de región como el ejemplo: azul/carotenoides 440–520, absorción de clorofila 640–700,
  borde rojo 700–760.
- La misma función se aplica a la primera derivada (página 1, franja «ρ vs tiempo» debajo de cada panel).

### 3.5 Δ reflectancia vs campaña(s) inicial(es) (ítem 3a)
- `Δ(λ, t) = R(λ, t) − media_{primeras n_base fechas de esa hoja} R(λ)`. **`n_base` = 2 por defecto**
  (= `TEMPORAL_BASELINE_CAMPAIGNS`, menos ruido que una sola fecha); selector 1/2/3. Para R1 su línea
  base son sus propias primeras fechas (15/07), no las del dataset.
- Mapa de calor fechas × λ, escala divergente centrada en 0 y **simétrica** (±máx |Δ| de la hoja),
  etiqueta de fila «dd-Mmm (n=puntos)» como el ejemplo; las filas de línea base se marcan «(base)».
- Estadística: Δ medio por región (azul 440–520, verde 520–600, rojo 640–700, borde rojo 700–760,
  NIR 760–900) por fecha → **Theil–Sen + Mann–Kendall + FDR BH** con `temporal.leaf_trends`
  (familias «Δ región cruda» y «Δ región normalizada», FDR sobre las 18 hojas × 5 regiones).
  Ruido de referencia: SD entre puntos p1–p3 en las fechas base, por región (tabla al lado).

### 3.6 PCA (ítem 3b)
- **Por hoja** (principal): matriz fechas × λ, **centrada por λ, sin escalar** (todas las λ están en
  las mismas unidades; escalar inflaría el azul ruidoso). SVD de numpy (sin sklearn). 3 componentes.
- Signo: se orienta cada PC para que su puntaje tenga ρ de Spearman ≥ 0 con el tiempo (así la carga
  se lee como «hacia dónde cambia el espectro con el tiempo»). Si ρ = 0 exacto, se deja el signo de SVD.
- Se muestra: varianza explicada, cargas vs λ (con franjas de región), puntajes PC1–PC3 vs fecha.
  Cruda y normalizada.
- **Espacio común** (secundario, desplegable): PCA ajustada sobre todas las hojas-fecha de todas las
  hojas (normalizada), y trayectoria PC1–PC2 de cada hoja por separado (no se promedian hojas;
  sirve para ver si M de susceptibles se mueve hacia R1).
- Estadística: puntajes PC1–PC3 de la PCA por hoja vs tiempo con `leaf_trends` (Theil–Sen +
  Mann–Kendall + FDR); se declara que en PCA por hoja PC1 de hojas distintas no es el mismo eje.

### 3.7 Rasgos espectrales (ítem 4, lo que los índices no dan)
Por hoja-fecha, sobre el espectro medio crudo (y su derivada de §3.3):

| Rasgo | Definición | Por qué |
|---|---|---|
| `REP_max` (nm) | λ del máximo de dR/dλ en 680–760, refinado con parábola sobre 3 puntos | Posición del borde rojo (clorofila); los índices solo ven su pendiente |
| `REP_lineal` (nm) | Guyot & Baret (1988): Rre=(R670+R780)/2; 700+40·(Rre−R700)/(R740−R700) | Robusto al doble pico |
| `D_max` (%/nm) | máx dR/dλ en 680–760 | Amplitud del borde |
| `Doble pico` | máx dR/dλ 695–712 / máx dR/dλ 715–735 | Visible en el ejemplo; se asocia a estrés |
| `λ verde` (nm), `R verde` (%) | posición y valor del máximo de R en 500–600 | Pico verde |
| `Prof. clorofila` | 1 − R/Rc mínimo en 600–720, continuo lineal entre 540 y 760 nm | Profundidad del pozo de absorción, independiente del nivel |
| `Área clorofila` (nm) | ∫ (1 − R/Rc) dλ en 540–760 | Ídem, integrada |
| `SAM base` (°) | ángulo espectral (440–900) contra la línea base de la hoja (§3.5) | Cambio de forma total, invariante a la escala |
| `SAM R1` (°) | ángulo contra R1 de su variedad el mismo día; solo Bourbon y Pacamara (M y T) | Parecido de forma con la hoja con roya |

Estadística: tendencia por hoja de cada rasgo con `temporal.leaf_trends` (familia «rasgos», FDR sobre
todas las hojas × rasgos) + lectura por grupos con `temporal.index_change_summary` (T / M susceptibles
/ M controles / R1), igual que *¿Roya o edad?*. Las limitaciones son las de `METODOLOGIA.md` §6–7:
fechas autocorrelacionadas → p optimistas; con una R por variedad, «propio de la roya» describe a esa hoja.

## 4. Arquitectura

```
src/config.py            + SPECTRAL_WL, SPECTRAL_DERIV_WINDOW/POLY, DERIV_REGIONS, SHADE_BANDS,
                           DELTA_REGIONS, NDVI_SIN_HOJA
src/spectral.py          (nuevo) cálculo puro, sin Streamlit salvo @st.cache_data en el wrapper de carga
src/spectral_page.py     (nuevo) contexto compartido y barra lateral de las 4 páginas
src/spectral_plots.py    (nuevo) ayudas comunes de Plotly: escala de fechas, franjas, mapa de calor Δ
src/plots_forma.py       (nuevo) figuras de derivadas y correlación
src/plots_cambio.py      (nuevo) figuras de Δ, PCA y rasgos
views/derivadas.py, views/correlacion_tiempo.py, views/cambio_pca.py, views/rasgos.py
tests/test_spectral.py   (nuevo) pruebas con espectros sintéticos de resultado conocido
```

### 4.1 Contrato de `src/spectral.py` (lo usan todas las páginas)
```python
def leaf_matrix(spectra: pd.DataFrame, leaf_id: str, wl=SPECTRAL_WL) -> LeafMatrix
    # spectra = salida de temporal.leaf_mean_spectra. Devuelve dataclass con:
    # dates (DatetimeIndex ordenado), dias (ndarray), wl (ndarray), R (n_fechas x n_wl, %),
    # n_puntos (ndarray int)
def normalize(R, wl, method: str = "area") -> ndarray          # "area" | "nir" | "none"
def derivative(R, wl, order: int, window=SPECTRAL_DERIV_WINDOW, poly=SPECTRAL_DERIV_POLY) -> ndarray
def spearman_by_wl(Y, dias, min_fechas=TEMPORAL_MIN_FECHAS_TENDENCIA) -> pd.DataFrame
    # columnas: wavelength, rho, p, p_fdr (p y p_fdr NaN si n < min_fechas o columna constante)
def delta_vs_baseline(R, n_base=TEMPORAL_BASELINE_CAMPAIGNS) -> ndarray
def region_means(Y, wl, regions: dict[str, tuple]) -> pd.DataFrame   # fechas x regiones
def pca(R, n_comp=3, dias=None) -> dict   # scores (n x k), loadings (k x n_wl), explained (k,), orientado §3.6
def spectral_features(R, wl, dR=None) -> pd.DataFrame   # una fila por fecha, columnas de §3.7 sin SAM
def sam_deg(a, b) -> float | ndarray                     # ángulo en grados, a y b (…, n_wl)
def features_table(spectra, meta) -> pd.DataFrame        # todas las hojas: LEAF_KEYS + campaign_date + dia + rasgos (incl. SAM)
def region_delta_table(spectra, meta, norm_method, n_base) -> pd.DataFrame  # todas las hojas, para leaf_trends
```
`meta` = tabla hoja-fecha con `LEAF_KEYS`, `campaign_date`, `dia` (de `temporal.leaf_timeseries`).
Las salidas tipo `ts` deben tener las columnas que exige `temporal.leaf_trends`
(`species, leaf_id, leaf, leaf_type, campaign_date, dia`).

### 4.2 `src/spectral_page.py`
- `load_context(include_sin_hoja: bool, excl_atipicas: bool) -> SpectralContext` (cacheado): files
  filtrados, `ts` hoja-fecha con `qc_atipico`, `spectra = leaf_mean_spectra(...)`, `T_CERO`,
  `species_with_rust`, `n_sin_hoja` excluidos.
- `sidebar(ctx_args) -> Selection`: Variedad (selectbox), Hoja (selectbox, una), Normalización,
  los dos interruptores de §3.1. **La selección se conserva al pasar entre las 4 páginas**: guardar en
  claves de `st.session_state` que no son de widget (`_esp_species`, `_esp_leaf`, …) con `on_change`,
  y usarlas como valor inicial del widget de cada página.
- Pie: `ui.sidebar_footer(df)`.

### 4.3 Estilo (obligatorio)
- Usar `src/ui.py`: `page_header`, `section`, `note`, `chart`, `html_table`/`st.dataframe` con
  `numeric_column_config`; plantilla Plotly de la app (no fijar `template`).
- Fechas → escala secuencial **Viridis** con barra de color etiquetada con fechas (como el ejemplo).
- Δ y ρ → `ui.DIVERGING_SCALE` (azul–gris–rojo), centrada en 0, simétrica.
- Textos de la interfaz en español, con «Cómo leer» corto y una nota de limitaciones por página.
- Rendimiento: dibujar solo la hoja elegida; pestañas perezosas (`st.tabs(..., key=, on_change="rerun")`
  + `tab.open`, ver `views/evolucion.py`) donde haya más de una figura pesada; cálculos de todas las
  hojas (tablas estadísticas) con `@st.cache_data`. Objetivo: recarga ≤ 1,5 s por página (`AppTest`).

## 5. Contenido de cada página

1. **Derivadas espectrales**: pestañas «Primera derivada» / «Segunda derivada». En cada una, fila
   *cruda* (azul-verde | borde rojo) y fila *normalizada* (ídem), una curva por fecha coloreada por fecha,
   línea en 0. Debajo de cada panel, franja de ρ de Spearman de la derivada vs tiempo (§3.4). Tabla:
   REP_max, REP_lineal, D_max, doble pico por fecha de esta hoja + su tendencia (enlace a *Rasgos*).
2. **Correlación con el tiempo**: figura del ejemplo (cruda | normalizada) para la hoja elegida.
   Sección «Todas las hojas»: mapa de calor hojas (18 filas, agrupadas por variedad y tipo) × λ con ρ
   (normalización elegida), celdas con p_FDR ≥ 0,05 atenuadas. Tabla resumen por hoja y región:
   ρ mediana y % de λ significativas.
3. **Cambio espectral y PCA**: pestaña «Δ vs línea base» (mapas de calor del ejemplo, crudo |
   normalizado, + tabla de tendencias por región y ruido de referencia); pestaña «PCA por hoja»
   (varianza explicada, cargas, puntajes vs fecha, crudo | normalizado, + tendencias de puntajes);
   desplegable «Espacio común».
4. **Rasgos espectrales**: series de cada rasgo de la hoja elegida (puntos + LOWESS de
   `temporal_plots.lowess_curve`, igual que *Evolución temporal*), tabla de tendencias de todas las
   hojas y tabla de lectura por grupos (`index_change_summary`). Tabla de definiciones de §3.7.

## 6. Pruebas (`tests/test_spectral.py`)
Con espectros sintéticos (sin datos reales), cada una con resultado conocido:
- `normalize`: un espectro × constante da la misma forma; media 440–900 = 1 para "area".
- `derivative`: de una recta da la pendiente; de una logística centrada en 720 nm, el máximo de dR/dλ
  cae en 720 ± 1 nm; `REP_max` ≈ 720.
- `spearman_by_wl`: serie monótona creciente → ρ = 1 y p_fdr < 0,05 con 10 fechas; < 5 fechas → p NaN.
- `delta_vs_baseline`: las filas base promedian 0.
- `pca`: datos de rango 1 → varianza explicada PC1 ≈ 1; orientación con ρ(PC1, tiempo) ≥ 0.
- `sam_deg`: mismo vector × 3 → 0°; ortogonales → 90°.
- `REP_lineal` de un espectro lineal en 670–780 conocido.
- Datos reales: `features_table` y `region_delta_table` tienen las 18 hojas y las columnas que pide
  `leaf_trends`; `leaf_trends` corre sobre ellas sin error.
- Humo: agregar las 4 vistas a `tests/test_smoke_pages.py`.
- Que no cambie nada existente: la suite actual (29 pruebas) sigue pasando.

## 7. Fases y reparto

| Fase | Quién | Entregable | Depende de |
|---|---|---|---|
| F0 | yo | este plan | — |
| F1 | Agente A (Sonnet 5.5) | config + `src/spectral.py` + `src/spectral_page.py` + `src/spectral_plots.py` + `tests/test_spectral.py` | F0 |
| F2 | Agente B (Sonnet 5.5) | `src/plots_forma.py` + `views/derivadas.py` + `views/correlacion_tiempo.py` | F1 |
| F3 | Agente C (Sonnet 5.5), en paralelo con F2 | `src/plots_cambio.py` + `views/cambio_pca.py` + `views/rasgos.py` | F1 |
| F4 | yo | `app.py` (navegación), `tests/test_smoke_pages.py`, revisión de código, suite completa, tiempos con `AppTest`, captura visual | F2, F3 |
| F5 | yo | `METODOLOGIA.md` §10, `README.md` (tabla de vistas), `ESTADO_PROYECTO.md` | F4 |

Reglas para los agentes: no tocar archivos fuera de su lista; no commitear; no cambiar ningún número
de las vistas existentes; nada de `Co-Authored-By`.

## 8. Riesgos
- **Ruido en 440–500 nm** de la derivada (visible en el ejemplo): se muestra tal cual, con la ventana
  en «Avanzado» para ver la sensibilidad; no se suaviza más por defecto.
- **p optimistas** por autocorrelación entre fechas y λ vecinas: se declara; el FDR por λ controla
  la multiplicidad pero no la autocorrelación temporal.
- **Canefora M2/T2** (4 fechas): figuras sí, estadística no.
- **Sobrecarga visual**: una hoja a la vez y pestañas perezosas.

## 9. Opinión sobre el Drive con Excel + carpeta de fotos (secundario; no se implementa ahora)

**Costo en dinero:** prácticamente cero (API de Google Drive y Sheets gratis, cuenta de servicio
gratis). **Costo real:** configuración y mantenimiento.

| Opción | Cómo | A favor | En contra |
|---|---|---|---|
| A. La app escribe en Drive | Cuenta de servicio de Google en `secrets`, carpeta compartida, se sube Excel + PNG al pulsar «Exportar» | La persona abre Drive y ya está | Credenciales en Streamlit Cloud; exportar PNG de Plotly en la nube necesita Kaleido + Chrome (pesado y frágil); 18 hojas × ~10 figuras ≈ 180 imágenes por actualización: lento dentro de la app |
| **B. Script de informe + GitHub Action → Drive (recomendada)** | `scripts/export_report.py` genera `analisis.xlsx` (una hoja por tabla) + `figuras/<variedad>/<hoja>/*.png` con matplotlib (como las imágenes de ejemplo); una GitHub Action lo corre en cada push a `data/` y lo sincroniza a la misma carpeta de Drive (rclone o API, cuenta de servicio en GitHub Secrets) | No carga la app; se reutiliza siempre la misma carpeta; las figuras salen idénticas en cada corrida; el script sirve también local | Configurar la cuenta de servicio una vez (~30 min de tu lado); 1 día de trabajo |
| C. Botón de descarga en la app | `st.download_button` con un `.zip` (Excel + PNG) de la hoja elegida | Cero credenciales, rápido de hacer | No hay carpeta compartida; cada quien descarga |

Mi recomendación: **la carga de plots se resuelve dentro de la app** (una hoja a la vez, pestañas
perezosas, caché), así que el Drive no hace falta por rendimiento. Para que le sirva a la persona,
hacer **B**: el script de informe reutiliza `src/spectral.py` tal cual, y el Drive se llena solo cada
vez que se suben datos. Empezar por el script (útil aunque el Drive nunca se configure) y conectar
Drive cuando haya una cuenta de servicio y una carpeta compartida.
