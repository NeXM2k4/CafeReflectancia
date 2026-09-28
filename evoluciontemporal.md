# Plan — Evolución temporal de hojas (roya) por índices y espectro

Fecha: 2026-09-27 · Estado: **Fases 0–4 y 6 implementadas** (§11); Fase 5 (figura del paper)
pendiente, a pedido · Documento hermano de `ESTADO_PROYECTO.md`

Código: `src/temporal.py` (cálculo) y `pages/5_Evolucion_Temporal.py` (página). Constantes en el
bloque "Evolucion temporal" de `src/config.py`. Primeros resultados en §12.

## 0. Objetivo

Seguir en el tiempo a **cada hoja física**, medida en todas las campañas, para responder:

1. **P1:** ¿Cómo evolucionan los 8 índices (NDVI, PRI, PSRI, RCI, EDI, FSR, NDRE, mNDVI705) de la
   hoja con roya (R1) semana a semana, en Bourbon y Pacamara?
2. **P2:** ¿Esa evolución es propia de la roya o también aparece en las hojas sanas y en las
   especies sin roya? Si también aparece ahí, la causa sería la estación, el envejecimiento de la
   hoja o el instrumento.
3. **P3:** ¿Alguna hoja madura (M) o tierna (T) empieza a parecerse espectralmente a R1 con el
   tiempo? Eso sería una señal de detección temprana.
4. **P4 (visualización):** mostrar una animación de cómo cambia el espectro de reflectancia
   completo de cada hoja a lo largo de las semanas.

Fuera de alcance: cambiar el score de severidad de la alerta de Telegram, el score de la página 4
o las figuras del paper. El trabajo temporal va en un módulo y una página nuevos, sin modificar
el comportamiento de lo existente.

## 1. Premisa y evidencia en los datos

**Premisa (confirmada por el usuario el 2026-09-27):** la hoja `M1` de la campaña 1 es la misma
hoja física que `M1` en las campañas 5, 10 y 12. Lo mismo vale para M2, T1, T2 y R1 dentro de
cada especie.

**Evidencia (verificada con `get_dataset()` el 2026-09-27):** son archivos por hoja y campaña,
después del filtro del dashboard.

| Bourbon | 29/06 | 06/07 | 15/07 | 21/07 | 27/07 | 10/08 | 17/08 | 24/08 | 31/08 | 07/09 | 14/09 | 21/09 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M1 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | **6** | 9 | **18** |
| M2 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 |
| T1 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 |
| T2 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 |
| R1 | – | – | 30 | **–** | 30 | 30 | 15 | 12 | 15 | 15 | 15 | 9 |

| Pacamara | 29/06 | 06/07 | 15/07 | 21/07 | 27/07 | 10/08 | 17/08 | 24/08 | 31/08 | 07/09 | 14/09 | 21/09 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M1, M2, T2 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 |
| T1 | 9 | 9 | 9 | 9 | 9 | 9 | **7** | 9 | 9 | 9 | 9 | 9 |
| R1 | – | – | 30 | **–** | 30 | 28 | 15 | 12 | 15 | 12 | 15 | 9 |

Las hojas M y T aparecen sin huecos en las 12 campañas. R1 aparece desde la primera detección de
roya (15/07) en 9 de las 10 campañas posteriores.

**Consecuencia:** el diseño longitudinal existe en los datos y se puede analizar. Las celdas en
negrita son irregularidades que hay que tratar, y se listan en la sección 3.

## 2. Unidad de análisis e identidad de hoja

### 2.1 Clave de hoja

```
leaf_id = f"{species}|{session}{session_num}"      # ej. "Bourbon|R1", "Pacamara|M2"
```

- **No incluye `susceptibility`.** R1 de Pacamara figura como `Susceptible` en todas las
  campañas excepto `Roya_27_07`, donde vale `NaN`. Esa carpeta es `Pacamara/Roya/` y no tiene la
  subcarpeta de susceptibilidad (ver `ESTADO_PROYECTO.md` §12). Si se incluyera, R1 se partiría
  en dos series. Como las Pacamara No susceptible ya se filtran en `get_dataset()`, la especie
  sola alcanza para desambiguar.
- **No incluye `campaign_id`**, porque la campaña es el eje temporal.
- Se reutiliza `parser.leaf_label()` para la parte `M1` y así evitar el bug de "M1.0" (§11.9 del
  estado del proyecto).

### 2.2 Eje temporal

- Se usa la **fecha real** (`campaign_date`), no el orden de campaña. El espaciado es irregular:
  6 a 9 días en julio, **14 días** entre 27/07 y 10/08, y 7 días desde ahí. Un eje ordinal
  achataría ese hueco.
- Se derivan dos columnas:
  - `dia` = días desde la primera campaña (2026-06-29 es el día 0).
  - `dia_roya` = días desde la primera detección de roya (2026-07-15 es el día 0). Solo aplica a R1.
- Para ordenar se usa `parser.sorted_campaigns()` o se ordena por fecha directamente, nunca por
  `campaign_id`, que ordena mal alfabéticamente ("Campaña_07_09" queda antes que "Campaña_10_08").

### 2.3 Qué hojas entran

