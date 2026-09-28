# Metodología — Reflectancia foliar y similitud espectral con roya

Fuente única de verdad del método que implementa la app (rama `mejora-app`, 2026-09-28). Si algo de
aquí contradice a `ESTADO_PROYECTO.md`, `ESTADO_ROYA.md` o `evoluciontemporal.md`, **vale este
documento** (esos son historia). Cada sección indica el módulo que la implementa, para poder
auditarla. El paper debe salir de aquí.

---

## 1. Diseño del muestreo y unidades de análisis

- **Especies:** Bourbon, Pacamara, Canefora, Cuscatleco. Solo **Bourbon y Pacamara** son
  susceptibles y tienen una hoja con roya confirmada (R1). Canefora y Cuscatleco son **controles
  sin roya**. Las hojas Pacamara "No susceptible" se ocultan del análisis (se cuentan en «Datos y calidad»).
- **Tipo de hoja** (prefijo del nombre de archivo): **T** tierna, **M** madura, **R** con roya,
  **V** vieja. *Tierna y madura significan "sin roya visible", **no** "sana"*: el estado real de la
  hoja madura es justamente lo desconocido. La tierna es la referencia sana porque la roya no ha
  tenido tiempo de manifestarse en tejido nuevo.
- **Hojas longitudinales:** M1, M2, T1, T2 y R1 son **las mismas hojas físicas en todas las
  campañas**. La unidad de análisis es la **hoja-fecha**.
- **Puntos:** dentro de cada hoja se mide en varios puntos, pero **no son ubicaciones fijas** entre
  campañas y solo **p1–p3** se consideran válidos (p4–p6 aparecen en algunas campañas y se
  excluyen). Cada punto tiene varias repeticiones (3 en las campañas recientes, hasta 10 en las de
  julio).
- **Agregación (`src/indices.py`):** archivo → **punto** (media de repeticiones) → **hoja-fecha**
  (media de los puntos p1–p3). Es la única cadena de agregación de la app; todas las vistas y
  Telegram la comparten (`file_index_table`, `point_table`, `leaf_date_table`).
- **Consecuencia estadística:** hay pocas hojas físicas (≈1 con roya por variedad), así que las
  conclusiones describen *trayectorias de esas hojas*, no un efecto poblacional de la roya.

## 2. Procesamiento del espectro (`src/processing.py`, `src/config.py`)

1. Lectura del `.txt` de SpectraSuite (reflectancia en %, 0–100).
2. Suavizado **Savitzky–Golay**, ventana 41, polinomio de orden 2.
3. Recorte a 420–1000 nm (las figuras temporales usan 440–1000 nm: por debajo, ~13 % de los
   espectros con roya da reflectancia negativa).
4. Reflectancia en una longitud de onda = valor suavizado más cercano dentro de ±5 nm.

Los parámetros son fijos y comunes a toda la app (los controles de suavizado de «Espectros» solo
afectan a ese gráfico y están bajo "Avanzado").

## 3. Índices espectrales (`processing.calcular_indices`)

Siete índices activos (`DISPLAY_INDICES`). Nombres estándar, con el nombre anterior de la app.

| Índice | Fórmula | Qué mide |
|---|---|---|
| NDVI | (R800 − R670) / (R800 + R670) | Vigor/verdor general |
| PRI | (R531 − R570) / (R531 + R570) | Eficiencia fotosintética / estrés (xantofilas) |
| PSRI | (R678 − R500) / R750 | Senescencia |
| RCI | 1/R510 − 1/R550 | Carotenoides; **no acotado** y escala con la reflectancia (0–100 %) |
| EDI | (R750 − R705) / (R750 + R705) | Borde rojo (equivale a ND705) |
| NDRE | (R790 − R720) / (R790 + R720) | Clorofila vía borde rojo |
| mNDVI705 | (R750 − R705) / (R750 + R705 − 2·R445) | Borde rojo corregido por dispersión con la banda azul |

- **FSR se retiró:** usa las mismas bandas que NDVI y da un valor idéntico. Se sigue calculando
  internamente por compatibilidad, pero no se muestra ni entra en estadística, similitud, distancia
  ni control de calidad.
