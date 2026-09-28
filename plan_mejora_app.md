# Plan — Mejora de la aplicación: más clara, más útil y coherente

Fecha: 2026-09-28 · Estado: **propuesta, pendiente de tus decisiones (§7)** · Prioridad: **va antes
que `plan_mejora_paper.md`**. El paper se escribe después, a partir de lo que muestre la app.

**Regla de alcance:** no se agregan funcionalidades nuevas. Se corrige, se reorganiza, se unifica
y se explica lo que ya existe: las 5 páginas, la alerta de Telegram y los módulos de `src/`.

**Principio rector:** *cada página responde una pregunta, y un mismo número vale lo mismo en toda
la app.* Hoy la misma hoja puede tener tres "severidades" distintas según dónde se mire, y "Sana"
significa cosas distintas en cada página. Eso es lo primero que hay que resolver.

---

## 0. Resumen del diagnóstico

1. **Hay un riesgo inmediato en Telegram.** El registro de "archivos ya vistos"
   (`.state/last_run.json`) es del 17/07 y tiene 576 archivos; hoy hay 2377. El próximo clic en
   "Verificar y analizar nueva data" mandaría **~1800 archivos como nuevos**, en decenas de mensajes.
   Además, si el envío falla, el registro se guarda igual y esas novedades no se vuelven a avisar
   (`app.py:72`). **Nadie debería tocar ese botón hasta hacer la tarea F0.2.**
2. **Un mismo concepto significa cosas distintas en páginas distintas:**
   - **"Sana"** incluye a las hojas **maduras**, cuyo estado es desconocido (lo dice la propia
     página 4). En la página 2, "Sana vs Con roya" mezcla hojas maduras y tiernas, que es el mismo
     problema de la Tabla I del paper.
   - **"Severidad"** se calcula de 3 formas:
     - página 4 y Telegram: ancla sana = todas las hojas T, promediando archivos;
     - página 5: ancla sana = hojas T de las 2 primeras campañas, promediando fechas;
     - el resumen de la página 4 promedia archivos y no hojas.
   - **Los colores de "Madura" y "Tierna" cambian entre páginas** (`GROUP_COLORS` frente a
     `LEAF_TYPE_COLORS`).
3. **La estadística de las páginas 2 y 3 usa puntos como si fueran hojas independientes** y mezcla
   las 12 campañas. Muestra Shapiro, ANOVA, Kruskal-Wallis y Dunn, pero nunca dice en una frase si
   el índice separa o no los grupos.
4. **Falta claridad de lenguaje:**
   - textos sin tildes ("deteccion", "Indices") en las páginas 1–4 y con tildes en la 5;
   - campañas con nombres técnicos (`Roya_15_07`, `C1_29_06`, `Campaña_10_08`) en vez de fechas;
   - jerga sin explicar en la página 5 (Δ\*, FDR, robust z, Theil-Sen);
   - el subtítulo de la app dice "Bourbon · Pacamara" aunque hay 4 especies;
   - la página de inicio menciona 3 de las 5 páginas;
   - la escala de riesgo describe **plantas enteras** ("defoliación", "muerte de la planta") a
     partir de 3 puntos de **una hoja**.
5. **Hay código repetido y lento.** Las páginas 2, 3 y 4 recalculan los índices de cada archivo en
   cada interacción, cada una con su propio bucle. La página 5 ya tiene una tabla cacheada que
   podrían usar todas. Además, los controles de suavizado de las páginas 1–3 cambian los números
   solo en esa página, así que la app deja de ser coherente consigo misma.

---

## 1. Para quién es cada parte y qué pregunta responde

| Usuario | Qué necesita | Dónde |
|---|---|---|
| **Vos, investigador** | Revisar datos, explorar y validar resultados | Páginas 1–5 |
| **Advisor y revisores** | Entender el método y confiar en los números | Textos de ayuda, glosario, `METODOLOGIA.md` |
| **Técnico de campo** | Saber qué hoja revisar | Alerta de Telegram |

**Mapa propuesto (mismas páginas, reordenadas por pregunta):**

