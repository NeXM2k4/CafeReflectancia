# Plan — Mejora y pulido del proyecto y del paper de CONCAPAN

Fecha: 2026-09-28 · Estado: **en pausa: primero va `plan_mejora_app.md`**; pendiente de tus respuestas (§8) · Documentos hermanos:
`ESTADO_PROYECTO.md`, `evoluciontemporal.md`, `PAPER/`

**Regla de alcance:** no se agregan funcionalidades nuevas. Todo lo que sigue corrige, reencuadra,
valida o explica lo que ya existe: los datos de `data/`, el pipeline de `src/`, las 5 páginas, la
alerta de Telegram y `make_ieee_figures.py`.

**Objetivos:**
1. Que el advisor quede satisfecho: cada número del paper sale de un script y se puede rastrear.
2. Que la investigación sea rigurosa y útil: afirmar solo lo que los datos sostienen y responder
   cada comentario de los revisores con evidencia de los datos que ya tenemos.
3. Que se entienda: el paper, el dashboard y la documentación usan los mismos términos.

---

## 0. Resumen ejecutivo

1. **El paper tiene errores que un revisor experto o el advisor van a encontrar**, además de los
   que marcaron los revisores. Los más graves:
   - p-valores que no se reproducen;
   - una Tabla I que mezcla grupos distintos de los que dice el texto;
   - FSR idéntico a NDVI;
   - el signo de PRI invertido en el texto;
   - un n de hojas con roya mayor que el real;
   - **al menos 4 referencias con datos incorrectos o que no pudimos encontrar** (§1.3).
