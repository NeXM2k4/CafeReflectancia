# Estado del Proyecto — Reflectancia Foliar / Detección de Roya

Última actualización: 2026-09-27

> ⚠️ **Aviso (2026-09-28):** este documento describe la app **antes** de la sesión de pulido de
> `plan_mejora_app.md` (rama `mejora-app`). Muchas secciones de abajo ya no son exactas —
> páginas renombradas (`4_Severidad_Roya.py` → `4_Estado_Hojas.py`), FSR quitado de las vistas
> activas, la escala de riesgo pasó de 11 a 4 clases, las anclas de severidad se recalculan
> distinto (por fecha, no por archivo), Telegram pasó a español, y hay un módulo nuevo
> (`src/indices.py`) que centraliza los cálculos que antes describía este documento repartidos
> por página. **La referencia vigente de esa sesión es `PROGRESO_MEJORA_APP.md`** (qué se hizo,
> por qué, y qué quedó pendiente). Este archivo se reescribirá una vez cerrada esa fase
> (`plan_mejora_app.md` F5.3: separar bitácora histórica de referencia vigente); hasta entonces,
> tratá las secciones 6-9 y 13-14 como historia, no como el comportamiento actual del código.

Este documento resume qué es el proyecto, cómo está construido, qué se hizo en la sesión de trabajo hasta ahora, y qué queda pendiente. El objetivo es que cualquiera (vos en una sesión futura, u otra persona) pueda retomarlo sin tener que releer todo el historial de conversación.

## 1. Qué es este proyecto

App web en **Streamlit (Python puro)** para automatizar el análisis de datos de reflectancia foliar tomados con un espectrómetro (formato SpectraSuite), con el objetivo de **detectar roya** en hojas de café. Reemplaza el análisis manual que antes se hacía en un notebook (`logic/Reflectancia_PIN1109.ipynb`).

El dashboard muestra las 4 especies del dataset (Bourbon, Canefora, Cuscatleco, Pacamara), pero
**Bourbon y Pacamara** son las únicas **susceptibles a la roya** y las únicas con muestras reales
de roya confirmada — son el foco real del análisis de detección. Canefora y Cuscatleco aportan
solo hojas sanas, útiles para comparar el cultivar pero no para el score de severidad.

**Cambio del 2026-08-03, revertido el 2026-09-11:** entre esas fechas, **Canefora** y
**Cuscatleco** estuvieron fuera del dashboard y de las figuras del paper por no tener permiso de
uso de esos datos (`EXCLUDED_SPECIES` en `src/config.py`). El usuario pidió el 2026-09-11 volver
a mostrar las 4 especies, así que esa tupla está **vacía** de nuevo y las 4 especies aparecen en
todo el dashboard. El punto único de reversión sigue siendo `EXCLUDED_SPECIES`: si en el futuro
hay que excluir alguna especie otra vez, basta con agregarla ahí.

**Cambio del 2026-09-11 — nuevas campañas y categoría "hoja vieja":** se agregaron 5 campañas de
muestreo (agosto/septiembre 2026) y una categoría de madurez de hoja nueva, "Vieja" (letra `V`
en el nombre de archivo). Ver sección 4 para la convención de nombres (cambió de forma no trivial
entre campañas) y sección 12 para el pendiente de atribución de especie que dejó esta categoría.

**Cambio del 2026-09-27 — 2 campañas nuevas, sin tocar código:** se agregaron `Campaña_14_09`
(2026-09-14) y `Campaña_21_09` (2026-09-21), con la misma carpeta sin prefijo y el mismo nivel
duplicado (`data/14_09_2026/14_09_2026/...`) que las campañas de agosto/septiembre. El parser las
reconoció sin ajustes: mismos 3 esquemas de nombre para `roya/` y `vieja/`, mismas subcarpetas de
especie/susceptibilidad, **cero archivos nuevos sin reconocer**. Confirmado corriendo
`get_dataset()` directamente. Ver sección 5 para las cifras actualizadas.

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
make_ieee_figures.py            # genera las figuras del paper en figures_ieee/ (ver seccion 13)
figures_ieee/                   # figuras PNG 600 dpi para el paper + README con los captions
pages/
  1_Espectros.py                # curvas de reflectancia individuales + promedio ± SD
  2_Indices_Espectrales.py      # indices espectrales por especie, con agrupamiento dinamico
  3_Comparacion_Especies.py     # comparacion de indices entre las 4 especies
  4_Severidad_Roya.py           # score de severidad 0-100% por hoja/especie/campaña
  5_Evolucion_Temporal.py       # la misma hoja fisica en el tiempo: indices, tendencias, espectro animado (2026-09-27)
src/
  config.py                     # constantes: rutas, parametros SG, longitudes de onda, colores, labels
  parser.py                     # descubrimiento y parseo de archivos .txt de data/ (el modulo mas importante)
  processing.py                 # suavizado, filtrado, calculo de indices espectrales, promedio de grupo
  stats_utils.py                # pipeline estadistico generico (Shapiro -> ANOVA/Tukey o Kruskal/Dunn)
  state.py                      # tracking de "ultima verificacion" para saber que archivos son nuevos
  severity.py                   # anclas sana/enferma por especie + agregacion de severidad por hoja
  temporal.py                   # series por hoja fisica, Δ/Δ*, severidad relativa, tendencias, QC, espectros medios
  ui.py                         # header, CSS global y helpers de presentacion compartidos
  notifier.py                   # armado y envio de los mensajes de Telegram via Bot API
data/                           # datos crudos (.txt), organizados por carpeta de campaña > especie > (subcarpeta opcional)
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

**Nota (actualizada 2026-09-28):** hay una carpeta `roya/` en la raíz que es un virtualenv de Python (contiene `Lib/site-packages/...`). El proyecto **sí es un repo git** desde julio de 2026, y `roya/` **sí está en `.gitignore`** (junto con `.state/`, `.streamlit/secrets.toml`, `__pycache__/`). Esta nota queda como referencia histórica de una duda ya resuelta.

## 4. Convención de nombres de archivos y carpetas (clave para entender todo el parser)

Esto fue lo más difícil de reverse-engineerear en la sesión, y quedó **confirmado y documentado** así:

### Carpeta de campaña
Patrón genérico: `{prefijo}_dd_mm_yyyy` (cualquier prefijo, para que campañas futuras se detecten solas). El `campaign_id` derivado **siempre incluye el sufijo `dd_mm`** para que dos campañas con el mismo prefijo (p. ej. varias campañas `roya_*`) no se colisionen en pivotes/filtros. Ejemplos reales:
- `Reflectancia_ISC_C1_29_06_2026` → campaña **C1_29_06**, fecha 2026-06-29
- `Reflectancia_ISC_C2_06_07_2026` → campaña **C2_06_07**, fecha 2026-07-06
- `roya_15_07_2026` → campaña **Roya_15_07**, fecha 2026-07-15
- `roya_21_07_2026` → campaña **Roya_21_07**, fecha 2026-07-21
- `roya_27_07_2026` → campaña **Roya_27_07**, fecha 2026-07-27

**Variante sin prefijo (agregada 2026-09-11):** las 5 campañas de agosto/septiembre 2026 vinieron
en carpetas nombradas **solo** `dd_mm_yyyy` (sin ningún texto antes), y además cada una está
duplicada un nivel adentro (p. ej. `data/10_08_2026/10_08_2026/bourbon/...`, probablemente un
artefacto de como se comprimió/extrajo cada carpeta). El regex original exigía un prefijo antes
de la fecha y no las reconocía; se agregó `_CAMPAIGN_BARE_RE` en `parser.py` como fallback, y
estas campañas quedan con `campaign_id = Campaña_{dd}_{mm}` (p. ej. **Campaña_10_08**,
fecha 2026-08-10). La carpeta duplicada no rompe nada: `_find_campaign()` recorre cada parte de
la ruta y encuentra la fecha en cualquiera de las dos, así que no hizo falta limpiar el disco.
Campañas nuevas: **Campaña_10_08** (2026-08-10), **Campaña_17_08** (2026-08-17),
**Campaña_24_08** (2026-08-24), **Campaña_31_08** (2026-08-31), **Campaña_07_09** (2026-09-07).

### Carpeta de especie
Una de: `Bourbon`, `Canefora`, `Cuscatleco`, `Pacamara` (case-insensitive, la carpeta puede estar en minúsculas como en C2).