| Página | Pregunta que responde | Cambio principal |
|---|---|---|
| **Inicio** | ¿Qué datos hay, están bien y qué hay de nuevo? | Inventario por **tipo de hoja** y fecha, un recuadro de **calidad de datos** y una vista previa de la alerta antes de enviarla |
| **1. Espectros** | ¿Cómo se ve la reflectancia de estas hojas? | Color por tipo de hoja y un promedio **por grupo**, no de todo lo seleccionado |
| **2. Índices** | ¿Qué índices separan hojas con roya de hojas sin roya? | Una tabla-resumen con veredicto en palabras, calculada **por hoja-fecha** |
| **3. Especies** | ¿Las variedades difieren entre sí con el mismo tipo de hoja? | Comparar siempre el **mismo** tipo de hoja, sin mezclar hojas con roya |
| **4. Estado de las hojas** (hoy "Severidad") | ¿Cómo está hoy cada hoja madura? | Una fila por hoja y fecha, con la misma similitud que Telegram |
| **5. Evolución** | ¿Cómo cambia cada hoja en el tiempo y es por roya o por edad? | Pestañas en vez de 10 secciones, lenguaje llano y lo técnico plegado |

---

## 2. Decisiones transversales (se aplican a toda la app)

| ID | Decisión | Qué resuelve |
|---|---|---|
| **X1** | **"Tipo de hoja" como agrupación principal:** Tierna (T), Madura (M), Con roya (R) y Vieja (V), con la explicación "Tierna/Madura = sin roya **visible**; su estado real no se conoce". `health_status` queda como dato interno. | Problema 2: "Sana" engañoso |
| **X2** | **Campañas mostradas por fecha** (`15/07/2026`) en filtros, tablas y ejes. El `campaign_id` sigue existiendo por dentro. | Nombres técnicos |
| **X3** | **Una sola tabla de índices por archivo, cacheada**, que usan todas las páginas y la alerta. Hoy es `temporal.file_indices`; pasaría a un módulo común. Se cachea también en disco, así la primera carga no tarda 20–40 s cada vez que se reinicia Streamlit. | Velocidad, código repetido, números distintos |
| **X4** | **Unidad por defecto: hoja-fecha.** Se promedian las repeticiones → los puntos → la hoja, solo con p1–p3. La tabla por punto queda como detalle descargable. | Pseudo-réplica |
| **X5** | **Una sola definición de "similitud con roya"** (ver D3), con el mismo número en la página 4, la página 5 y Telegram. Las variantes S1 y S2 de la página 5 quedan como **análisis de sensibilidad**, plegadas. | Tres severidades |
| **X6** | **Una sola estadística** en `stats_utils`: por índice, mediana por grupo, tamaño de efecto (δ de Cliff), p de Mann-Whitney o Kruskal-Wallis con corrección de Holm, y un **veredicto en palabras** ("separa claramente", "diferencia débil", "no separa"). Los tests intermedios van a "Detalle técnico". | Estadística ilegible |
| **X7** | **Parámetros de procesamiento fijos** (Savitzky-Golay 41/2, 440–1000 nm) y visibles en un solo lugar. Se quitan los controles de las páginas 2 y 3; en la página 1 quedan bajo "Avanzado", con un aviso de que solo cambian ese gráfico. | Incoherencia entre páginas |
| **X8** | **Índices:** quitar FSR (idéntico a NDVI) y, si aceptás D2, mostrar los nombres estándar (ND705 en vez de EDI, CRI1 en vez de RCI) con una etiqueta de transición "(antes EDI)". | Duplicado y nombres incorrectos |
| **X9** | **Vocabulario, colores e idioma únicos:** español con tildes en toda la interfaz; una paleta por tipo de hoja (la validada para daltonismo de la página 5) y otra por especie; glosario en Inicio. | Claridad |
| **X10** | **Calidad de datos visible en un solo lugar (Inicio):** qué se excluye y por qué (Pacamara no susceptible: 432 archivos; especie pendiente de "vieja": 45; nombres no reconocidos: 5; puntos p4–p6), hojas-fecha atípicas del control de calidad y valores imposibles (mNDVI705 > 1). | Lo que hoy se filtra en silencio |

---

## 3. Plan por fases

### F0 — Proteger lo que funciona (primero, antes de cualquier cambio)

