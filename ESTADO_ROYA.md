# Cómo se calcula el nivel de riesgo de roya de una hoja

Última actualización: 2026-08-01

## 1. Punto de partida: los 7 índices

No hay un índice único que determine si una hoja está sana o enferma. La app parte de los 7 índices espectrales que ya calcula por archivo, en `calcular_indices()` (`src/processing.py`):

| Índice | Qué mide |
|---|---|
| NDVI | Vigor / verdor general (clorofila vs. infrarrojo cercano) |
| PRI | Eficiencia fotosintética / estrés |
| PSRI | Senescencia (degradación del tejido) |
| CARI | Concentración relativa de clorofila |
| RCI | Carotenoides asociados a estrés por roya |
| EDI | Corrimiento del borde rojo (detección temprana) |
| FSR | Estrés foliar (por ahora usa las mismas bandas que NDVI, ver la limitación al final) |

Un índice por sí solo (NDVI = 0.62, por ejemplo) no dice nada de sano o enfermo. Necesita algo con qué compararse — de ahí el siguiente paso.

## 2. Las dos referencias: sano y enfermo

Para saber si un valor está "cerca de sano" o "cerca de enfermo", la app necesita dos anclas por índice y por especie, calculadas a partir de lo que ya hay en `data/` (`_severity_baselines()`, `app.py`):

- **Ancla sana (0):** promedio del índice entre todas las hojas tiernas (T) de esa especie. La roya tarda en manifestarse, así que una hoja recién formada es la referencia sana más confiable disponible, aunque la planta ya tenga hojas con roya cerca.
- **Ancla enferma (1):** promedio del índice entre las hojas con roya confirmada (archivos que empiezan con `R`).

Canefora y Cuscatleco todavía no tienen hojas con roya confirmada en `data/` — solo Bourbon y Pacamara las tienen (campañas Roya_15_07, Roya_21_07 y Roya_27_07 para Bourbon; Roya_15_07 y Roya_21_07 para Pacamara). Mientras tanto, esas dos especies usan como ancla enferma el promedio combinado de Bourbon + Pacamara. La app deja esto marcado internamente (`referencia_propia: False`) y el mensaje de Telegram lo aclara con "referencia estimada", para dejar claro que ese número pesa menos que uno con ancla propia. En cuanto Canefora o Cuscatleco tengan sus primeras hojas con roya, la app pasa a usar su propia ancla sin que haya que tocar nada.

**Nota importante (2026-07-31):** las anclas se calculan sobre el dataset que devuelve `get_dataset()`, que ya excluye Pacamara "No susceptible". Es decir, todas las hojas Pacamara que participan en las anclas son de la variedad Susceptible — coherente con el objetivo del proyecto de analizar plantas susceptibles a roya.

## 3. Normalizar cada índice

Con las dos anclas de un índice y el valor en la hoja nueva, se aplica una regla de tres (`severity_score()`, `src/processing.py`):

```
normalizado = (valor_hoja − ancla_sana) / (ancla_enferma − ancla_sana)
```

Un valor igual al ancla sana da 0; igual al ancla enferma da 1; en medio, algo intermedio. El resultado se recorta entre 0 y 1 por si la hoja nueva queda más extrema que las propias referencias.

Esto se repite para cada uno de los 7 índices, pero solo con los que tengan datos válidos: si un índice no se pudo calcular para esa hoja, o su especie no tiene diferencia entre ancla sana y enferma, simplemente queda fuera del cálculo.

## 4. De 7 números a uno solo

Con hasta 7 valores normalizados (escala 0–1), se combinan usando la mediana, no el promedio:

```
score_final = mediana(normalizado_NDVI, normalizado_PRI, normalizado_PSRI, ...)
```

La mediana se prefiere porque un solo índice fuera de rango (por ruido de medición, por ejemplo) puede arrastrar un promedio hacia un extremo; la mediana lo ignora y refleja mejor el consenso entre índices.

La app también guarda cuántos de los 7 índices se pudieron usar (`n_indices`), y eso aparece en Telegram como `(6/7 índices)`, para que se sepa qué tan respaldado está el número.

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

`src/notifier.py` (`format_severity_summary()` y `format_severity_detail()`) traduce el score a algo legible para alguien sin formación técnica:

| Score | Etiqueta |
|---|---|
| < 33% | 🟢 riesgo bajo |
| 33%–66% | 🟡 riesgo medio |
| > 66% | 🔴 riesgo alto |