| Grupo | Rol en el análisis |
|---|---|
| Bourbon, Pacamara: R1 | Serie principal de progresión de roya (P1). |
| Bourbon, Pacamara: M1, M2 | Candidatas a detección temprana (P3). |
| Bourbon, Pacamara: T1, T2 | Referencia sana dentro de la misma planta o especie (P2). |
| Canefora, Cuscatleco: M y T | **Controles negativos** de deriva temporal (P2): no tienen roya, así que una tendencia en ellas no puede atribuirse a la roya. |
| Vieja (especie pendiente) | **Excluida** hasta que se confirme la especie (`ESTADO_PROYECTO.md` §12). |
| Archivos no reconocidos (`araña*`, `vieja1`, `prueba_adri`) | Excluidos. `name_recognized=False` ya los deja fuera. |

## 3. Irregularidades en los datos: decisión antes de implementar

| # | Irregularidad | Tratamiento propuesto | ¿Requiere al usuario? |
|---|---|---|---|
| I1 | **Falta R1 en `Roya_21_07`** (ambas especies). | Hueco explícito en la serie: la línea no se interpola sobre ese punto y la animación muestra "sin medición". | Confirmar que no es un archivo perdido. |
| I2 | **Cambia el número de repeticiones de R1**: 10 por punto en 15/07, 27/07 y 10/08; 5 en 17/08; 3 desde 24/08. | Agregación en dos pasos (§4): las repeticiones se promedian dentro de cada punto, así que su número no pesa. **Sí cambia la precisión** de cada punto, y se declara en la ficha de n. | No. |
| I3 | **Cambia el número de puntos de R1** entre campañas (3, 4 o 5). | El punto **no** se trata como ubicación física estable: se promedia a nivel de hoja. Si los puntos de R1 se eligen sobre la lesión y su número crece, la media de hoja se mueve hacia la lesión. Es un sesgo de muestreo, no progresión, y hay que documentarlo. | **Sí**: ¿los puntos p1..p5 son ubicaciones fijas? ¿Se agregaron puntos porque creció la lesión? |
| I4 | **Bourbon M1, 21/09: 18 archivos**: p3 con 6 repeticiones, más p5 y p6 (no hay p4). | Se usa tal cual con la agregación en dos pasos, pero con una **alerta visible en la página**. Podría ser un error de nombre o que M1 mostró síntomas y se midieron más puntos. Lo segundo sería relevante para P3. | **Sí**: ¿qué pasó con M1 de Bourbon el 21/09? |
| I5 | Bourbon M1, 07/09: 6 archivos (falta p3). | Hoja con 2 puntos: se reporta `n_puntos=2`. | No. |
| I6 | Pacamara T1, 17/08: 7 archivos (faltan 2 repeticiones). | Irrelevante con la agregación en dos pasos. | No. |
| I7 | **La hoja "Tierna" envejece.** T1 en 29/06 y T1 en 21/09 es la misma hoja, 12 semanas más vieja. | Ver §5.3: afecta el ancla sana del score de severidad. Sus series se etiquetan "T (tierna al inicio)". | Confirmar si en algún momento se reemplazaron las hojas T por hojas nuevas. |
| I8 | La etiqueta de susceptibilidad de Pacamara R1 es inconsistente (`Roya_27_07`). | Se resuelve con la clave de §2.1. No hace falta tocar el parser. | No. |

**Regla general:** no se descarta ni se imputa ningún dato en silencio. Cada serie lleva `n_puntos`
y `n_archivos` por campaña, visibles en el hover y en la tabla de detalle.

## 4. Agregación (de archivo a hoja-campaña)

Es la misma lógica que `severity.leaf_severity_reports()`, en dos pasos:

1. **Archivo:** `load_spectrum()`, luego `prepare_spectrum()` (Savitzky-Golay 41/2, recorte
   420–1000 nm), luego `calcular_indices()`.
2. **Punto:** media de las repeticiones de ese punto. Las repeticiones son réplicas técnicas.
3. **Hoja-campaña:** media de los puntos.
4. **Dispersión:** SD **entre puntos** de la hoja en esa campaña, que refleja la heterogeneidad
   espacial. No se usa la SD entre repeticiones, que solo refleja el acople de la sonda y
   subestimaría la incertidumbre. Con `n_puntos < 2` la banda no se dibuja.

Esquema de la tabla resultante (`leaf_ts`):

```
species, leaf, leaf_id, leaf_type(M|T|R), campaign_id, campaign_date, dia, dia_roya,
n_puntos, n_archivos, <8 indices: media>, <8 indices: sd_entre_puntos>
```

**Chequeo de consistencia obligatorio:** para cualquier campaña, las medias de `leaf_ts` deben
coincidir, con tolerancia de 1e-9, con los valores de índice que devuelve
`leaf_severity_reports()` sobre ese mismo subconjunto. Si difieren, hay un bug en la agregación.

## 5. Métricas temporales

### 5.1 Índices crudos en el tiempo (métrica principal)

Muestra el valor de cada índice por hoja en función de la fecha. **No depende de anclas ni de
ningún modelo**, así que es lo más defendible. Es la vista por defecto.

### 5.2 Cambio respecto de la línea base propia (Δ)

```
Δ_indice(hoja, t) = indice(hoja, t) − indice(hoja, t0)
```

`t0` es la primera campaña en que se midió esa hoja: 29/06 para M y T, 15/07 para R1. Cada hoja
es su propio control, lo que elimina la diferencia de nivel entre hojas y entre especies y deja
solo la trayectoria.

**Δ corregido por deriva común** (responde P2):

```
Δ*_indice(hoja, t) = Δ_indice(hoja, t) − mediana_{hojas T de la misma especie}(Δ_indice(·, t))
```

