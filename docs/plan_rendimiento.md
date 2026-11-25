# Propuesta: rendimiento (arranque en la nube y clics en *Evolución temporal*)

Fecha: 2026-11-18. Estado: **P1 y P2 hechos el 2026-11-19 (resultados en § 6); falta medir en la nube.**
Antecedente: `docs/plan_fondo_blanco_tendencias_rendimiento.md` (almacén `data_cache/`, arranque
~36 s → ~11 s). Pendientes previos: `ESTADO_PROYECTO.md` § «Pendiente para la próxima sesión».

## 1. Problema
- El equipo reporta que la app en Streamlit Community Cloud tarda en arrancar.
- Al medir en local apareció un segundo problema que no estaba en la lista: **cada clic en
  *Evolución temporal* tarda ~4 s**, aunque todo esté en caché.

Regla de este trabajo: **ningún número de la app puede cambiar.** Solo cambia cuándo y cuántas
veces se calcula o se dibuja algo.

## 2. Mediciones (local, 2026-11-18, `main` en `081e8dc`, 20 campañas, 3809 `.txt`, 212 MB)

### 2.1 Arranque en frío
| Paso | Tiempo |
|---|---|
| Importar librerías (streamlit, pandas, numpy, scipy, plotly, statsmodels) | 2,65 s |
| Importar `src/` | 1,05 s |
| Huella de `data/` (`stat` de cada archivo) | 0,32 s |
| `scan_dataset` (descubrir y clasificar archivos) | 0,72 s |
| **Leer + sha1 de los 212 MB** (dentro de `store.build_store`) | **2,85 s** con el disco en frío (1,5 s en caliente) |
| Leer solo los parquet de `data_cache/` | 0,32 s (11 MB en RAM) |

El sha1 crece ~35 MB por campaña y el disco de la nube es más lento que el local, así que es el
candidato principal en la nube. **Falta medir en la nube** (ver § 4, paso 0).

### 2.2 Por página (`AppTest`; primera ejecución / recarga)
| Página | 1.ª | Recarga |
|---|---|---|
| Panorama (incluye cargar todo) | 5,6 s | 0,2 s |
| **Evolución temporal** | 4,9 s | **4,1 s** |
| Alerta de campo | 2,9 s | 1,8 s |
| Variedades | 1,5 s | 0,8 s |
| Índices | 1,1 s | 0,8 s |
| Espectros | 0,9 s | 0,6 s |
| Estado actual | 0,7 s | 0,3 s |
| Datos y calidad / Método | ≤0,3 s | ≤0,1 s |

### 2.3 Perfil de una recarga de *Evolución temporal* (cProfile, 7,2 s con el perfilador activo)
- **Construcción de figuras Plotly**: la mayor parte. ~1.175 trazos `Scatter` en 13 figuras; Plotly
  valida cada propiedad (`_set_property`, `validate_coerce`, `update`: ~1,9 s acumulados).
- **Plantilla `plotly_white+reflec`**: `merge_templates` se ejecuta en cada `go.Figure` → 0,88 s
  en 13 figuras.
- `make_subplots`: 0,74 s (7 llamadas). `temporal_plots.m_panels`: 1,36 s; `add_leaf_lines`: 1,16 s.
- **`temporal.leaf_trends`** (LOWESS + Mann–Kendall): 0,95 s, **sin caché**, se recalcula en cada clic.
- `views/evolucion.py::_familia`: 0,82 s.
- Las **5 pestañas** (y sus subpestañas) se dibujan completas en cada recarga, aunque se vea una.

## 3. Propuesta (ordenada por impacto esperado / riesgo)

### P1. *Evolución temporal*: de ~4 s a ~1 s por clic (no cambia ningún número)
1. **Plantilla combinada una sola vez.** En `src/ui.py`, registrar
   `pio.templates["reflec_full"] = pio.templates["plotly_white"]` combinada con `reflec` y usarla
   como predeterminada, en vez de la cadena `"plotly_white+reflec"` que Plotly vuelve a combinar
   en cada figura. Ahorro esperado ~0,9 s por recarga (y algo en todas las páginas con gráficos).
