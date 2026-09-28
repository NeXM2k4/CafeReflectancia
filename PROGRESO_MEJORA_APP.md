# Progreso — Mejora de la app (ejecución autónoma)

Inicio: 2026-09-28. Ejecutando `plan_mejora_app.md` fase por fase mientras el usuario está fuera.
Este archivo se actualiza en cada paso: qué se hizo, qué se decidió y qué falta.

**Rama de trabajo:** `mejora-app` (se crea en F0.1 para no tocar `main` directo). **No se hizo
merge a `main`** — queda para que el usuario revise el diff y decida.

## Resumen de cierre (para leer primero)

**Hecho:** F0 completo (incluye un arreglo urgente: el registro de Telegram estaba
desactualizado desde julio y el primer click iba a generar ~1800 "novedades" falsas — resuelto
y el flujo pasa ahora por una vista previa obligatoria antes de enviar nada). F1 completo
(módulo único de índices, similitud y estadística). F2 completo en Inicio, páginas 1, 2, 3 y 4;
página 5 recibió solo un cambio dirigido (ver su nota) por riesgo/beneficio. F3 completo
(Telegram en español, 4 clases, sin FSR). F4 cubierto de forma incidental dentro de F2. F5
parcial (README nuevo, avisos de desactualización; falta `METODOLOGIA.md`). F6 completo con un
hallazgo sin resolver (ver su nota, requiere navegador real).

**Bugs reales encontrados y corregidos durante la verificación** (no estaban en el diagnóstico
original del plan): el ancla de similitud para RCI en Pacamara seguía inflada por el mismo
problema ya documentado en `ESTADO_PROYECTO.md` (ahora corregido automáticamente); y la similitud
que vería Telegram no coincidía numéricamente con la de las páginas 4/5 para la misma hoja-fecha
(orden de operaciones distinto) — corregido y verificado con diferencia 0.0 en las 191
hojas-fecha del dataset.

**9 commits** en la rama sobre `main` (uno de ellos el checkpoint inicial con trabajo previo a
esta sesión), cada fase con su propio commit (`git log main..mejora-app`). 6/6 pruebas de humo
pasan en el estado final. `main` queda intacto — nada de esto se fusionó.

## Decisiones D1–D7 (tomadas por mí, siguiendo mis propias recomendaciones del plan,
porque el usuario está fuera y pidió avanzar con todas las fases; quedan documentadas
para que las revise al volver — cualquiera se puede deshacer)

| # | Decisión tomada |
|---|---|
| D1 | Telegram pasa a **español**. |
| D2 | Se **renombran** los índices a sus nombres estándar (ND705, CRI1) mostrando "(antes EDI/RCI)" durante la transición. **FSR se quita** de las vistas activas (duplicado de NDVI); queda documentado por qué. |
| D3 | Ancla sana = **todas las hojas T, promediada por fecha, sin atípicos** (opción a). La versión "solo primeras campañas" queda como sensibilidad en la página 5 (ya existe: S1/S2). |
| D4 | Escala de riesgo reducida a **4 clases** ("Sin señal" / "Vigilar" / "Revisar en campo" / "Alta similitud con roya"), sin descripciones de planta entera. |
| D5 | Página 4 se mantiene **separada** de la página 5. |
| D6 | Asumo que además del usuario usan la app el equipo de campo (vía Telegram) y potencialmente el advisor — texto de ayuda visible pero conciso, detalle técnico en expanders. |
| D7 | Pacamara "No susceptible" sigue **oculta** en las páginas de análisis, pero contada y explicada en "Calidad de datos" de Inicio. |

## Registro de avance

- [x] F0.1 — commit de lo pendiente + rama `mejora-app` + tag
- [x] F0.2 — arreglo del registro de Telegram (riesgo inmediato)
- [x] F0.3 — matplotlib en requirements.txt
- [x] F0.4 — prueba de humo (AppTest)
- [x] F1.1 — tabla de índices única y cacheada
- [x] F1.2 — agregación única archivo→punto→hoja-fecha
- [x] F1.3 — similitud con roya única
- [x] F1.4 — estadística única con veredicto
- [x] F1.5 — etiquetas y colores únicos
- [x] F1.6 — control de calidad extendido a valores imposibles
- [x] F2 — Inicio
- [ ] F2 — página 2 (Índices)
- [ ] F2 — página 3 (Especies)
- [x] F2 — página 4 (Estado de las hojas)
- [x] F2 — página 1 (Espectros)
- [~] F2 — página 5 (Evolución temporal) — parcial, ver nota
- [x] F3 — alerta de Telegram
- [~] F4 — textos, ayuda y glosario (mayormente cubierto dentro de F2, ver nota)
- [~] F5 — documentación del repo (README nuevo + avisos de desactualización; METODOLOGIA.md pendiente)
- [x] F6 — verificación final