| ID | Tarea | Criterio de aceptación |
|---|---|---|
| F0.1 | Commitear el trabajo pendiente (página 5, `temporal.py`, docs, planes) y crear el tag `app-antes-de-pulir`. | `git status` limpio y tag creado. |
| F0.2 | **Arreglar el registro de Telegram:** (a) identificar los archivos por **ruta relativa + contenido** en vez de ruta absoluta + fecha de modificación, que cambia al mover o clonar la carpeta; (b) **no guardar el registro si el envío falla**; (c) al actualizar a la versión nueva, dar la opción de marcar todo lo actual como visto, sin avisar. | Mover la carpeta del proyecto no genera novedades. Un envío fallido deja las novedades pendientes. |
| F0.3 | Agregar `matplotlib` a `requirements.txt`: lo usa `make_ieee_figures.py` y hoy falta. | `pip install -r requirements.txt` alcanza para todo. |
| F0.4 | Prueba de humo: `AppTest` que abre las 5 páginas con los filtros por defecto, más un recorrido real en el navegador. | 0 excepciones. Es la red de seguridad para todo lo que sigue. |

### F1 — Núcleo común en `src/` (sin cambiar lo que se ve todavía)

| ID | Tarea | Archivos | Criterio de aceptación |
|---|---|---|---|
| F1.1 | Tabla de índices por archivo única y cacheada, también en disco (X3). Incluye tipo de hoja, fecha y marca de control de calidad. | `processing.py` o módulo común, `temporal.py` | Las páginas 2–5, `severity.py` y `make_ieee_figures.py` la usan. Ningún bucle propio de `calcular_indices` en las páginas. |
| F1.2 | Funciones de agregación únicas (archivo → punto → hoja-fecha), con p1–p3. | idem | La hoja-fecha de la página 2 = la de la página 5 = la de Telegram, con tolerancia 1e-9 (se extiende el chequeo que ya existe en `evoluciontemporal.md` §4). |
| F1.3 | Similitud con roya única (X5, D3): anclas **promediadas por fecha** (hoy promedian archivos, así que julio pesa 3 veces más), **sin FSR** y **sin las hojas-fecha atípicas**. | `severity.py`, `temporal.py` | Mismo número en la página 4, la página 5 y Telegram para la misma hoja-fecha. El ancla de CRI1 de Pacamara deja de estar inflada ~7 veces. |
| F1.4 | Estadística única con veredicto (X6). | `stats_utils.py` | Una función devuelve la tabla-resumen y otra el detalle técnico. |
| F1.5 | Etiquetas y colores únicos (X1, X2, X9): `leaf_type_label()`, `campaign_label()` y una paleta. | `config.py`, `ui.py` | Ninguna página define colores o etiquetas propias. |
| F1.6 | Regla de control de calidad extendida a valores imposibles (mNDVI705 > 1 o < 0, reflectancia negativa en bandas usadas). Solo **marca**, no excluye. | `temporal.py` | Aparecen marcados el 24/08 y el 31/08 (Pacamara) y el punto de Bourbon M1 del 24/08. |

### F2 — Página por página

**Inicio (`app.py`)**
- Orden nuevo: (1) qué hay (inventario por especie × tipo de hoja y por fecha);
  (2) **calidad de datos** (X10); (3) **novedades y alerta**; (4) glosario y "qué responde cada página".
- La alerta pasa a dos pasos con el mismo código de hoy: **"Revisar novedades"** muestra las
  tarjetas por hoja → **"Enviar a Telegram"**. Así nada sale sin que lo veas, y la vista previa
  sirve también como resumen de la última campaña.
- Corregir el subtítulo ("4 especies"), la navegación (las 5 páginas) y el texto que dice que M y
  T se registran como "Sana".

**1. Espectros**
- Color por **tipo de hoja**, con la hoja en el trazo y el detalle en el cursor. Hoy las 12 fechas
  de M1 comparten color y no se distinguen.
- "Promedio ± SD" se calcula **por grupo visible**. Hoy promedia todo lo seleccionado, incluso roya
  y no roya juntas.
- Eje X desde 440 nm (como la página 5 y las figuras) y eje Y automático, con un aviso si hay
  reflectancia negativa.
- Suavizado bajo "Avanzado" (X7).

**2. Índices**
- Agrupar por **tipo de hoja** (T / M / R / V) en lugar de 3 dimensiones que se pisan.
- **Arriba, la respuesta:** tabla-resumen de 7 índices × veredicto (X6), por hoja-fecha, y debajo
  los boxplots (un punto por hoja-fecha, con la forma según la hoja).
- Las dos tablas grandes y los tests intermedios bajan a expanders de "Datos" y "Detalle técnico".
- Aviso fijo: "hay 1 sola hoja con roya por variedad: esto describe esa hoja en N fechas".