2. **Dibujar solo la pestaña abierta.** Streamlit 1.59 admite `st.tabs(..., key=…, on_change="rerun")`
   y `tab.open`: envolver el contenido de cada pestaña en `if tab.open:`. Subir el mínimo de
   `requirements.txt` a la versión que lo introdujo (verificar cuál; hoy dice `>=1.38`).
   Cuidado: las claves de los widgets dentro de pestañas cerradas no se crean; revisar que
   ninguna pestaña lea `st.session_state` de otra.
3. **Caché de `leaf_trends`** con `st.cache_data`, con clave igual a sus entradas (tabla hoja-fecha,
   columnas, familia). Ahorro esperado ~0,95 s.
4. **Caché de figuras** pesadas (`m_panels`, grillas por índice): función cacheada que devuelve la
   figura (o su `dict`) según los parámetros de la selección. Medir después de 1–3; solo si hace falta.
5. Si sigue lento: `st.fragment` para que los controles de una pestaña recarguen solo esa pestaña.

### P2. Arranque: no leer los 212 MB en cada arranque (punto 2 pendiente en `ESTADO_PROYECTO.md`)
- En la app, `build_store` da por vigente un archivo del almacén si coinciden **ruta relativa +
  tamaño** (sin leerlo). La verificación por contenido (sha1) queda en `scripts/build_cache.py` y en
  `tests/test_store.py::test_almacen_versionado_esta_al_dia`, que ya falla si el almacén está
  desactualizado antes de commitear.
- **Riesgo a declarar:** un `.txt` reemplazado por otro del **mismo tamaño** sin regenerar el
  almacén pasaría sin detectarse en la app (la prueba sí lo detecta). Los archivos de SpectraSuite
  tienen tamaños muy parecidos, así que no es imposible: se documenta en `METODOLOGIA.md` y en
  `README.md` («después de cambiar datos, correr `build_cache.py`»).
- Ahorro esperado: ~1,5–3 s en local; más en la nube.

### P3. Solo si la nube sigue lenta después de P1 y P2
- Guardar en `data_cache/` resultados derivados (tablas hoja-fecha, `leaf_trends`, espectros medios,
  tendencias espectrales) con la misma huella de método.
- Leer del parquet solo las columnas de índices en las páginas que no usan espectros.
- Retrasar imports pesados (`statsmodels`, `scipy.stats`) a las páginas que los usan.
- *Alerta de campo* (1,8 s por recarga): perfilarla aparte.

## 4. Orden de trabajo
0. **Medir en la nube primero** (con la URL de la app, desde Chrome): tiempo hasta ver la app, y si
   se queda en la pantalla de Streamlit («in the oven» / «waking up»: contenedor de la plataforma,
   no se arregla desde el código) o en «Running…» (nuestro código). Anotar los tiempos aquí.
1. P1.1 → medir → P1.2 → medir → P1.3 → medir (un commit por paso, con el tiempo en el mensaje).
2. P2 → medir en local y en la nube.
3. Decidir P3 con los números.

## 5. Criterios de aceptación
- Recarga de *Evolución temporal* ≤ 1,5 s en local (hoy 4,1 s), medida con el mismo script de
  `AppTest` de § 2.2.
- Arranque en frío local (hasta mostrar Panorama) al menos 2 s más rápido que hoy.
- **Mismos números**: las tablas de `leaf_trends`, las tablas hoja-fecha y los índices por archivo
  son idénticos antes y después (prueba que los compare con una copia guardada hoy).
- Las 22 pruebas existentes siguen pasando; se agregan pruebas para la plantilla combinada, las
  pestañas perezosas (cada pestaña se dibuja sin errores al abrirla) y la verificación por tamaño.
- Tiempos en la nube anotados antes y después en este documento.

## 6. Resultados (2026-11-19, local)

