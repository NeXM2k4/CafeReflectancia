# Revisión del paper y del proyecto, leída con los ojos del advisor

Fecha: 2026-10-01 · Paper: *Early Detection of Coffee Leaf Rust in Susceptible Varieties Using a
Portable Reflectance IoT Prototype* (versión enviada a CONCAPAN) · Fuentes: PDF del paper, las
tres revisiones, `data/` (cabeceras de SpectraSuite incluidas) y el pipeline de `src/`.

Todo lo marcado **[verificado]** se comprobó hoy contra los datos crudos con un script; lo marcado
**[28/09]** viene de la verificación previa de `plan_mejora_paper.md`.

---

## 0. Veredicto en una frase

> «El sistema es interesante y el seguimiento longitudinal es valioso, pero el paper enviado afirma
> una detección temprana que no se midió, con una estadística cuya unidad es incorrecta, sobre un
> grupo "con roya" que es **una sola hoja medida en dos días**, y con varias afirmaciones que sus
> propias figuras y metadatos contradicen. Así no lo firmo.»

Esa es la lectura más probable de alguien con su nivel de exigencia. La buena noticia es que **casi
todo se corrige con los datos que ya existen**, y que el proyecto tiene hoy más fuerza que el paper
enviado (12 campañas, controles sin roya, validación en el tiempo).

---

## 1. Lo que va a ver en los primeros cinco minutos

Ordenado por gravedad. Cada punto es algo que él puede comprobar solo mirando el PDF o pidiendo
los datos.

### 1.1 El grupo «rust-infected» es una hoja medida en dos días **[verificado]**

- En el período del paper (5 campañas de julio) la única hoja con roya por variedad es **R1**, y se
  midió **solo el 15/07 y el 27/07**. Los «n = 60» de las Figs. 3–4 son 2 fechas × 3 puntos × 10
  repeticiones de **la misma hoja**.
- Métodos dice «Two plants per variety… one leaf per category (H and R) from each plant», es decir
  2 hojas con roya por variedad. Los datos no lo respaldan.
- Consecuencia: ninguna prueba de hipótesis «roya vs sana» es interpretable. Lo que se comparó es
  *la hoja R1* contra *las hojas T1/T2*. Es un estudio de caso, no una muestra.

### 1.2 La figura principal contradice el texto **[verificado en el PDF]**

- El texto, el abstract y la conclusión dicen que **EDI** es el índice más consistente (p < 0.001).
  La **Fig. 6** marca EDI como **«ns» en Bourbon y en Pacamara**.
- La Fig. 6 marca NDVI, RCI y FSR como significativos (\*\*) en Bourbon y PSRI en Pacamara. El
  texto dice que esos cuatro **no** son significativos.
- Coincide con lo que reproduce el pipeline: con T vs R por punto, EDI da p = 0.094 (Bourbon) y
  0.071 (Pacamara) **[28/09]**.

### 1.3 La Tabla I no describe los grupos que dice el texto **[verificado]**

- «H» en la Tabla I es **maduras + tiernas juntas**. Los valores coinciden al tercer decimal con la
  media M+T: EDI Bourbon 0.438 = M+T (T = 0.336, M = 0.541). Pero el texto y las figuras dicen
  «healthy (H, young)» y usan solo tiernas (n = 90 = 2 hojas × 5 fechas × 9).
- **FSR es idéntico a NDVI** en todas las celdas, mientras Métodos dice que FSR usa 850 nm. El
  código usa 800 nm para ambos. El texto de Métodos no describe lo que se calculó.
- **Falta la fila de PSRI**, aunque el paper dice «ocho índices».

### 1.4 «Measurements at 7:00 a.m.» es falso según los propios archivos **[verificado]**

Cada archivo de SpectraSuite guarda la hora de medición en la cabecera:

| Campaña | Hora mínima | Mediana | Máxima |
|---|---|---|---|
| 29/06 | 7:59 | 10:41 | 12:29 |
| 06/07 | 8:00 | 10:35 | 12:16 |
| 15/07 | 7:28 | 9:12 | **16:59** |
| 21/07 | 9:49 | 11:22 | 13:35 |
| 27/07 | 8:02 | 11:52 | 14:47 |

- **Pacamara R1 el 15/07 se midió a las ~16:54, cinco horas y media después que las hojas sanas
  (~11:11).** El paper presenta a PRI como el índice con «el mayor cambio (407 % en Pacamara)», y la
  referencia que cita para PRI (Gamon et al. 1992) se titula literalmente *«…tracks diurnal changes
  in photosynthetic efficiency»*. Un físico lo va a ver de inmediato: el efecto de PRI está
  confundido con la hora del día.
- Tampoco existen en el repositorio los «environmental data (humidity, temperature, PM) recorded»
  que menciona Métodos.

### 1.5 Afirmaciones que el diseño no puede sostener