Resta lo que les pasó a las hojas sanas de la misma especie en la misma fecha: condición de
luz, humedad, calibración de ese día o estación. Si la tendencia de R1 persiste en `Δ*`, es
atribuible a la hoja y no al entorno. **Limitación:** las hojas T también envejecen (I7), así que
`Δ*` también resta el envejecimiento foliar normal. Es conservador, que es lo que se busca.

### 5.3 Severidad en el tiempo: problema de circularidad (decisión pendiente)

Hoy, `severity_baselines()` calcula:
- el ancla sana como la media de **todas** las hojas T de **todas** las campañas, y
- el ancla enferma como la media de **todos** los R de **todas** las campañas.

Para una serie temporal eso trae dos problemas:

1. **Circularidad:** en Bourbon y Pacamara hay una sola hoja R (R1), así que el ancla enferma
   *es* el promedio temporal de R1. Graficar la severidad de R1 contra su propio promedio
   produce una curva que por construcción cruza el ~50–100 % en la mitad de la serie y satura
   en 100 % después (por el `clip`). La forma de la curva sale del método, no de la biología.
2. **Deriva del ancla sana:** las hojas T envejecen (I7). Un ancla sana promediada sobre 12
   semanas mezcla hoja tierna con hoja casi madura.

Opciones:

| Opción | Descripción | A favor | En contra |
|---|---|---|---|
| **S1 (recomendada)** | **Anclas congeladas.** Sana = T de las 2 primeras campañas (29/06, 06/07), cuando eran realmente tiernas. Enferma = el ancla actual. La severidad temporal se declara "relativa al promedio de R1". | Simple y honesta con la etiqueta. | No resuelve la circularidad, solo la declara. |
| S2 | **Leave-one-campaign-out:** para la campaña *t*, el ancla enferma sale de R1 en todas las campañas menos *t*. | Reduce la circularidad directa. | Con una sola hoja, sigue siendo casi la misma información. Es más cara de calcular. |
| S3 | **Sin severidad en la vista temporal.** Solo índices crudos (5.1) y Δ (5.2). | Cero circularidad. | Se pierde el número 0–100 %, que es lo más legible para el usuario de campo. |

**Recomendación:** mostrar 5.1 y 5.2 como vista principal, y la severidad (S1) como vista
secundaria con una leyenda explícita de su limitación. **No cambiar** `severity_baselines()`: la
alerta de Telegram y la página 4 siguen como están. Las anclas congeladas se calculan en el
módulo nuevo.

### 5.4 Tendencia por hoja (cuantificación)

Para cada combinación (hoja, índice) con al menos 5 fechas:

- **Pendiente de Theil-Sen** (`scipy.stats.theilslopes`) en unidades de índice por semana, con
  su intervalo de confianza del 95 %. Es robusta a atípicos y adecuada para n = 9–12.
- **Test de Mann-Kendall** vía `scipy.stats.kendalltau(dia, valor)`: da la dirección y la
  significancia de la tendencia monótona.
- Salen 8 índices × ~20 hojas, unos 160 tests, así que se corrige por comparaciones múltiples con
  **Benjamini-Hochberg** (la misma corrección que ya usa `make_ieee_figures._bh_significant()`).

**Interpretación permitida:** "la hoja R1 de Bourbon muestra una tendencia monótona decreciente
en mNDVI705 (−0,0X/semana, p_FDR < 0,05), ausente en T1/T2 y en los controles".

**Interpretación NO permitida:** "la roya reduce mNDVI705 a razón de X/semana". Con n = 1 hoja
enferma por especie no se puede generalizar a la población. Además, las mediciones consecutivas
de la misma hoja están autocorrelacionadas, así que el p-valor es optimista y debe leerse como
descriptivo.

### 5.5 Detección temprana (P3): distancia a R1

Para cada hoja M o T y cada fecha:

```
d(hoja, t) = distancia euclídea entre el vector de índices estandarizados de la hoja en t
             y el de R1 (misma especie) en t
```

La estandarización es un z-score por índice, con media y SD de las hojas T de la especie en las
2 primeras campañas. **Se excluye FSR del vector** porque es idéntico a NDVI y pesaría doble.

Si una hoja M muestra `d` decreciente y sostenida mientras las T no, esa hoja es candidata a
infección asintomática. **No es un diagnóstico**, es una señal para que el equipo de campo la
inspeccione. La irregularidad I4 (Bourbon M1, 21/09) es el primer caso a mirar con esta métrica.

## 6. Animación del espectro (P4)

### 6.1 Datos

- Un **espectro medio por hoja y campaña**, siguiendo la misma lógica de dos pasos:
  primero la media de repeticiones por punto (sobre la grilla común), luego la media de puntos.
  Se usa `processing.average_group()` en cada nivel, o una versión que acepte la grilla como
  parámetro para que **todas las campañas compartan exactamente la misma grilla**. Esto es un
  requisito: si cada frame tiene una grilla distinta, el cambio visual es artefacto.
- **Rango 440–1000 nm**, no 420. Por debajo de 440 nm, ~13 % de los espectros con roya tiene
  reflectancia negativa por baja relación señal/ruido (`ESTADO_PROYECTO.md` §13). Ningún índice
  usa bandas por debajo de 445 nm.
- Grilla de **~300 puntos** (no los 1000 por defecto de `average_group`), para que el payload de
  la animación no crezca de más: ~20 hojas × 12 frames × 300 puntos.