Hechos: P1.1, P1.2, P1.3 y P2. P1.4 y P1.5 no hicieron falta. P3 queda pendiente de medir en la nube.

Recarga de *Evolución temporal* (`AppTest`, mediana de 3):

| Paso | Recarga (pestaña *Resumen*) |
|---|---|
| Antes | 3,86 s |
| P1.1 plantilla combinada una vez | 3,38 s |
| P1.3 `leaf_trends` en caché | 2,79 s |
| P1.2 solo se dibuja la pestaña abierta | **0,59 s** |

Recarga por pestaña después de P1: Resumen 0,61 · Hojas maduras 0,68 · Hojas maduras › Los 7 índices
1,19 · ¿Roya o edad? 1,03 · Detalle por hoja 1,03 · Detalle › Los 7 índices 1,27 · Datos y calidad
0,62 s. **Criterio (≤ 1,5 s) cumplido en todas.** Las otras páginas también ganan algo con la plantilla
(p. ej. *Variedades* 0,66 → 0,58 s).

Primera visita a *Evolución temporal* en un proceso nuevo: ~9,5 s → ~6,3 s. Con el disco en frío
(primer arranque tras un rato sin usar los archivos) llegó a 58,8 s antes del cambio: es el caso
normal de la nube y la razón principal de P2.

P2 (`build_store(verify_content=False)` en la app): 1,2 → 0,85 s con los archivos en la caché del
sistema. Lo que se ahorra de verdad es la lectura de los 212 MB con el disco en frío (~2,9 s en
local, más en la nube). Lo que queda (0,85 s) son ~3800 `stat` y la lectura de los parquet.

**Mismos números:** `tests/test_rendimiento.py` (plantilla idéntica; `leaf_trends` con caché =
cálculo directo) y `tests/test_store.py` (verificación rápida = tabla idéntica a la completa, sin
leer archivos; detecta archivos nuevos y cambios de tamaño; el riesgo del mismo tamaño queda fijado
en una prueba). 29 pruebas pasan.

**Comportamiento verificado en Chrome (headless, servidor local):** al cambiar el índice o el modo,
la pestaña y la subpestaña abiertas se mantienen; *Detalle por hoja* recibe el índice y el modo
elegidos en *Hojas maduras*; al volver, se conservan; ninguna excepción. AppTest no simula el estado
de las pestañas, por eso `tabs_evol` también se conserva con `keep_widget_state`.

**Costo aceptado:** antes, cambiar de pestaña era instantáneo (todo estaba dibujado de antemano);
ahora cada cambio de pestaña es una recarga de ~0,6–1,3 s. A cambio, cada control pasó de ~4 s a
≤ 1,3 s.

Intento descartado: medir los clics en Chrome esperando a que desaparezca el indicador «Running»
dio tiempos imposibles (0,2 s para una recarga que AppTest mide en 3,9 s). Los tiempos válidos son
los de `AppTest`.

Cambios: `src/ui.py` (plantilla `reflec_full`, `keep_widget_state`), `src/temporal.py`
(`leaf_trends` con caché), `src/store.py` (`verify_content`), `views/evolucion.py` (pestañas
perezosas), `.streamlit/config.toml` (silencia el aviso de log del patrón de estado),
`requirements.txt` (`streamlit>=1.59`, necesario para `st.tabs(on_change=…)` y `.open`).

## 7. Cómo se midió (para repetirlo)
- Arranque: script con `time.perf_counter()` alrededor de imports, `parser.data_fingerprint`,
  `parser.raw_dataset`, lectura + sha1 de `data/**/*.txt`, `store.build_store(write=False)` y
  `store._read_store`.
- Páginas: `AppTest.from_file("views/<página>.py").run()` y una segunda `.run()` (recarga).
  Nota: Panorama lanza `KeyError: 'url_pathname'` con `AppTest` suelto (por `st.page_link` sin
  navegación); no ocurre en la app.
- Perfil: `cProfile` activado dentro del hilo del script con `threading.setprofile`.