**3. Especies**
- Selector de **un** tipo de hoja (por defecto Tierna). Nunca se mezclan hojas con roya en una
  comparación entre variedades.
- Misma tabla-resumen que la página 2. Canéfora y Cuscatleco etiquetadas "control sin roya".

**4. Estado de las hojas** (hoy "Severidad de Roya")
- Unidad **hoja**: una fila por hoja madura (Bourbon M1, M2; Pacamara M1, M2) y columnas por fecha,
  como mapa de calor de similitud. Se eliminan el "resumen por especie", que promedia 12 semanas y
  varias hojas, y el boxplot por punto.
- En la misma vista, T y R1 como referencia (≈0 % y ≈100 % esperados). Si una T sale alta, es una
  señal de problema de medición, no de roya.
- "Índices vs. referencias" por hoja y fecha elegida, no promediado sobre todo.
- Textos: "similitud espectral con la hoja con roya", sin descripciones de planta entera (D4).

**5. Evolución temporal**
- Cinco pestañas en vez de 10 secciones:
  **Resumen** (los hallazgos que ya se recalculan solos) · **Hojas maduras** (sección 1) ·
  **¿Roya o edad?** (secciones 2–3) · **Detalle por hoja** (secciones 5–9) ·
  **Datos y calidad** (sección 4, tabla 10 y control de calidad).
- Lenguaje llano con el término técnico entre paréntesis:
  - Δ\* → "cambio corregido por las hojas tiernas (Δ\*)";
  - FDR → "significativa tras corregir por pruebas múltiples";
  - "robust z", Theil-Sen, S1/S2 y autocorrelación → al "Detalle técnico".
- La similitud por defecto es la de X5, y S1/S2 van como sensibilidad.
- Mover los helpers de gráficos (~400 líneas) a un módulo, para que la página sea legible.

### F3 — Alerta de Telegram

| ID | Cambio |
|---|---|
| F3.1 | Enfocar la alerta en las **hojas maduras** (las de estado desconocido). T y R1 van en una línea de "control de referencia": si T sale alta o R1 sale baja, se avisa que la medición de ese día es dudosa. |
| F3.2 | Texto de la tarjeta: "Similitud con la hoja con roya: 34 %", las clases de riesgo según D4 y una acción concreta ("revisar esta hoja en campo"). Sin afirmaciones sobre la planta entera. |
| F3.3 | Umbral de negrita alineado con las clases (hoy 0,66, heredado de la escala vieja de 3 niveles). |
| F3.4 | Idioma según D1. |
| F3.5 | Marcar en la tarjeta si la hoja-fecha tiene control de calidad dudoso o menos de 3 puntos. |

### F4 — Textos, ayuda y glosario

- Un texto de "Cómo leer esta página" arriba de cada página, en 2–3 líneas y con la misma
  estructura: qué muestra, qué **no** se puede concluir y la unidad (hoja-fecha).
- Glosario único en `config.py`, visible en Inicio y referenciado desde cada página: tipo de hoja,
  hoja-fecha, similitud con roya, anclas, control de calidad, Δ y Δ\*, y los nombres de índices
  con fórmula y cita.
- Revisión ortográfica completa: tildes, "Canéfora" y mayúsculas consistentes.

### F5 — Documentación del repo

| ID | Tarea |
|---|---|
| F5.1 | `README.md` corto: qué es, cómo correrlo, qué responde cada página y el flujo "agregar campaña → revisar → enviar alerta". |
| F5.2 | `METODOLOGIA.md` como única fuente de verdad del método: diseño, agregación, índices, similitud, control de calidad y estadística. La app enlaza a él y el paper saldrá de él. |
| F5.3 | `ESTADO_PROYECTO.md`: separar la bitácora histórica (`docs/bitacora.md`) de lo vigente y corregir lo desactualizado. Hoy dice que no hay repo git, que `roya/` no está ignorado y que 14/09 y 21/09 no están commiteadas. |
| F5.4 | `ESTADO_ROYA.md` se fusiona con la sección de similitud de `METODOLOGIA.md`. Hoy tiene punteros a `app.py`, un ejemplo con CARI y una tabla de rangos vieja. |
| F5.5 | Corregir comentarios falsos en el código: "ningún índice usa < 500 nm" (mNDVI705 usa 445), `_severity_baselines()` en `app.py`, "7 índices". |

### F6 — Verificación final