### 6.2 Visualización (Plotly, sin dependencias nuevas)

- `go.Figure` con `frames` (uno por fecha) y un slider con play/pausa. `px.line` con
  `animation_frame` no alcanza porque no permite fijar la traza fantasma de referencia ni el
  panel de diferencia.
- **Eje Y fijo** en todos los frames (min/max global del subconjunto elegido). Si el eje se
  reescala por frame, la animación exagera o esconde cambios. Es el error más común en este tipo
  de animación.
- En cada frame:
  1. la curva actual de cada hoja seleccionada, con color fijo por hoja;
  2. una **traza fantasma** (gris y punteada) con el espectro de la misma hoja en su `t0`, para
     que el cambio se vea contra un punto fijo;
  3. una banda ±SD entre puntos (opcional; apagada por defecto para no saturar);
  4. **bandas de los índices sombreadas** (670, 705, 720, 750, 790, 800 nm, etc.), para ver en
     qué región del espectro ocurre el cambio que mueven los índices.
- **Panel inferior:** espectro de diferencia `R(t) − R(t0)` en puntos de reflectancia, con el
  mismo recurso que las figuras del paper. Es donde mejor se ve la progresión.
- El título de cada frame muestra la fecha real, `día N` y `n_puntos`. Si la hoja no se midió en
  esa fecha (I1), el frame dice "R1 sin medición el 21/07" en lugar de repetir la curva anterior.
- Controles en la barra lateral: especie, hojas (multiselect, R1 por defecto más T1 como
  contraste) y velocidad (ms por frame).

### 6.3 Alternativa estática, para el paper

Plotly no exporta animaciones a GIF o MP4 sin dependencias extra, y el paper necesita figuras
estáticas de todas formas. Se propone un **small multiples** (una curva por fecha, con color en
gradiente temporal y colorbar de fechas) como figura candidata para `make_ieee_figures.py`. Es
opcional y va en una fase posterior (§8, Fase 5).

## 7. Diseño del código

### 7.1 Módulo nuevo `src/temporal.py`

| Función | Entrada | Salida | Notas |
|---|---|---|---|
| `leaf_id(species, session, session_num)` | fila | `str` | Usa `leaf_label()`. |
| `leaf_timeseries(dataset)` | `get_dataset()` | DataFrame `leaf_ts` (§4) | `@st.cache_data`, que se invalida con el mismo fingerprint del dataset. |
| `add_deltas(leaf_ts)` | `leaf_ts` | + columnas `Δ_*` y `Δ*_*` (§5.2) | Función pura. |
| `frozen_baselines(leaf_ts)` | `leaf_ts` | dict con la misma forma que `severity_baselines()` | Opción S1 (§5.3). |
| `leaf_trends(leaf_ts, min_fechas=5)` | `leaf_ts` | DataFrame: hoja, índice, pendiente/semana, IC, τ, p, p_FDR | §5.4 |
| `distance_to_rust(leaf_ts)` | `leaf_ts` | DataFrame: hoja, fecha, d | §5.5 (sin FSR). |
| `leaf_mean_spectra(dataset, leaf_ids, grid)` | dataset y selección | DataFrame largo: leaf_id, fecha, wavelength, mean, sd | §6.1, cacheada. |

Constantes nuevas en `src/config.py` (bloque `# --- Evolución temporal ---`):
`TEMPORAL_WL_MIN = 440`, `TEMPORAL_GRID_POINTS = 300`, `TEMPORAL_MIN_FECHAS_TENDENCIA = 5`,
`TEMPORAL_BASELINE_CAMPAIGNS = 2` (número de campañas iniciales del ancla congelada).

### 7.2 Página nueva `pages/5_Evolucion_Temporal.py`

Sigue el patrón de las páginas existentes (`inject_base_css`, `render_header`, `filter_tag`,
`SPECIES_COLORS`). Tiene estas secciones, en orden:

1. **Ficha de datos**: tabla hoja × fecha con `n_puntos` y alertas para las irregularidades de §3.
   Es lo primero que se ve, así nadie interpreta una curva sin saber cuántos datos la sostienen.
2. **Índices en el tiempo**: selector de índice y de modo (crudo, Δ, Δ*). Una línea por hoja con
   banda ±SD y marcadores; los huecos quedan sin línea.
3. **Tendencias**: tabla de §5.4 con pendientes, IC y p_FDR, y marca en las significativas.
4. **Severidad relativa (S1)**: línea por hoja, las 11 clases de riesgo como líneas de fondo (igual
   que la página 4) y un aviso fijo de circularidad.
5. **Distancia a R1**: línea por hoja M/T, más baja = más parecida a la hoja con roya.
6. **Animación del espectro** (§6.2).
7. **Descarga CSV** de `leaf_ts`.

### 7.3 Qué NO se toca

`severity.py`, `notifier.py`, `parser.py` (salvo que I3 o I4 revelen un error de nombre), las
páginas 1–4 y `make_ieee_figures.py` hasta la Fase 5.

## 8. Fases de implementación y criterios de aceptación

