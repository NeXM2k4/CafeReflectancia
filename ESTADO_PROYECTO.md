# Estado del Proyecto — Reflectancia Foliar / Detección de Roya

Última actualización: 2026-07-17

Este documento resume qué es el proyecto, cómo está construido, qué se hizo en la sesión de trabajo hasta ahora, y qué queda pendiente. El objetivo es que cualquiera (vos en una sesión futura, u otra persona) pueda retomarlo sin tener que releer todo el historial de conversación.

## 1. Qué es este proyecto

App web en **Streamlit (Python puro)** para automatizar el análisis de datos de reflectancia foliar tomados con un espectrómetro (formato SpectraSuite), con el objetivo de **detectar roya** en hojas de café. Reemplaza el análisis manual que antes se hacía en un notebook (`logic/Reflectancia_PIN1109.ipynb`).

Especies analizadas: **Bourbon, Canefora, Cuscatleco, Pacamara**.

La lógica central es:
1. Escanear automáticamente la carpeta `data/` (recursivamente, tolerando nuevas subcarpetas de campañas de muestreo que se agreguen en el futuro).
2. Parsear cada archivo `.txt` (espectro crudo) y extraer metadatos del nombre de archivo/carpeta (especie, campaña, hoja, punto, medida, estado sanitario, madurez, susceptibilidad de variedad).
3. Suavizar el espectro (Savitzky-Golay) y calcular índices espectrales por archivo.
4. Comparar grupos (ej. Sana vs. Con roya) con estadística automática (normalidad → paramétrico o no paramétrico).
5. Notificar por Telegram cuando hay datos nuevos, con un botón (no hay servidor corriendo en background, es 100% manual/on-demand porque es de uso personal).

## 2. Cómo correr la app

```bash
pip install -r requirements.txt
streamlit run app.py
```

**Importante:** cada vez que se edite código en `src/` o `pages/`, hay que **reiniciar el proceso de Streamlit por completo** (`Ctrl+C` y volver a correr `streamlit run app.py`), no alcanza con guardar el archivo. Ya tuvimos un bug (`KeyError: 'health_status'`) causado por un proceso viejo corriendo con código desactualizado — no era un bug real de código.

Para forzar un re-escaneo de `data/` sin reiniciar el proceso, existe el botón **"🔄 Recargar datos"** en la barra lateral de la página de inicio (limpia `st.cache_data`).

## 3. Estructura del repo

```
app.py                          # pagina de inicio (Home)
pages/
  1_Espectros.py                # curvas de reflectancia individuales + promedio ± SD
  2_Indices_Espectrales.py      # indices espectrales por especie, con agrupamiento dinamico
  3_Comparacion_Especies.py     # comparacion de indices entre las 4 especies
src/
  config.py                     # constantes: rutas, parametros SG, longitudes de onda, colores, labels
  parser.py                     # descubrimiento y parseo de archivos .txt de data/ (el modulo mas importante)
  processing.py                 # suavizado, filtrado, calculo de indices espectrales, promedio de grupo
  stats_utils.py                # pipeline estadistico generico (Shapiro -> ANOVA/Tukey o Kruskal/Dunn)
  state.py                      # tracking de "ultima verificacion" para saber que archivos son nuevos
  notifier.py                   # envio de mensajes a Telegram via Bot API
data/                           # datos crudos (.txt), organizados por carpeta de campana > especie > (subcarpeta opcional)
logic/
  Reflectancia_PIN1109.ipynb    # notebook original (analisis manual) — referencia historica
.streamlit/
  secrets.toml                  # credenciales Telegram (NO versionado, gitignored)
  secrets.toml.example          # plantilla con instrucciones para crear el bot en BotFather
.state/
  last_run.json                 # ultimo set de archivos verificados (para detectar "que hay nuevo")
.gitignore                      # excluye secrets.toml, .state/, __pycache__, .venv/
requirements.txt
```

**Nota:** hay una carpeta `roya/` en la raíz que es un virtualenv de Python (contiene `Lib/site-packages/...`). No está en `.gitignore` todavía. Si en algún momento se inicializa un repo git en este proyecto (actualmente **no** es un repo git), hay que agregar `roya/` al `.gitignore` antes del primer commit para no versionar el entorno virtual completo.