- **Detección temprana / antes de los síntomas** (título, abstract, discusión, conclusión): no hay
  ni una hoja asintomática infectada. Los revisores 2 y 3 lo marcaron. Frases como «This supports
  EDI's utility for early detection before visible symptoms appear» son un *non sequitur*.
- **Severidad de 11 clases** con descripciones de planta entera («defoliation», «plant death»)
  asignadas a partir de 3 puntos de una hoja. La Fig. 7 muestra R1 con «76 %», pero R1 *es* el
  ancla de 100 %: el número es circular.
- **«Clear quantitative threshold for early warning»**: no se reporta ningún umbral.
- **«Low-cost»** con un USB4000 + HL-2000: el revisor 2 lo señaló; no hay lista de materiales.
- **«IoT prototype»**: el espectrómetro va por USB a una computadora y la alerta se dispara con un
  botón en un dashboard. Es un *flujo de alerta conectado*, no un dispositivo IoT. Él lo va a
  preguntar.

### 1.6 Referencias **[28/09]**

- [6]: la revista es *Agronomy*, no *Agriculture*, y los autores son Soares, Martins y Siquieroli.
- [9] (CATIE 2018) y [10] (*J. Plant Pathol.* 2022): **no se encontraron**. De ellas salen las
  incidencias 9.44 % y 8.28 % de la introducción.
- [11]: existe, pero es arXiv:2407.14737, no *IEEE Access* vol. 12 pp. 12345–12356 (páginas
  aparentemente inventadas).
- [16]: autor mal formateado («J. W. R. Jr.»); el año habitual de cita es 1974.
- [3] se usa como fuente de «pérdidas de hasta 50 %», pero es un paper de UAV; esa cifra debe venir
  de una fuente epidemiológica.
- [4] (modelo de *survival ratio*) se cita para afirmar que las hojas tiernas son buena referencia
  sana por tener «cutícula más delgada y menor densidad estomática». La referencia no dice eso.

> Una referencia inexistente es motivo de rechazo o retractación. Para alguien de su perfil, esto
> pesa más que cualquier resultado.

---

## 2. Preguntas de óptica que hará un especialista en espectroscopía

Las cabeceras de SpectraSuite responden varias **[verificado]**:

| Pregunta | Lo que dicen los datos | Qué falta |
|---|---|---|
| ¿Reflectancia respecto de qué blanco? | Hay referencia y oscuro guardados («Presente Oscuro/Referencia: Sí») | Qué estándar (¿Spectralon? ¿de qué %?), cada cuánto se renovaba y con qué geometría |
| ¿Correcciones del detector? | **No-linealidad: No. Oscuridad eléctrica: No.** | Justificarlo o discutir el efecto |
| ¿Integración y promedios? | 300 ms × 5 en 1931 espectros; **10 espectros a 100 ms × 1** | Explicar o excluir esos 10 |
| ¿Por qué hay reflectancia > 100 %? | 30 espectros con mediana NIR > 100 % (máximo 114.8 %), 15 de ellos el 06/07 | Probable deriva del blanco o presión/ángulo de la sonda. Se debe discutir |
| ¿Ventana del suavizado? | 41 píxeles ≈ 8–9 nm (≈ 0.2 nm/píxel en el USB4000) | Declararlo en nm, no en píxeles |
| ¿Corrección de línea base? | **No existe en el código** | Quitarla de Métodos |
| ¿Señal en el azul? | Fuente halógena con poca emisión bajo 450 nm; parte de los espectros con roya da reflectancia negativa bajo 440 nm | El índice estrella (mNDVI705) usa R445. Hay que discutir su SNR |
| ¿Dónde se apoyó la sonda en R1? | No consta | ¿Sobre la pústula o en tejido verde? ¿Haz o envés? Cambia la interpretación |
| ¿Espectros que no son de hoja? | **4 espectros con NDVI ≈ 0** (referencia blanca guardada como hoja): Bourbon M1 p3 24/08 ×3, Cuscatleco M1 p3 17/08 ×1 | Fuera del período del paper, pero muestran que falta un control de calidad por espectro |

---

## 3. Estadística: lo que va a objetar y lo que sí se puede defender

**Lo que va a objetar:**

1. **Unidad de análisis.** Métodos dice «nine technical replicates averaged per leaf per session to
   avoid pseudo-replication», pero las figuras usan n = 90/60 espectros, los boxplots muestran
   puntos individuales y las bandas de las Figs. 3–4 (± SE, BH por longitud de onda) tratan cada
   espectro como independiente.
2. **La prueba nombrada es la equivocada.** «Kruskal-Wallis con Dunn post hoc» para dos grupos es
   Mann–Whitney U, sin post hoc. No hay corrección entre los 8 índices × 2 variedades.
