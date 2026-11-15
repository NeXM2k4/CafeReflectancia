# Cambios a la versión final del paper (CONCAPAN)

Fecha: 2026-10-18 · Archivo revisado: `last_version_paper1.tex` · Observaciones: `OBSERVACIONES FINALES.txt`

## 1. Alcance de los datos

El paper usa **solo 5 campañas de julio de 2026**: `C1_29_06`, `C2_06_07`, `Roya_15_07`, `Roya_21_07`, `Roya_27_07`
(Bourbon y Pacamara). La hoja con roya (R1) solo existe el 15/07 y el 27/07. Las 7 campañas de agosto y
septiembre **no entran**.

- Todo número, tabla y figura sale de `make_final_figures.py` (filtra esas 5 campañas).
- **No usar `make_ieee_figures.py`** de la raíz: lee todo `data/` y mezclaría las 12 campañas.

## 2. Decisiones

| Decisión | Valor | Por qué |
|---|---|---|
| Grupo H | **Solo hojas tiernas (T1, T2)** | Es lo que dicen Métodos, resumen y figuras. La Tabla I enviada usaba tiernas + maduras. |
| Grupo R | Hoja R1, 15/07 y 27/07 | Única hoja con roya por variedad. |
| Unidad | Punto de medición (se promedian sus repeticiones) | n = 30 (H) y 6 (R) por variedad. |
| Prueba | Mann-Whitney U, Holm sobre los 8 índices por variedad | Con 2 grupos no hay post-hoc de Dunn. |
| Reflectancia | Fracción (0–1) para CRI1 | SpectraSuite da %; CRI1 no es invariante a la escala. |
| FSR | Con 850 nm | Lo que dice Métodos; el código de la app usa 800 nm y da igual a NDVI. |
| Nombres | CRI1, ND705, mND705 | Los de Métodos. En la app: RCI, EDI, mNDVI705. |

## 3. Hallazgos que cambian el texto

- Con H = tiernas, **ND705 (EDI) no es significativo**: Bourbon p = 0.094, Pacamara p = 0.071.
  Con tiernas + maduras tampoco llega a p < 0.001 (p = 0.0026 y 0.0094).
- Robustos en las dos variedades (Holm): **PRI** (p = 0.0005 / 0.0012) y **mND705** (p < 0.0001 / 0.0012).
- NDRE y PSRI: solo Pacamara. NDVI y FSR: solo Bourbon, y **suben** ~19 %.
- PRI **bajó** (−0.034 → −0.083 en Bourbon; −0.025 → −0.137 en Pacamara); el texto decía "increased".
- Cambios relativos con tiernas: mND705 −34 % / −52 %; NDRE −23 % / −49 %; ND705 −18 % / −38 %.
- Espectros: en el NIR R < H en ambas variedades. A 700–720 nm Pacamara **sube** (+9.6 puntos, máx. en 706 nm)
  y Bourbon casi no cambia (−4.4); la mayor diferencia de Bourbon está en 764 nm.
- 10 archivos del 15/07 usan 100 ms × 1 promedio (el texto dice 300 ms × 5 para todos).
- El código de la alerta ancla con la **media** de H y de R, no con máximos y mínimos.

## 4. Cambios por línea del `.tex`

**Tabla II (líneas 244–271)** — código completo en la sección 5.
- Agregar la fila PSRI; corregir CRI1 (×100); FSR con 850 nm; H = tiernas; nombres de Métodos.
- Caption (línea 250) y nota al pie (línea 269) actualizadas.

**Escala de alertas (línea 299)**
- Declarar que la escala de 11 niveles la definieron los autores (2026-08-02) y no está validada contra severidad visual.
  **Pendiente:** si hay una fuente externa, citarla.
- Cambiar "based on the maximum and minimum values" por "based on the healthy and rust reference means".
- Agregar el procedimiento: ancla H = 0, ancla R = 1, normalizar $(x-H)/(R-H)$, recortar a [0,1], mediana entre
  índices, nivel más cercano de los 11.
- Aclarar que son niveles de similitud con la referencia de roya, no severidad medida (las descripciones hablan de planta entera).

**Figuras (líneas 228–238 y 287–297)**
- Fig. 6 (sana vs. roya) → `fig_boxplots_indices.png` en `figure*` (más grande, bigotes gruesos, asteriscos, nombres de Métodos).
- Fig. 5 (Bourbon vs. Pacamara, solo hojas tiernas) → `fig_boxplots_cultivares.png`, mismo formato. Ningún índice difiere entre variedades tras Holm (p_holm ≥ 0.19; el menor crudo es mND705, p = 0.023). Si el texto dice que las variedades difieren, hay que quitarlo.
- Figs. 3 y 4 regeneradas: `fig_spectra_pacamara.png`, `fig_spectra_bourbon.png`.
- "Cambiar EDI por CRI1" se interpretó como renombrar a los nombres de Métodos. **Pendiente de confirmar** con el asesor.

**Otras líneas**