## 4. Convención de nombres de archivos y carpetas (clave para entender todo el parser)

Esto fue lo más difícil de reverse-engineerear en la sesión, y quedó **confirmado y documentado** así:

### Carpeta de campaña
Patrón genérico: `{prefijo}_dd_mm_yyyy` (cualquier prefijo, para que campañas futuras se detecten solas). Ejemplos reales:
- `Reflectancia_ISC_C1_29_06_2026` → campaña **C1**, fecha 2026-06-29
- `Reflectancia_ISC_C2_06_07_2026` → campaña **C2**, fecha 2026-07-06
- `roya_15_07_2026` → campaña **Roya**, fecha 2026-07-15 (no tiene código `Cx`, así que se usa el último segmento del prefijo capitalizado)

### Carpeta de especie
Una de: `Bourbon`, `Canefora`, `Cuscatleco`, `Pacamara` (case-insensitive, la carpeta puede estar en minúsculas como en C2).

### Subcarpeta opcional de susceptibilidad (solo vista en Pacamara)
`Susceptible` / `No_susceptible` (con variantes de ortografía toleradas: `suseptibles`, `suceptible`, `no_suceptible`, etc.) — es una propiedad de la **variedad de la planta**, no del estado sanitario actual de la hoja.

### Nombre de archivo
Patrón: `{M|T|R}{n}p{punto}{especie}{medida}`, ejemplo `M1p2bourbon3.txt`

- **M / T / R** (primera letra): **M = hoja madura, T = hoja tierna, R = hoja con roya** (confirmado por el usuario — esto reemplaza la interpretación anterior/incorrecta de que M/T eran "sesiones"). Las hojas con R **no tienen** dato de madurez (son roya, un estado aparte).
- **n** (número después de la letra): identifica la **hoja física** (son 2 hojas por grupo, ej. M1 y M2 son dos hojas maduras distintas, no repeticiones de la misma).
- **p{punto}**: punto de medición sobre la hoja (se miden 3 puntos por hoja: p1, p2, p3).
- **{especie}**: nombre de la especie repetido en el archivo (se descarta al parsear).
- **{medida}** (número final): repetición de la medición en ese mismo punto (se repite 3 veces por punto).

**Diseño real de muestreo confirmado por el usuario:** 2 hojas × 3 puntos × 3 medidas repetidas = 18 mediciones por estado de madurez (Madura o Tierna) por especie por campaña.

- **Estado sanitario** (`health_status`): derivado de la letra M/T/R → `Sana` (si M o T) o `Con roya` (si R). Por ahora solo **Bourbon** y **Pacamara** tienen muestras reales con roya (campaña Roya, 2026-07-15); Canefora y Cuscatleco todavía solo tienen hojas sanas.
- **Susceptibilidad** (`susceptibility`): viene de la subcarpeta si existe; si no, se intenta un fallback por sufijo `NS`/`S` al final del nombre de archivo (solo se busca para Pacamara).

Estos 3 conceptos son **independientes entre sí** y así se tratan en todo el código:
| Campo | Valores | Aplica a |
|---|---|---|
| `leaf_maturity` | Madura / Tierna / None | hojas M o T (no aplica a R) |
| `health_status` | Sana / Con roya | derivado de M,T (=Sana) vs R (=Con roya) |
| `susceptibility` | Susceptible / No susceptible | solo Pacamara (variedad de planta) |

## 5. Estado actual de los datos (`data/`)

574 archivos totales reconocidos (1 archivo con nombre no reconocido, se excluye del agrupamiento pero aparece en un expander de "no reconocidos" en la Home).

| Especie | C1 | C2 | Roya | Total |
|---|---|---|---|---|
| Bourbon | 36 | 36 | 66 | 138 |
| Canefora | 36 | 36 | — | 72 |
| Cuscatleco | 36 | 35 | 36 | 107 |
| Pacamara | 72 | 73 | 112 | 257 |

Estado sanitario (`health_status`):
- Bourbon: 108 Sana, 30 Con roya
- Canefora: 72 Sana (sin roya aún)
- Cuscatleco: 107 Sana (sin roya aún)
- Pacamara: 216 Sana, 40 Con roya