3. **El confusor edad.** «Sana» = hoja tierna y «con roya» = hoja adulta. Las tiernas cambian al
   madurar (7 de 7 hojas oscurecen el visible). Contra la madura de la misma edad, EDI separa casi
   perfectamente; contra la tierna no.
4. **Los porcentajes de cambio.** «PRI increased by 130 %» cuando pasa de −0.036 a −0.083 (baja). Un
   porcentaje sobre un índice que cruza el cero no tiene sentido físico.
5. **Incluso a nivel hoja-fecha sigue habiendo pseudo-réplica temporal**: las 9 hojas-fecha de R1
   son la misma hoja. Esto aplica también a los p-valores que muestra hoy la app.

**Lo que sí se puede defender, con los datos actuales:**

- **Tamaños de efecto descriptivos** (δ de Cliff) de R1 frente a las maduras de la misma edad y
  frente a las tiernas, presentados como estudio de caso, sin p-valores poblacionales.
- **Repetibilidad temporal:** en cuántas fechas R1 queda fuera del rango de las 4 hojas M/T de su
  variedad ese mismo día. Preliminar: PRI, EDI, NDRE y mNDVI705 lo cumplen en 8 de 9 fechas
  (Bourbon) y 9 de 9 (Pacamara) **[28/09]**.
- **Validación en el tiempo:** umbrales fijados solo con julio y evaluados en agosto–septiembre,
  más **controles negativos** (Canefora y Cuscatleco). Preliminar: mNDVI705 reconoce R1 en 7 de 7
  fechas y da 0 falsas alarmas en 44 hojas-fecha de los controles **[28/09]**. Esto responde
  directamente a los puntos 3 y 4 del revisor 2.
- **El resultado longitudinal:** en 12 semanas ninguna hoja madura se desplazó hacia la firma de la
  roya más allá del envejecimiento que también muestran los controles. Es un resultado negativo
  honesto, y la mejor respuesta a «¿dónde está la detección temprana?».

---

## 4. Texto y discusión: contradicciones internas

| Dónde | Dice | Problema |
|---|---|---|
| Resultados A | «Infected leaves exhibited decreased reflectance in the red-edge (700–750 nm)» | En Pacamara (Fig. 3) la diferencia R − H es **+10 pp** cerca de 705 nm: el borde rojo se corre hacia el azul. En Bourbon (Fig. 4) la hoja con roya refleja menos en **todo** el espectro |
| Discusión | «Bourbon exhibited larger and more consistent differences than Pacamara» | La Tabla I muestra cambios mayores en Pacamara en todos los índices |
| Atribución espectral | «Chlorophyll degradation increases reflectance in the red and blue» | La Fig. 4 muestra **menos** reflectancia visible en la hoja con roya |
| Atribución espectral | «NIR decrease (FSR, NDVI)» | NDVI y FSR no cambian según la Tabla I |
| Discusión | «NDVI saturation in moderate to high biomass canopies» | Es medición de contacto en una hoja, no de dosel |
| Fig. 5 | Boxplots Bourbon vs Pacamara | No se discuten en el texto; no queda claro para qué están |

---

## 5. Forma (lo primero que se ve, aunque sea lo menos importante)

- Numeración de autores «1st, 1nd, 2rd, 3th, 4th, 5th» (el revisor 3 la marcó). ¿Hay dos primeros
  autores? Si es coautoría principal, se indica con una nota, no con «1st/1nd».
- Erratas en las figuras: «Prube» (Fig. 1), «Preprocesing» (Fig. 2).
- La Fig. 2 muestra una alerta por «1 new file(s)»: ilustra el sistema con un solo espectro.
- Los pies de figura no dicen qué es n (espectros, puntos u hojas) ni de qué campañas salen.
- Decimales y signos inconsistentes; «Very light/Light/Beginning of moderate» son traducciones
  literales.

---

## 6. El proyecto, más allá del paper

**Fortalezas que él va a valorar si se las presentas bien:**

- **Diseño longitudinal real:** las mismas hojas medidas 12 semanas. Es poco común y es lo más
  valioso que tienen.
- **Controles negativos:** dos variedades sin roya, medidas igual.
- **Trazabilidad:** pipeline reproducible, una única tabla de índices, control de calidad
  documentado, pruebas automáticas y una app que muestra todo lo excluido y por qué.
- **Datos para validar fuera de muestra:** 7 campañas que el paper no usó.

**Debilidades que va a señalar:**

- **n = 1 hoja con roya por variedad**, ya sintomática en su primera medición. Es el límite duro del
  estudio y no se arregla con análisis.
- **No hay verdad de terreno:** sin fotos por fecha, sin escala visual de severidad, sin hojas
  marcadas antes de los síntomas.
- **Deriva de protocolo:** repeticiones 10 → 5 → 3, horario de 7:00 a 17:00, puntos no fijos, 10
  espectros con otra configuración, blancos guardados como hojas, archivos «araña» y hojas viejas
  sin variedad.