(Se marca [x] y se agrega una nota corta a medida que se completa cada ítem, más abajo.)

## Notas detalladas por tarea

### F4 — Textos, ayuda y glosario
No se hizo como fase separada: cada pagina reescrita en F2 ya incorporo su propio "como leer
esta pagina" (captions al inicio, avisos de n=1 hoja con roya, notas de que NO se puede
concluir) y el glosario central quedo en Inicio (seccion 4), con enlaces conceptuales desde las
demas paginas. **No hecho:** una revision ortografica pasada por **todas** las paginas
(tildes/mayusculas consistentes) — las paginas reescritas (Inicio, 1-4) usan tildes en el texto
nuevo; la pagina 5 ya las tenia. `src/ui.py` y algunos textos viejos de las paginas 1-4 que no
se tocaron directamente pueden seguir sin tildes en frases sueltas.

### F5 — Documentacion del repo
- **Hecho:** `README.md` nuevo (no existia) con como correr la app, que responde cada pagina,
  el flujo de agregar una campaña, la estructura del repo y las limitaciones centrales.
- **Hecho:** avisos de desactualizacion agregados al inicio de `ESTADO_PROYECTO.md` y
  `ESTADO_ROYA.md`, mas correcciones puntuales de las afirmaciones ya falsas (repo git, `roya/`
  en `.gitignore`, campañas sin commitear, pendiente de FSR resuelto por eliminacion en vez de
  redefinicion).
- **Hecho:** comentario desactualizado en `src/processing.py` (`_severity_baselines()` en
  `app.py` → ahora `severity_baselines()` en `src/severity.py`).
- **No hecho (queda pendiente):** `METODOLOGIA.md` como fuente unica de verdad del metodo
  (F5.2) — es la pieza que faltaria para que el paper (`plan_mejora_paper.md`) pueda apoyarse en
  ella directamente. Tampoco se separo la bitacora historica de `ESTADO_PROYECTO.md` en un
  `docs/bitacora.md` (F5.3): se opto por el aviso al inicio como paso intermedio menos
  arriesgado dado el tiempo disponible.

### F6 — Verificacion final
- **Pruebas de humo:** 6/6 pasan de forma consistente en cada fase (se corrieron ~15 veces
  durante la sesion, siempre en verde antes de cada commit).
- **Combinaciones de filtros:** las 4 especies probadas en las paginas 1-4 por separado (16
  combinaciones, 14 aplicables — Canefora/Cuscatleco no aplican en la pagina 4 por diseño, eso
  es correcto) + casos limite especificos (un solo tipo de hoja, una sola campaña, seleccion de
  hoja R, "sin recorte" con la similitud unificada): **0 excepciones reales** en todos los casos.
- **Coherencia numerica:** verificada explicitamente en 3 puntos (F1.1/F1.2 vs. el codigo viejo,
  F1.3 vs. el ancla vieja de RCI, y X5 entre `leaf_date_similarity`/`leaf_severity_reports`/
  pagina 5) — todas con diferencia 0.0 tras las correcciones.
- **Rendimiento:** con la cache en disco de `file_index_table` calentada, Inicio y las paginas
  1-4 cargan en 0.5-3.6 s desde un proceso nuevo. La pagina 5 tarda ~13-17 s en frio (calcula
  tendencias espectrales y espectros medios que no tienen cache en disco, solo `st.cache_data`
  en memoria) pero baja a ~6 s al cambiar de especie **dentro de la misma sesion** ya calentada.
  No se optimizo mas alla de eso: agregar cache en disco a esos calculos tambien queda como
  posible mejora futura si se vuelve molesto en uso real.