## 6. Módulos de código — qué hace cada uno

### `src/config.py`
Todas las constantes centralizadas: ruta de datos, parámetros de suavizado Savitzky-Golay (ventana 41, orden 2), rango útil de longitud de onda (420–1000 nm), diccionarios de normalización de nombres (especie, susceptibilidad, madurez), longitudes de onda de cada índice espectral, paleta de colores, colores estables por grupo, alfa de significancia (0.05).

### `src/parser.py`
El módulo más importante. Responsable de:
- `get_dataset()`: punto de entrada público. Calcula un "fingerprint" liviano de `data/` (ruta relativa + mtime + tamaño de cada `.txt`) y llama a `scan_dataset()`, que está cacheada con `@st.cache_data` usando ese fingerprint como key — así el cache se invalida solo cuando cambian los archivos en disco (se agregan/editan mediciones), sin necesitar botón manual (aunque el botón "Recargar datos" también existe por si acaso).
- `_discover_records()`: recorre `data/` recursivamente, identifica campaña (regex genérica `{prefijo}_dd_mm_yyyy`), especie, subcarpeta de susceptibilidad, y parsea el nombre de archivo con `_parse_filename()`.
- `_parse_filename()`: aplica el regex `^([MTR])(\d+)p(\d+)` + sufijo de repetición, deriva `leaf_maturity`, `has_roya`, y (solo para Pacamara) el sufijo de susceptibilidad NS/S como fallback.
- `FileRecord`: dataclass con todos los campos por archivo (incluye `session`, `session_num`, `point`, `repetition`, `leaf_maturity`, `has_roya`, `health_status`, `susceptibility`, etc.)
- `read_spectrasuite()` / `load_spectrum()`: parsea el archivo `.txt` crudo (encoding latin-1, busca el marcador "Comienza Data"/"Begin Spectral", extrae pares longitud de onda/reflectancia), cacheado por archivo+mtime.

### `src/processing.py`
- `smooth()`: Savitzky-Golay sobre la reflectancia cruda.
- `filter_range()`: recorta al rango útil 420–1000 nm.
- `prepare_spectrum()`: pipeline completo (suavizar + recortar).
- `reflectance_at()`: reflectancia interpolada más cercana a una longitud de onda dada (tolerancia 5 nm).
- `calcular_indices()`: calcula los 7 índices espectrales actuales (ver sección 7).
- `average_group()`: interpola varios espectros a una grilla común y calcula media ± desviación estándar (para el gráfico de "Promedio ± SD" en la página de Espectros).
- `severity_score()`: normaliza los 7 índices de un archivo a un score de severidad de roya 0 (sana) – 1 (enferma), usando anclas por especie calculadas en `app.py` (ver sección 9).

### `src/stats_utils.py`
`compare_groups(groups, alpha=0.05)`: pipeline estadístico genérico y reusado en las 2 páginas de índices:
1. Shapiro-Wilk por grupo (normalidad).
2. Si todos los grupos son normales → ANOVA + post-hoc Tukey HSD.
3. Si no → Kruskal-Wallis + post-hoc Dunn (corrección Bonferroni).
Devuelve un dict con resumen descriptivo, resultados de Shapiro, nombre del test, estadístico, p-valor, si es significativo, y la tabla post-hoc.

### `src/state.py` y `src/notifier.py` (feature de Telegram)
- `state.py`: guarda en `.state/last_run.json` el set de archivos (`path|mtime_ns`) vistos en la última verificación manual. Permite calcular qué archivos son "nuevos" sin depender de ningún proceso corriendo en background.
- `notifier.py`: `send_telegram_message()` lee `st.secrets["telegram"]["bot_token"]` y `chat_id"]`, hace un POST a la API de Telegram (`sendMessage`). Confirmado por el usuario que **ya funciona en producción**. También tiene `format_severity_summary()` y `format_severity_detail()`, que arman en texto plano el score de severidad de roya por especie y por hoja (ver sección 9).