- CARI se eliminó el 2026-08-02.
- Los rangos absolutos de la literatura (blogs, satélite) **no son comparables** con estos valores
  (medición de contacto a nivel de hoja; RCI escala con la reflectancia). Por eso la app no compara
  contra rangos externos, sino contra referencias propias (§5).

## 4. Control de calidad (`src/indices.quality_flags`)

Solo **marca**; nunca borra datos. Una hoja-fecha queda marcada (`qc_flag`) si:

- **Atípica** (`qc_atipico`): al menos **4 de los 7 índices** tienen |robust z| > 3.5 respecto de
  la propia serie de esa hoja. Robust z = 0.6745·(x − mediana)/MAD. Un solo índice raro puede ser
  biología; casi todos a la vez indica un problema de medición ese día. Requiere ≥ 5 fechas.
- **Implausible** (`qc_implausible`): mNDVI705 fuera de [−0.05; 1.05] (indicio de reflejo especular
  en el azul).

Las hojas-fecha marcadas se **excluyen de las anclas** de similitud y siguen visibles (marcadas) en
todas las páginas. Ejemplos conocidos: Pacamara R1 el 10/08 (reflectancia hundida en todo el
espectro) y mNDVI705 > 1 en Pacamara el 24/08 y 31/08.

## 5. Similitud espectral con roya (`src/severity.py`)

**No es un diagnóstico ni una severidad de planta.** Mide qué tan parecido es el conjunto de
índices de una hoja al de la hoja con roya de su especie, respecto de una hoja tierna.

1. **Ancla sana (0):** media del índice sobre las hojas T de la especie, **promediando por
   hoja-fecha** (cada fecha pesa igual) y sin hojas-fecha marcadas por control de calidad.
2. **Ancla con roya (1):** ídem con las hojas R. Una especie sin roya propia (Canefora,
   Cuscatleco) usa la media combinada de las que sí tienen y queda marcada como
   *referencia estimada*.
3. **Normalización por índice:** (valor − sana) / (roya − sana), recortado a [0, 1]. Un índice sin
   diferencia entre anclas o sin dato se omite.
4. **Combinación:** **mediana** de los índices normalizados (robusta a un índice atípico). Se guarda
   cuántos se usaron (`n_indices`).
5. **Orden de operaciones (importante):** primero se promedian los índices crudos a nivel
   hoja-fecha y **después** se calcula la similitud una sola vez. Así «Estado actual», «Evolución temporal»
   (opción "U") y Telegram dan **exactamente el mismo número** para la misma hoja-fecha (verificado:
   diferencia 0.0 en las 191 hojas-fecha del dataset).

**Escala de 4 clases** (`config.RUST_RISK_CLASSES`; cada valor se asigna a la clase de nivel más
cercano): Sin señal de roya (0), Vigilar (1/3), Revisar en campo (2/3), Alta similitud con roya (1).
Los límites entre clases son los puntos medios: 1/6, 1/2 y 5/6.
Las clases describen similitud espectral, no síntomas de la planta.

**Limitaciones que hay que declarar:**
- *Circularidad:* con una sola hoja R por especie, el ancla con roya *es* esa hoja; su similitud
  contra sí misma tiende a ~100 % por construcción. Sirve para comparar hojas entre sí, no como
  medida absoluta.
- Las hojas tiernas envejecen durante las 12 semanas; el ancla sana "todas las T" mezcla tejido
  tierno con casi maduro. Para la pregunta temporal «Evolución temporal» ofrece anclas alternativas
  (§7.3).
- Las hojas T y R son las que definen las anclas: salen ≈0 % y ≈100 % por construcción. Si una T
  sale alta en una fecha, es señal de un problema de medición, no de roya.

## 6. Estadística de comparación entre grupos (`src/stats_utils.py`)

Vistas «Índices por tipo de hoja» y «Comparación entre variedades», sobre la tabla **hoja-fecha**
(no sobre puntos, para evitar pseudo-réplica):

- **Comparación por pares** (`pairwise_effects`): para cada índice y cada par de grupos, medianas,
  **δ de Cliff** (−1 a +1; positivo si el primer grupo tiende a valores más altos) y p de
  **Mann–Whitney U** bilateral. El p se ajusta por **Holm** sobre toda la matriz índices × pares.