- **Hallazgo sin resolver, para investigar con calma:** al simular 3 interacciones seguidas en
  el mismo `AppTest` de la pagina 5 (cambiar especie dos veces), la tercera interaccion lanzo un
  `KeyError` de Streamlit sobre una key de `session_state` de un widget (`toggle`) que no
  aparecio en las pruebas normales (una sola interaccion por instancia, que es como se probo el
  resto de la sesion). Puede ser una particularidad del arnes de pruebas `AppTest` con widgets
  condicionales, o una señal real de un problema de `session_state` en la pagina 5 al navegar
  mucho sin recargar. **Recomendacion:** probar la pagina 5 en un navegador real cambiando de
  especie varias veces seguidas (esto ya estaba pendiente desde `evoluciontemporal.md`: nunca se
  probo en un navegador real, solo con `AppTest` de una interaccion por corrida).
- **No verificado:** la app en un navegador real (Chrome no respondio en la sesion anterior,
  segun `evoluciontemporal.md`; no se reintento aqui por no tener acceso a la extension en esta
  sesion). Todo lo de arriba es via `AppTest` (ejecuta el script real de Streamlit sin
  navegador) y pruebas de consistencia numerica directas.

### F3 — Alerta de Telegram (D1 español, F3.1, F3.2, F3.3, F3.5)
`src/notifier.py` reescrito en español (antes en ingles, ver D1). Cambios:
- `INDICES_ORDER` sin FSR (7 indices, coherente con `DISPLAY_INDICES`).
- Texto de la tarjeta: "Similitud con la hoja con roya: X %" en vez de "Estimated severity...
  healthy reference leaf" (X5/D4: ya no se habla de severidad de planta).
- **F3.1:** hojas Tierna/Con roya que llegan en el mismo lote (son la referencia que define las
  anclas) llevan la nota "(hoja de referencia sana/con roya — no requiere accion en si misma)".
- **F3.5:** si la hoja se midio con menos de 3 puntos esa fecha, la tarjeta lo marca con ⚠️.
- **F3.3:** el umbral de negrita (0.66) no se toco: coincide casi exacto con el nivel "Revisar
  en campo" de la escala nueva (2/3 = 0.667), documentado el porque en el comentario del codigo.
- Probado: tarjetas de ejemplo (Bourbon T1/M1, campaña Roya_21_07) se ven correctamente en
  español; el empaquetado de mensajes sigue bajo el limite de 4096 caracteres de Telegram
  (maxlen 3963/4096 en una prueba con 4 especies).
- **Nota de redaccion pendiente de pulir** (no bloqueante): en una hoja de referencia (T/R), el
  texto de accion generico ("Revisar esta hoja...") queda debajo de la nota "no requiere accion
  en si misma", lo que puede leerse contradictorio a primera vista. Cosmetico, no afecta los
  numeros.

### F2 — página 5: hecho parcialmente (decision razonada, no fue solo falta de tiempo)
La pagina 5 (1244 lineas) es la mas grande y la mejor probada del proyecto (`evoluciontemporal.md`
documenta rondas previas de test con AppTest y 15 combinaciones de filtros). Reescribirla
completa a pestañas + mover ~400 lineas de helpers a un modulo es una transformacion mecanica
grande (reindentar cientos de lineas bajo `with tab:`) con alto riesgo de romper algo que un
smoke test (solo detecta excepciones, no corrección visual) no atraparía. Decidí **no** hacer
esa reescritura completa esta sesion, y en cambio:

- **Hecho:** agregada la **similitud unificada (opcion "U")** al selector de anclas de la
  seccion 7, junto a S1/S2. Verificado que da el mismo numero que `leaf_date_similarity` y que
  `leaf_severity_reports` (Telegram) para las mismas hojas-fecha.
- **Decision importante, no un bug:** S1/S2 (anclas propias de esta pagina, congeladas a las
  primeras 2 campañas) **se mantienen como principal** en esta pagina, no U. Motivo documentado
  en el propio `evoluciontemporal.md` §5.3: usar "todas las hojas T" como ancla (la opcion
  unificada) mezcla hoja tierna con hoja casi madura porque las T envejecen 12 semanas — es
  exactamente el problema que S1 evita a proposito para *esta* pregunta (evolucion en el
  tiempo). Forzar la misma ancla en todos lados hubiera sido peor, no mejor. Se agrego una
  explicacion en pantalla de por que esta pagina usa una ancla distinta al resto de la app.
- **Verificacion durante el desarrollo:** al conectar "U", los primeros numeros no coincidian
  con el chequeo anterior (2.0 % vs 4.43 %) — pero era una comparacion contra el valor *antes*
  del fix de `leaf_severity_reports`, no una regresion nueva. Re-verificado en un mismo proceso:
  `leaf_date_similarity` y `leaf_severity_reports` dan **exactamente 0.04431585467491947** para
  Bourbon M1 el 21/07, coincidiendo entre si.