| Línea(s) | Cambio |
|---|---|
| 62, 241, 274–285, 312, 316, 326 | Reescribir con PRI y mND705 como índices robustos; quitar "EDI el más consistente" y "p < 0.001" para los cuatro. |
| 279, 316 | PRI "bajó", no "aumentó". |
| 280–281 | mND705 −34 % / −52 %; NDRE −23 % / −49 % (solo Pacamara significativo). |
| 285, 318 | NDVI y FSR sí son significativos en Bourbon (suben). |
| 226 | Matizar la caída en el borde rojo (ver sección 3). |
| 83 | Una sola hoja con roya (R1) por variedad, medida el 15/07 y el 27/07. |
| 86 | Excepción: 10 espectros del 15/07 con 100 ms y 1 promedio. |
| 211 | Repeticiones promediadas por punto, no por hoja; Mann-Whitney con Holm; quitar Dunn. |
| 62, 66, 74, 312, 326 | "Early detection" sigue sin respaldo: no hay datos presintomáticos. |

## 5. Código LaTeX de la Tabla II

```latex
\begin{table}[!t]
\centering
\scriptsize
\setlength{\tabcolsep}{1.5pt}
\renewcommand{\arraystretch}{1.2}
\caption{Mean $\pm$ SD of reflectance indices per measurement point, by variety and health status (H: $n=30$, R: $n=6$ per variety). CRI1 is computed with reflectance as a fraction (0--1).}
\label{tab:indices}

\begin{tabularx}{\columnwidth}{@{}l X X X X@{}}
\toprule
& \multicolumn{2}{c}{\textbf{Bourbon}} & \multicolumn{2}{c}{\textbf{Pacamara}} \\
\cmidrule(lr){2-3} \cmidrule(lr){4-5}
\textbf{Index} & \hfil H & \hfil R & \hfil H & \hfil R \\
\midrule
NDVI   & \hfil $0.535 \pm 0.126$  & \hfil $0.637 \pm 0.071$  & \hfil $0.595 \pm 0.162$  & \hfil $0.632 \pm 0.214$ \\
PRI    & \hfil $-0.034 \pm 0.020$ & \hfil $-0.083 \pm 0.032$ & \hfil $-0.025 \pm 0.010$ & \hfil $-0.137 \pm 0.039$ \\
PSRI   & \hfil $-0.002 \pm 0.030$ & \hfil $0.018 \pm 0.007$  & \hfil $0.002 \pm 0.016$  & \hfil $0.045 \pm 0.047$ \\
CRI1   & \hfil $3.11 \pm 9.17$    & \hfil $3.00 \pm 1.10$    & \hfil $3.48 \pm 5.03$    & \hfil $6.46 \pm 5.98$ \\
FSR    & \hfil $0.536 \pm 0.127$  & \hfil $0.641 \pm 0.068$  & \hfil $0.595 \pm 0.162$  & \hfil $0.635 \pm 0.213$ \\
ND705  & \hfil $0.336 \pm 0.077$  & \hfil $0.275 \pm 0.074$  & \hfil $0.392 \pm 0.108$  & \hfil $0.241 \pm 0.134$ \\
mND705 & \hfil $0.554 \pm 0.063$  & \hfil $0.365 \pm 0.099$  & \hfil $0.609 \pm 0.100$  & \hfil $0.291 \pm 0.140$ \\
NDRE   & \hfil $0.160 \pm 0.037$  & \hfil $0.124 \pm 0.036$  & \hfil $0.191 \pm 0.056$  & \hfil $0.097 \pm 0.052$ \\
\bottomrule
\multicolumn{5}{@{}p{\columnwidth}@{}}{\scriptsize H: healthy young leaves (T1, T2); R: one rust-confirmed leaf (R1), measured on 15/07 and 27/07. FSR uses NIR at 850\,nm.}
\end{tabularx}
\end{table}
```

Notas: CRI1 tiene SD grande en H por unos pocos puntos atípicos en 510 nm (Bourbon: SD 9.17). FSR queda casi igual a NDVI;
si se prefiere quitarlo, borrar la fila y cambiar "eight" por "seven" en las líneas 62, 120 y 122.

## 6. Archivos generados (en esta carpeta)

- `make_final_figures.py` — genera todo desde las 5 campañas.
- `fig_boxplots_indices.png`, `fig_spectra_bourbon.png`, `fig_spectra_pacamara.png` — 600 dpi.
- `fig_boxplots_cultivares.png`, `estadistica_cultivares_5campanas.csv` — comparación entre variedades (H = tiernas).
- `estadistica_5campanas.csv` — medias, SD, cambio %, δ de Cliff, p crudo y p Holm; tres versiones de H (tiernas, maduras, ambas).
- `espectros_diferencia_5campanas.csv` — R − H por longitud de onda.
- `make_alert_message.py` → `fig_alert_message_telegram.png` — mensaje de alerta de Telegram con
  datos reales (Bourbon R1, 27/07/2026), sin EDI. **2026-10-18: pasado al tema claro** (fondo
  blanco, burbuja `#F3F6F9` con borde suave, texto oscuro) para que se integre en la página del
  paper; los números no cambian (severidad 79 %, "Very severe").

## 7. Pendiente

1. Fuente de la escala de 11 niveles (o declararla como propia).
2. Confirmar con el asesor el sentido de "cambiar EDI por CRI1".
3. Reescribir Resumen, Resultados, Discusión y Conclusión con los números de la sección 3.
4. Decidir si se mantiene o se quita FSR.
5. Los límites de la muestra siguen ahí: R es una sola hoja medida dos días, así que las pruebas son exploratorias.