| Fase | Entregable | Criterio de aceptación |
|---|---|---|
| **0** | El usuario responde las preguntas de §9. | Decisiones registradas en este archivo. |
| **1** | `src/temporal.py`: `leaf_id`, `leaf_timeseries`, `add_deltas`. | (a) La tabla de presencia de §1 se reproduce exacta. (b) El chequeo de consistencia de §4 contra `leaf_severity_reports()` pasa. (c) Hay 0 filas con `leaf_id` nulo. (d) R1 de Pacamara es una sola serie (I8). |
| **2** | Página 5, secciones 1, 2 y 7. | Se ve en el navegador (`streamlit run app.py`, reiniciando el proceso). Los huecos (I1) se ven como huecos. El eje X está en fechas reales. |
| **3** | `leaf_trends`, `frozen_baselines`, `distance_to_rust`, y las secciones 3, 4 y 5. | Hay p_FDR en la tabla. El aviso de circularidad está visible. FSR queda excluido de la distancia. |
| **4** | `leaf_mean_spectra` y la animación (sección 6). | Eje Y fijo, la misma grilla en todos los frames, la traza fantasma de `t0`, el frame "sin medición" en 21/07 y el panel de diferencia. La animación carga en menos de 5 s con el cache caliente. |
| **5 (opcional)** | Figura estática para el paper en `make_ieee_figures.py`. | Solo si el usuario lo pide. Regenerar `figures_ieee/` es una decisión explícita (ver `ESTADO_PROYECTO.md` §12). |
| **6** | Actualizar `ESTADO_PROYECTO.md` (estructura, sección de páginas y pendientes). | El doc refleja la página 5 y las decisiones tomadas. |

**Controles de validación transversales:**
- **Control negativo:** Canefora y Cuscatleco no deberían mostrar tendencias significativas en
  `Δ*`. Si las muestran en muchos índices, hay deriva instrumental o estacional que `Δ*` no está
  absorbiendo, y hay que revisarlo antes de interpretar R1.
- **Control de reproducibilidad:** las medias de hoja-campaña coinciden con las de la página 2
  (tabla por punto y hoja, promediada a hoja) para la misma campaña.

## 9. Decisiones del usuario (2026-09-27)

Respuestas a las preguntas que bloqueaban la implementación, y cómo se aplican:

| # | Pregunta | Respuesta | Aplicación |
|---|---|---|---|
| D1 | ¿Los puntos p1, p2, p3… son ubicaciones fijas? (I3) | **No.** Se midieron intentando ser objetivos, pero no son el mismo lugar físico entre campañas. | Los puntos se tratan como **muestras espaciales intercambiables** dentro de la hoja: nunca se sigue "el punto 2" en el tiempo, solo la hoja. La SD entre puntos se interpreta como heterogeneidad espacial de la hoja en esa fecha. |
| D2 | ¿Qué puntos cuentan? (I3, I4) | **Solo p1 a p3.** Los que faltan son mediciones que no se tomaron ese día. | Filtro `point ∈ {1, 2, 3}` (`TEMPORAL_VALID_POINTS`). Quedan fuera 45 archivos: p4/p5 de R1 en 5 campañas de cada especie, y p5/p6 de Bourbon M1 el 21/09. Resuelve I4. Tras el filtro, **todas** las hojas de Bourbon y Pacamara tienen 3 puntos en todas sus fechas, salvo Bourbon M1 el 07/09 (2 puntos). |
| D3 | ¿R1 falta el 21/07? (I1) | Implícita en D2: lo que falta son mediciones no tomadas. | Hueco explícito, sin interpolar. |
| D4 | ¿Se reemplazaron las hojas T? (I7) | **No**, son las mismas desde el 29/06. | Las series T son continuas y **envejecen**: el ancla sana de la severidad temporal usa solo las 2 primeras campañas (S1). El confusor edad-roya se declara (§10). |
| D5 | ¿S1 o S3? (§5.3) | "Lo más completo y riguroso posible." | Se implementan **todas** las vistas: índices crudos, Δ y Δ* como principal; severidad S1 como secundaria; **S2 (leave-one-campaign-out) como análisis de sensibilidad** junto a S1, y un modo **sin recorte** para ver cuándo la severidad pasa las anclas en lugar de saturar en 0/100 %. |
| D6 | ¿Fecha de inicio de la roya? | **No se sabe.** | `dia_roya` = días desde la **primera medición** de R1 (15/07), etiquetado siempre como "desde la primera medición con roya", nunca como "desde la infección". |

**Decisiones de rigor adicionales tomadas al implementar:**
- **Anclas de severidad temporal ponderadas por fecha, no por archivo.** El ancla actual de
  `severity_baselines()` promedia archivos, así que las campañas de julio (10 repeticiones por
  punto) pesan ~3 veces más que las de septiembre (3 repeticiones). En el módulo temporal, el
  ancla enferma es la media de los valores **hoja-fecha** de R1: cada fecha pesa igual. El ancla
  de Telegram y la página 4 no cambian.
- **La severidad temporal usa los 8 índices**, igual que la página 4, para que el número sea
  comparable. La **distancia a R1** (§5.5) sí excluye FSR, porque ahí la duplicación con NDVI
  distorsiona la geometría.
- **Estandarización de la distancia:** z-score con media y SD de los valores **por punto** de las
  hojas T en las 2 primeras campañas de la especie (12 valores: 2 hojas × 3 puntos × 2 fechas). A
  nivel hoja-fecha habría solo 4 valores, una SD demasiado inestable.
- **Autocorrelación:** la tabla de tendencias reporta la autocorrelación lag-1 de los residuos
  de Theil-Sen como diagnóstico. Con n ≤ 12 la estimación es ruidosa: sirve para marcar series
  sospechosas, no para corregir el p-valor.
