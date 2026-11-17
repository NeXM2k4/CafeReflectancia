# Plan — fondo blanco, tendencias suavizadas, significancia y arranque rápido

Fecha: 2026-11-16 · Rama: `fondo-blanco-tendencias-rendimiento`

## Pedido

1. Fondo blanco en toda la app.
2. Evolución temporal: no unir los puntos con líneas.
3. Evolución temporal: línea de tendencia suavizada.
4. Significancia (asteriscos, como en las figuras del paper) **en las cajas** de «Índices por tipo
   de hoja» y «Comparación entre variedades» **y** al lado de la tendencia de cada hoja.
5. Reducir el tiempo de arranque en Streamlit Community Cloud.

## Decisiones

### 1. Fondo blanco
- `.streamlit/config.toml` pasa a `base = "light"` con fondo `#FFFFFF`; `src/ui.py` (tinta, rejilla,
  superficies, CSS) y la plantilla Plotly pasan a `plotly_white`.
- Los colores con significado se mantienen (validados sobre blanco con el validador de paletas:
  contraste ≥ 3:1 y separación para daltonismo). Única excepción: Pacamara `#C98500` → `#B97A00`
  (contraste 2.99:1 → ≥ 3:1).
- Escalas de calor (similitud, divergente, inventario) rehechas para fondo claro: secuencial de un
  solo tono de claro a oscuro; divergente con gris claro en el centro.

### 2–3. Series temporales: puntos sin unir + tendencia suavizada
- Todas las series temporales por hoja se dibujan **solo con marcadores** (con sus barras de ±1 DE
  entre puntos cuando corresponda).
- Tendencia suavizada: **LOWESS** (`statsmodels`), por hoja, sobre los mismos valores que se grafican,
  con x = días desde la primera campaña; `frac = 2/3`, 3 iteraciones robustas (atenúan un día
  atípico sin borrarlo). Se dibuja solo si la hoja tiene ≥ `TEMPORAL_MIN_FECHAS_TENDENCIA` (5) fechas,
  el mismo mínimo que los tests de tendencia. Misma paleta y trazo que la hoja.
- El LOWESS es **descriptivo**: no hay p ni intervalo asociado. La inferencia sigue siendo
  Theil–Sen + Mann–Kendall.

### 4a. Significancia en las cajas
- Corchetes entre pares de grupos con `***` (p < 0.001), `**` (< 0.01), `*` (< 0.05), `ns`.
- El p es **el mismo p de Holm** de la matriz de δ de Cliff de la vista (Mann–Whitney, Holm sobre
  índices × pares, unidad hoja-fecha). No se calcula un p nuevo: un solo número por comparación en
  toda la vista.
- Con 4 grupos (6 pares) se dibujan solo los pares significativos para no tapar las cajas; la nota
  al pie lo dice.

### 4b. Significancia al lado de la tendencia
- Al final de la línea de cada hoja: `***/**/*/ns` del **Mann–Kendall con corrección BH (FDR)**.
- La familia de corrección es la misma que la de la tabla de tendencias (todas las variedades y
  hojas a la vez), así que la estrella coincide con la columna «p FDR».
- Variable → familia: valor y Δ → familia «Valor» (Mann–Kendall es invariante a restar una constante,
  así que el p de Δ es el del valor); Δ\* → familia Δ\*; similitud (S1/S2/U) y distancia a R1 →
  familia propia de esa variable (todas las hojas a la vez).

### 5. Arranque rápido
Medido (local): ~6 ms por espectro para leer + suavizar + calcular índices → ~22 s para 3471 archivos,
más otra pasada completa para los espectros medios. En Community Cloud el disco se borra al dormir o
reiniciar, así que el caché en `.state/` no sirve allí: **cada arranque en frío recalcula todo**.

- **Almacén precalculado versionado** (`data_cache/`, parquet): por archivo, índices + espectro
  suavizado sobre la grilla temporal. La app lo lee al arrancar y solo procesa los archivos nuevos o
  cambiados.
- Clave de cada archivo: ruta relativa a `data/` + tamaño + sha1 del contenido (las fechas de
  modificación cambian al clonar el repo; el tamaño solo no detecta un archivo reemplazado).
- Huella del método: si cambian `processing.py` o los parámetros de suavizado/recorte/grilla, el
  almacén se invalida entero y se recalcula (nunca se sirven números de un método viejo).
- `scripts/build_cache.py` lo regenera; correr la app localmente también lo actualiza.
- Lector de `.txt` más rápido (numpy en vez de un bucle de Python), verificado **idéntico** al
  anterior sobre todos los archivos.

## Criterios de aceptación
- Pruebas de humo y de interacción pasan.
- Lector nuevo = lector viejo en los 3471 archivos (igualdad exacta).
- Almacén: índices y espectros iguales a los calculados desde cero; un archivo modificado se
  recalcula y uno nuevo se agrega.
- Estrellas de las cajas = p Holm de la tabla por pares; estrellas de tendencia = p FDR de la tabla.
- Arranque en frío (sin `.state/`) medido antes y después.

## Fuera de alcance
- Hojas de validación (`Validacion1p*`) sin reconocer, y demás pendientes de datos.
- El paper (usa sus propias figuras en `PAPER/FINAL_VERSION`).

## Resultado (2026-11-16)

- 22 pruebas pasan (humo de todas las vistas, interacciones de Evolución, lector, almacén y significancia).
- Lector nuevo idéntico al anterior en los 3471 archivos; `file_index_table` y `leaf_mean_spectra`
  idénticas (igualdad exacta) a las de antes del cambio.
- Tiempos medidos en local (proceso nuevo, `AppTest`):

  | | Antes | Después |
  |---|---|---|
  | Arranque en frío (Panorama + Evolución, sin cachés en disco) | ~36 s | ~9.6 s |
  | Recarga de Evolución temporal (cachés calientes) | ~8 s | ~3.9 s |

- Hallazgos de rendimiento además del almacén: `add_vline`/`add_hline`/`add_annotation` de Plotly
  revalidan todas las formas en cada llamada (~8 s por recarga en Evolución): ahora se acumulan y se
  agregan una vez por figura (`ui.defer_layout_items`, aplicado en `ui.chart`).
- Bug corregido: `scan_dataset(_fingerprint)` — Streamlit no hashea parámetros con guion bajo, así
  que la huella de `data/` nunca invalidaba el caché. Ahora es `data_fingerprint()` (sha1, TTL 60 s).