Flujo completo (botón "Verificar y analizar nueva data" en Home): compara archivos actuales vs. última verificación → si hay nuevos, arma un resumen (cantidad por especie + cuántos son "Con roya") + el score de severidad de roya por índices → lo manda por Telegram → guarda el nuevo estado como línea base.

## 7. Índices espectrales calculados

Todos se calculan en `calcular_indices()` a partir del espectro ya suavizado, y se muestran en las páginas 2 y 3:

| Índice | Fórmula | Qué mide |
|---|---|---|
| **NDVI** | (R800 − R670) / (R800 + R670) | Vigor/verdor general de la hoja (clorofila vs. NIR) |
| **PRI** | (R531 − R570) / (R531 + R570) | Eficiencia fotosintética / estrés (ciclo de xantofilas) |
| **PSRI** | (R678 − R500) / R750 | Senescencia — sube cuando el tejido se degrada |
| **CARI** | ver nota de bug abajo | Concentración relativa de clorofila, corregida por línea base 550–700 nm |
| **RCI** (nuevo) | 1/R510 − 1/R550 | "Rust Carotenoid Index", adaptado del índice de carotenoides de Gitelson |
| **EDI** (nuevo) | (R750 − R705) / (R750 + R705) | "Early Detection Index", shift del red-edge (formulación tipo PRI de Gamon) |
| **FSR** (nuevo) | (R800 − R670) / (R800 + R670) | "Foliar Stress Ratio" — **usa las mismas bandas que NDVI** (no se especificaron bandas distintas), por lo que da un valor **idéntico** a NDVI. Si se quieren bandas NIR/Rojo distintas para que aporte información diferente, hay que definirlas en `WL_FSR` en `config.py`. |

**Bug corregido en CARI:** el notebook original usaba la reflectancia en 670 nm (`R670`) en el numerador de la fórmula de la recta base, cuando la fórmula correcta usa la **longitud de onda** 670 (constante), no el valor de reflectancia ahí. Ya está corregido en `processing.py` (con comentario explicando la diferencia). Esto significa que los valores de CARI de la app **no van a coincidir exactamente** con los del notebook viejo — es intencional, es la corrección del bug.

Validado que NDVI, PRI y PSRI reproducen exactamente los valores del notebook original (confirma que el resto del pipeline —parseo, suavizado, lectura de reflectancia— está bien).

## 8. Las 3 páginas de la app

### `app.py` (Home)
- Botón "Recargar datos" (limpia cache).
- Botón "Verificar y analizar nueva data" → dispara notificación Telegram si hay archivos nuevos.
- Métricas generales (archivos, especies, campañas, no reconocidos).
- Tabla pivote: archivos por especie y campaña.
- Tabla pivote: estado sanitario (Sana/Con roya) por especie.
- Tabla pivote: susceptibilidad de variedad por especie (solo Pacamara tiene datos).
- Detalle de campañas detectadas.
- Expander de archivos no reconocidos.

### `pages/1_Espectros.py`
Curvas de reflectancia individuales + curva promedio ± 1 SD. Filtros en sidebar: especie → campaña → estado sanitario (si aplica) → susceptibilidad (si aplica) → madurez de hoja (si aplica) → punto. Parámetros de suavizado ajustables.

### `pages/2_Indices_Espectrales.py`
La página más rica. Filtros: especie → campaña → dimensión de agrupamiento (radio button dinámico: Estado sanitario / Susceptibilidad / Madurez — solo aparecen las dimensiones que tienen ≥2 grupos con los filtros actuales). Muestra:
1. **Detalle de cada medición (sin promediar)** — nueva tabla agregada en esta sesión: una fila por archivo/medida individual con columnas Especie, Campaña, Estado sanitario, Susceptibilidad, Madurez, **Hoja** (ej. "M1", "T2"), Punto, Medida, Archivo, + los 7 índices. Con botón de descarga CSV.
2. **Tabla de índices por punto y hoja (promedio de las 3 medidas repetidas)** — el promedio correcto: agrupa por (Especie, Campaña, Estado sanitario, Susceptibilidad, Madurez, **Hoja**, Punto), promediando *solo* las 3 repeticiones técnicas de ese punto en esa hoja específica. **Importante:** antes de la corrección de esta sesión, el agrupamiento no incluía "Hoja" y mezclaba M1 con M2 (dos hojas físicamente distintas) en un solo promedio — ya está corregido.
3. Boxplots de distribución por grupo (uno por índice).
4. Estadística automática (Shapiro → ANOVA/Tukey o Kruskal/Dunn) por índice, sobre la tabla promediada por punto y hoja.