- Las series con varianza nula (p. ej. Δ* de la única hoja T de Canefora, que por definición es
  0) se omiten de los tests en lugar de reportar un p-valor sin sentido.

## 10. Limitaciones a declarar (en la página y en cualquier texto derivado)

- **n = 1 hoja con roya por especie.** Los resultados describen la trayectoria de *esa* hoja, no
  un efecto poblacional.
- **Autocorrelación temporal:** las mediciones sucesivas de una hoja no son independientes, así
  que los p-valores de tendencia son optimistas.
- **Confusión con el envejecimiento foliar:** las hojas T y M también envejecen 12 semanas. `Δ*`
  lo mitiga pero no lo separa de forma limpia de la roya.
- **Cambio de protocolo en R1** (10 a 5 a 3 repeticiones; 3 a 5 puntos): la precisión y la
  representatividad espacial cambian entre fechas.
- **Condiciones de medición no registradas** (hora, luz, temperatura, operador, calibración de
  blanco): no se pueden modelar. Solo `Δ*` y los controles negativos las absorben parcialmente.
- **FSR ≡ NDVI:** se muestra por consistencia con el resto de la app, pero no aporta una serie
  independiente.

## 11. Estado de la implementación (2026-09-27)

| Fase | Estado | Verificación |
|---|---|---|
| 0 | Hecha | Decisiones en §9. |
| 1 | Hecha | Tabla de presencia de §1 reproducida; **diferencia 0** contra `leaf_severity_reports()` en 3 campañas (15/07, 31/08, 21/09); 0 `leaf_id` nulos; Pacamara R1 es una sola serie; huecos solo en R1 el 21/07 (ambas especies). |
| 2–4 | Hechas | `AppTest` de Streamlit sobre 15 combinaciones de filtros (4 especies, 3 modos, S1/S2, con/sin recorte, con/sin control de calidad, banda SD, FSR, una sola hoja): 0 excepciones. Figuras renderizadas a PNG y revisadas a ojo (etiquetas, leyendas, ejes, cuadro intermedio de la animación). **No se probó en un navegador real**: la extensión de Chrome no respondió; conviene abrir la página una vez y darle "Reproducir". |
| 5 | Pendiente | Solo si se pide (regenera `figures_ieee/`). |
| 6 | Hecha | `ESTADO_PROYECTO.md` actualizado. |

**Diferencias respecto del diseño de §7.1, decididas al implementar:**
- `file_indices(dataset)` (cacheada) calcula los índices una sola vez por archivo; todo lo demás
  (series, anclas, severidad, distancia) se deriva de esa tabla. La primera carga tarda ~20–40 s
  (lectura de ~1.850 espectros); después queda en cache.
- `temporal_selection()` devuelve el motivo de exclusión de cada archivo. Hoy quedan fuera: 45 por
  punto fuera de p1–p3, 44 de la especie pendiente, 9 de la hoja V1 de Canefora (una sola fecha,
  no forma serie) y 4 no reconocidos.
- `with_gaps(ts, t_cero)` recibe el día 0 del dataset completo: al calcularlo sobre una tabla
  parcial (p. ej. la de distancia, que empieza el 15/07) los días de los huecos salían corridos.
- **Control de calidad (`qc_flags`)**, que no estaba en el plan original. Ver §11.1.
- **FSR queda fuera también de las tendencias**, no solo de la distancia: duplicaba cada resultado
  de NDVI e inflaba el número de tests de la corrección FDR.
- **Colores:** tipo de hoja → color (Madura `#3987E5`, Tierna `#199E70`, Con roya `#D95926`) y
  número de hoja → trazo (1 continuo, 2 discontinuo), más la etiqueta de cada línea al final. Se
  probaron 5 colores (uno por hoja) y ninguna combinación de la paleta del proyecto pasaba la
  validación de daltonismo; el trío sí pasa (ΔE deutan 9,4 sobre el fondo `#0E1117`).

### 11.1 Control de calidad

Se agregó después de encontrar que **Pacamara R1 el 10/08** tiene la reflectancia hundida en todo
el espectro (R800 = 29 % contra ~75–80 % en las fechas vecinas; R510 = 0,18 %), con las 28
repeticiones consistentes entre sí. Parece una falla de medición de ese día (contacto de la sonda
o referencia de blanco), no biología.

- **Regla:** robust z = 0,6745·(x − mediana)/MAD de cada índice (sin FSR) contra la propia serie
  de la hoja; una hoja-fecha es atípica si 4 o más de los 7 índices superan |z| > 3,5
  (Iglewicz & Hoaglin). Un solo índice raro puede ser biología; casi todos a la vez apunta a la
  medición.
- **Resultado:** 4 hojas-fecha marcadas, con una separación limpia (ninguna tiene 3 índices
  atípicos: o son ≤ 2 o son ≥ 4): Pacamara R1 10/08 (5 de 7), Bourbon M2 29/06, Cuscatleco M2
  10/08 y Pacamara T2 29/06 (4 de 7 cada una).
- **Nada se excluye por defecto.** Las marcadas se ven en la ficha y con un círculo en los
  gráficos. Un interruptor en la barra lateral las excluye y **recalcula todo**, para ver la
  sensibilidad.
- **Efecto medido de excluirlas:** el ancla "con roya" de RCI en Pacamara baja de 0,242 a 0,034
  (estaba inflada ~7 veces por ese solo día); NDVI, de 0,595 a 0,550. Las conclusiones de
  tendencia **no cambian** (§12).

