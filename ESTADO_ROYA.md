# Cómo se calcula el nivel de riesgo de roya de una hoja

Última actualización: 2026-09-11

## 1. Punto de partida: los 8 índices

No hay un índice único que determine si una hoja está sana o enferma. La app parte de los 8 índices espectrales que ya calcula por archivo, en `calcular_indices()` (`src/processing.py`):

| Índice | Qué mide |
|---|---|
| NDVI | Vigor / verdor general (clorofila vs. infrarrojo cercano) |
| PRI | Eficiencia fotosintética / estrés |
| PSRI | Senescencia (degradación del tejido) |
| RCI | Carotenoides asociados a estrés por roya |
| EDI | Corrimiento del borde rojo (detección temprana) |
| FSR | Estrés foliar (por ahora usa las mismas bandas que NDVI, ver la limitación al final) |
| NDRE | Clorofila vía borde rojo (790/720 nm) |
| mNDVI705 | NDVI del borde rojo corregido por dispersión foliar con R445 |

Un índice por sí solo (NDVI = 0.62, por ejemplo) no dice nada de sano o enfermo. Necesita algo con qué compararse — de ahí el siguiente paso.

## 2. Las dos referencias: sano y enfermo

Para saber si un valor está "cerca de sano" o "cerca de enfermo", la app necesita dos anclas por índice y por especie, calculadas a partir de lo que ya hay en `data/` (`_severity_baselines()`, `app.py`):

- **Ancla sana (0):** promedio del índice entre todas las hojas tiernas (T) de esa especie. La roya tarda en manifestarse, así que una hoja recién formada es la referencia sana más confiable disponible, aunque la planta ya tenga hojas con roya cerca.
- **Ancla enferma (1):** promedio del índice entre las hojas con roya confirmada (archivos que empiezan con `R`).

**Bourbon y Pacamara tienen ancla enferma propia** (campañas con roya confirmada en ambas), así que sus scores se calculan con la referencia de su propia especie.

El código conserva un respaldo genérico para una especie que no tuviera hojas con roya propias: usa el promedio combinado de las que sí las tienen, marcado internamente como `referencia_propia: False` y aclarado en Telegram como "referencia estimada", para dejar claro que ese número pesa menos. **Canefora y Cuscatleco no tienen roya propia** y, desde que se reincluyeron en el dataset el 2026-09-11 (antes estaban excluidas por falta de permisos, ver `ESTADO_PROYECTO.md` sección 1), **este respaldo se activa para ellas**: sus scores de severidad usan la referencia enferma combinada de Bourbon+Pacamara, no una propia.

**Nota importante (2026-07-31):** las anclas se calculan sobre el dataset que devuelve `get_dataset()`, que ya excluye Pacamara "No susceptible". Es decir, todas las hojas Pacamara que participan en las anclas son de la variedad Susceptible — coherente con el objetivo del proyecto de analizar plantas susceptibles a roya.

## 3. Normalizar cada índice

Con las dos anclas de un índice y el valor en la hoja nueva, se aplica una regla de tres (`severity_score()`, `src/processing.py`):

```
normalizado = (valor_hoja − ancla_sana) / (ancla_enferma − ancla_sana)
```

Un valor igual al ancla sana da 0; igual al ancla enferma da 1; en medio, algo intermedio. El resultado se recorta entre 0 y 1 por si la hoja nueva queda más extrema que las propias referencias.

Esto se repite para cada uno de los 8 índices, pero solo con los que tengan datos válidos: si un índice no se pudo calcular para esa hoja, o su especie no tiene diferencia entre ancla sana y enferma, simplemente queda fuera del cálculo.

## 4. De 7 números a uno solo

Con hasta 8 valores normalizados (escala 0–1), se combinan usando la mediana, no el promedio:

```
score_final = mediana(normalizado_NDVI, normalizado_PRI, normalizado_PSRI, ...)
```

La mediana se prefiere porque un solo índice fuera de rango (por ruido de medición, por ejemplo) puede arrastrar un promedio hacia un extremo; la mediana lo ignora y refleja mejor el consenso entre índices.

