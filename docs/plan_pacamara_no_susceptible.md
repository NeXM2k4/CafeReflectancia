# Plan: mostrar la planta de Pacamara «No susceptible» como grupo propio

Fecha: 2026-11-24. Estado: **implementado el 2026-11-24.** El usuario confirmó que «No susceptible» = **planta resistente**,
pidió ocultar por ahora la alerta de Telegram (resuelve el riesgo de §3.7) y renombrar sus hojas
(sufijo `-NS`: M1-NS, M2-NS, T1-NS, T2-NS). Ancla con roya (§3.4): la R1 de Pacamara, también para la
distancia a R1 y el SAM R1. La comparación explícita de §3.5 (Pacamara M susceptible vs resistente) queda
pendiente; hoy entra como control sin roya en todas las lecturas.

## 1. Problema (reportado por el equipo)
En `data/`, Pacamara tiene dos plantas: **Susceptible** (la de la roya) y **No susceptible**. La app solo
muestra una. Causa: `parser.get_dataset()` (`src/parser.py:398`) descarta a propósito
`species == "Pacamara" & susceptibility == "No susceptible"`; solo se cuentan en *Datos y calidad*.

Datos de la planta no susceptible: **711 espectros**, las **20 campañas** completas, hojas **M1, M2, T1, T2**,
puntos p1–p3 (≈36 archivos por campaña; 27 el 05/10). Sin hoja con roya.
Sus hojas se llaman igual que las de la susceptible y `leaf_id = especie|hoja`, así que **quitar el filtro
sin más mezclaría las dos plantas** en una sola serie.

## 2. Decisiones del usuario (2026-11-24)
- **Grupo propio:** «Pacamara no susceptible», separado de Pacamara susceptible; sus hojas nunca se mezclan.
- **La roya es solo de la susceptible**, también cuando la carpeta `Roya` está al lado de `Susceptible` y
  `No susceptible` (27/07, 05/10, 26/10, 05/11). Es lo que ya hace el parser; no cambia.

## 3. Diseño
1. **Identidad (parser):** en `_discover_records`, si la especie es Pacamara y la susceptibilidad es
   «No susceptible», la especie pasa a ser `PACAMARA_NS = "Pacamara no susceptible"` (constante en
   `config.py`). La susceptible conserva el nombre «Pacamara» → sus `leaf_id`, tablas y números no cambian.
   Se quita el filtro de `get_dataset()`. Las hojas R siguen siendo de «Pacamara».
2. **Lista única de grupos:** `config.SPECIES_ORDER = ["Bourbon", "Pacamara", "Pacamara no susceptible",
   "Canefora", "Cuscatleco"]`, y que la usen todas las vistas (hoy hay listas fijas en `temporal_plots.py`,
   `espectros.py`, `indices.py`, `panorama.py`, `variedades.py`, `estado_actual.py`).
   `SUSCEPTIBLES` sigue siendo Bourbon y Pacamara (se deriva de quién tiene hoja R).
3. **Color:** uno nuevo en `SPECIES_COLORS`, de la familia de Pacamara pero distinguible (validar contraste
   ≥ 3:1 sobre blanco y separación para daltonismo con el resto, igual que la paleta actual).
4. **Similitud con roya (anclas):** hoy una especie sin R usa la media de las R de las especies con roya
   («referencia estimada»). Para Pacamara no susceptible **se propone usar la R1 de Pacamara** (misma
   variedad) como ancla con roya y sus propias hojas T como ancla sana. Mostrarla como «referencia de la
   misma variedad». *Alternativa:* tratarla como Canefora/Cuscatleco. **Confirmar con el usuario.**
5. **Rol en «¿roya o edad?»:** es un **control sin roya** (entra en «M, controles sin roya») y además el
   control más directo de Pacamara: agregar en *Evolución temporal* la comparación explícita
   Pacamara M susceptible vs Pacamara M no susceptible.
6. **Datos y calidad:** deja de figurar como «Excluido»; la tabla de susceptibilidad se mantiene como
   inventario.
7. **Telegram (riesgo):** sus 711 archivos nunca estuvieron en el registro de vistos y saldrían todos como
   «novedad» en la próxima alerta. Al migrar, marcarlos como vistos (o filtrar la primera alerta) para no
   mandar un aviso masivo.

## 4. Qué números cambian (declararlo en la app y en `METODOLOGIA.md`)
- Aparece un grupo nuevo con 4 hojas: más pares en *Comparación entre variedades* → cambian los p de Holm.
- Tendencias con FDR «sobre todas las hojas» (Evolución temporal y las 4 vistas espectrales): 22 hojas en
  vez de 18 → los p FDR de las hojas existentes cambian un poco.
- Las anclas de las demás especies **no** cambian (salvo que se elija la alternativa de §3.4).
- Textos fijos que dicen «4 variedades» / «18 hojas»: generarlos desde los datos.

## 5. Pruebas
- Parser: un `M1p1pacamara1.txt` en `no suceptible/` da especie «Pacamara no susceptible»; en
  `suceptible/` da «Pacamara»; una R en `Pacamara/Roya` da «Pacamara».
- Ninguna hoja-fecha de Pacamara susceptible cambia de valor (comparar tabla hoja-fecha antes/después).
- Humo de todas las vistas con el grupo nuevo; las 4 vistas espectrales listan 22 hojas.
- Telegram: la primera verificación después de migrar no reporta los 711 archivos.

## 6. Pendiente para preguntar al equipo
- ¿Qué significa «No susceptible»: planta de Pacamara que no se ha enfermado, o resistente?
  (Cambia cómo se redacta el rol de control.)
