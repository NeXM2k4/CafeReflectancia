# Cómo se calcula el nivel de riesgo de roya de una hoja

Última actualización: 2026-07-17

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

Canefora y Cuscatleco todavía no tienen hojas con roya confirmada en `data/` — solo Bourbon y Pacamara las tienen. Mientras tanto, esas dos especies usan como ancla enferma el promedio combinado de Bourbon + Pacamara. La app deja esto marcado internamente (`referencia_propia: False`) y el mensaje de Telegram lo aclara con "referencia estimada", para dejar claro que ese número pesa menos que uno con ancla propia. En cuanto Canefora o Cuscatleco tengan sus primeras hojas con roya, la app pasa a usar su propia ancla sin que haya que tocar nada.

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