- **No hecho, queda pendiente para la proxima sesion:** las 10 secciones no se agruparon en 5
  pestañas, ni se movieron los helpers de graficos a un modulo separado. El lenguaje tecnico
  (Δ*, FDR, robust z, Theil-Sen) sigue mayormente como estaba (ya tenia bastante explicacion en
  captions y expanders, revisado en la lectura inicial). Recomendacion para retomarlo: hacerlo
  en un cambio dedicado, seccion por seccion, con captura de pantalla antes/despues de cada una
  (no solo AppTest) antes de dar por buena la reorganizacion.

### D4 aplicada — Escala de riesgo reducida a 4 clases
`src/config.py`: `RUST_RISK_CLASSES` pasa de 11 clases (con descripciones de planta entera:
"defoliacion", "muerte de la planta") a 4 clases en español, describiendo **similitud
espectral** en vez de sintomas de planta: Sin señal de roya (0), Vigilar (1/3), Revisar en campo
(2/3), Alta similitud con roya (1). `RUST_RISK_ACTIONS` bajo de 5 a 4 acciones (una por clase).
`notifier._class_bounds()` corregido: asumia espaciado uniforme de 10 % (valido solo para 11
clases); ahora calcula el limite como el punto medio entre niveles adyacentes, generico para
cualquier cantidad de clases. Los nombres de identificadores (`RUST_RISK_CLASSES`,
`rust_risk_class()`, `rust_risk_action()`) se mantuvieron sin cambios a proposito para que la
pagina 5 (que ya las usaba para las lineas de fondo) heredara las 4 clases sin tocar su codigo.
Ajustado en la pagina 5 el throttle "cada 20%" de las etiquetas (pensado para 11 clases, dejaba
las 2 clases del medio sin etiqueta con solo 4).

### F2 — página 4 (renombrada `pages/4_Estado_Hojas.py`, antes `4_Severidad_Roya.py`)
Reescrita: unidad **hoja** (una fila por hoja, columnas = fecha) en vez de punto/archivo.
Mapa de calor de similitud por especie con T y R1 como filas de referencia (deberian salir cerca
de 0 % y 100 % por construccion). Se elimino el "resumen por especie" (promediaba 12 semanas y
2 hojas en un numero) y el boxplot por punto. Detalle por hoja+fecha elegida en vez de promedio
global. Titulo y textos usan "similitud espectral con roya", no "severidad".

**Bug real encontrado y corregido al verificar la unificacion (X5):** comparando el numero de
esta pagina contra el que production la ruta de Telegram (`leaf_severity_reports`) para la misma
hoja-fecha, salian **distintos** (4.43 % vs 2.0 % para Bourbon M1 el 21/07) — el orden de
operaciones no era el mismo: Telegram calculaba la mediana normalizada **por archivo** y despues
promediaba esas medianas; la pagina 4/5 promedia primero los indices crudos y normaliza una sola
vez. Se corrigio `leaf_severity_reports()` para usar el mismo orden (agregar indices crudos a
nivel hoja, un solo `severity_score()` al final). **Verificado tras el fix: diferencia 0.0 en
las 191 hojas-fecha del dataset**, comparando `leaf_date_similarity()` contra
`leaf_severity_reports()` alimentada con cada subconjunto especie+campaña por separado (simula
exactamente lo que veria Telegram con datos nuevos).

### F2 — Inicio (`app.py`)
Reordenado en 4 secciones numeradas: (1) que datos hay — metricas + pestañas "por especie y
campaña" / "por tipo de hoja" (antes solo estado sanitario Sana/Con roya, que mezclaba M+T como
"Sana"); (2) **calidad de datos**, tabla nueva que junta en un solo lugar los 6 tipos de
exclusion/marca que antes estaban repartidos o no se mostraban (Pacamara No susceptible,
especie pendiente, nombre no reconocido, puntos p4-p6, hojas-fecha atipicas de control de
calidad, mNDVI705 implausible), con un expander de detalle; (3) novedades y alerta (logica de
F0.2, sin cambios); (4) glosario + mapa de las 5 paginas.
Corregido: subtitulo global ("Bourbon · Pacamara" -> las 4 especies, en `src/ui.py`), metrica
"Especies" que contaba la categoria "especie pendiente" como una especie real (ahora la excluye
y lo explica en el tooltip), agregada `parser.raw_dataset()` (dataset sin filtrar, solo para
contar exclusiones) y `parser.campaign_options()` ya en uso (columnas del pivote muestran fecha
dd/mm/yyyy en vez de `Campaña_10_08`).