### Subcarpeta opcional de susceptibilidad (solo vista en Pacamara)
`Susceptible` / `No_susceptible` (con variantes de ortografía toleradas: `suseptible`, `suseptibles`, `suceptible`, `no_suceptible`, `no suseptible` con espacio, `no_suseptible`, `no suceptibles` en plural, etc. — ver `SUSCEPTIBILITY_CANONICAL` en `config.py`; las variantes `suseptible` singular y `no suceptibles` plural se agregaron el 2026-09-11 al verlas en las campañas nuevas) — es una propiedad de la **variedad de la planta**, no del estado sanitario actual de la hoja. También se vio una carpeta `roña` (typo de `roya`) anidada bajo `suseptible` en `Campaña_10_08`; no afecta el parseo porque la susceptibilidad se lee un nivel antes.

**Regla de negocio (agregada 2026-07-31):** las hojas Pacamara clasificadas como **"No susceptible"** se filtran en `get_dataset()` y **no aparecen en ninguna página del dashboard** (Home, Espectros, Índices, Comparación, Severidad). El filtro cubre las dos fuentes de etiqueta NS: subcarpeta y sufijo `NS` en el filename (usado en `roya_15_07_2026`). Motivo: el análisis se enfoca en plantas susceptibles a roya; las NS aportan ruido al comparar. Si se necesita el dataset crudo, usar `_discover_records(DATA_DIR)` en lugar de `get_dataset()`.

**Regla de negocio (agregada 2026-08-03, inactiva desde 2026-09-11):** las especies listadas en `EXCLUDED_SPECIES` (`src/config.py`) se filtran en el mismo punto. Se usó para **Canefora y Cuscatleco** por no contar con permisos de uso de sus datos; hoy la tupla está **vacía** (ver sección 1), así que este filtro no excluye nada. Si se necesita excluir una especie de nuevo, así funciona:

- Cualquier especie en `EXCLUDED_SPECIES` no aparece en ninguna página del dashboard ni en ninguna figura de `figures_ieee/`.
- `make_ieee_figures.py` también carga por `get_dataset()`, así que hereda el filtro sin lógica propia: recorre las especies que efectivamente vengan en el dataset y nunca las nombra.
- Los archivos **no se borran de `data/`** y el parser los sigue reconociendo; solo se excluyen al entregar el DataFrame.
- Los mapeos de nombre/color de las 4 especies se conservan en `config.py` y `make_ieee_figures.py` justamente para que excluir/reincluir una especie sea de una línea.

### Nombre de archivo
Patrón: `{M|T|R}{n}p{punto}{especie}{medida}`, ejemplo `M1p2bourbon3.txt`

- **M / T / R** (primera letra): **M = hoja madura, T = hoja tierna, R = hoja con roya** (confirmado por el usuario — esto reemplaza la interpretación anterior/incorrecta de que M/T eran "sesiones"). Las hojas con R **no tienen** dato de madurez (son roya, un estado aparte).
- **n** (número después de la letra): identifica la **hoja física** (son 2 hojas por grupo, ej. M1 y M2 son dos hojas maduras distintas, no repeticiones de la misma).
- **p{punto}**: punto de medición sobre la hoja (se miden 3 puntos por hoja: p1, p2, p3).
- **{especie}**: nombre de la especie repetido en el archivo (se descarta al parsear).
- **{medida}** (número final): repetición de la medición en ese mismo punto (se repite 3 veces por punto).

**Letra `V` = hoja vieja (agregada 2026-09-11):** cuarta categoría de madurez, junto a M/T/R.
Sigue el mismo patrón `V{n}p{punto}{especie}{medida}`. Ver más abajo el problema de atribución
de especie que trae esta categoría en la mayoría de campañas.

**Variantes de nombre sin número de hoja (agregadas 2026-09-11):** desde las campañas de
agosto/septiembre 2026, las carpetas `roya/` y `vieja/` usan 3 esquemas de nombre distintos
según la campaña (probablemente por quién tipeó los archivos, no por diseño):
- Estándar: `R1p1bourbon1.txt` (igual que siempre, se reconocía ya).
- Con la palabra "roya" en vez de la letra `R`: `roya1p1bourbon1.txt` (campaña `Campaña_17_08`;
  el número después de "roya" es el número de hoja, igual que en el estándar). Nunca se vio un
  equivalente `vieja1p1...` con número de hoja explícito.
- **Punto primero, sin número de hoja ni especie**: `p1roya1.txt`, `p1vieja1.txt` (campañas
  `Campaña_07_09`, `Campaña_24_08`, `Campaña_31_08` para roya; mismas tres para vieja excepto
  `Campaña_17_08` que sí especifica especie). El parser asume **hoja única "1"** en este caso,
  igual que la convención ya documentada de una sola hoja `R1` por campaña de roya. La especie
  en estos archivos viene de la carpeta contenedora (`bourbon/roya/`, `pacamara/suceptible/roya/`),
  **excepto** en la carpeta `vieja/`, que no está anidada dentro de ninguna carpeta de especie
  (ver el problema de atribución más abajo).

Las 3 variantes se normalizan en `parser._parse_filename()` (regex `_ROYA_WORD_RE` y
`_POINT_FIRST_RE`) al mismo resultado biológico (`session`, `session_num`, `point`, `repetition`)
que el patrón estándar, así que el resto del pipeline no distingue de dónde vino cada archivo.

**Problema abierto: especie de la "hoja vieja" sin identificar (2026-09-11).** La carpeta
`vieja/` aparece al mismo nivel que las carpetas de especie (`bourbon/`, `canefora/`, etc.), no
adentro de ninguna. Solo en `Campaña_17_08` el nombre de archivo trae la especie explícita
(`v1p1canefora1.txt` → Canefora); en `Campaña_07_09`, `Campaña_24_08` y `Campaña_31_08` los
archivos son `p{punto}vieja{medida}.txt`, **sin especie en ningún lado**. Consultado con el
usuario el 2026-09-11: no sabe a qué especie corresponden esos archivos sin especificar y pidió
agruparlos aparte hasta que el equipo de campo lo confirme (ver sección 12). Se implementó un
bucket separado, `SPECIES_PENDING_LABEL = "Vieja (especie pendiente)"` en `config.py`: estos 27
archivos (9 por campaña × 3 campañas) aparecen en el dashboard como su propia "especie", visibles
y contables, pero **sin mezclarse** con Bourbon/Canefora/Cuscatleco/Pacamara. Cuando se sepa la
especie real, hay que reclasificar esos archivos (o ajustar `_discover_records()` en `parser.py`)
y la etiqueta puede dejar de usarse. Nota: esta categoría nunca entra en `severity_baselines()`
(no tiene hojas Tierna ni Con roya) ni en las figuras del paper (mismo motivo), así que no
contamina esos cálculos mientras se resuelve.

**Archivos ignorados (2026-09-11):** `data/10_08_2026/.../bourbon/roya/araña.txt`, `araña2.txt`,
`araña3.txt` no siguen ningún patrón conocido (ni roya ni vieja). Consultado con el usuario: no
sabe qué son, pidió ignorarlos por ahora. Quedan en el dataset con `name_recognized=False` y
`health_status=None` — visibles en el expander "archivos no reconocidos" de Home, sin afectar
ningún cálculo. **Pendiente:** aclarar qué representan (¿otra plaga, ej. araña roja/ácaro?) y
decidir si hay que excluirlos explícitamente o incorporarlos con su propio significado.

**Diseño real de muestreo confirmado por el usuario:** 2 hojas × 3 puntos × 3 medidas repetidas = 18 mediciones por estado de madurez (Madura o Tierna) por especie por campaña.

**Las hojas con roya siguen otro diseño (verificado 2026-08-02):** en las campañas con roya se muestreó **una sola hoja** (`R1`), con 3 puntos × **10** medidas repetidas = 30 archivos. No hay `R2`. Esto importa para cualquier análisis agregado a nivel de hoja: el grupo "Con roya" tiene **n = 1 hoja por campaña** (n = 2 en total por especie), razón por la cual las figuras del paper usan el punto de medición como unidad de observación (ver sección 13).

- **Estado sanitario** (`health_status`): derivado de la letra M/T/R → `Sana` (si M o T) o `Con roya` (si R). **Bourbon** y **Pacamara**, las dos especies susceptibles a la roya, tienen muestras reales con roya (campañas Roya_15_07 y Roya_27_07, más las campañas nuevas de agosto/septiembre).
- **Susceptibilidad** (`susceptibility`): viene de la subcarpeta si existe; si no, se intenta un fallback por sufijo `NS`/`S` al final del nombre de archivo (solo se busca para Pacamara).