- **El índice de similitud con roya es ad hoc:** mediana de posiciones entre dos anclas definidas
  por una sola hoja. Es útil como heurística de monitoreo, pero hay que presentarlo así, o
  compararlo contra enfoques establecidos (p. ej. *spectral angle*, distancia de Mahalanobis,
  PLS-DA) antes de darle peso científico.
- La app está muy bien, pero él evaluará **primero la ciencia**. Conviene mostrarla como la
  herramienta que garantiza que cada número es reproducible, no como el resultado.

---

## 7. Cómo presentárselo (estrategia)

1. **Empezar por la auditoría, antes de que él la haga.** Una tabla de una página con «lo que dice
   el paper / lo que muestran los datos / cómo se corrige» (secciones 1 y 4). Un advisor exigente
   respeta mucho más a quien encontró sus propios errores.
2. **Proponer el reencuadre**, no defender el paper enviado:
   *discriminación repetible de una hoja sintomática en campo, validada en campañas posteriores e
   independientes, con controles sin roya y un seguimiento de 12 semanas que separa la firma de la
   roya del envejecimiento, como base para una alerta temprana*. Título sugerido: *Toward Early
   Warning of Coffee Leaf Rust: Portable Point-Reflectance Monitoring with Connected Alerts in
   Bourbon and Pacamara*.
3. **Mostrar que cada número sale de un script** (`make_ieee_figures.py` → `paper_numbers.csv`) y
   que la app usa el mismo método (`METODOLOGIA.md`).
4. **Traer escrita la sección de limitaciones** y el diseño del próximo experimento: más hojas con
   roya, hojas marcadas antes de los síntomas con foto y escala visual por fecha, registro de hora y
   blanco, protocolo fijo.
5. **Llevar respuestas a las preguntas que hará:**

| Pregunta probable | Respuesta honesta |
|---|---|
| ¿Cuántas hojas con roya independientes hay? | Una por variedad. Por eso se presenta como estudio de caso con validación temporal, no como inferencia poblacional |
| ¿Dónde está la detección temprana? | No se demostró. En 12 semanas ninguna madura se desplazó hacia la firma de la roya; se necesitan hojas infectadas antes de los síntomas |
| ¿Por qué EDI si la Fig. 6 dice ns? | Porque la comparación fue contra hojas tiernas (confusor edad). Contra maduras de la misma edad, sí separa; se corrige la referencia sana |
| ¿Cómo controlaron la hora del día? | No se controló: las cabeceras muestran de 7:30 a 17:00. Se reporta y se discute para PRI |
| ¿Qué blanco usaron? | (Pendiente: confirmar con el equipo) |
| ¿Cuánto cuesta el equipo? | (Pendiente: lista de materiales) |
| ¿Por qué «IoT»? | Es un flujo de alerta conectado (Telegram); se cambia el término o se justifica |

---

## 8. Lo que falta de tu lado (bloquea partes de la corrección)

1. Confirmar el diseño real: cuántas plantas por variedad y de qué planta sale cada hoja; que R1 es
   una sola hoja física.
2. En R1: ¿sonda sobre la pústula o en tejido verde? ¿Haz o envés?
3. Estándar de blanco, frecuencia de recalibración y geometría de la sonda.
4. ¿Existen los datos ambientales? Si no, se quitan del texto.
5. Fotos de las hojas y del equipo (lo pidió el revisor 1).
6. Precios aproximados del equipo (revisor 2).
7. ¿Se revisaban visualmente las maduras en cada campaña? Si nunca mostraron síntomas, se las puede
   llamar «asintomáticas» y no solo «maduras».
8. Decisión sobre los 4 espectros sin firma de hoja (excluirlos o no).
9. Estado del paper: ¿hay revisión mayor o camera-ready? ¿Fecha límite y límite de páginas? ¿Hay
   `.tex`?

---

## 9. Qué puedo hacer ya, sin esperar nada

En este orden (corresponde a la Fase A de `plan_mejora_paper.md`):

1. `PAPER/auditoria_paper_enviado.md`: cada número del paper contrastado con un script.
2. Verificar las 18 referencias una por una, con DOI, y proponer reemplazos recientes verificados.
3. Script de números del paper: δ con IC por bootstrap por hojas-fecha, repetibilidad, validación
   julio → agosto–septiembre con IC de Wilson y controles negativos, todo escrito en
   `paper_numbers.csv`.
4. Análisis de sensibilidad: con y sin hojas-fecha dudosas, con y sin los 4 blancos, por punto
   frente a hoja-fecha, y **controlando la hora de medición** para PRI.
5. Figuras nuevas: espectros T/M/R, *forest plot* de efectos y figura longitudinal.
6. Borrador de la respuesta a los revisores.