### F0.1 — Checkpoint
Rama `mejora-app` creada desde `main`. Commit `7008d79` con todo lo pendiente de la sesion
anterior (pagina 5, `temporal.py`, `evoluciontemporal.md`, `PAPER/`, ambos planes). Tag
`app-antes-de-pulir` en ese commit, por si hay que volver atras.

### F0.2 — Registro de Telegram (riesgo resuelto)
- `src/state.py`: `file_key()` ahora usa **ruta relativa a `data/` + hash sha1 (16 hex) del
  contenido**, cacheado con `st.cache_data` por archivo+mtime (mismo patron que
  `read_spectrasuite`). Ya no depende de la ruta absoluta ni de que el mtime se conserve al
  mover/clonar el proyecto.
- `app.py`: el flujo pasa a **dos pasos**. "Verificar y analizar nueva data" solo calcula y
  muestra la vista previa (tarjetas + resumen) en `st.session_state`; un boton nuevo "✅ Enviar a
  Telegram" hace el envio real. Si el envio falla, **no se guarda el registro** (las novedades se
  vuelven a mostrar la proxima vez en vez de perderse). Se agrego un botón "🧹 Marcar todo como
  visto (sin avisar)" para resetear la linea base sin enviar nada.
- **Migracion inmediata ejecutada:** el registro viejo (576 archivos, formato
  `ruta_absoluta|mtime`, del 17/07) se respaldo en
  `.state/last_run_backup_2026-09-28_pre_migracion.json` y se reemplazo por uno nuevo con los
  **1945 archivos actuales** del dataset filtrado, en el formato nuevo. Se hizo directo con
  `src.parser.get_dataset()` + `src.state.save_last_run()`, **sin llamar a la API de Telegram**.
  Motivo: cambiar el formato de la clave invalida cualquier registro viejo por completo, así que
  sin esta migracion el primer click en "Verificar" iba a mostrar ~1800 archivos como "nuevos" de
  una sola vez (ya no se enviarían solos gracias al paso de vista previa, pero seguía siendo un
  resultado sin sentido). De aqui en adelante, "Verificar" solo va a mostrar lo que se agregue a
  partir de ahora.
- Pendiente para el usuario: si en algun momento quiere notificar retroactivamente sobre alguna
  campaña vieja, puede restaurar el backup manualmente — se deja documentado, no se borra nada.

### F0.3 — matplotlib
Agregado `matplotlib>=3.8` a `requirements.txt` (lo usa `make_ieee_figures.py`, no estaba
declarado). Creado `requirements-dev.txt` con `pytest` para las pruebas.

### F1.1 / F1.2 — Modulo unico `src/indices.py`
- `file_index_table(dataset)`: unico lugar de la app que llama a `calcular_indices()`. Excluye
  solo nombre no reconocido y especie pendiente; no filtra puntos ni tipo de hoja (cada
  consumidor decide). Cache en memoria (`st.cache_data`) **y en disco**
  (`.state/file_indices_cache.pkl`, invalidado por huella sha1 de `(path, mtime_ns)` de los
  archivos seleccionados): primera carga 13,7 s con el dataset actual (1897 archivos), 0,4 s en
  la siguiente ejecucion del proceso.
- `point_table()` / `leaf_date_table()`: agregacion generica archivo→punto→hoja-fecha, solo
  p1-p3 por defecto (`TEMPORAL_VALID_POINTS`).
- **Verificado numericamente:** comparado contra `temporal.file_indices()` (la version vieja,
  con su propio bucle) para las 1843 filas M/T/R en p1-p3 → **diferencia maxima 0.0 en los 8
  indices**, 0 mismatches de `leaf_id`. `src/temporal.py` ahora importa el calculo desde aqui
  (su `file_indices()` quedo como envoltorio de 6 lineas que filtra y reordena columnas).