2. **La comparación correcta es más fuerte que la publicada.** El paper compara hojas con roya
   contra hojas **tiernas**, así que mezcla edad de la hoja con roya. Contra hojas **maduras**
   (misma edad, sin síntomas), EDI, NDRE, mNDVI705 y PRI separan casi perfectamente
   (Cliff's δ entre −0,82 y −1,00). Contra tiernas, EDI **no** es significativo (§1.4).
3. **Ya tenemos datos para responder a 3 de los 6 pedidos del revisor 2 sin campañas nuevas.** Las
   7 campañas de agosto y septiembre nunca se usaron en el paper y sirven como conjunto de
   **validación independiente en el tiempo**. Con umbrales fijados solo con los datos de julio,
   mNDVI705 detecta la hoja con roya en 7/7 fechas en ambas variedades y da **0 falsas alarmas en 44
   hojas-fecha** de las especies sin roya (§1.4, preliminar).
4. **"Detección temprana" no se puede sostener** con estos datos, y así lo marcaron los revisores 2
   y 3. El estudio longitudinal (`evoluciontemporal.md`) es la respuesta honesta: en 12 semanas
   ninguna hoja madura se desplazó hacia la firma de roya más allá del envejecimiento normal. El
   paper debe reencuadrarse como **discriminación y monitoreo de hojas sintomáticas, en camino a la
   alerta temprana**.
5. El repo funciona, pero la documentación tiene afirmaciones desactualizadas y la "severidad
   0–100 %" describe síntomas de **planta entera** a partir de **3 puntos de una hoja**. Es el
   punto 6 del revisor 2 y también afecta al dashboard (§6).

---

## 1. Diagnóstico

### 1.1 Comentarios de los revisores y cómo se resuelven con lo que ya tenemos

| # | Revisor | Comentario | ¿Se resuelve sin datos nuevos? | Cómo (tarea) |
|---|---|---|---|---|
| R1.1 | 1 | Fotos del tipo de hoja estudiada | Sí, si existen fotos | Figura con H/M/R y los puntos de medición (T-F3). Pregunta Q6. |
| R2.1 | 2 | Muestra biológica muy chica | **No** | Declararlo en una sección de limitaciones, decir qué es el n real, pasar a unidad hoja-fecha y reportar repetibilidad en 9 fechas (T-A2, T-A3). Se propone como trabajo futuro. |
| R2.2 | 2 | Faltan datos pre-sintomáticos | **No** | Quitar la afirmación. Presentar el resultado longitudinal negativo como evidencia honesta (T-A6, T-P1). |
| R2.3 | 2 | Faltan métricas de clasificación (sens., espec., ROC/AUC) | **Sí** | Métricas a nivel hoja-fecha, con IC (T-A4). |
| R2.4 | 2 | Validar umbrales en un conjunto independiente | **Sí** | Umbrales de julio aplicados a agosto–septiembre, más los controles negativos (T-A4). |
| R2.5 | 2 | Lista de materiales y contradicción con "bajo costo" | Sí | Lista de materiales con costos; cambiar "low-cost" por "portable, field-deployable" y discutir el camino a bajo costo (T-P5). Pregunta Q7. |
| R2.6 | 2 | Distinguir detección binaria de severidad | Sí | El paper reporta detección binaria validada. El score 0–100 % se renombra y se declara no validado como severidad (T-P4, T-D1). |
| R3.1 | 3 | Numeración de autores | Sí | "1st, 1nd, 2rd, 3th…" → formato IEEE correcto (T-P7). |
| R3.2 | 3 | Literatura de los últimos 5 años | Sí | Verificar todas las referencias y agregar las recientes (T-P6). |
| R3.3 | 3 | Aclarar el alcance de "detección temprana" | Sí | Igual que R2.2. |
| R3.4 | 3 | Discutir el tamaño de muestra como limitación | Sí | Igual que R2.1. |

### 1.2 Problemas que no marcaron los revisores pero que el advisor o un experto sí verían

Verificados contra el código, los datos y `ESTADO_PROYECTO.md`.

| # | Dónde | Problema | Evidencia |
|---|---|---|---|
| E1 | Tabla I, Abstract, Resultados | **"H" en la Tabla I = maduras + tiernas juntas** (n=60), pero el texto dice "healthy (H, young)" y las figuras usan solo tiernas (n=30). | `ESTADO_PROYECTO.md` §14.1. EDI H 0,438 = media de M (0,541) y T (0,336). |
| E2 | Resultados | **Los p-valores no se reproducen.** El paper dice que EDI, PRI, NDRE y mNDVI705 dan p<0,001 y que NDVI, FSR, RCI y PSRI no son significativos. Con el pipeline actual (T vs R, unidad punto): EDI p=0,094 (Bourbon) y p=0,071 (Pacamara), **no significativo**; NDRE Bourbon p=0,037; NDVI Bourbon p=0,008; RCI Bourbon p=0,004 y PSRI Pacamara p=0,005, **significativos**. | §1.4, tabla A. |
| E3 | Tabla I, Métodos | **FSR ≡ NDVI**: mismas bandas (800/670), así que la fila es idéntica. En Métodos FSR figura con 850 nm, que **no** es lo que calcula el código. | `config.py`: `WL_FSR = WL_NDVI`. |
| E4 | Tabla I | **Falta la fila de PSRI**, aunque el texto dice "ocho índices". | PDF, Tabla I. |
| E5 | Abstract, Resultados, Conclusión | **Signo de PRI invertido**: "increasing 130 %" cuando pasa de −0,036 a −0,083, es decir que **baja**. Además, un % de cambio sobre un índice que cruza el cero no tiene sentido. | Tabla I. |
| E6 | Métodos | "Two plants per variety… one leaf per category from each plant" implica 2 hojas con roya por variedad. **En los datos hay una sola hoja con roya (R1) por variedad**, la misma hoja física en todas las campañas. | `evoluciontemporal.md` §1, memoria del proyecto. |
| E7 | Métodos | "Nine technical replicates averaged per leaf per session": las hojas R tienen 30 espectros por sesión (3×10) y la estadística se hizo por **punto**, no por hoja. | `figures_ieee/README.md`. |
| E8 | Métodos | "Kruskal-Wallis with Dunn post-hoc": con 2 grupos es Mann-Whitney U y no hay post-hoc. El pipeline además elige ANOVA si hay normalidad. No hay corrección por comparaciones múltiples (16 tests). | `stats_utils.py`. |
| E9 | Métodos | "Savitzky-Golay smoothing **and baseline correction**": **no hay corrección de línea base** en el código. | `processing.py`. |
| E10 | Métodos | "Environmental data (humidity, temperature, PM) recorded": **no existe en el repo**, y `evoluciontemporal.md` §10 dice que las condiciones no se registraron. | Pregunta Q4. |
| E11 | Métodos | No se describe la **referencia de blanco ni la de oscuro** (cómo se obtiene reflectancia de un USB4000), ni la ventana SG en nm, ni que la reflectancia está en % (RCI escala con eso). | — |
| E12 | Índices | **Nombres y citas de índices incorrectos.** "EDI" es ND705 / Red-edge NDVI (Gitelson & Merzlyak 1994; Sims & Gamon 2002), no un "Early Detection Index", y se cita el paper de PRI de Gamon. "RCI" es CRI1 de Gitelson et al. 2002. mNDVI705 es de Sims & Gamon 2002, no de Gitelson 2003. NDRE es de Barnes et al. 2000. Renombrar índices conocidos es lo primero que marca un especialista. | Fórmulas de `processing.py`. |
| E13 | mNDVI705 | **El mejor índice usa 445 nm, donde la señal es mala**: bajo 440 nm, ~13 % de los espectros R da reflectancia negativa; mNDVI705 > 1 el 24/08 y el 31/08 y negativo en un punto de Bourbon M1. El comentario del código "ningún índice usa bandas < 500 nm" es falso. | `evoluciontemporal.md` §12.4; `make_ieee_figures.py` l.74–76. |
| E14 | Discusión | "Bourbon exhibited larger and more consistent differences than Pacamara" **contradice la Tabla I**, donde Pacamara cambia más en todos los índices. | Tabla I. |
| E15 | Discusión | "NIR decrease (FSR, NDVI)" cuando NDVI/FSR no cambian. "37–41 % reduction provides a clear quantitative threshold" sin ningún umbral calculado. "supports EDI's utility for early detection before visible symptoms" sin datos pre-sintomáticos. | Texto. |
| E16 | Fig. 7 / IoT | Escala de 11 clases con descripciones de **planta entera** ("defoliation", "death of the plant") asignadas a **una hoja** medida en 3 puntos, sin severidad visual de referencia. | `config.py` `RUST_RISK_CLASSES`. |
| E17 | Diseño | **Confusor edad–roya**: "sana" = hoja tierna y "con roya" = hoja adulta. Las tiernas se oscurecen al madurar (7/7 hojas), así que parte de la diferencia es edad. | `evoluciontemporal.md` §14.2; §1.4. |
| E18 | Intro | Incidencias "Bourbon 9,44 %, Pacamara 8,28 %" citadas a [9] y [10], que no pudimos encontrar (§1.3). | — |

### 1.3 Referencias: verificación preliminar

Hecha el 2026-09-28 con búsqueda web. **Hay que verificar las 18 con DOI** (T-P6), pero ya
aparecieron problemas serios:

| Ref | Problema encontrado |
|---|---|
| [6] | El título existe, pero la revista es **Agronomy** (no *Agriculture*), 12(12):2911, 2022, y los autores son **Soares, Martins y Siquieroli**, no "de Oliveira et al.". |
| [10] | "de Oliveira & de Souza, *Incidence of CLR… in El Salvador*, J. Plant Pathol. 2022": **no se encontró**. Es probable que no exista. De ella salen las incidencias 9,44 % / 8,28 %. |
| [9] | Informe técnico de CATIE 2018: **no se encontró** con ese título. Hay que confirmar la fuente o quitarla. |
| [11] | Cabrera, Avramidis y Narayanan existe, pero es **arXiv:2407.14737 (2024)**, no *IEEE Access* vol. 12, pp. 12345–12356. Las páginas parecen inventadas. |
| [14] | Existe (Sci. Rep., 2026, doi:10.1038/s41598-025-32624-4). Falta confirmar la lista de autores. |
| [2], [3], [7], [15], [17], [18] | Parecen reales. Solo falta confirmar volumen y páginas. |

> Una referencia inexistente en un paper IEEE es causa de retracción. **Es la tarea de mayor
> prioridad del plan, junto con E2.**

### 1.4 Números preliminares (script de prueba, 2026-09-28)

Salen de `get_dataset()` + `temporal.file_indices()`, con puntos p1–p3. **Son preliminares**: la
versión oficial debe generarla un script del repo (T-A0).

**A. Replicación del período del paper (29/06–27/07; unidad punto; T n=30, R n=6)**

| Índice | Bourbon: p (T vs R) | Bourbon: δ (R vs M) | Pacamara: p (T vs R) | Pacamara: δ (R vs M) |
|---|---|---|---|---|
| PRI | 0,0001 | −0,89 | 0,0001 | −1,00 |
| EDI | **0,094** | **−0,98** | **0,071** | **−0,82** |
| NDRE | 0,037 | −0,99 | 0,002 | −1,00 |
| mNDVI705 | <0,0001 | −1,00 | 0,0001 | −1,00 |
| NDVI | 0,008 | −0,62 | 0,92 | −0,04 |
| PSRI | 0,078 | +0,62 | 0,005 | +0,72 |
| RCI | 0,004 | −0,17 | 0,059 | +0,38 |

Lectura: **EDI solo separa si la comparación es contra la hoja de la misma edad.** Es el argumento
central para cambiar la referencia sana del paper (T-A2).

**B. Repetibilidad en las 12 campañas (unidad hoja-fecha)**

Cuenta las fechas en que R1 queda más allá de las 4 hojas M/T de su especie ese mismo día:

| Índice | Bourbon | Pacamara |
|---|---|---|
| PRI | 8/9 | 9/9 |
| EDI | 8/9 | 9/9 |
| NDRE | 8/9 | 9/9 |
| mNDVI705 | 8/9 | 9/9 |
| NDVI | 3/9 | 5/9 |

**C. Validación independiente en el tiempo**

Umbral de Youden con los puntos de julio (T vs R) aplicado a las hojas-fecha de agosto–septiembre:

| Índice | Variedad | Sensibilidad (R1) | Especificidad (M+T propias) | Especificidad (controles sin roya) |
|---|---|---|---|---|
| mNDVI705 | Bourbon | 7/7 | 27/28 | 44/44 |
| mNDVI705 | Pacamara | 7/7 | 28/28 | 44/44 |
| NDRE | Pacamara | 6/7 | 28/28 | 44/44 |
| PRI | Bourbon | 7/7 | 23/28 | 34/44 |
| EDI | Pacamara | 1/7 | 28/28 | 44/44 |

EDI falla porque su umbral salió de la comparación contra hojas tiernas: otra vez la edad.
**Advertencia que va en el paper:** los positivos son **una sola hoja por variedad** medida en 7
fechas. La sensibilidad mide la **repetibilidad** de la detección de esa hoja, no la sensibilidad
poblacional.

### 1.5 Estado del repo (para "que se entienda")

- Trabajo sin commitear: `pages/5_Evolucion_Temporal.py`, `src/temporal.py`,
  `evoluciontemporal.md`, `PAPER/` y cambios en `ESTADO_PROYECTO.md` y `src/config.py`.
- **Afirmaciones desactualizadas** en la documentación:
  - `ESTADO_PROYECTO.md` §3 dice "no es un repo git" y que `roya/` no está en `.gitignore` (sí está).
  - §5 dice que 14_09 y 21_09 no están commiteadas.
  - `ESTADO_ROYA.md` apunta a `_severity_baselines()` en `app.py` (hoy está en `severity.py`), su
    ejemplo muestra CARI y "7/7", y la tabla §9.1 está desactualizada.
  - `processing.severity_score` tiene el mismo puntero viejo.
- `ESTADO_PROYECTO.md` pesa 64 KB y mezcla bitácora histórica con referencia vigente: no sirve
  para que alguien nuevo entienda el proyecto.
- La página 5 tiene 10 secciones y 1244 líneas; para un usuario de campo es demasiado.
- **No hay una sola fuente de verdad para la metodología**: el paper, `figures_ieee/README.md`, las
  páginas 2–3 y la página 5 usan unidades de análisis y referencias sanas distintas.

---

## 2. Tesis del paper revisado

| | Paper enviado | Paper revisado (propuesta) |
|---|---|---|
| Afirmación principal | Detección **temprana**, antes de los síntomas | **Discriminación repetible** de hojas con roya sintomática en campo, con validación independiente en el tiempo y un sistema de alerta IoT, como base para la alerta temprana |
| Referencia sana | Hojas tiernas | **Hojas maduras de la misma edad, sin síntomas** (principal) + tiernas (secundaria), con el confusor edad declarado |
| Unidad | Punto (pseudo-réplica) | **Hoja-fecha**, con la unidad punto solo como análisis secundario |
| Evidencia | p-valores | Tamaños de efecto con IC, repetibilidad en 9 fechas, sensibilidad/especificidad en datos no vistos, controles negativos (especies sin roya) |
| Longitudinal | No | 12 semanas: ninguna hoja madura migró hacia la firma de roya. Maduración y roya se mueven en direcciones opuestas en el visible |
| IoT | 11 clases de severidad | Alerta **binaria/ternaria** validada. El score continuo se presenta como "similitud espectral", sin validar como severidad |
| Costo | "Low-cost" | "Portable, field-deployable", con lista de materiales. Las ~7 bandas que usan los índices abren el camino a un sensor multiespectral barato (trabajo futuro) |

**Títulos candidatos** (a decidir con el advisor):
- *Field Discrimination of Coffee Leaf Rust in Susceptible Varieties Using a Portable Reflectance
  IoT Prototype: A 12-Week Longitudinal Study*
- *Toward Early Warning of Coffee Leaf Rust: Portable Point-Reflectance Monitoring with IoT Alerts
  in Bourbon and Pacamara*

**Contribución, en una frase:** un flujo de extremo a extremo (sonda de contacto → índices →
alerta por Telegram) cuya capacidad de discriminar se validó en campañas posteriores e
independientes de las que fijaron los umbrales, y cuyo seguimiento longitudinal separa la señal de
la roya de la del envejecimiento foliar. Esto es lo que el revisor 2 reconoció como aporte (la
integración), ahora con la validación que pidió.

---

## 3. Fase A — Análisis riguroso y reproducible para el paper

Todo va en **un solo script**, extendiendo `make_ieee_figures.py` y sin crear un módulo nuevo del
dashboard. El script escribe las figuras y además `figures_ieee/paper_numbers.csv` y
`figures_ieee/tables.tex`. **Ningún número se copia a mano al paper.**

| ID | Tarea | Detalle | Criterio de aceptación |
|---|---|---|---|
| **T-A0** | Congelar el dataset del paper | Guardar la lista de archivos y hashes usados, en dos subconjuntos: "período original" (5 campañas de julio) y "validación" (7 de agosto–septiembre). | El script falla si cambia un archivo de esos conjuntos. |
| **T-A1** | Auditoría del paper enviado | Reproducir la Tabla I tal como se envió (H = M+T) y dejar escrito qué número no coincide con qué afirmación (E1–E5). | Tabla de auditoría en `PAPER/auditoria_paper_enviado.md`. |
| **T-A2** | Comparación principal | Unidad hoja-fecha, R1 vs M (principal) y R1 vs T (secundaria), por variedad. Tamaño de efecto (Cliff's δ) con IC por **bootstrap por conglomerados** (se remuestrean hojas-fecha, no puntos). Mann-Whitney con **corrección de Holm** sobre 7 índices × 2 variedades. Sin FSR. | Tabla I nueva: media ± SD por grupo (T, M, R), δ con IC y p ajustado. Todo el paper con el mismo n. |
| **T-A3** | Repetibilidad temporal | Por índice: en cuántas fechas R1 queda fuera del rango de las hojas M/T de ese día (tabla B de §1.4). | Una columna "k/n fechas" en la Tabla I o una tabla corta. |
| **T-A4** | Métricas y validación independiente | Umbrales fijados **solo** con julio (Youden, con la referencia M y con la referencia T) y evaluados en agosto–septiembre: sensibilidad, especificidad y exactitud balanceada con IC de Wilson; AUC con IC bootstrap; controles negativos por separado. **La alerta de Telegram también se evalúa así** (¿qué clase habría asignado a cada hoja-fecha de validación?). | Tabla II "Detection performance on held-out campaigns", con la advertencia de n=1 hoja positiva por variedad. |
| **T-A5** | Sensibilidad (robustez) | Repetir A2 y A4: (a) con y sin las 4 hojas-fecha marcadas por el control de calidad (Pacamara R1 10/08); (b) mNDVI705 frente a EDI, para ver cuánto depende de R445; (c) unidad punto frente a hoja-fecha; (d) solo 5 campañas frente a 12. | Una frase por caso en el paper y la tabla completa en el repo. Una conclusión se afirma solo si sobrevive a (a)–(d). |
| **T-A6** | Resultado longitudinal | Reusar `temporal.py`: firma espectral de la tendencia por grupo (T se oscurece y R1 se aclara en el visible) y 0 hojas M candidatas. Una figura estática (la Fase 5 pendiente de `evoluciontemporal.md`). | Figura y 1 párrafo, con n=2 hojas con roya declarado. |
| **T-A7** | Chequeo de los espectros publicados | Comprobar que la frase "infected leaves exhibited decreased reflectance in red-edge and NIR" coincide con las figuras regeneradas. Si no coincide, corregir el texto. | Texto y figura consistentes. |

**Métodos estadísticos, fijados de antemano** (para no elegir el test según el resultado):
unidad hoja-fecha; Mann-Whitney bilateral; Holm; δ de Cliff con IC bootstrap de 2000
remuestreos con semilla fija; umbral de Youden sobre julio; α = 0,05. El resto es descriptivo.

---

## 4. Fase P — Reescritura del paper

**Necesito el `.tex`** (pregunta Q1). Sin él, entrego los párrafos en `PAPER/cambios_paper.md`.

| ID | Sección | Cambios |
|---|---|---|
| **T-P1** | Título, Abstract, Intro | Quitar "early detection" como afirmación demostrada (usar "toward early warning"). Abstract con los números nuevos de T-A2/T-A4. Objetivo reformulado. |
| **T-P2** | Materiales y métodos | Diseño real: cuántas plantas y hojas, R1 = 1 hoja por variedad (Q2), hojas M/T fijas medidas en 12 campañas, dónde se tomaron los puntos en la hoja R (Q3). Protocolo óptico: blanco y oscuro, integración, SG en nm, reflectancia en %, rango 440–1000 nm (Q4). Quitar "baseline correction" y los datos ambientales si no existen. Estadística según §3. |
| **T-P3** | Índices | Nombres y citas estándar: ND705 (en vez de "EDI"), CRI1 (en vez de "RCI"), NDRE (Barnes 2000), mNDVI705 (Sims & Gamon 2002), PSRI, PRI, NDVI. **Eliminar FSR.** Nota sobre la sensibilidad de mNDVI705 a R445. |
| **T-P4** | Resultados e IoT | Tablas I y II nuevas, figura longitudinal, y una sección IoT que describe la **alerta binaria validada**. El score continuo va como "spectral similarity to the rust reference", no como severidad. La escala de 11 clases de planta entera se saca del paper (o se declara explícitamente como escala agronómica no validada). |
| **T-P5** | Costo | Tabla corta de materiales con precio aproximado (Q7). Discusión: los índices útiles usan ~7 bandas (445, 531, 570, 705, 720, 750, 790 nm), compatibles con un sensor multiespectral de bajo costo como trabajo futuro, sin afirmarlo como hecho. |
| **T-P6** | Referencias | Verificar las 18 con DOI. Corregir [6] y [11]; quitar o reemplazar [9] y [10] y las incidencias que dependen de ellas. Agregar trabajos recientes (2021–2026) **verificados**: candidatos Soares et al. 2022 (Agronomy), Cabrera et al. 2024 (arXiv), Koutouleas et al. 2024 (*Plant Pathology*, revisión de la pandemia de roya), el dataset multiespectral de hojas de café de Colombia (2025, *Data in Brief*). Agregar Gitelson & Merzlyak 1994, Sims & Gamon 2002 y Barnes et al. 2000 para los índices. |
| **T-P7** | Forma | Autores en formato IEEE (sin "1nd/2rd/3th"). Unidades, decimales y signos consistentes. Reemplazar los "% de cambio" por diferencias absolutas y δ. Captions autocontenidas con el n. |
| **T-P8** | Discusión y limitaciones | Sección explícita de **limitaciones**: n=1 hoja con roya por variedad, pseudo-réplica temporal, confusor edad, cambio de protocolo en R1 (10→5→3 repeticiones), puntos no fijos, condiciones no registradas, ruido en 445 nm. Quitar E14 y E15. **Trabajo futuro concreto**: inoculación controlada o hojas marcadas antes de los síntomas con severidad visual por fecha, más plantas y hojas R, sensor de pocas bandas. |
| **T-P9** | Respuesta a revisores | `PAPER/respuesta_revisores.md`: cada comentario → qué se cambió → dónde (sección, figura, tabla). Sirve para el advisor aunque la conferencia no lo pida. |

**Figuras del paper** (regenerar con `make_ieee_figures.py`):

| ID | Figura |
|---|---|
| T-F1 | Espectros medios T/M/R por variedad, con SE y espectro de diferencia (R − M). |
| T-F2 | Resumen de efectos: forest plot de δ con IC, R vs M y R vs T, 7 índices × 2 variedades. Reemplaza los boxplots por punto. |
| T-F3 | Foto de las hojas (Q6), con la sonda y los puntos de medición. |
| T-F4 | Figura longitudinal (T-A6). |
| T-F5 | Alerta de Telegram con el formato nuevo (binaria + similitud). |

---

## 5. Fase D — Dashboard y alerta: correcciones de coherencia (sin funciones nuevas)

Lo mínimo para que la app diga lo mismo que el paper. **Cambia lo que ve el usuario de Telegram,
así que cada ítem requiere tu OK** (Q9).

| ID | Cambio | Por qué |
|---|---|---|
| T-D1 | Renombrar "Severidad" → "Similitud espectral con roya" en la página 4, la página 5 y Telegram, y quitar las descripciones de planta entera de las clases (o mostrarlas solo como referencia agronómica). | E16, revisor 2 punto 6. |
| T-D2 | Sacar FSR del score (sigue visible como dato, o se elimina del todo). | E3: hoy pesa doble en la mediana. |
| T-D3 | Anclas de `severity_baselines()` ponderadas **por fecha** (como en `temporal.py`) y con opción de excluir las hojas-fecha marcadas por QC. | El ancla de RCI de Pacamara está inflada ~7× por el 10/08 (pendiente abierto de `ESTADO_PROYECTO.md`). |
| T-D4 | Páginas 2 y 3: la estadística usa la **misma unidad y el mismo test que el paper** (hoja-fecha, Mann-Whitney/Holm, δ) y muestra el n de hojas biológicas. | Una sola metodología en todo el proyecto. |
| T-D5 | Corregir los comentarios falsos o viejos ("ningún índice usa < 500 nm", punteros a `app.py`, "7 índices"). | E13, §1.5. |
| T-D6 | Página 5: dejar arriba lo que responde preguntas (resumen, hojas M, qué cambia con el tiempo) y mandar las secciones de detalle a pestañas o expanders. Es reorganizar, no agregar. | Entendible para el usuario. |
| T-D7 | Glosario único (T/M/R, hoja-fecha, similitud, Δ*) visible en Inicio. | Términos consistentes. |

---

## 6. Fase C — Documentación y orden del repo

| ID | Tarea |
|---|---|
| T-C0 | **Primero:** commitear el trabajo pendiente (página 5, `temporal.py`, docs) y crear el tag `concapan-enviado` que marque el estado del envío. |
| T-C1 | `README.md` corto: qué es, cómo correrlo, qué responde cada página y un mapa de documentos. |
| T-C2 | `METODOLOGIA.md` como **única fuente de verdad**: diseño de muestreo, protocolo óptico, índices con fórmula y cita, unidad de análisis, estadística y limitaciones. El paper y el dashboard remiten a él. |
| T-C3 | `ESTADO_PROYECTO.md`: separar la bitácora histórica (`docs/bitacora.md`) de lo vigente y corregir las afirmaciones desactualizadas de §1.5. |
| T-C4 | `ESTADO_ROYA.md`: actualizar al score vigente (8→7 índices, anclas por fecha, nombre nuevo) y la tabla §9.1 con el dataset actual, o marcarla como histórica. |
| T-C5 | Un script de verificación, `python -m src.checks`, que corra las invariantes que hoy solo están descritas en los docs: NDVI/PRI/PSRI iguales al notebook, consistencia de `leaf_ts` con `leaf_severity_reports`, tabla de presencia. Es un control de calidad, no una función. |

---

## 7. Fuera de alcance

- Clasificadores o machine learning nuevos, severidad visual y modelos predictivos.
- Índices nuevos o bandas nuevas para FSR: FSR se **elimina**, no se redefine.
- Cambiar el diseño de muestreo retroactivamente.
- **Opcional, solo si lo pedís:** simular los índices con bandas anchas (~20 nm FWHM) sobre los
  espectros existentes, para respaldar numéricamente el argumento de bajo costo de T-P5. Usa
  solo datos existentes, pero es un análisis nuevo.

---

## 8. Preguntas abiertas (bloquean partes del plan)

Entre paréntesis, lo que haría si no hay respuesta.

| # | Pregunta | Bloquea |
|---|---|---|
| Q1 | ¿En qué etapa está el paper (camera-ready, revisión mayor), con qué **fecha límite** y **límite de páginas**? ¿Tenés el `.tex` o el proyecto de Overleaf? (Asumo 6 páginas IEEE y trabajo sobre un `.md` con los párrafos.) | Toda la Fase P |
| Q2 | ¿Cuántas plantas hay por variedad y de qué planta sale cada hoja (M1, M2, T1, T2, R1)? ¿R1 es **una sola hoja física** por variedad en todas las campañas? (Asumo que sí, por la memoria del proyecto.) | T-P2, E6 |
| Q3 | En R1, ¿los puntos se midieron **sobre la lesión/pústula** o en tejido verde cercano? ¿Haz o envés? | Interpretación de todo el resultado |
| Q4 | ¿Cómo se tomó la referencia de blanco (Spectralon u otra) y la de oscuro? ¿Siempre a las 7:00? ¿Existen los datos ambientales que menciona el paper? (Si no existen, se quitan del texto.) | T-P2, E10, E11 |
| Q5 | ¿Hay **permiso** para usar Canefora y Cuscatleco en el paper como controles negativos? Estuvieron excluidas por eso. (Si no hay, T-A4 reporta solo la especificidad en las hojas propias.) | T-A4, T-A6 |
| Q6 | ¿Hay fotos de las hojas (R1, M, T) y del equipo en campo? | T-F3, revisor 1 |
| Q7 | ¿Precio aproximado del USB4000, el HL-2000, la fibra y la sonda, la batería, etc.? | T-P5 |
| Q8 | ¿El advisor acepta ampliar el paper a las 12 campañas, usando las posteriores como validación? (Recomiendo que sí: es la respuesta más fuerte al revisor 2.) | T-A4, T-A6 |
| Q9 | ¿Aprobás los cambios visibles de la alerta y el dashboard (T-D1 a T-D3)? Cambian los números que recibe Telegram. | Fase D |
| Q10 | ¿Las hojas M se revisaban visualmente en cada campaña? ¿Alguna mostró síntomas? Eso permite llamarlas "asintomáticas" y no solo "maduras". | T-A2, T-P2 |

---

## 9. Orden de ejecución

| Paso | Qué | Depende de |
|---|---|---|
| 1 | T-C0 (commit + tag) y T-P6 (referencias). La verificación de referencias no depende de nada. | — |
| 2 | T-A0, T-A1 (congelar y auditar). | — |
| 3 | Respuestas Q1–Q5, Q8 y Q10. | Vos y el equipo de campo |
| 4 | T-A2 → T-A5, en ese orden: la sensibilidad decide qué se puede afirmar. | 2, 3 |
| 5 | T-A6, T-A7 y las figuras T-F1 a T-F5. | 4 |
| 6 | T-P1 → T-P9. **Revisión del advisor** sobre el borrador y la respuesta a revisores. | 5, Q1 |
| 7 | Fase D (con Q9) y Fase C. Se hace **después** de fijar la metodología, para que la app copie la metodología del paper y no al revés. | 6 |

**Criterio de "terminado":**
- (a) Cada número del paper aparece en `paper_numbers.csv`.
- (b) Cada comentario de revisor tiene su fila en `respuesta_revisores.md`.
- (c) Las 18+ referencias tienen DOI o URL verificada.
- (d) Ninguna frase del paper afirma detección pre-sintomática.
- (e) El dashboard, `METODOLOGIA.md` y el paper usan los mismos nombres de índices, la misma unidad
  de análisis y la misma referencia sana.