### `pages/3_Comparacion_Especies.py`
Compara los 7 índices entre las 4 especies (mínimo 2 especies seleccionadas). Mismos filtros de campaña y estado sanitario. Mismo fix de "Hoja" aplicado al agrupamiento. Tabla de promedios, boxplots por especie, estadística automática entre especies.

## 9. Score de severidad de roya en la alerta de Telegram

Implementado a pedido de Samuel (vía WhatsApp, 2026-07-17): la alerta de Telegram ahora, además de contar archivos nuevos por especie, incluye un **score de 0% (sana) a 100% (enferma)** calculado a partir de los índices espectrales, para que un trabajador de campo sepa de un vistazo qué tan comprometida está una hoja.

**Cómo se calibra (decidido con el usuario en esta sesión):**
- Se usan los **7 índices espectrales** existentes (NDVI, PRI, PSRI, CARI, RCI, EDI, FSR) — no solo uno, para que el resultado sea más robusto.
- Por cada índice y especie se calculan dos **anclas** a partir de los datos ya existentes en `data/`:
  - **Ancla sana (0)** = promedio del índice en hojas **Tierna** (T). Razonamiento del usuario: la roya todavía no tuvo tiempo de manifestarse en tejido nuevo, así que la hoja tierna es la referencia sana más confiable disponible.
  - **Ancla enferma (1)** = promedio del índice en hojas **Con roya** (R) de esa misma especie.
  - **Bourbon y Pacamara** ya tienen su propia ancla enferma (son las únicas con muestras de roya reales). **Canefora y Cuscatleco** todavía no, así que usan como respaldo el promedio combinado de Bourbon + Pacamara — el código marca estos casos como `referencia_propia: False` y el mensaje de Telegram lo aclara con una nota ("referencia estimada").
- Cada índice de un archivo nuevo se normaliza por separado entre sus dos anclas (clip a 0–1), y el score final del archivo es la **mediana** de los índices normalizados (más robusto ante un índice atípico que el promedio). El mensaje también reporta cuántos de los 7 índices se pudieron usar (`n/7`).
- El mensaje de Telegram muestra el **promedio de severidad por especie** y el **detalle por hoja individual** (ambos, no solo uno — decidido con el usuario), con etiquetas en lenguaje simple (🟢 riesgo bajo / 🟡 riesgo medio / 🔴 riesgo alto) en vez de jerga técnica, pensado para que lo entienda un agricultor.

**Dónde está el código:**
- `src/processing.py` → `severity_score(values, baseline)`: función pura, normaliza y agrega.
- `app.py` → `_severity_baselines(dataset)` (cacheada con `@st.cache_data`): calcula las anclas sana/enferma por especie recorriendo todo `data/`; y el bloque dentro del botón "Verificar y analizar nueva data" que calcula el score de cada archivo nuevo y arma `severidad_detalle` / `severidad_por_especie`.
- `src/notifier.py` → `format_severity_summary()` y `format_severity_detail()`: arman las líneas de texto para el mensaje de Telegram.

**Limitación conocida:** como `FSR` usa exactamente las mismas bandas que `NDVI` (ver sección 7, todavía no se le definieron bandas propias), en la práctica el score de severidad usa 6 índices con información distinta más uno duplicado. No afecta la validez del score (la mediana lo diluye), pero si en el futuro se definen bandas propias para `FSR`, el score va a aportar información algo más rica.

## 10. Decisiones de diseño importantes (y el porqué)