La app también guarda cuántos de los 8 índices se pudieron usar (`n_indices`), y eso aparece en Telegram como `(7/8 comparable)`, para que se sepa qué tan respaldado está el número.

## 5. Ejemplo

Hoja madura nueva de Bourbon:

| Índice | Sana (ancla 0) | Enferma (ancla 1) | Valor de la hoja | Normalizado |
|---|---|---|---|---|
| NDVI | 0.80 | 0.30 | 0.55 | 0.50 |
| PSRI | 0.10 | 0.50 | 0.38 | 0.70 |
| RCI | 2.0 | 6.0 | 3.2 | 0.30 |
| PRI | 0.05 | −0.05 | 0.01 | 0.40 |

Score final = mediana(0.50, 0.70, 0.30, 0.40) = **0.45 → 45%**

## 6. Cómo se ve en Telegram

`src/notifier.py` traduce el score a algo legible para alguien sin formación técnica, usando la **escala de 11 clases** definida en `config.py` (`RUST_RISK_CLASSES`, actualizada el 2026-08-02; antes eran 3 niveles). Cada clase representa un riesgo nominal cada 10 %, y un score se asigna a **la clase cuyo nivel tiene más cerca** (0.34 → Slight 30 %; 0.36 → Onset of moderate 40 %):

| Clase | Riesgo | Qué se ve en la planta |
|---|---:|---|
| 🟢 Healthy | 0 % | Planta limpia, fuerte y sin ningún rastro del hongo |
| 🟢 Incipient | 10 % | Puntos amarillos aislados y casi imperceptibles en la base |
| 🟡 Very slight | 20 % | Primeras pústulas de polvo anaranjado en el envés |
| 🟡 Slight | 30 % | Manchas visibles en varias hojas del tercio inferior |
| 🟡 Onset of moderate | 40 % | El hongo empieza a subir hacia el centro |
| 🟠 Moderate | 50 % | Mitad del follaje afectado con polvo naranja evidente |
| 🟠 Onset of severe | 60 % | Hojas del centro se secan y pierden color |
| 🔴 Severe | 70 % | Infección alta y primeras caídas notorias de hojas |
| 🔴 Very severe | 80 % | Defoliación avanzada en casi toda la estructura |
| 🔴 Critical | 90 % | Planta casi desnuda con daño extremo en el tejido |
| ⚫ Very critical | 100 % | Infección destructiva total y muerte de la planta |

Los nombres de clase van **en inglés** porque la alerta de Telegram se envía en inglés; la descripción de arriba es la traducción de referencia. La acción sugerida no es una por clase (serían 11 y se vuelve ruido en el campo) sino una por tramo: `RUST_RISK_ACTIONS` en `config.py` agrupa en 5 acciones, de "no hacer nada" a "tratar con urgencia".

**La unidad de reporte es la hoja** (rediseñado 2026-08-02): la severidad de la hoja es el promedio de la severidad de sus 3 puntos de medición, y cada punto es a su vez el promedio de sus 3 medidas repetidas. Una tarjeta por hoja, ordenadas de mayor a menor severidad:

```
🔴 Riesgo alto

Roya_27_07, Bourbon, hoja R1

Severidad estimada: 77 % respecto a una hoja sana de referencia. Inspeccionar la planta
cuanto antes y evaluar manejo o tratamiento contra la roya.

Índices (promedio de la hoja · 7/7 comparables):
NDVI      0.583   (sana 0.535)
PRI      -0.059   (sana -0.034)
PSRI      0.019   (sana -0.002)     <- en negrita
CARI     76.466   (sana 86.624)
RCI       0.022   (sana 0.031)      <- en negrita
EDI       0.280   (sana 0.336)      <- en negrita
FSR       0.583   (sana 0.535)
```

Un índice va **en negrita** cuando está *en rango de alerta*: su valor normalizado (sección 3) llega a **0,66**, es decir, está a dos tercios o más del camino entre la referencia sana y la referencia con roya de su especie. Es el mismo umbral que define "riesgo alto" para la hoja completa, así que la negrita responde a "¿qué índices están empujando este score hacia arriba?".