- **Magnitud del efecto** (Romano et al., 2006): |δ| < 0.147 despreciable; < 0.33 pequeño;
  < 0.474 mediano; ≥ 0.474 grande.
- **Prueba global** (`summarize_indices`): Kruskal–Wallis (3 o más grupos) o Mann–Whitney (2), con
  Holm entre índices. Solo dice si algún grupo difiere; el desglose es la tabla por pares.
- El detalle técnico (Shapiro–Wilk, ANOVA/Tukey o Kruskal/Dunn con `compare_groups`) queda plegado.

Aun con hoja-fecha como unidad, las fechas sucesivas de una misma hoja **no son independientes**:
los p-valores son optimistas. El tamaño de efecto es la cifra más informativa.

## 7. Evolución temporal (`src/temporal.py`, vista «Evolución temporal»)

### 7.1 Cambios respecto de la primera medición
- **Δ** = valor − valor en la primera fecha de esa hoja (cada hoja es su propio control).
- **Δ\*** = Δ − mediana de Δ de las hojas T de la misma especie ese día. Resta la deriva común (luz,
  calibración, estación) y *también* la maduración normal: es conservador a propósito.

### 7.2 Tendencias por hoja
Pendiente de **Theil–Sen** (por semana, IC 95 %) y test de **Mann–Kendall**, por hoja e índice, con
≥ 5 fechas. Corrección de **Benjamini–Hochberg (FDR 5 %)** sobre todas las especies y hojas a la
vez. Se reporta la autocorrelación de los residuos (r1) como diagnóstico. Una tendencia en una hoja
M susceptible es "candidata" solo si ninguna hoja M de los controles sin roya cambia en el mismo
sentido; si también cambia un control, la lectura es "compatible con envejecimiento".

### 7.3 Anclas alternativas para la similitud en el tiempo
- **S1:** ancla sana = T de las primeras 2 campañas (cuando eran realmente tiernas); ancla con roya
  = media de todas las fechas de R.
- **S2:** como S1, pero el ancla con roya se calcula sin la fecha evaluada (leave-one-campaign-out).
- **U:** la similitud unificada de §5.
S1 es la recomendada *para esta pregunta*; U es la que ve el resto de la app. Todas comparten la
limitación de circularidad.

### 7.4 Distancia a R1
Distancia RMS en z-scores (7 índices) entre cada hoja M/T y R1 el mismo día. El z usa media y SD de
los valores por punto de las hojas T en las primeras 2 campañas. Más baja = más parecida a R1.

### 7.5 Tendencia espectral
Pendiente de Theil–Sen de cada longitud de onda (puntos de reflectancia por semana), por hoja,
resumida por grupo con la mediana entre hojas. Opcionalmente se normaliza por la meseta NIR
(750–900 nm) para descartar cambios de nivel entre días.

## 8. Alerta de Telegram (`src/notifier.py`, `src/state.py`)

- Botón manual (no hay servidor en segundo plano). "Verificar" calcula las novedades y muestra una
  **vista previa**; "Enviar a Telegram" hace el envío real. Un envío fallido **no** actualiza el
  registro de archivos vistos.
- Cada archivo se identifica por **ruta relativa a `data/` + hash sha1 del contenido**; mover o
  clonar la carpeta no genera novedades falsas.
- Una tarjeta por hoja (promedio de puntos p1–p3), en español, con la similitud, su clase y la
  acción sugerida. Los mensajes se reparten bajo el límite de 4096 caracteres de Telegram. Un
  índice va en negrita cuando su valor normalizado llega a 2/3 (≈ nivel "Revisar en campo").
- Las hojas T y R se marcan como referencia; una tarjeta con menos de 3 puntos lleva ⚠️.

## 9. Lo que NO se puede concluir

1. Con una hoja con roya por variedad no hay efecto poblacional de la roya, solo trayectorias.
2. La fecha de infección no se conoce: el "día 0" de R1 es su primera medición (15/07).
3. No hay etiqueta de hoja asintomática *infectada*, así que no se puede afirmar detección
   temprana ni entrenar un predictor.
4. Un cambio en hojas M o T puede ser envejecimiento o estación, no roya (para eso existen Δ\* y los
   controles).
5. La similitud no es severidad de planta ni de campo.