El mensaje trae el promedio por especie de las hojas nuevas detectadas, y el detalle hoja por hoja (por ejemplo: "Bourbon hoja M1, punto 2: 42% 🟡 riesgo medio (6/7 índices)"), con la nota de "referencia estimada" cuando aplica.

## 7. Qué significa este número — y qué no

No es un diagnóstico de laboratorio. Es una medida relativa: qué tan parecido es el espectro de la hoja al de una hoja con roya confirmada de esa especie, frente al de una hoja sana de referencia.

Es más confiable en especies con ancla enferma propia (hoy, Bourbon y Pacamara). En Canefora y Cuscatleco, con referencia estimada, el número es una aproximación razonable pero menos ajustada a la especie.

Donde más aporta es en hojas maduras (M) de estado desconocido, que es el caso real de interés. Una hoja tierna va a dar un score cercano a 0% casi por definición — es su propia referencia sana — y una con roya confirmada va a dar cercano a 100% por la misma razón.

## 8. Limitación conocida

`FSR` usa hoy las mismas bandas que NDVI (ver `ESTADO_PROYECTO.md`, sección 7), así que en la práctica el score combina 6 índices con información distinta más uno duplicado. No invalida el cálculo — la mediana diluye el efecto de la duplicación — pero si más adelante se definen bandas propias para FSR en `config.py`, el score va a tener algo más de información real sin cambiar nada de esta lógica.

## 9. Rangos observados vs. rangos "de literatura"

Los valores de los índices en tu dataset **no siempre coinciden** con los rangos que aparecen en blogs genéricos ("NDVI 0 a 1", "CARI 0 a 1", etc.). Eso no es un bug: son consecuencia esperada de cómo se toman las mediciones. Verificado el 2026-07-31 sobre 828 espectros (dataset del dashboard, post-filtro).

### 9.1 Rangos observados (todo el dataset filtrado)

| Índice | Min observado | Mediana | Max observado | Rango típico literatura |
|---|---:|---:|---:|---|
| NDVI | +0.35 | +0.62 | +0.99 | -1 a +1; vegetación sana canopy 0.6–0.9 |
| PRI  | -0.42 | -0.03 | -0.007 | -0.2 a +0.2 típico; muy negativo = estrés severo |
| PSRI | -0.07 | +0.006 | +0.14 | ~-0.05 a +0.2 (Merzlyak 1999) |
| CARI | +11 | +68 | +432 | **no acotado**; depende de la escala de reflectancia |
| RCI  | +0.004 | +0.017 | +23.3 | **no acotado**; depende de la escala |
| EDI  | +0.08 | +0.38 | +0.74 | 0.2–0.9 (RENDVI/NDVI705, Gitelson & Merzlyak 1994) |
| FSR  | idéntico a NDVI (mismas bandas) |

### 9.2 Por qué los valores "se salen"

1. **Escala de reflectancia SpectraSuite = 0–100 (%), no 0–1.** Los índices normalizados por suma/diferencia (NDVI, PRI, PSRI, EDI) son invariantes a escala y quedan en sus rangos esperados. Los que **no se normalizan** (CARI, RCI) escalan con la magnitud de la reflectancia — por eso CARI da valores en el rango 10–400 y RCI puede llegar a 20+, en vez de los "0 a 1" de un blog genérico.

2. **Medición a nivel hoja vs. canopy/satélite.** La mayoría de rangos citados en literatura no académica vienen de datos satelitales o de canopy. A nivel hoja individual con espectrómetro de contacto:
   - NDVI llega más arriba (hasta ~0.95) por reflectancia NIR muy alta en tejido sano.
   - PRI puede bajar mucho más (hoja aislada con estrés severo puede llegar a -0.4).
   - CARI y RCI son bandas puras sin efecto de LAI ni suelo, por lo que la magnitud absoluta pierde sentido "de referencia" y solo interesa la comparación relativa Sana ↔ Con roya.

3. **R670 muy pequeño en hojas sanas** (fondo de absorción de clorofila) hace que ratios tipo R700/R670 crezcan a 40–50×, disparando CARI a valores altos incluso sin patología.

4. **R510 muy pequeño en algunos parches con roya avanzada** dispara RCI por el término `1/R510`; los outliers con RCI = 20+ vienen de hojas Pacamara con R510 ≈ 0.04 (real, no artefacto — corresponden a tejido con roya severa donde la reflectancia en esa banda cae mucho).

5. **PRI extremos (-0.42)** aparecen en hojas Con roya donde R531 (≈3) es mucho menor que R570 (≈8) — coherente con el estrés fotosintético severo que causa el hongo.

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