La nota de "referencia estimada" vuelve a poder aparecer desde el 2026-09-11 (hojas de Canefora o Cuscatleco, ver arriba); el conteo `n/8` indica cuántos índices se pudieron comparar contra sus dos anclas.

Telegram no acepta mensajes de más de 4.096 caracteres, así que la notificación se reparte en varios mensajes sin partir ninguna tarjeta por la mitad (`pack_messages()`).

## 7. Qué significa este número — y qué no

No es un diagnóstico de laboratorio. Es una medida relativa: qué tan parecido es el espectro de la hoja al de una hoja con roya confirmada de esa especie, frente al de una hoja sana de referencia.

Bourbon y Pacamara tienen ancla enferma propia, así que su score no depende de ninguna referencia estimada. Canefora y Cuscatleco sí dependen de una referencia estimada (no tienen hojas con roya propias): su número es una aproximación razonable pero menos ajustada, y la app lo marca como tal ("referencia estimada" en Telegram).

Donde más aporta es en hojas maduras (M) de estado desconocido, que es el caso real de interés. Una hoja tierna va a dar un score cercano a 0% casi por definición — es su propia referencia sana — y una con roya confirmada va a dar cercano a 100% por la misma razón.

## 8. Limitación conocida

`FSR` usa hoy las mismas bandas que NDVI (ver `ESTADO_PROYECTO.md`, sección 7), así que en la práctica el score combina 6 índices con información distinta más uno duplicado. No invalida el cálculo — la mediana diluye el efecto de la duplicación — pero si más adelante se definen bandas propias para FSR en `config.py`, el score va a tener algo más de información real sin cambiar nada de esta lógica.

## 9. Rangos observados vs. rangos "de literatura"

Los valores de los índices en tu dataset **no siempre coinciden** con los rangos que aparecen en blogs genéricos ("NDVI 0 a 1", etc.). Eso no es un bug: son consecuencia esperada de cómo se toman las mediciones.

### 9.1 Rangos observados (todo el dataset filtrado)

Recalculado el **2026-08-03** sobre los **480 espectros** del dashboard de esa fecha (solo Bourbon + Pacamara, con Canefora/Cuscatleco todavía excluidas). **Desactualizada desde el 2026-09-11**: el dataset ahora tiene 1618 espectros post-filtro (4 especies + 5 campañas nuevas, ver `ESTADO_PROYECTO.md` sección 5) y esta tabla no se recalculó todavía. Los rangos de abajo pueden no reflejar el dataset actual — recalcular antes de citarlos en el paper.

| Índice | Min observado | Mediana | Max observado | Rango típico literatura |
|---|---:|---:|---:|---|
| NDVI | +0.357 | +0.604 | +0.962 | -1 a +1; vegetación sana canopy 0.6–0.9 |
| PRI  | -0.192 | -0.033 | -0.007 | -0.2 a +0.2 típico; muy negativo = estrés severo |
| PSRI | -0.067 | +0.009 | +0.138 | ~-0.05 a +0.2 (Merzlyak 1999) |
| RCI  | +0.004 | +0.018 | +0.517 | **no acotado**; depende de la escala |
| EDI  | +0.082 | +0.371 | +0.729 | 0.2–0.9 (RENDVI/NDVI705, Gitelson & Merzlyak 1994) |
| FSR  | idéntico a NDVI (mismas bandas) | | | |
| NDRE | +0.038 | +0.173 | +0.440 | ~0 a 0.6 a nivel hoja |
| mNDVI705 | +0.098 | +0.571 | +1.021 | 0 a ~1; puede pasar de 1 si el término -2·R445 achica el denominador |

**Discrepancia pendiente de explicar.** Los extremos de la tabla vieja no se reproducen, y **la exclusión de especies no lo explica**: se verificó el 2026-08-03 recorriendo los 948 espectros del dataset **crudo** (`_discover_records()`, sin ningún filtro) y el máximo de RCI en todo el conjunto es **+0.517** (una hoja Bourbon), no el +23.3 que decía la tabla; el PRI más negativo es **-0.192** (Pacamara con roya), no -0.42. Ambos extremos vienen de especies que siguen en el dataset, así que los números viejos tuvieron que salir de una versión anterior del pipeline —antes de alguna corrección de fórmula o de suavizado—, no de las hojas que se quitaron. Conviene no citar los valores viejos en ningún lado hasta entender de dónde salieron.

