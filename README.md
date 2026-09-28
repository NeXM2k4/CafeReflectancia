# Reflectancia foliar en café — detección de roya

App en **Streamlit** para analizar mediciones de reflectancia foliar (espectrómetro
SpectraSuite) y ayudar a detectar roya del café (*Hemileia vastatrix*) en Bourbon y Pacamara,
las dos variedades susceptibles del dataset. Reemplaza el análisis manual que antes se hacía en
un notebook.

## Cómo correrla

```bash
pip install -r requirements.txt
streamlit run app.py
```

Cada vez que se edite código en `src/` o `pages/`, hay que **reiniciar el proceso de Streamlit**
(`Ctrl+C` y `streamlit run app.py` de nuevo) — guardar el archivo no alcanza.

Para las credenciales de Telegram (opcional, solo si se va a usar la alerta), copiar
`.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y completarlo.

Para correr las pruebas:

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
```

## Qué responde cada página

| Página | Pregunta que responde |
|---|---|
| **Inicio** | Qué datos hay, su calidad, y si hay novedades para avisar por Telegram |
| **1. Espectros** | Cómo se ve la reflectancia de estas hojas |
| **2. Índices Espectrales** | Qué índices separan hojas con roya de las que no, por especie |
| **3. Comparación Especies** | Cómo difieren las 4 variedades entre sí (mismo tipo de hoja) |
| **4. Estado de las Hojas** | Qué tan parecida es cada hoja madura a una hoja con roya, hoy |
| **5. Evolución Temporal** | Cómo cambia cada hoja física en el tiempo, y si es por roya o por envejecimiento |

## Flujo típico: agregar una campaña nueva

1. Copiar la carpeta de la campaña a `data/` (cualquier subcarpeta nueva se detecta sola).
2. Abrir la app (o "🔄 Recargar datos" en Inicio si ya estaba abierta).
3. Revisar la sección "Calidad de datos" de Inicio: confirma que no hay archivos sin
   reconocer ni sorpresas.
4. "Verificar novedades" → revisar la vista previa → "✅ Enviar a Telegram" si corresponde.

No hace falta tocar código para que la app reconozca campañas o especies nuevas, siempre que
sigan el patrón de nombres ya documentado (ver `METODOLOGIA.md`).

## Estructura del repo

```
app.py                    # Inicio: inventario, calidad de datos, alerta
pages/                    # 1-5, ver tabla de arriba
src/
  parser.py                 # descubre y parsea los .txt de data/
  processing.py              # suavizado + 8 índices espectrales (fórmulas puras)
  indices.py                 # tabla única de índices por archivo/punto/hoja-fecha (cacheada)
  severity.py                 # anclas sana/con-roya y similitud con roya
  stats_utils.py               # comparación estadística con veredicto en palabras
  temporal.py                   # series por hoja física en el tiempo (página 5)
  notifier.py                    # mensajes y envío por Telegram
  config.py, ui.py, state.py      # constantes, estilos compartidos, registro de novedades
data/                      # mediciones crudas (.txt), no se versiona la lógica de negocio aquí
figures_ieee/              # figuras para el paper (make_ieee_figures.py)
tests/                     # pruebas automáticas
```

## Documentos de referencia

- **`METODOLOGIA.md`** *(pendiente de escribir, ver `plan_mejora_app.md` F5.2)* — única fuente
  de verdad del método: diseño de muestreo, índices con fórmula y cita, unidad de análisis,
  similitud con roya, control de calidad y estadística.
- **`plan_mejora_app.md`** — plan de la sesión de pulido de la app (en curso).
- **`PROGRESO_MEJORA_APP.md`** — bitácora de esa sesión: qué se hizo, qué se decidió, qué falta.
- **`plan_mejora_paper.md`** — plan para el paper de CONCAPAN (pausado hasta cerrar la app).
- **`evoluciontemporal.md`** — plan y hallazgos detallados de la página 5.
- **`ESTADO_PROYECTO.md`** / **`ESTADO_ROYA.md`** — bitácora histórica del proyecto (partes
  desactualizadas tras la sesión de pulido, ver el aviso al inicio de cada uno).

## Limitaciones importantes (léase antes de sacar conclusiones)

- **n = 1 hoja con roya confirmada por especie** en todo el dataset. Cualquier resultado sobre
  "hojas con roya" describe esa hoja puntual, no una muestra poblacional.
- Los puntos de medición (p1, p2, p3) **no son ubicaciones fijas** entre campañas: son muestras
  espaciales intercambiables dentro de la hoja, nunca se sigue "el punto 2" en el tiempo.
- "Madura" y "Tierna" son hojas **sin síntomas visibles**, no "sanas" — su estado sanitario real
  se desconoce; es justo lo que la similitud con roya trata de estimar.
- La similitud con roya (0-100 %) es una medida relativa a los propios datos, **no un
  diagnóstico**.

Detalle completo en `plan_mejora_app.md` y `evoluciontemporal.md`.
