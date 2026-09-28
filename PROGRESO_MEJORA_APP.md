# Progreso — Mejora de la app (ejecución autónoma)

Inicio: 2026-09-28. Ejecutando `plan_mejora_app.md` fase por fase mientras el usuario está fuera.
Este archivo se actualiza en cada paso: qué se hizo, qué se decidió y qué falta.

**Rama de trabajo:** `mejora-app` (se crea en F0.1 para no tocar `main` directo).

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
- [ ] F2 — Inicio
- [ ] F2 — página 2 (Índices)
- [ ] F2 — página 3 (Especies)
- [ ] F2 — página 4 (Estado de las hojas)
- [ ] F2 — página 1 (Espectros)
- [ ] F2 — página 5 (Evolución temporal)
- [ ] F3 — alerta de Telegram
- [ ] F4 — textos, ayuda y glosario
- [ ] F5 — documentación del repo
- [ ] F6 — verificación final

(Se marca [x] y se agrega una nota corta a medida que se completa cada ítem, más abajo.)

## Notas detalladas por tarea

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
