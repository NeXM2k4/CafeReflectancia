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

- [ ] F0.1 — commit de lo pendiente + rama `mejora-app` + tag
- [ ] F0.2 — arreglo del registro de Telegram (riesgo inmediato)
- [ ] F0.3 — matplotlib en requirements.txt
- [ ] F0.4 — prueba de humo (AppTest)
- [ ] F1.1 — tabla de índices única y cacheada
- [ ] F1.2 — agregación única archivo→punto→hoja-fecha
- [ ] F1.3 — similitud con roya única
- [ ] F1.4 — estadística única con veredicto
- [ ] F1.5 — etiquetas y colores únicos
- [ ] F1.6 — control de calidad extendido a valores imposibles
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