Estos 3 conceptos son **independientes entre sí** y así se tratan en todo el código:
| Campo | Valores | Aplica a |
|---|---|---|
| `leaf_maturity` | Madura / Tierna / Vieja / None | hojas M, T o V (no aplica a R) |
| `health_status` | Sana / Con roya | derivado de M,T,V (=Sana) vs R (=Con roya) |
| `susceptibility` | Susceptible / No susceptible | solo Pacamara (variedad de planta) |

`Vieja` (V, agregada 2026-09-11) es una cuarta etapa de madurez, biológicamente paralela a
Madura/Tierna (hoja sana de otra edad), no un estado sanitario — de ahí que siga contando como
`Sana` en `health_status`.

## 5. Estado actual de los datos (`data/`)

Al 2026-09-27: **2377 archivos** `.txt` en disco (subió de 1978 con las 2 campañas nuevas de
septiembre 2026, `Campaña_14_09` y `Campaña_21_09` — ver sección 4). Tras aplicar el filtro de
`get_dataset()` (solo Pacamara "No susceptible" — `EXCLUDED_SPECIES` sigue vacía, ver sección 1),
el dashboard analiza **1945 archivos**. La categoría `Vieja (especie pendiente)` (45 archivos) se
cuenta aparte, no se mezcla con las 4 especies reales (ver sección 4).

Pivote de archivos por especie y campaña (dataset del dashboard, post-filtro):

| Especie    | C1_29_06 | C2_06_07 | Roya_15_07 | Roya_21_07 | Roya_27_07 | Campaña_10_08 | Campaña_17_08 | Campaña_24_08 | Campaña_31_08 | Campaña_07_09 | Campaña_14_09 | Campaña_21_09 | Total |
|------------|---------:|---------:|-----------:|-----------:|-----------:|--------------:|--------------:|--------------:|--------------:|--------------:|--------------:|--------------:|------:|
| Bourbon    | 36 | 36 | 66 | 36 | 66 | 69 | 51 | 48 | 51 | 48 | 51 | 54 | 612 |
| Canefora   | 36 | 36 | 0  | 36 | 0  | 36 | 27 | 17 | 18 | 18 | 18 | 18 | 260 |
| Cuscatleco | 36 | 36 | 36 | 36 | 36 | 36 | 36 | 36 | 36 | 36 | 36 | 36 | 432 |
| Pacamara   | 36 | 36 | 66 | 36 | 66 | 64 | 49 | 48 | 51 | 48 | 51 | 45 | 596 |

`Vieja (especie pendiente)`: 0 en todas las campañas viejas y en `Campaña_17_08` (ese archivo se
cuenta como Canefora, ver sección 4); 9 en cada una de `Campaña_24_08`, `Campaña_31_08`,
`Campaña_07_09`, `Campaña_14_09` y `Campaña_21_09` (45 en total). Las dos campañas nuevas siguen
el mismo esquema sin especie explícita que las tres anteriores, así que engordan el mismo
pendiente de la sección 12 en vez de resolverlo.

Estado sanitario (`health_status`, dataset del dashboard):
- Bourbon: 438 Sana, 171 Con roya (+3 sin reconocer, los archivos `araña*.txt` — sección 4)
- Canefora: 260 Sana, 0 Con roya (sigue sin campañas de roya propias)
- Cuscatleco: 432 Sana, 0 Con roya (sigue sin campañas de roya propias)
- Pacamara: 430 Sana, 166 Con roya
- Vieja (especie pendiente): 44 Sana, 1 sin reconocer (`vieja1.txt`, sin número de punto)

Susceptibilidad de variedad: 566 archivos Pacamara Susceptible; el resto queda con
`susceptibility=NaN` (Bourbon/Canefora/Cuscatleco no tienen esa clasificación, más las hojas con
roya de Pacamara que no vienen anidadas bajo una subcarpeta Susceptible/No susceptible).

Notas:
- **Canefora y Cuscatleco siguen sin hojas con roya propias.** El score de severidad para esas
  dos especies sigue usando la referencia enferma combinada (`referencia_propia: False`, ver
  sección 9).
- Los 432 archivos restantes en disco tras el filtro (2377 − 1945) son las hojas Pacamara "No
  susceptible".
- Siguen siendo **5 archivos sin reconocer** en todo el dataset crudo (las 2 campañas nuevas no
  agregaron ninguno): 3 `araña*.txt` (Bourbon, campaña `Campaña_10_08`), 1 `vieja1.txt` (bucket
  pendiente, campaña `Campaña_07_09`) y 1 `prueba_adri.txt` preexistente (Pacamara No susceptible,
  se filtra antes de llegar a la UI).
- ~~`Campaña_14_09` y `Campaña_21_09` aún no están commiteadas a git~~ — resuelto: quedaron
  commiteadas en `913923c` (":zap: add more data and campaigns"), antes de la sesión de pulido
  del 2026-09-28.

## 6. Módulos de código — qué hace cada uno

### `src/config.py`
Todas las constantes centralizadas: ruta de datos, parámetros de suavizado Savitzky-Golay (ventana 41, orden 2), rango útil de longitud de onda (420–1000 nm), diccionarios de normalización de nombres (especie, susceptibilidad, madurez), longitudes de onda de cada índice espectral, paleta de colores, colores estables por grupo, alfa de significancia (0.05).

### `src/parser.py`
El módulo más importante. Responsable de:
- `get_dataset()`: punto de entrada público. Calcula un "fingerprint" liviano de `data/` (ruta relativa + mtime + tamaño de cada `.txt`) y llama a `scan_dataset()`, que está cacheada con `@st.cache_data` usando ese fingerprint como key — así el cache se invalida solo cuando cambian los archivos en disco (se agregan/editan mediciones), sin necesitar botón manual (aunque el botón "Recargar datos" también existe por si acaso). **Además aplica el filtro de exclusión de Pacamara No susceptible y `EXCLUDED_SPECIES`** (esta última vacía desde 2026-09-11) antes de devolver el DataFrame al resto de la app. Es el único punto donde se filtra: las 4 páginas y `make_ieee_figures.py` lo heredan sin repetir la condición.
- `_discover_records()`: recorre `data/` recursivamente, identifica campaña (regex genérica `{prefijo}_dd_mm_yyyy`, más el fallback sin prefijo `_CAMPAIGN_BARE_RE` agregado 2026-09-11), especie, subcarpeta de susceptibilidad, y parsea el nombre de archivo con `_parse_filename()`. Si la especie no sale de ninguna carpeta ni del nombre del archivo pero la ruta pasa por una carpeta `vieja/`, cae en el bucket `SPECIES_PENDING_LABEL` (ver sección 4).
- `_parse_filename()`: aplica el regex `^([MTRV])(\d+)p(\d+)` (letra `V` = hoja vieja, agregada 2026-09-11) + sufijo de repetición, deriva `leaf_maturity`, `has_roya`, y (solo para Pacamara) el sufijo de susceptibilidad NS/S como fallback. Desde 2026-09-11 también reconoce dos variantes sin número de hoja explícito (`_ROYA_WORD_RE`, `_POINT_FIRST_RE`) vistas en las campañas nuevas — ver sección 4 para el detalle.
- `FileRecord`: dataclass con todos los campos por archivo (incluye `session`, `session_num`, `point`, `repetition`, `leaf_maturity`, `has_roya`, `health_status`, `susceptibility`, etc.)
- `read_spectrasuite()` / `load_spectrum()`: parsea el archivo `.txt` crudo (encoding latin-1, busca el marcador "Comienza Data"/"Begin Spectral", extrae pares longitud de onda/reflectancia), cacheado por archivo+mtime.

### `src/processing.py`
- `smooth()`: Savitzky-Golay sobre la reflectancia cruda.
- `filter_range()`: recorta al rango útil 420–1000 nm.
- `prepare_spectrum()`: pipeline completo (suavizar + recortar).
- `reflectance_at()`: reflectancia interpolada más cercana a una longitud de onda dada (tolerancia 5 nm).
- `calcular_indices()`: calcula los 8 índices espectrales actuales (ver sección 7).
- `average_group()`: interpola varios espectros a una grilla común y calcula media ± desviación estándar (para el gráfico de "Promedio ± SD" en la página de Espectros).
- `severity_score()`: normaliza los 8 índices de un archivo a un score de severidad de roya 0 (sana) – 1 (enferma), usando anclas por especie calculadas en `app.py` (ver sección 9).