## 12. Primeros resultados (2026-09-27, 12 campañas)

Son descriptivos; valen las limitaciones de §10.

1. **Ninguna hoja R1 tiene tendencia monótona significativa** en ningún índice, ni en valor ni
   en Δ*. La severidad relativa de Bourbon R1 oscila entre 71 % y 100 % desde la primera
   medición; la de Pacamara R1, entre 53 % y 95 %. Los datos no muestran una progresión gradual
   de la roya dentro de la hoja en estas 10 semanas: cuando se empezó a medir, R1 ya estaba
   espectralmente lejos de las hojas sanas.
2. **Las tendencias significativas en Δ\* son solo de Bourbon M1 y Cuscatleco M1**, las dos
   hojas maduras M1, en los mismos índices (NDVI, EDI, NDRE, mNDVI705; pendientes de −0,017 a
   −0,027 por semana; Cuscatleco M1 además en RCI). **Cuscatleco no tiene roya**, así que el patrón en Bourbon M1 se explica
   mejor por envejecimiento de la hoja madura que por roya asintomática. Es el caso para el que
   se diseñaron los controles negativos.
3. **Pacamara R1 el 15/07 (su primera medición)** queda en 53 % de severidad con todas las fechas
   y en **10 %** si se excluye el 10/08 atípico. Es el único indicio de que R1 estaba menos
   afectada al principio, pero depende de las anclas (circularidad, §5.3), así que no alcanza
   para afirmar progresión.
4. **mNDVI705 pasa de 1** en varias hojas sanas de Pacamara el 24/08 y el 31/08 (hasta 1,2) y
   Bourbon M1 tiene un punto con mNDVI705 negativo el 24/08. Eso ocurre cuando R445 se acerca a
   R705, lo que sugiere reflejo especular en el azul durante la medición. El control de calidad
   no lo marca porque afecta a un solo índice. **Vale revisar** cómo se midió esos días antes de
   usar mNDVI705 de esas fechas en el paper.

**Hallazgo lateral, fuera del alcance temporal pero importante:** el ancla de RCI de Pacamara
que usa la alerta de Telegram y la página 4 (`severity_baselines()`, promedio por archivo) incluye
las 28 repeticiones del 10/08 y está igual de inflada. No se tocó, porque cambiarlo modifica la
alerta y los números del paper. Queda en los pendientes de `ESTADO_PROYECTO.md` §12.

## 13. Foco en hojas maduras de especies susceptibles (2026-09-27)

A pedido del usuario, **la evolución de las hojas M de Bourbon y Pacamara es lo principal** de la
página: es la hoja de estado sanitario desconocido, donde tendría que verse una infección todavía
sin síntomas. La página se reorganizó así:

1. **Sección 1 — Hojas maduras (M) de las especies susceptibles**, siempre visible con las dos
   especies lado a lado y el mismo eje Y, independiente de la especie elegida en la barra lateral:
   - Tarjetas con la severidad relativa actual de cada M y su cambio desde la primera medición.
   - Pestañas: índice elegido (valor, Δ o Δ*), severidad relativa, distancia a R1 y los 8 índices.
     M1/M2 van en color pleno; el **rango de las hojas T** (banda verde) y **R1** (línea naranja
     punteada) de la misma especie van de fondo como referencias sana y con roya.
   - Tabla que cruza cada tendencia de una hoja M con las hojas M de Canefora y Cuscatleco:
     "Candidata" si la tendencia no aparece en ningún control sin roya, "Compatible con
     envejecimiento" si algún control muestra la misma tendencia con el mismo signo.
2. Secciones 2–8: el detalle por especie de antes (ficha, índices, tendencias, severidad,
   distancia, animación y tabla). La animación arranca con las hojas M seleccionadas.

**Resultado con los datos al 2026-09-27 (Δ\*, FDR 5 %):** 28 series M evaluadas (4 hojas × 7
índices), **0 candidatas** y **4 compatibles con envejecimiento** (Bourbon M1 en NDVI, EDI, NDRE y
mNDVI705, las mismas tendencias que Cuscatleco M1). En severidad relativa, las M de Bourbon
(10–51 %) y las de Pacamara (0–19 %) quedan casi siempre dentro o muy cerca del rango de sus
propias hojas T; las excepciones son puntos aislados (p. ej. Bourbon M1 y Pacamara M2 el 29/06),
no tendencias. Hoy ninguna hoja madura se separa de forma sostenida de la referencia sana hacia la
de roya.

## 14. ¿Qué cambia con el tiempo? Roya frente a envejecimiento (2026-09-27)

**Motivo:** el objetivo del estudio es identificar qué variables cambian con el tiempo, para después
intentar predecir la evolución de otras hojas. Los gráficos hoja por hoja no respondían eso de forma
directa. Se agregó arriba de todo, en este orden:

- **Resumen de hallazgos** que se recalcula solo con los datos.
- **Sección 1:** hojas maduras.
- **Sección 2 — ¿Qué cambia con el tiempo?**
  - Firma espectral de la tendencia por grupo.
  - Mapa de calor hoja × longitud de onda.
  - Clasificación de índices.
- **Sección 3 — La misma hoja semana a semana:** R1 junto a una hoja tierna, con todos sus
  espectros coloreados por fecha y el cambio respecto de la primera medición.

El detalle por especie pasó a las secciones 4–10.