### 9.2 Por qué los valores "se salen"

1. **Escala de reflectancia SpectraSuite = 0–100 (%), no 0–1.** Los índices normalizados por suma/diferencia (NDVI, PRI, PSRI, EDI, NDRE) son invariantes a escala y quedan en sus rangos esperados. **RCI no se normaliza** y escala con la magnitud de la reflectancia (es una diferencia de recíprocos, `1/R510 − 1/R550`), así que su valor absoluto no es comparable con el "0 a 1" de un blog genérico y solo tiene sentido leerlo de forma relativa. Lo mismo aplicaba a CARI, eliminado el 2026-08-02.

2. **Medición a nivel hoja vs. canopy/satélite.** La mayoría de rangos citados en literatura no académica vienen de datos satelitales o de canopy. A nivel hoja individual con espectrómetro de contacto:
   - NDVI llega más arriba (hasta ~0.95) por reflectancia NIR muy alta en tejido sano.
   - PRI puede bajar mucho más (hoja aislada con estrés severo puede llegar a -0.4).
   - RCI usa bandas puras sin efecto de LAI ni suelo, por lo que la magnitud absoluta pierde sentido "de referencia" y solo interesa la comparación relativa Sana ↔ Con roya.

3. **R510 pequeño dispara RCI** por el término `1/R510`. Es el mecanismo por el que RCI tiene una cola larga hacia arriba: la mediana es +0.018 pero el máximo llega a +0.517, un orden de magnitud y medio más. No es artefacto, es la forma del índice.

4. **PRI negativo en hojas con roya**: los valores más negativos del dataset (hasta -0.192) son todos de hojas Pacamara Con roya, donde R531 queda bastante por debajo de R570 — coherente con el estrés fotosintético severo que causa el hongo. Verificado el 2026-08-03.

### 9.3 Implicación para el score de severidad

Ninguno de estos "sale-de-rango" invalida el score de severidad. El pipeline **no compara los índices contra rangos absolutos de literatura** — usa dos anclas empíricas (sana = hoja tierna de la misma especie; enferma = hoja Con roya de la misma especie) y normaliza cada índice entre ellas (ver sección 3). Es una comparación **relativa a los propios datos**, por lo que la escala del SpectraSuite o el rango absoluto del índice son irrelevantes.

**Consejo para presentar los índices en la UI:** si en algún momento se agregan bandas de referencia "normal" en las páginas de índices, calcularlas empíricamente desde el propio dataset (p5–p95 por especie/estado) en vez de tomarlas de blogs. Para CARI y RCI directamente no mostrar banda "normal" y limitarse a comparación relativa Sana ↔ Con roya.

### 9.4 Fuentes

- NDVI: [USGS Remote Sensing Phenology](https://www.usgs.gov/special-topics/remote-sensing-phenology/science/ndvi-foundation-remote-sensing-phenology), [EOS FAQ](https://eos.com/blog/ndvi-faq-all-you-need-to-know-about-ndvi/)
- PRI: [Wikipedia PRI](https://en.wikipedia.org/wiki/Photochemical_Reflectance_Index), [Wong et al. 2015 (New Phytologist)](https://nph.onlinelibrary.wiley.com/doi/10.1111/nph.13159)
- PSRI: [Frontiers in Plant Science — wheat senescence](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2019.01749/full)
- CARI: [Living Textbook ITC](https://ltb.itc.utwente.nl/508/concept/98924), [Space4Water — MCARI](https://www.space4water.org/taxonomy/term/1320)
- RENDVI/EDI: [MicaSense Knowledge Base](https://support.micasense.com/hc/en-us/articles/227837307-Overview-of-Agricultural-Indices)
- Índices para roya en trigo: [Precision Agriculture, Springer](https://link.springer.com/article/10.1007/s11119-008-9100-2)
- Roya del café con Sentinel-2: [ResearchGate](https://www.researchgate.net/publication/329611161)