### `src/stats_utils.py`
`compare_groups(groups, alpha=0.05)`: pipeline estadístico genérico y reusado en las 2 páginas de índices:
1. Shapiro-Wilk por grupo (normalidad).
2. Si todos los grupos son normales → ANOVA + post-hoc Tukey HSD.
3. Si no → Kruskal-Wallis + post-hoc Dunn (corrección Bonferroni).
Devuelve un dict con resumen descriptivo, resultados de Shapiro, nombre del test, estadístico, p-valor, si es significativo, y la tabla post-hoc.

### `src/state.py` y `src/notifier.py` (feature de Telegram)
- `state.py`: guarda en `.state/last_run.json` el set de archivos (`path|mtime_ns`) vistos en la última verificación manual. Permite calcular qué archivos son "nuevos" sin depender de ningún proceso corriendo en background.
- `notifier.py`: `send_telegram_message()` lee `st.secrets["telegram"]["bot_token"]` y `chat_id"]`, hace un POST a la API de Telegram (`sendMessage`) con `parse_mode="HTML"`. Confirmado por el usuario que **ya funciona en producción**. Además:
  - `format_leaf_report()`: arma la tarjeta de una hoja (riesgo, ubicación, severidad, los 8 índices con negrita en los que están en rango de alerta) — ver sección 9.
  - `format_header()`: primer mensaje con el conteo de archivos nuevos por especie y cómo leer lo que sigue.
  - `pack_messages()`: agrupa las tarjetas en la menor cantidad de mensajes posible **sin pasar los 4096 caracteres** que admite Telegram, nunca cortando una tarjeta por la mitad.
  - `build_notification()`: encabezado + una tarjeta por hoja, ya partido en mensajes listos para enviar.
  - `send_telegram_messages()`: envía la lista en orden (con 0,4 s entre mensajes por el rate limit de Telegram), se detiene en el primer fallo e informa cuántos salieron.

Flujo completo (botón "Verificar y analizar nueva data" en Home): compara archivos actuales vs. última verificación → si hay nuevos, arma un encabezado (cantidad por especie + cuántos son "Con roya") + una tarjeta de severidad por hoja → los manda por Telegram (uno o varios mensajes) → guarda el nuevo estado como línea base. La Home también muestra el mensaje enviado en un expander, para poder auditarlo sin salir de la app.

## 7. Índices espectrales calculados

Todos se calculan en `calcular_indices()` a partir del espectro ya suavizado, y se muestran en las páginas 2 y 3:

| Índice | Fórmula | Qué mide |
|---|---|---|
| **NDVI** | (R800 − R670) / (R800 + R670) | Vigor/verdor general de la hoja (clorofila vs. NIR) |
| **PRI** | (R531 − R570) / (R531 + R570) | Eficiencia fotosintética / estrés (ciclo de xantofilas) |
| **PSRI** | (R678 − R500) / R750 | Senescencia — sube cuando el tejido se degrada |
| **RCI** | 1/R510 − 1/R550 | "Rust Carotenoid Index", adaptado del índice de carotenoides de Gitelson |
| **EDI** | (R750 − R705) / (R750 + R705) | "Early Detection Index", shift del red-edge (formulación tipo PRI de Gamon) |
| **FSR** | (R800 − R670) / (R800 + R670) | "Foliar Stress Ratio" — **usa las mismas bandas que NDVI** (no se especificaron bandas distintas), por lo que da un valor **idéntico** a NDVI. Si se quieren bandas NIR/Rojo distintas para que aporte información diferente, hay que definirlas en `WL_FSR` en `config.py`. |
| **NDRE** (2026-08-02) | (R790 − R720) / (R790 + R720) | Normalized Difference Red Edge: clorofila vía borde rojo |
| **mNDVI705** (2026-08-02) | (R750 − R705) / (R750 + R705 − 2·R445) | NDVI modificado del borde rojo, corregido por dispersión foliar con la banda azul |