### 14.1 Métodos agregados

- **Tendencia por longitud de onda:** pendiente de Theil-Sen del espectro medio de cada hoja
  (grilla común de 440–998 nm, 299 puntos) contra las semanas. Se calcula vectorizada (mediana de
  las pendientes de todos los pares de fechas) y **coincide exactamente con `scipy.stats.theilslopes`**
  en las longitudes de onda verificadas.
  - Solo entran hojas con ≥ 5 fechas (16 hojas).
  - Resumen por grupo: mediana entre hojas, con rango intercuartil cuando el grupo tiene ≥ 3 hojas.
  - **Sin p-valor por longitud de onda** (serían ~4.800 tests con pocas hojas por grupo). La solidez
    la da la coincidencia de signo entre hojas, que se reporta como "k/n suben".
- **Normalización por la meseta NIR** (opcional): cada espectro se divide por su media en 750–900 nm.
  Quita cambios de nivel entre días (sonda, blanco), pero también cambios reales del NIR. Una
  conclusión se considera robusta si se mantiene con y sin normalizar.
- **Peor punto:** para cada hoja, fecha e índice, el punto (p1–p3) más desplazado hacia el ancla con
  roya. La dirección es el signo de (ancla con roya − ancla sana) de la especie.
  - Motivo: la roya aparece en manchas y el promedio de 3 puntos la diluye.
  - Con 3 puntos elegidos a ojo es ruidoso: es una señal complementaria, no un reemplazo.
- **Heterogeneidad:** la SD entre puntos de la hoja, tratada como variable propia. Una hoja que
  empieza a enfermarse debería volverse más desigual antes de que cambie su promedio.
- **Cuatro familias de tendencia** (Δ*, valor, peor punto, heterogeneidad). La corrección FDR se
  aplica por separado dentro de cada familia.
- **Clasificación de índices por reglas fijas**, sobre las tendencias significativas de cada grupo
  (T de todas las especies, M susceptibles, M de control, R1):
  - **propio de la roya:** R1 cambia y ni las T ni las M de control cambian con el mismo signo;
  - **envejecimiento de la hoja madura:** las M susceptibles y las M de control cambian igual;
  - **candidata:** una M susceptible cambia y ningún control lo hace;
  - **maduración:** cambia alguna T.

### 14.2 Resultados (datos al 2026-09-27, sin control de calidad)

Mediana de la pendiente por grupo y región, en pp de reflectancia por semana (k/n = hojas que suben):

| Grupo | Azul-verde 450–600 | Rojo 650–690 | Borde rojo 700–740 | NIR 760–950 |
|---|---|---|---|---|
| T (tierna al inicio), 7 hojas | −1,18 (0/7) | −0,88 (0/7) | −1,53 (0/7) | −1,26 (0/7) |
| M susceptibles, 4 hojas | +0,16 (2/4) | +0,14 (2/4) | −0,46 (1/4) | −1,27 (0/4) |
| M controles sin roya, 3 hojas | +0,25 (2/3) | +0,30 (2/3) | +0,14 (2/3) | −0,15 (1/3) |
| R1 con roya, 2 hojas | +1,14 (2/2) | +1,22 (2/2) | +1,77 (2/2) | +1,03 (2/2) |

1. **El visible separa la roya de la maduración, en direcciones opuestas.**
   - Las 7 hojas tiernas **se oscurecen** en el visible (~−1 pp/semana). Es coherente con la
     acumulación de clorofila al madurar.
   - Las 2 hojas con roya **se aclaran** (~+1,2 pp/semana). Es coherente con la degradación de
     clorofila por la roya.
   - La dirección se mantiene al normalizar por el NIR.
   - Es el resultado más útil para una variable predictora, pero con **n = 2 hojas con roya**:
     describe esas dos hojas, no está validado como marcador.
2. **R1 sube en todo el espectro, incluido el NIR (+1,0).** Parte del cambio es un aclarado general
   (tejido que se seca o necrosa, o cambios de nivel entre días). Por eso la conclusión se apoya en el
   visible normalizado y no en la reflectancia absoluta.
3. **Índices (Δ\*):**
   - NDVI, EDI, NDRE y mNDVI705 bajan con la edad de la hoja madura, también en los controles.
   - **Ningún índice cambia de forma significativa solo en la hoja con roya.**
   - En las hojas maduras susceptibles hay 0 candidatas y 4 tendencias compatibles con
     envejecimiento, todas de Bourbon M1.
   - Las "candidatas" de otras familias (RCI en el valor crudo, NDVI del peor punto, ambas de
     Bourbon M1) no sobreviven al contraste con Δ\* o con el promedio de la misma hoja.
4. **Peor punto de Bourbon M1 el 24/08:** mNDVI705 = −0,75 en un solo punto, compatible con reflejo
   en el azul. Es la misma alerta de calidad de §12.4.

### 14.3 Próximo paso para la predicción

Lo que se puede modelar hoy es la **evolución normal**: maduración de T y envejecimiento de M, con
los controles incluidos. Sirve para detectar hojas que se desvíen de lo esperado (detección
temprana por anomalía).

Para predecir la evolución **de la roya** hacen falta hojas medidas **antes** de los síntomas y una
severidad visual por fecha como variable respuesta. Hoy ninguna hoja pasó de sana a enferma durante
el estudio.

La variable candidata más prometedora para ese modelo es la **reflectancia visible normalizada**
(§14.2).