### F1.3 — Similitud con roya unica (anclas por fecha, sin FSR, sin atipicos)
`src/severity.py` reescrito: las anclas ya no promedian archivos (sobre-pesaban julio, que
tenia hasta 10 repeticiones por punto en las hojas con roya) sino **hojas-fecha** de
`leaf_date_table`, excluyendo las marcadas por `quality_flags()`. FSR desaparece de las anclas
(no se agrega su clave; `severity_score()` ya lo saltaba solo si no encontraba baseline, asi que
no hizo falta tocar `processing.py`).

**Verificado contra el codigo viejo** (recuperado del tag `app-antes-de-pulir`):

| Ancla | Vieja (por archivo) | Nueva (por fecha, sin atipicos) |
|---|---|---|
| Pacamara RCI "con roya" | **0.3541** | **0.0345** (−90 %) |
| Bourbon RCI "con roya" | 0.0500 | 0.0439 |
| Pacamara PRI "con roya" | -0.1671 | -0.1213 |
| Bourbon EDI "con roya" | 0.2650 | 0.2554 |

Confirma exactamente el problema que ya estaba documentado en `ESTADO_PROYECTO.md` §12 (el 10/08
de Pacamara R1 tenia la reflectancia hundida e inflaba el ancla de RCI ~7-10x) — con la ventaja
de que ahora la correccion es automatica (por fecha + control de calidad) en vez de depender de
excluir esa fecha a mano.

`leaf_severity_reports()` ahora filtra a p1-p3 (antes no filtraba, inconsistente con el resto de
la app) y usa `DISPLAY_INDICES` (sin FSR) para el detalle por indice de cada tarjeta.

### F1.6 — Control de calidad extendido
`src/indices.py::quality_flags()` es ahora el unico lugar con la regla de control de calidad
(antes vivia solo en `temporal.qc_flags()`, usado solo por la pagina 5). Se agrego una segunda
regla independiente de la historia de la hoja: `qc_implausible` (mNDVI705 fuera de
[-0.05, 1.05], indicio de reflejo especular en el azul — ver `evoluciontemporal.md` 12.4).
`qc_flag = qc_atipico OR qc_implausible` es lo que ahora excluyen las anclas de severidad.
`temporal.qc_flags()` quedo como envoltorio de una linea.

### F1.4 — Estadistica con veredicto
`src/stats_utils.py`: `summarize_indices(data, group_col, indices)` nueva, pensada para tablas
hoja-fecha. Por indice: n y mediana por grupo, δ de Cliff (si son 2 grupos), Mann-Whitney o
Kruskal-Wallis, **p ajustado por Holm** entre todos los indices de la llamada, y un veredicto en
palabras ("Separa claramente los grupos" / "Diferencia moderada" / "Diferencia debil" / "No
separa los grupos"). Probado con Bourbon M vs R (hoja-fecha): PRI/PSRI/EDI/NDRE/mNDVI705
"separan claramente" (p Holm < 0.003), NDVI y RCI "no separan" — coherente con el analisis
preliminar de `plan_mejora_paper.md` §1.4. La funcion vieja `compare_groups()` se conserva
intacta para el detalle tecnico (Shapiro, post-hoc).

### F1.5 — Etiquetas y colores unicos
`src/config.py`: `LEAF_TYPE_COLORS`/`LEAF_TYPE_LABELS`/`LEAF_NUM_DASH` (antes solo en el bloque
de la pagina 5, con **colores distintos** a los que usaban las paginas 2-4 vía `GROUP_COLORS`)
pasan a ser la **unica** definicion, cerca de arriba del archivo. `GROUP_COLORS["Madura"/"Tierna"
/"Vieja"/"Con roya"]` ahora leen de ahi, en vez de tener su propio hex. Se agrego `leaf_type_label()`
y `LEAF_TYPE_HELP` (una frase por tipo, para tooltips) y se agrego "V" (Vieja) al set de colores
validado (antes solo M/T/R). Se elimino el bloque duplicado que quedaba mas abajo en el archivo.
`src/parser.py`: `campaign_label()` / `campaign_options()` para mostrar fechas `dd/mm/yyyy` en
vez de ids tecnicos (`Roya_15_07`, `Campaña_10_08`) — listas para que cada pagina las use en sus
selectores de campaña durante F2.

### F0.4 — Prueba de humo
`tests/test_smoke_pages.py`: `AppTest` de Streamlit sobre las 5 paginas + Inicio, filtros por
defecto. **Las 6 pasan sobre el estado original** (antes de tocar nada de F1/F2) — es la linea de
base para detectar regresiones en cada fase siguiente. Se vuelve a correr al final de cada fase.