**CARI se eliminó el 2026-08-02** a pedido del usuario, y en su lugar se agregaron NDRE y mNDVI705 (el conteo pasó de 7 a 8 índices). El resultado de ese cambio fue muy favorable: **mNDVI705 es el índice que mejor separa sana de con roya de todo el conjunto** (Cliff's δ ≈ −1.0 en Bourbon *y* Pacamara, p<0.001 en ambas), superando incluso a PRI; NDRE también separa en las dos especies (p<0.05 en Bourbon, p<0.01 en Pacamara). Ver `figures_ieee/summary_effect_size.png`.

**Nota histórica sobre el bug de CARI:** mientras CARI existió, el notebook original usaba la reflectancia en 670 nm (`R670`) en el numerador de la fórmula de la recta base, cuando la fórmula correcta usa la **longitud de onda** 670 (constante). Se corrigió en `processing.py` antes de eliminar el índice; se documenta acá por si alguien compara con el notebook viejo.

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
1. **Detalle de cada medición (sin promediar)** — nueva tabla agregada en esta sesión: una fila por archivo/medida individual con columnas Especie, Campaña, Estado sanitario, Susceptibilidad, Madurez, **Hoja** (ej. "M1", "T2"), Punto, Medida, Archivo, + los 8 índices. Con botón de descarga CSV.
2. **Tabla de índices por punto y hoja (promedio de las 3 medidas repetidas)** — el promedio correcto: agrupa por (Especie, Campaña, Estado sanitario, Susceptibilidad, Madurez, **Hoja**, Punto), promediando *solo* las 3 repeticiones técnicas de ese punto en esa hoja específica. **Importante:** antes de la corrección de esta sesión, el agrupamiento no incluía "Hoja" y mezclaba M1 con M2 (dos hojas físicamente distintas) en un solo promedio — ya está corregido.
3. Boxplots de distribución por grupo (uno por índice).
4. Estadística automática (Shapiro → ANOVA/Tukey o Kruskal/Dunn) por índice, sobre la tabla promediada por punto y hoja.

### `pages/3_Comparacion_Especies.py`
Compara los 8 índices entre las especies disponibles (mínimo 2 seleccionadas; desde el 2026-09-11 pueden ser hasta las 4 — Bourbon, Canefora, Cuscatleco, Pacamara). Mismos filtros de campaña y estado sanitario. Mismo fix de "Hoja" aplicado al agrupamiento. Tabla de promedios, boxplots por especie, estadística automática entre especies.

### `pages/4_Severidad_Roya.py`
Score de severidad de roya 0–100% por hoja, con las mismas anclas sana/enferma que usa la alerta de Telegram (ver sección 9). Restringida a **hojas maduras** de Bourbon y Pacamara (`SUSCEPTIBLE` en el módulo): son las especies susceptibles, y la hoja madura es la de estado sanitario desconocido, que es el caso de interés real. Filtros por campaña y especie. Muestra el detalle por hoja/punto y el promedio por especie, con las etiquetas 🟢/🟡/🔴 correspondientes al mismo rango que Telegram.

### `pages/5_Evolucion_Temporal.py` (2026-09-27)
Sigue a **cada hoja física en el tiempo**: M1, M2, T1, T2 y R1 son las mismas hojas en todas las
campañas (confirmado por el usuario y verificado en los datos). Plan, decisiones y resultados en
**`evoluciontemporal.md`**, que es la referencia de esta página. En resumen:
- Unidad = hoja-fecha (media de repeticiones por punto, luego media de puntos); solo p1–p3,
  porque los puntos no son ubicaciones fijas y p4–p6 no cuentan (decisión del usuario).
- **Lo principal es la sección 1: la evolución de las hojas maduras (M1, M2) de Bourbon y
  Pacamara**, lado a lado, con las hojas T y R1 de fondo como referencias, y una tabla que
  contrasta cada tendencia con las hojas M de los controles sin roya (`evoluciontemporal.md` §13).
- Arriba de todo, un **resumen de hallazgos** que se recalcula solo; después la **sección 2** (qué
  longitudes de onda e índices cambian con el tiempo, por grupo de hojas) y la **sección 3** (la
  misma hoja semana a semana: R1 frente a hoja tierna). Hallazgo principal: en el visible, las hojas
  tiernas se oscurecen al madurar (7/7) y las R1 se aclaran (2/2); ningún índice cambia solo en la
  hoja con roya (`evoluciontemporal.md` §14).
- Después, detalle por especie: ficha de datos, índices en el tiempo (valor / Δ / Δ* corregido por hojas T),
  tendencias (Theil-Sen + Mann-Kendall + FDR, con Canefora y Cuscatleco como controles negativos),
  severidad relativa (anclas S1 congeladas y S2 leave-one-campaign-out, con aviso de
  circularidad), distancia espectral a R1, animación del espectro y CSV.
- Control de calidad (robust z contra la propia serie de la hoja): marca 4 hojas-fecha, incluida
  Pacamara R1 el 10/08; un interruptor las excluye y recalcula todo.
- **No modifica** `severity.py`, la alerta de Telegram ni las páginas 1–4: sus anclas temporales
  se calculan aparte.

## 9. Score de severidad de roya en la alerta de Telegram

Implementado a pedido de Samuel (vía WhatsApp, 2026-07-17): la alerta de Telegram ahora, además de contar archivos nuevos por especie, incluye un **score de 0% (sana) a 100% (enferma)** calculado a partir de los índices espectrales, para que un trabajador de campo sepa de un vistazo qué tan comprometida está una hoja.

**Cómo se calibra (decidido con el usuario en esta sesión):**
- Se usan los **8 índices espectrales** existentes (NDVI, PRI, PSRI, RCI, EDI, FSR, NDRE, mNDVI705) — no solo uno, para que el resultado sea más robusto.
- Por cada índice y especie se calculan dos **anclas** a partir de los datos ya existentes en `data/`:
  - **Ancla sana (0)** = promedio del índice en hojas **Tierna** (T). Razonamiento del usuario: la roya todavía no tuvo tiempo de manifestarse en tejido nuevo, así que la hoja tierna es la referencia sana más confiable disponible.
  - **Ancla enferma (1)** = promedio del índice en hojas **Con roya** (R) de esa misma especie.
  - **Bourbon y Pacamara** tienen su propia ancla enferma (campañas con roya confirmada). **Canefora y Cuscatleco no tienen roya propia** y, desde que se reincluyeron el 2026-09-11 (sección 1), usan el respaldo genérico: promedio combinado de las especies que sí tienen roya propia, marcado como `referencia_propia: False` y con nota de "referencia estimada" en Telegram. Entre el 2026-08-03 y el 2026-09-11 este respaldo no se activaba nunca porque esas dos especies estaban excluidas del dataset; **ahora sí se activa** para cualquier hoja nueva de Canefora o Cuscatleco.
- Cada índice de un archivo nuevo se normaliza por separado entre sus dos anclas (clip a 0–1), y el score final del archivo es la **mediana** de los índices normalizados (más robusto ante un índice atípico que el promedio). El mensaje también reporta cuántos de los 8 índices se pudieron usar (`n/8`).

**Formato del mensaje (rediseñado 2026-08-02, a partir de `formato_mensaje.txt`):** la unidad de reporte es la **hoja**, no la especie ni el archivo. Una tarjeta por hoja con esta estructura:

```
🔴 Critical

Date: 27/07/2026 - Pacamara - R1

Estimated severity: 86 % compared to a healthy reference leaf.
Plant almost bare, with extreme tissue damage.
Treat urgently and assess whether the plant can still be recovered.

Indices — value and severity of that single index (8/8 comparable):
NDVI          0.438     0 %
PRI          -0.106    72 %     <- en negrita (en rango de alerta)
PSRI          0.076   100 %
...
```

Ajustes de formato del 2026-08-02 (a pedido del usuario):
- El **encabezado es solo la clase de riesgo**, sin el porcentaje nominal de la clase.
- La segunda línea identifica la medición como **fecha de campaña (dd/mm/yyyy) - especie - hoja**, en vez del nombre de la carpeta de campaña.
- Al lado de cada índice va el **porcentaje de severidad que indica ese índice por sí solo** (su valor normalizado entre el ancla sana y la de roya). La severidad de la hoja es la mediana de esos 8 porcentajes, así que la tarjeta deja ver qué índices la empujan.
- La alerta se envía en tres partes: (1) `format_risk_scale()` — qué significa cada color y en qué tramo de severidad cae cada clase; (2) las tarjetas de las hojas; (3) `format_index_ranges()` — informe de min/max observado de cada índice sobre todas las hojas de referencia. La leyenda y el informe se mandan como mensajes propios, no empaquetados con las tarjetas.
- El rango min-max **por especie** sigue calculándose en `severity_baselines()` y propagándose en `leaf_severity_reports()` (claves `min`/`max` de cada índice), aunque la tarjeta ya no lo muestre.

- **Severidad de la hoja** = promedio de la severidad de sus puntos de medición (primero se promedian las 3 medidas repetidas de cada punto, después los puntos entre sí, para que una hoja con puntos incompletos no quede sesgada).
- **Negrita = índice en rango de alerta**: su valor normalizado entre el ancla sana y el ancla con roya llega a **≥ 0,66**, el mismo umbral que la app usa para "riesgo alto" (`ALERT_THRESHOLD` en `notifier.py`).
- Se reportan **todas** las hojas nuevas, ordenadas de mayor a menor severidad, no solo las de riesgo alto.
- **Escala de 11 clases de riesgo** (`RUST_RISK_CLASSES` en `config.py`, definida por el usuario el 2026-08-02; antes eran 3 niveles): Healthy 0 %, Incipient 10 %, Very slight 20 %, Slight 30 %, Onset of moderate 40 %, Moderate 50 %, Onset of severe 60 %, Severe 70 %, Very severe 80 %, Critical 90 %, Very critical 100 %. Cada una trae la descripción de lo que se ve en la planta (ver `ESTADO_ROYA.md` sección 6). Un score se asigna a la clase **más cercana**, no al tramo inferior, para que cada clase quede centrada en su riesgo nominal. La acción sugerida se agrupa en 5 tramos (`RUST_RISK_ACTIONS`) y no una por clase, para no saturar a quien lee la alerta en el campo. La página de Severidad del dashboard usa la misma escala.
- La nota "referencia estimada" vuelve a poder aparecer (Canefora/Cuscatleco, ver arriba) desde el 2026-09-11. El texto de la nota se dejó redactado de forma genérica, sin nombrar especies, así que no hizo falta tocar `notifier.py`.

**Dónde está el código:**
- `src/processing.py` → `severity_score(values, baseline)`: función pura, normaliza y agrega (nivel archivo).
- `src/severity.py` → `severity_baselines(dataset)` (cacheada con `@st.cache_data`): anclas sana/enferma por especie; y `leaf_severity_reports(new_df, baselines)`: agrega las mediciones nuevas a nivel de hoja y devuelve, por hoja, el score, el valor promedio de cada índice, su referencia sana y su posición normalizada (lo que decide la negrita).
- `src/notifier.py` → `format_leaf_report()`, `format_header()`, `pack_messages()`, `build_notification()`, `send_telegram_messages()` (ver sección 6).

**Limitación conocida:** como `FSR` usa exactamente las mismas bandas que `NDVI` (ver sección 7, todavía no se le definieron bandas propias), en la práctica el score de severidad usa 6 índices con información distinta más uno duplicado. No afecta la validez del score (la mediana lo diluye), pero si en el futuro se definen bandas propias para `FSR`, el score va a aportar información algo más rica.

## 10. Decisiones de diseño importantes (y el porqué)

- **Sin servidor en background para Telegram**: el usuario eligió explícitamente un botón dentro de la app en vez de un proceso corriendo 24/7, porque es de uso personal y "tener un servidor es demasiado".
- **Detección de campañas 100% genérica** (regex `{prefijo}_dd_mm_yyyy`): para que cuando se agreguen carpetas de campañas futuras, la app las reconozca solas sin tocar código.
- **Cache de Streamlit basado en fingerprint de archivos**, no en un botón manual obligatorio: la app se auto-actualiza cuando se agregan mediciones nuevas a `data/`, tal como pidió el usuario desde el principio ("la idea es analizar estas y otras posibles cada vez que se suban nuevas mediciones").
- **`leaf_maturity`, `health_status` y `susceptibility` son campos separados**, no uno solo: reflejan 3 conceptos biológicos distintos (madurez de la hoja, estado sanitario actual, variedad de la planta) que pueden variar independientemente.
- **Agrupamiento por "Hoja"** (no solo por punto): las 2 hojas de cada grupo (M1/M2, T1/T2) son unidades biológicas distintas y no deben promediarse entre sí — solo se promedian las 3 medidas repetidas dentro del mismo punto de la misma hoja.

## 11. Bugs corregidos

1. **`use_container_width` deprecado** → reemplazado por `width='stretch'` en todo el proyecto.
2. **`or` con corto-circuito en `parser.py`**: `susceptibility = susceptibility or meta.pop(...)` nunca hacía el `.pop()` cuando `susceptibility` ya era verdadero, dejando una key sobrante que rompía `FileRecord(**meta)`. Corregido haciendo el `.pop()` incondicional antes del `or`.
3. **`KeyError: 'health_status'`** reportado por el usuario en un run real de Streamlit — no era un bug de código (validado exhaustivamente), sino un **proceso de Streamlit viejo corriendo con módulos no recargados**. Se resolvió reiniciando el servidor.
4. **Bug de fórmula CARI** (ver sección 7): usaba reflectancia en vez de longitud de onda en el numerador. Corregido, documentado con comentario en el código.
5. **Bug de agrupamiento/promediado** (ver sección 8, página 2 y 3): mezclaba hojas distintas (M1 con M2) en un solo promedio por no incluir "Hoja" como clave de agrupamiento. Corregido agregando `Hoja` = `{session}{session_num}` a las claves de agrupamiento en ambas páginas, y se agregó además una tabla de detalle sin promediar para poder auditar cada medición individual.
6. **`campaign_id` colapsaba campañas homónimas (2026-07-31)**: dos carpetas con el mismo prefijo (`roya_15_07_2026`, `roya_21_07_2026`, `roya_27_07_2026`) recibían el mismo `campaign_id = "Roya"`, por lo que aparecían como una sola columna en el pivote de la Home y como una sola opción en los multiselects de las 4 páginas de análisis. Corregido en `parser.py:_find_campaign()` incluyendo siempre el sufijo `dd_mm` en el id (`Roya_15_07`, `Roya_21_07`, `Roya_27_07`).
7. **Variantes de carpeta "No susceptible" no reconocidas (2026-07-31)**: `SUSCEPTIBILITY_CANONICAL` no cubría `no suseptible` (con espacio y ortografía distinta) usada en `roya_21_07_2026`, dejando esas 36 hojas sin susceptibilidad clasificada. Agregadas las variantes con espacio y con guión bajo `no_suseptible`.
8. **La alerta de Telegram no llegaba nunca (2026-08-02)**: el mensaje se armaba como **un solo texto** con una línea de detalle por archivo nuevo. Con 312 archivos nuevos pendientes el texto medía **30.603 caracteres** y la API de Telegram rechaza cualquier mensaje de más de **4.096** → devolvía 400, `resp.raise_for_status()` lanzaba excepción y **no se entregaba nada** (ni siquiera el encabezado). Encima, `raise_for_status()` solo mostraba "400 Client Error", ocultando el `description` de la API que decía exactamente el problema. Corregido en `notifier.py`: el mensaje se arma por bloques y `pack_messages()` los reparte en varios envíos bajo el límite, y los errores ahora incluyen la descripción que devuelve Telegram.
9. **Etiqueta de hoja mostrada como "M1.0" (2026-08-02)**: `session_num` se guarda como `int`, pero la columna del DataFrame queda `float` porque los archivos de nombre no reconocido aportan NaN — así que `f"{session}{session_num}"` producía "M1.0" en las 4 páginas y en el mensaje de Telegram. Centralizado en `parser.leaf_label()`, usado por `severity.py` y las 4 páginas.

## 12. Pendientes / posibles próximos pasos

**Abiertos al cierre de la sesión del 2026-09-27 (los más importantes primero):**

- **Pacamara R1 el 10/08 parece una medición fallida** (reflectancia hundida en todo el espectro:
  R800 = 29 % contra ~75–80 % en las fechas vecinas). Infla ~7 veces el ancla "con roya" de RCI de
  Pacamara (0,242 en vez de 0,034 por fecha) y, como `severity_baselines()` promedia archivos, la
  alerta de Telegram y la página 4 usan esa ancla inflada. **Decidir** si se excluye ese día del
  ancla (cambia la alerta y los números del paper). Detalle en `evoluciontemporal.md` §11.1.
- **mNDVI705 > 1** en hojas sanas de Pacamara el 24/08 y el 31/08, y negativo en un punto de
  Bourbon M1 el 24/08: indica reflejo en el azul (R445 cerca de R705). Revisar cómo se midió esos
  días antes de usar mNDVI705 de esas fechas en el paper.
- **La tendencia de Bourbon M1 también aparece en Cuscatleco M1 (sin roya):** es más probable que
  sea envejecimiento que roya asintomática. No presentarla como detección temprana (ver
  `evoluciontemporal.md` §12).
- **Siguiente paso del estudio temporal:** modelo de evolución normal (hojas sanas + controles) para
  detectar desvíos, y pedir al equipo de campo hojas marcadas antes de los síntomas con severidad
  visual por fecha, sin lo cual no se puede entrenar un predictor de roya (`evoluciontemporal.md` §14.3).
- **Probar la página 5 en un navegador real** y darle "Reproducir" a la animación: se validó con
  `AppTest` y renderizando las figuras a PNG, pero la extensión de Chrome no respondió.

- **Especie de la "hoja vieja" sin identificar — creció con las 2 campañas nuevas.** Ahora son
  **45 archivos** (`Campaña_24_08`, `Campaña_31_08`, `Campaña_07_09`, `Campaña_14_09`,
  `Campaña_21_09`) sin especie en el nombre ni en la carpeta, no 27. Sigue sin confirmación del
  equipo de campo; siguen agrupados bajo `SPECIES_PENDING_LABEL`. Cuando se confirme la especie,
  reclasificar (renombrar o mover de carpeta) y correr `Recargar datos` — no hace falta tocar
  código.
- **Archivos `araña*.txt` sin explicación.** 3 archivos en `Campaña_10_08/Bourbon/roya/` no
  siguen ningún patrón conocido. El usuario pidió ignorarlos por ahora; quedan como "no
  reconocidos" en el dataset. Aclarar qué representan (¿otra plaga?) y decidir si hay que
  excluirlos explícitamente o incorporarlos con su propio significado.
- **Figuras y tablas del paper (sección 13/14) siguen desactualizadas, ahora con más margen.** Se
  generaron el 2026-08-02/03 con Canefora y Cuscatleco excluidas y sin ninguna de las 7 campañas
  agregadas desde entonces (5 en 09-11 + 2 en 09-27, ~1400 archivos nuevos en total). Falta correr
  `make_ieee_figures.py` a propósito (reescribe `figures_ieee/`, por eso no se hace automático) y
  recalcular las tablas de la sección 14. El argumento de la Tabla II sobre Cuscatleco/Canephora
  (sección 14.2) sigue válido al tener las 4 especies de nuevo.
- **Revisar si `Campaña_17_08` de Canefora mezcla "hoja vieja" con hojas M/T normales sin
  distinguirlas en los pivotes existentes.** Por ahora `leaf_maturity=Vieja` sí las distingue,
  pero ninguna página del dashboard tenía antes una tercera categoría de madurez — vale la pena
  confirmar visualmente en la página de Índices que el filtro "Madurez de hoja" se ve bien con 3
  grupos en vez de 2.

**Abiertos al cierre de la sesión del 2026-08-03 (los más importantes primero):**

- ~~**Revisar el texto del paper por las dos especies excluidas.**~~ — superado el 2026-09-11: Canefora y Cuscatleco ya no están excluidas (sección 1), así que el problema es ahora el inverso (paper/figuras/tablas desactualizadas por defecto, no por exclusión). Ver la entrada correspondiente en la sección de pendientes del 2026-09-11, arriba.

- **Índices que dan 0 % de severidad en hojas con roya confirmada.** Con el porcentaje por índice visible en la alerta (sección 9) quedó expuesto: en Pacamara R1, NDVI, FSR y RCI marcan 0 % porque su valor cae del lado *sano* de la referencia y el `np.clip(…, 0, 1)` de `severity_score()` lo lleva a cero. El score final sale bien igual (86 %) porque la mediana de los 8 lo absorbe, pero se está desperdiciando información. Dos opciones: excluir por especie los índices que no discriminan, o usar la desviación absoluta respecto del ancla sana en vez del recorte con signo. **Cualquiera de las dos cambia los números del paper.**
- **Falta la etiqueta de hoja asintomática infectada** (madura de planta con roya confirmada, pero sin síntomas en esa hoja). Sin ella no se puede sostener un análisis de detección temprana: ver la advertencia de la sección 14.2. Requiere anotarlo en la próxima campaña de muestreo.
- **Más hojas con roya.** Hoy hay 1 hoja `R1` por campaña (2 por especie). Todo el grupo enfermo del paper y todas las anclas de severidad dependen de esas 2 hojas por especie.
- **Umbral de negrita de la alerta**: sigue en 0,66, heredado de la escala vieja de 3 niveles. Con la escala de 11 clases quedaría más coherente en 0,60, que es el límite de "Onset of severe".
- **NDVI se comporta al revés en Bourbon**: sube con roya (0,50 → 0,64 a nivel de hoja tierna vs. con roya), al contrario de lo esperable. Puede ser real (caída de R670 mayor que la de R800) o efecto de que las hojas R se midieron sobre tejido distinto. Conviene resolverlo antes de publicar.

**Anteriores:**

- ~~Definir si `FSR` debe usar bandas distintas a NDVI~~ — resuelto el 2026-09-28 (X8 de
  `plan_mejora_app.md`): en vez de redefinir sus bandas, `FSR` se **quitó** de las vistas activas
  (paginas 1-5, Telegram, `src.stats_utils`), la estadistica y la similitud con roya —
  `src.indices.DISPLAY_INDICES` es la lista de 7 indices que usan. `calcular_indices()` sigue
  calculando FSR por compatibilidad (identico a NDVI), pero nada nuevo lo muestra ni lo usa.
- **Etiquetado final de enfermedad**: el usuario mencionó en su momento que se vería más adelante ("luego podemos ver lo de las etiquetas finales") — por ahora el etiquetado real que existe es `health_status` (Sana/Con roya) derivado del prefijo R del nombre de archivo, ya incorporado. Confirmar si esto es lo que se consideraba "etiquetado final" o si falta algo más granular (ej. severidad/grado de roya).
- **Canefora y Cuscatleco todavía no tienen muestras con roya real.** Vuelve a ser un pendiente activo desde el 2026-09-11: estuvo "resuelto" (sin efecto) entre el 2026-08-03 y el 2026-09-11 solo porque ambas especies estaban excluidas del dataset, no porque el problema se haya resuelto de fondo. Hoy ambas especies están de nuevo en el dashboard (sección 1) pero siguen sin roya propia, así que su score de severidad usa la referencia estimada (sección 9). Si se muestrean hojas con roya para estas especies, la app las reconoce sin cambios de código (mismo patrón `R{n}p{punto}`) y el score pasa a usar su ancla propia automáticamente.
- **Susceptibilidad en subcarpetas nuevas**: en `roya_27_07_2026/Pacamara/Roya/` las hojas con roya quedan con `susceptibility=NaN` porque la subcarpeta se llama `Roya` en vez de indicar Susceptible/No_susceptible. Biológicamente son susceptibles; si se decide inferir susceptibilidad automática para la subcarpeta `Roya` (o exigir doble anidamiento `Susceptible/Roya`), hay que ajustar `_discover_records()`.
- ~~Si se decide inicializar git en el proyecto, agregar `roya/` al `.gitignore`~~ — resuelto, ver nota de la sección 3.
- Considerar si la comparación estadística de "Sana vs Con roya" debería hacerse a nivel de **hoja** (promediando los 3 puntos de cada hoja primero) en vez de a nivel de **punto**, para evitar pseudo-réplicas (puntos de la misma hoja no son observaciones totalmente independientes). Se dejó el comportamiento existente (comparación a nivel de punto-hoja).
- **Documentar rangos observados vs. literatura** para cada índice en la UI (ver `ESTADO_ROYA.md` sección "Rangos observados y por qué se salen de la 'norma' de blog"): los índices no normalizados (RCI) escalan con la reflectancia en 0–100% del SpectraSuite y por eso salen valores muy por encima de los "0 a 1" que dicen los blogs genéricos.

## 13. Figuras del paper (IEEE / CONCAPAN)

`make_ieee_figures.py` genera las **29 figuras** de `figures_ieee/` (PNG 600 dpi, fondo blanco, Times New Roman, ancho de una columna IEEE = 3,5 in). Todo el contenido está **en inglés** porque el paper se presenta en inglés. Se regenera corriendo `python make_ieee_figures.py`.

**Eran 45 hasta el 2026-08-03**: al excluir Canefora y Cuscatleco (sección 4) desaparecieron los 16 boxplots por especie de esas dos. Los 16 PNG correspondientes (`boxplot_canephora_*.png`, `boxplot_cuscatleco_*.png`) **se borraron de `figures_ieee/`**, porque el script no los sobrescribe: al no generarse, habrían quedado en disco con la data restringida. El resto se regeneró completo.

- 16 boxplots: 8 índices × 2 especies (`boxplot_{especie}_{indice}.png`), Healthy (young) vs. Rust-infected.
- 8 boxplots de comparación entre cultivares (`species_comparison_{indice}.png`).
- 2 figuras de reflectancia (`spectra_{especie}_healthy_vs_rust.png`, Bourbon y Pacamara): panel superior con media ± 1 SE, panel inferior con el espectro de diferencia (roya − sana) en puntos de reflectancia.
- 3 figuras resumen para un paper de 4 páginas: `summary_rust_vs_healthy.png` (8 índices × 2 especies susceptibles, reemplaza los 16 boxplots), `summary_cultivars.png` (8 índices × 2 cultivares, reemplaza las 8 de comparación) y `summary_effect_size.png` (forest plot de Cliff's δ, alternativa de una sola figura).
- `figures_ieee/README.md`: índice auto-generado con el n de cada figura, para copiar los captions. Incluye una sección "Data excluded from every figure" que deja constancia de las dos exclusiones.

El script **no nombra especies en ningún lado**: recorre las que vengan en `get_dataset()`. Los diccionarios `SPECIES_DISPLAY` / `SPECIES_COLORS_PRINT` / `SPECIES_SHORT` conservan las 4 entradas a propósito, para que reactivar una especie sea solo vaciar `EXCLUDED_SPECIES` y volver a correr el script.

**Por qué las figuras de espectros usan SE y no SD:** la SD entre mediciones individuales es de 12–16 puntos de reflectancia (variación de acoplamiento sonda-hoja y entre hojas), varias veces mayor que la diferencia entre grupos (2–10 puntos), así que las bandas ±1 SD se solapaban por completo y ocultaban un efecto que sí es significativo. Con el error estándar de la media —que es lo que corresponde cuando lo que se compara son medias de grupo— la diferencia se separa con claridad. El panel inferior muestra la diferencia entre grupos en puntos de reflectancia. **Nota (2026-08-02):** las figuras tenían además sombreadas las longitudes de onda con diferencia significativa (Mann-Whitney por banda + corrección FDR de Benjamini-Hochberg); se quitó el sombreado a pedido del usuario. La función `_bh_significant()` sigue en `make_ieee_figures.py` por si se quiere reactivar.

**Decisiones de análisis (acordadas con el usuario el 2026-08-02):**
- **Unidad de observación: el punto de medición** (se promedian las medidas repetidas de cada punto: 3 en hojas M/T, 10 en hojas R). No se agrega hasta el nivel de hoja porque cada campaña de roya muestreó una sola hoja `R1` (ver sección 4) y el grupo con roya quedaría en n = 2.
- **Grupo "Healthy" = hojas tiernas (T) únicamente**, la misma referencia sana que usa el score de severidad. Las hojas **maduras (M) quedan fuera de todas las figuras**: su estado sanitario es desconocido, que es justo lo que el modelo estima.
- n resultante por especie: Bourbon 30 vs 6, Pacamara 30 vs 6 (72 puntos en total).
- La comparación entre cultivares usa solo hojas tiernas sanas, para que la diferencia entre especies no quede mezclada con la presencia de roya.
- El p-valor anotado sale del mismo pipeline del dashboard (`stats_utils.compare_groups`): Shapiro-Wilk por grupo → ANOVA si todos son normales, si no Kruskal-Wallis. Se muestra como asteriscos (`***` p<0.001, `**` p<0.01, `*` p<0.05, `ns`).
- `summary_cultivars.png` lleva **solo el asterisco del test global**, más la escala de asteriscos en la leyenda. Se probaron también letras de agrupamiento post-hoc (qué cultivar difiere de cuál) pero el usuario las descartó por difíciles de leer; las funciones `_pairwise_pvalues()` y `_compact_letters()` quedan en el script por si se quieren reactivar. **Con solo 2 cultivares el asterisco ya es inequívoco** (es la comparación directa Bourbon vs. Pacamara), así que la advertencia anterior de "dice que alguno difiere pero no cuál" dejó de aplicar. Los cultivares se abrevian en el eje X (B, P) y la leyenda expande las abreviaturas.
- **Ojo con las comparaciones múltiples:** los asteriscos de las figuras resumen usan α = 0,05 por test, sin corrección entre paneles (16 tests en `summary_rust_vs_healthy.png`). Las figuras de espectros sí corrigen (Benjamini-Hochberg) porque ahí eran ~3.000 tests. Si un revisor lo pide, aplicar la misma corrección FDR a los asteriscos: los resultados fuertes (PRI, mNDVI705, NDRE) sobreviven, los que están al filo pasarían a `ns`.
- **Las figuras de espectros arrancan en 440 nm**: por debajo, la relación señal/ruido del espectrómetro es tan baja que ~13 % de los espectros con roya devuelve reflectancia negativa (hasta −365 %), lo que deformaba la banda de SD. Ningún índice usa bandas por debajo de 500 nm, así que el análisis no cambia.
- El mapeo de **"Canefora" → "Canephora"** (grafía correcta de *Coffea canephora* en inglés) sigue en `SPECIES_DISPLAY`. Desde el 2026-09-11 Canefora ya no está excluida (sección 1), así que este mapeo vuelve a usarse la próxima vez que se corra el script — pendiente, ver sección 12.

**Tipografía de las figuras resumen (ajustada 2026-08-02):** van a dos columnas y se leen impresas, así que usan cuerpos mayores que los paneles individuales, centralizados en las constantes `SUMMARY_*` de `make_ieee_figures.py`: título de panel 10,5 pt, etiquetas del eje X 9,5 pt, marcas del eje Y 8,5 pt, leyenda 9,5 pt, pie de significancia 9,5 pt y **asteriscos 14 pt en negrita** (los asteriscos son glifos pequeños y elevados: a igual cuerpo se ven mucho menores que el resto del texto). Para que la letra grande entrara sin solapamientos: separación entre paneles reducida (`hspace` 0,30 / `wspace` 0,20), márgenes de figura casi al borde, altura por fila 2,05 in, margen vertical de cada panel 0,26 y **máximo 5 marcas en el eje Y** (`MaxNLocator`), que es lo que libera el ancho entre columnas.

**Limitación a declarar en el paper:** el grupo con roya proviene de 1 hoja por campaña (2 hojas por especie en total). Los 6 puntos por especie son puntos distintos de esas 2 hojas, no hojas independientes.

## 14. Tablas del paper — valores calculados (2026-08-02)

Valores entregados al usuario en código LaTeX para el paper de CONCAPAN. Se recalculan con
`make_ieee_figures.py` (mismo pipeline) o con los scripts ad-hoc descritos abajo.

### 14.1 Tabla I — media ± SD por variedad y estado sanitario

**Agrupamiento de esta tabla:** `H` = todas las hojas sin roya (**maduras + tiernas**, n = 60 por
especie) y `R` = hojas con roya confirmada (n = 6). **Ojo:** no coincide con las
figuras, donde "Healthy (young)" son solo tiernas (n = 30). Unidad de observación: el punto de
medición, igual que en las figuras.

**Actualizado el 2026-08-03:** se quitaron las columnas Cuscatleco H y Canephora H al excluirse
esas especies (sección 4). Los valores de Bourbon y Pacamara **no cambian** — se calculan por
especie y no dependían de las otras dos.

| Índice | Bourbon H | Bourbon R | Pacamara H | Pacamara R |
|---|---|---|---|---|
| NDVI | 0.632 ± 0.146 | 0.637 ± 0.071 | 0.605 ± 0.140 | 0.632 ± 0.214 |
| PRI | −0.036 ± 0.018 | −0.083 ± 0.032 | −0.027 ± 0.014 | −0.137 ± 0.039 |
| PSRI | 0.004 ± 0.022 | 0.018 ± 0.007 | 0.005 ± 0.015 | 0.045 ± 0.047 |
| RCI | 0.037 ± 0.067 | 0.030 ± 0.011 | 0.032 ± 0.052 | 0.065 ± 0.060 |
| EDI | 0.438 ± 0.134 | 0.275 ± 0.074 | 0.410 ± 0.094 | 0.241 ± 0.134 |
| FSR | 0.632 ± 0.146 | 0.637 ± 0.071 | 0.605 ± 0.140 | 0.632 ± 0.214 |
| NDRE | 0.231 ± 0.091 | 0.124 ± 0.036 | 0.204 ± 0.049 | 0.097 ± 0.052 |
| mNDVI705 | 0.623 ± 0.098 | 0.365 ± 0.099 | 0.623 ± 0.092 | 0.291 ± 0.140 |

- **La fila FSR es idéntica a NDVI** en las cuatro columnas (mismas bandas). En una tabla se nota más que en una figura; conviene dejar solo una de las dos y explicarlo en el texto.
- Los índices que realmente separan H de R son **PRI**, **mNDVI705**, **NDRE** y **EDI**; NDVI, FSR, RCI y PSRI casi no se mueven.
- El formato LaTeX entregado usa `\makecell` para partir cada celda en dos líneas (media arriba, SD abajo). Con 4 columnas en vez de 7 la tabla entra mucho más holgada en los 88 mm de una columna IEEE, así que ese `\makecell` quizá ya no haga falta — verificar al recompilar.

### 14.2 Tabla II — ROC, y por qué hay que reencuadrarla

El usuario pidió llenar una tabla de "early detection performance" con clases **H / A / S**. Como
en `data/` no existe ninguna etiqueta de hoja *asintomática infectada*, el único mapeo posible fue:
**H** = hojas tiernas (T), **A** = hojas maduras (M), **S** = hojas con roya (R).

| Variedad | Índice | AUC | IC 95 % | Umbral |
|---|---|---:|---|---:|
| Bourbon | RCI | 0.872 | 0.767–0.960 | 0.017 |
| Bourbon | EDI | 0.952 | 0.893–0.997 | 0.390 |
| Bourbon | FSR | 0.894 | 0.794–0.978 | 0.673 |
| Pacamara | RCI | 0.561 | 0.503–0.718 | 0.010 |
| Pacamara | EDI | 0.617 | 0.509–0.767 | 0.369 |
| Pacamara | FSR | 0.589 | 0.504–0.737 | 0.543 |

AUC vía estadístico de Mann-Whitney; IC por 2.000 remuestreos bootstrap; umbral óptimo por
índice de Youden (en todos los casos se predice A cuando el índice supera el umbral).
Sensibilidad/especificidad en el umbral: Bourbon EDI 97 %/90 %, Pacamara EDI 83 %/53 %.

**Actualizado el 2026-08-03:** se quitaron las filas de Cuscatleco (EDI, AUC 0.996) y Canephora
(EDI, 0.836) al excluirse esas especies. Las 6 filas de Bourbon y Pacamara no cambian.

**Advertencia importante (sigue en pie, y ahora es más difícil de sustentar):** con ese mapeo,
**H vs. A es en realidad tierna vs. madura**, o sea que el ROC mide capacidad de distinguir la
*edad* de la hoja, no detección temprana de roya. La evidencia más contundente de eso eran
justamente las dos especies que ya no se pueden usar: el ROC funcionaba muy bien en Cuscatleco
(0.996) y Canephora (0.836), donde no hay roya posible, y fallaba justo en Pacamara (0.56–0.62).
**Ese argumento ya no se puede escribir en el paper**, pero el problema de fondo no desapareció:
la tabla sigue midiendo edad foliar, no detección temprana. Con solo Bourbon y Pacamara queda un
contraste interno más débil (Bourbon 0.87–0.95 vs. Pacamara 0.56–0.62) que no distingue entre
"el índice detecta roya asintomática" y "el índice detecta madurez".

Dos salidas honestas, las mismas de antes: (a) reencuadrar la tabla como separabilidad entre
estadios de desarrollo foliar —lo más viable hoy—, o (b) hacer una campaña que etiquete hojas
maduras de plantas con roya confirmada pero sin síntomas en esa hoja, que es lo que haría válido
el análisis tal como está redactado. **Ojo:** el texto que el usuario tenía escrito ("Cuscatleco
and Canephora showed AUC near 0.5, confirming no discrimination") hay que borrarlo en cualquier
caso — era incorrecto y además cita datos que ya no se pueden usar.

## 15. Cómo retomar rápido

1. `streamlit run app.py` (reiniciar si ya estaba corriendo).
2. Revisar la sección 12 (pendientes) para saber por dónde seguir.
3. Si se agregan campañas nuevas a `data/`, no hace falta tocar código — la app las detecta sola con el patrón `{prefijo}_dd_mm_yyyy` en el nombre de carpeta y `{M|T|R}{n}p{punto}{especie}{medida}` en el nombre de archivo.
