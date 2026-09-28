# Reflectancia foliar y roya del café

Aplicación en **Streamlit** para analizar espectros de reflectancia foliar (espectrómetro de
contacto, formato SpectraSuite) de cuatro variedades de café medidas semana a semana sobre las
mismas hojas, con el objetivo de caracterizar la roya (*Hemileia vastatrix*) en el espectro y
distinguirla del envejecimiento normal de la hoja.

## Cómo correrla

```bash
pip install -r requirements.txt
streamlit run app.py
```

Tras editar código en `src/` hay que reiniciar el proceso (`Ctrl+C` y volver a ejecutar); los
cambios en `views/` se recargan solos. Para la alerta de Telegram (opcional), copiar
`.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y completarlo.

Pruebas:

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
```

## Organización de la aplicación

| Sección | Vista | Pregunta que responde |
|---|---|---|
| Resumen | **Panorama** | Qué se midió, cómo está diseñado el estudio y cómo están las hojas maduras en la última campaña |
| | **Método y glosario** | Cómo se procesa y agrega cada dato; qué significa cada término (lee `METODOLOGIA.md`) |
| Análisis exploratorio | **Espectros** | Cómo se ven las curvas de reflectancia por tipo de hoja |
| | **Índices por tipo de hoja** | Qué índices distinguen la hoja con roya de la tierna y la madura, y cuánto (δ de Cliff, Holm) |
| | **Comparación entre variedades** | Si las variedades difieren con el mismo tipo de hoja |
| Seguimiento de hojas | **Estado actual** | Similitud con roya de cada hoja, fecha por fecha, y cómo se forma ese porcentaje |
| | **Evolución temporal** | Si el cambio de una hoja madura es propio de la roya o envejecimiento |
| Datos y operación | **Datos y calidad** | Inventario y todo lo excluido o marcado, con el motivo |
| | **Alerta de campo** | Revisar mediciones nuevas y enviar el aviso por Telegram (con vista previa) |

## Agregar una campaña nueva

1. Copiar la carpeta de la campaña a `data/` (las subcarpetas nuevas se detectan solas).
2. Abrir la aplicación, o «Volver a escanear data/» en *Datos y calidad* si ya estaba abierta.
3. Revisar *Datos y calidad*: que no aparezcan archivos sin reconocer ni marcas inesperadas.
4. En *Alerta de campo*: «Revisar novedades» → leer la vista previa → «Enviar a Telegram».

No hace falta tocar código mientras los archivos sigan la convención de nombres
(`docs/bitacora.md` §4).

## Estructura del repositorio

```
app.py                  enrutador: configuración, tema y navegación
views/                  una vista por archivo (ver tabla de arriba)
src/
  parser.py             descubre y lee los .txt de data/
  processing.py         suavizado y fórmulas de los índices
  indices.py            tabla única de índices por espectro, punto y hoja-fecha; control de calidad
  severity.py           anclas y similitud con roya
  stats_utils.py        estadística por pares (δ de Cliff, Mann–Whitney, Holm) y prueba global
  temporal.py           series por hoja, Δ/Δ*, tendencias, distancia a R1
  temporal_plots.py     gráficos de la evolución temporal
  viz_groups.py         gráficos compartidos de comparación entre grupos
  ui.py                 sistema visual: encabezados, notas, tablas, filtros, plantilla Plotly
  notifier.py, state.py alerta de Telegram y registro de novedades
assets/                 logotipo
data/                   espectros crudos (.txt)
figures_ieee/           figuras del artículo (make_ieee_figures.py)
tests/                  pruebas de humo de todas las vistas e interacciones
```

## Documentos

- **`METODOLOGIA.md`**: fuente única del método (la vista *Método y glosario* lo muestra).
- **`ESTADO_PROYECTO.md`**: estado vigente y pendientes.
- **`DEPLOY.md`**: publicar la rama y desplegar.
- **`plan_mejora_app.md`**, **`plan_presentacion.md`**, **`PROGRESO_MEJORA_APP.md`**: planes y
  bitácora de la mejora de la aplicación.
- **`plan_mejora_paper.md`**: plan del artículo (pausado hasta cerrar la aplicación).
- **`evoluciontemporal.md`**: diseño y hallazgos del análisis temporal.
- **`docs/`**: historia del proyecto; no describe el comportamiento actual.

## Limitaciones (leer antes de sacar conclusiones)

- **Una sola hoja con roya por variedad** susceptible. Lo que se ve de «con roya» describe esa
  hoja, no una población.
- Los puntos p1–p3 **no son ubicaciones fijas** entre campañas.
- «Madura» y «Tierna» significan **sin síntomas visibles**, no «sana».
- La similitud con roya (0–100 %) es **relativa a los propios datos**; no es un diagnóstico.