| Chequeo | Criterio |
|---|---|
| Coherencia numérica | Para 3 hojas-fecha elegidas al azar, el valor de cada índice y la similitud coinciden en las páginas 2, 4 y 5 y en Telegram. |
| Humo | `AppTest` de las 5 páginas con varias combinaciones de filtros: 0 excepciones. |
| Navegador | Recorrido real de las 5 páginas (incluye la animación, que nunca se probó en un navegador) con capturas. |
| Rendimiento | Con la caché en disco, cada página abre en menos de 5 s después del primer uso. |
| Claridad | Prueba con alguien del equipo que no hizo la app: ¿entiende qué responde cada página en menos de 1 minuto? |

---

## 4. Qué cambia en los números (para que no sorprenda)

| Cambio | Efecto |
|---|---|
| Similitud con anclas por fecha, sin FSR y sin atípicos (F1.3) | Cambian los % de la página 4 y de Telegram. El que más cambia es CRI1 en Pacamara. |
| Unidad hoja-fecha en las páginas 2 y 3 (X4) | Los p-valores suben (hay menos n "falso"); los tamaños de efecto se mantienen. |
| Agrupar por tipo de hoja (X1) | "Sana vs Con roya" pasa a ser "Tierna / Madura / Con roya". Con eso, EDI/ND705 separa claramente la roya de la madura y débilmente de la tierna (ver `plan_mejora_paper.md` §1.4). |
| Quitar FSR (X8) | 7 índices en lugar de 8 en todas partes. |

Nada de esto borra datos: todo lo excluido o marcado sigue visible en "Calidad de datos".

---

## 5. Fuera de alcance

- Páginas, gráficos o métricas nuevas; modelos predictivos o clasificadores.
- Automatizar la alerta con un servidor en segundo plano: sigue siendo un botón, como elegiste.
- Cambiar el formato de los archivos o la organización de `data/`.
- El paper: se retoma cuando la app esté cerrada (`plan_mejora_paper.md`).

---

## 6. Orden de ejecución

1. **F0 completo.** F0.2 es urgente.
2. Tus respuestas a §7.
3. **F1**: el núcleo. Todo lo demás depende de esto.
4. **F2**, en este orden: Inicio → 2 → 3 → 4 → 1 → 5. Empiezo por donde hay confusión conceptual y
   dejo para el final la página más grande.
5. **F3** (Telegram), **F4** (textos) y **F5** (documentación).
6. **F6** (verificación) y una demo para vos.

Cada fase termina con un commit propio, así cualquier cambio se puede revertir por separado.

---

## 7. Decisiones que necesito de vos

Entre paréntesis, lo que recomiendo.

| # | Pregunta | Recomendación |
|---|---|---|
| **D1** | ¿La alerta de Telegram sigue en **inglés** o pasa a **español**? El técnico de campo es salvadoreño; el inglés venía de la figura del paper. | Español en Telegram. Una figura en inglés para el paper se puede hacer aparte. |
| **D2** | ¿Renombramos los índices a sus nombres estándar (ND705 en vez de EDI, CRI1 en vez de RCI) y quitamos FSR? | Sí, con "(antes EDI)" durante la transición. |
| **D3** | Ancla "sin roya" de la similitud: (a) **todas las hojas T**, como hoy en la página 4 y Telegram; (b) hojas T de las 2 primeras campañas, cuando eran de verdad tiernas, como la S1 de la página 5. | (a) con promedio por fecha y sin atípicos, y (b) como sensibilidad. (a) usa más datos y es lo que ya ve el técnico. |
| **D4** | Escala de riesgo: ¿mantener las 11 clases o reducir a 3–4 ("Sin señal / Revisar / Probable roya")? En cualquier caso se quitan las descripciones de planta entera. | Reducir a 4 clases: con 1 hoja con roya por especie no se puede sostener una escala fina. |
| **D5** | ¿Mantener la página 4 separada ("estado actual de cada hoja") o fundirla dentro de la 5? | Separada: la 4 es "¿cómo está hoy?" y la 5 es "¿cómo cambió?". |
| **D6** | ¿Quién más usa el dashboard además de vos (advisor, equipo de campo)? | Define cuánto texto de ayuda va en pantalla y cuánto en expanders. |
| **D7** | Las Pacamara "No susceptible" hoy se ocultan en todas las páginas. ¿Siguen ocultas, solo contadas en "Calidad de datos"? | Sí, ocultas pero contadas y explicadas. |