- **Sin servidor en background para Telegram**: el usuario eligió explícitamente un botón dentro de la app en vez de un proceso corriendo 24/7, porque es de uso personal y "tener un servidor es demasiado".
- **Detección de campañas 100% genérica** (regex `{prefijo}_dd_mm_yyyy`): para que cuando se agreguen carpetas de campañas futuras, la app las reconozca solas sin tocar código.
- **Cache de Streamlit basado en fingerprint de archivos**, no en un botón manual obligatorio: la app se auto-actualiza cuando se agregan mediciones nuevas a `data/`, tal como pidió el usuario desde el principio ("la idea es analizar estas y otras posibles cada vez que se suban nuevas mediciones").
- **`leaf_maturity`, `health_status` y `susceptibility` son campos separados**, no uno solo: reflejan 3 conceptos biológicos distintos (madurez de la hoja, estado sanitario actual, variedad de la planta) que pueden variar independientemente.
- **Agrupamiento por "Hoja"** (no solo por punto): las 2 hojas de cada grupo (M1/M2, T1/T2) son unidades biológicas distintas y no deben promediarse entre sí — solo se promedian las 3 medidas repetidas dentro del mismo punto de la misma hoja.

## 11. Bugs corregidos en esta sesión

1. **`use_container_width` deprecado** → reemplazado por `width='stretch'` en todo el proyecto.
2. **`or` con corto-circuito en `parser.py`**: `susceptibility = susceptibility or meta.pop(...)` nunca hacía el `.pop()` cuando `susceptibility` ya era verdadero, dejando una key sobrante que rompía `FileRecord(**meta)`. Corregido haciendo el `.pop()` incondicional antes del `or`.
3. **`KeyError: 'health_status'`** reportado por el usuario en un run real de Streamlit — no era un bug de código (validado exhaustivamente), sino un **proceso de Streamlit viejo corriendo con módulos no recargados**. Se resolvió reiniciando el servidor.
4. **Bug de fórmula CARI** (ver sección 7): usaba reflectancia en vez de longitud de onda en el numerador. Corregido, documentado con comentario en el código.
5. **Bug de agrupamiento/promediado** (ver sección 8, página 2 y 3): mezclaba hojas distintas (M1 con M2) en un solo promedio por no incluir "Hoja" como clave de agrupamiento. Corregido agregando `Hoja` = `{session}{session_num}` a las claves de agrupamiento en ambas páginas, y se agregó además una tabla de detalle sin promediar para poder auditar cada medición individual.

## 12. Pendientes / posibles próximos pasos

- **Definir si `FSR` debe usar bandas distintas a NDVI** (actualmente son las mismas 800/670, dando el mismo valor numérico que NDVI — puede que el usuario quiera otras longitudes de onda para que aporte información nueva).
- **Etiquetado final de enfermedad**: el usuario mencionó en su momento que se vería más adelante ("luego podemos ver lo de las etiquetas finales") — por ahora el etiquetado real que existe es `health_status` (Sana/Con roya) derivado del prefijo R del nombre de archivo, ya incorporado. Confirmar si esto es lo que se consideraba "etiquetado final" o si falta algo más granular (ej. severidad/grado de roya).
- **Canefora y Cuscatleco todavía no tienen muestras con roya real** — cuando se agreguen, la app las va a reconocer automáticamente sin cambios de código (mismo patrón `R{n}p{punto}`), y el score de severidad (sección 9) va a empezar a usar su propia ancla enferma en vez del respaldo combinado de Bourbon+Pacamara, automáticamente.
- Si se decide inicializar git en el proyecto, agregar `roya/` (virtualenv en la raíz) al `.gitignore` antes del primer commit.
- Considerar si la comparación estadística de "Sana vs Con roya" debería hacerse a nivel de **hoja** (promediando los 3 puntos de cada hoja primero) en vez de a nivel de **punto**, para evitar pseudo-réplicas (puntos de la misma hoja no son observaciones totalmente independientes). No se tocó en esta sesión, se dejó el comportamiento existente (comparación a nivel de punto-hoja).

## 13. Cómo retomar rápido

1. `streamlit run app.py` (reiniciar si ya estaba corriendo).
2. Revisar la sección 12 (pendientes) para saber por dónde seguir.
3. Si se agregan campañas nuevas a `data/`, no hace falta tocar código — la app las detecta sola con el patrón `{prefijo}_dd_mm_yyyy` en el nombre de carpeta y `{M|T|R}{n}p{punto}{especie}{medida}` en el nombre de archivo.
