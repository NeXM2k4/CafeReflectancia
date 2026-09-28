# Plan — Presentación profesional de la app

Fecha: 2026-09-28 · Rama: `mejora-app` · Estado: **ejecutado** (ver el registro al final).

**Regla de alcance:** no se agregan análisis nuevos. Se reorganiza, se rediseña la presentación y
se corrige lo que se ve mal. Todo número que aparece ya lo calculaba `src/`; donde una tabla
existente no informa (p. ej. Kruskal-Wallis con 3 grupos sin tamaño de efecto), se muestra la
misma estadística por pares con δ de Cliff y Holm, que es lo que `METODOLOGIA.md` §6 ya declara.

## Diagnóstico (capturas reales, Chrome headless, 1500 px)

| Dónde | Problema |
|---|---|
| Navegación | La primera entrada dice "app"; nombres sin tildes; sin agrupar por propósito. |
| Todas | Encabezado con emoji; etiquetas de filtro como pastillas de colores; emojis en expanders (ℹ️📄🔬🧹✅); plurales "(s)"; cajas amarillas/azules genéricas. |
| Filtro de campaña | 12 chips de fecha llenan media barra lateral; se usa en 4 páginas. |
| Inicio | La tabla especie × campaña se desborda a la derecha y muestra `campaign_id`/`species`; la tabla de calidad tiene los encabezados corridos ("Por que" sobre los números, "2"). Mezcla inventario, calidad, Telegram y glosario en una sola página larga. |
| Espectros | No llega a dibujar el gráfico en el primer minuto: relee y suaviza ~600 espectros en cada interacción; puntos como "1.0, 2.0"; eje Y fijo 0–105. |
| Índices | La tabla resumen con 3 tipos de hoja da "None" en el efecto y un veredicto que no dice qué grupo difiere; columna de veredicto cortada; 7 gráficos sueltos con el título de eje repetido; orden de categorías arbitrario (Madura, Con roya, Tierna). |
| Variedades | "Vieja (especie pendiente)" aparece como si fuera una especie; mismo problema de tabla. |
| Estado de las hojas | Escala de color verde→naranja (arcoíris, no secuencial); decimales "42.0"; R1 arriba y M1 abajo; dos barras de color; tarjeta con emoji gigante. |
| Evolución | Estilo de gráficos propio, distinto del resto. |

## Decisiones

1. **Navegación con `st.navigation`**, agrupada:
   - *Resumen*: Panorama · Método y glosario
   - *Análisis exploratorio*: Espectros · Índices por tipo de hoja · Comparación entre variedades
   - *Seguimiento de hojas*: Estado actual · Evolución temporal
   - *Datos y operación*: Datos y calidad · Alerta de campo
   Las vistas pasan a `views/`; `app.py` queda como enrutador (configuración, tema, navegación).
2. **Sistema visual único en `src/ui.py`**: tipografía IBM Plex Sans / Plex Mono (cifras),
   encabezado de página = sección + pregunta que responde + una línea de contexto; notas
   tipificadas (Cómo leer · Limitación · Método) en vez de `st.warning/info`; leyenda de tipos de
   hoja compacta; pie de barra lateral con la versión de los datos.
3. **Plantilla Plotly única** (`reflec`): fondo transparente, retícula de línea fina, tipografía y
   tooltip comunes. Paleta categórica existente (ya validada para daltonismo, pasos oscuros).
   Similitud: rampa secuencial de un solo tono (naranja). δ de Cliff: divergente azul–rojo con
   punto medio gris.
4. **Filtro de campaña = rango de fechas** (`select_slider` desde/hasta).
5. **Orden fijo de categorías**: Tierna → Madura → Vieja → Con roya (edad/estado).
6. **Estadística por pares** en Índices y Variedades: matriz índice × par con δ de Cliff, p de
   Mann-Whitney ajustado por Holm sobre toda la matriz y veredicto; la prueba global
   (Kruskal-Wallis) queda como columna de contexto.
7. **Espectros**: caché de espectros suavizados por archivo; modo de vista (curvas / media ± DE /
   ambos); puntos p1–p3 por defecto; eje Y automático.
8. **Estado actual**: un mapa de calor por especie con escala secuencial, enteros, maduras arriba y
   referencias abajo separadas; detalle con la posición de cada índice entre sus anclas (el
   componente que forma la mediana).
9. **Lenguaje**: registro impersonal, sin emojis en la interfaz (Telegram los conserva), sin "(s)",
   tildes completas.

## Criterios de aceptación

- 0 excepciones en todas las vistas (pruebas de humo actualizadas) y capturas revisadas a 1500 px
  y 1100 px sin desbordes ni textos cortados.
- Mismos números que antes en similitud (diferencia 0,0 con `leaf_date_similarity`).
- Espectros dibuja en < 10 s la primera vez y < 3 s después.

## Registro de ejecución

- Hecho todo lo de «Decisiones» 1–9. Verificado con capturas en Chrome headless (1500 px) de las 9
  vistas y de las 5 pestañas de *Evolución temporal*, y con 10 pruebas `AppTest` en verde.
- Magnitud del δ de Cliff alineada con Romano et al. (2006) en toda la app (antes 0.33/0.66).
- Decimales con punto y miles con coma en toda la interfaz (convención salvadoreña).
- **Hallazgo nuevo al revisar las capturas:** 4 espectros sin firma de hoja (NDVI ≈ 0), probables
  referencias blancas guardadas con nombre de hoja (Bourbon M1 p3 24/08 ×3, Cuscatleco M1 p3
  17/08 ×1). Se marcan en *Datos y calidad*; **no** se excluyen sin decisión del usuario.
- Similitud: sin cambios numéricos (misma función `leaf_date_similarity`).
