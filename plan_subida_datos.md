# Plan: subir campañas nuevas desde la app

Fecha: 2026-11-18. Estado: **diseño, pendiente de aprobación**.

## 1. Para qué

Un compañero del equipo mide en campo y quiere cargar cada campaña nueva sin usar git (clonar, pull,
add, commit, push, ramas). Hoy la única vía es copiar la carpeta a `data/`, correr
`scripts/build_cache.py` y hacer commit + push. Queremos que **arrastre un `.zip`, revise una vista
previa y apriete un botón**; la app guarda los datos en el repo y Streamlit Cloud se actualiza sola.

Éxito = el compañero sube una campaña de punta a punta sin ayuda, y lo que queda en el repo es
idéntico a lo que habría quedado haciéndolo a mano (`data/<campaña>/…` + `data_cache/<campaña>.parquet`).

## 2. Alcance

**Objetivos**
- Subir **una campaña nueva** (una fecha que todavía no existe) como `.zip`.
- Vista previa antes de guardar: qué se reconoce, qué no, y si hay espectros dudosos.
- Un único commit a `main` con los `.txt` y el parquet de `data_cache/` de esa campaña.
- Funciona en Streamlit Community Cloud (disco efímero) sin pasos manuales posteriores.

**No objetivos (v1)**
- Corregir, completar, reemplazar o borrar campañas ya subidas (eso sigue siendo por git).
- Renombrar archivos mal nombrados desde la app.
- Enviar el aviso de Telegram automáticamente (sigue en *Alerta de campo*, después del redespliegue).
- Cuentas de usuario o permisos por persona.

**Antiobjetivos (si pasa esto, falló aunque "funcione")**
- Que una subida pueda modificar o borrar un archivo que ya existe en el repo.
- Que entren archivos en silencio: todo lo no reconocido o ilegible se muestra antes de confirmar.
- Que quede un commit a medias (datos sin parquet, o parte de los archivos).
- Que el compañero tenga que entender qué es un commit, una rama o un conflicto.

## 3. Restricciones

- **Disco efímero en Streamlit Cloud:** lo que se escriba en `data/` del contenedor se pierde. La
  persistencia es el repo de GitHub (`NeXM2k4/CafeReflectancia`, rama `main`).
- Streamlit Cloud redespliega solo tras cada push a `main`: la app se reinicia para todos (~1–2 min).
- Una campaña son ~340 `.txt` de ~100 KB (≈35 MB sin comprimir, ~10 MB en zip). Límite de subida de
  Streamlit por defecto: 200 MB (alcanza; no se toca).
- Los `.txt` están en ISO-8859-1 con CRLF: se suben **byte a byte** (blobs en base64), sin decodificar.
- La variedad y la susceptibilidad salen de las subcarpetas (`pacamara/suceptible/roya/…`): por eso
  se pide un zip, que conserva la estructura.
- Nada de atribución a Claude en los commits que hace la app.

## 4. Enfoques considerados

| Enfoque | A favor | En contra |
|---|---|---|
| **A. Página en la app que commitea por la API de GitHub** (elegido) | Sin git para el usuario; valida antes de guardar; mantiene `data_cache/` al día; todo queda versionado como hoy | Requiere un token con permiso de escritura en `secrets`; ~1–2 min hasta ver los datos |
| B. Subir desde la web de GitHub (*Add file → Upload files*) | Cero código | Sin validación; `data_cache/` desactualizado; obliga a usar GitHub |
| C. Almacenamiento externo (Drive, S3, Supabase) | Datos fuera del repo | Cambia cómo lee los datos toda la app; demasiado para la necesidad |

Elegido A por el usuario (2026-11-18), solo para campañas nuevas.

## 5. Diseño

### 5.1 Página «Subir campaña»
Nueva vista `views/subir.py`, en la sección *Datos y operación* (junto a *Datos y calidad* y
*Alerta de campo*). Flujo en una sola pantalla, de arriba abajo:

```
Subir campaña
 ① Clave de subida        [••••••]                (solo si no se ingresó en esta sesión)
 ② Arrastrá el .zip       [ soltar aquí ]
 ③ Fecha de la campaña    [16/11/2026]  → se guarda como data/16_11_2026/
 ④ Vista previa
     Bourbon    M1 9 · M2 9 · T1 9 · T2 9 · R1 9          ✓
     Pacamara   …
     ⚠ 27 archivos no reconocidos (bourbon/validacion/…)  [ver lista]
     ⚠ 1 espectro sin firma de hoja (NDVI ≈ 0)            [ver lista]
 ⑤ ☐ Revisé los avisos y quiero subir igual   (solo si hay avisos)
    [ Subir campaña ]
 ⑥ ✓ Subida: 342 archivos. La app se actualiza en 1–2 min.  (enlace al commit)
```

### 5.2 Lectura del zip (`src/upload.py`, sin Streamlit)
- Se descomprime en una carpeta temporal `tmp/data/<dd_mm_yyyy>/…`.
- **Carpeta envoltorio:** si el zip tiene una sola carpeta en la raíz (p. ej. `16_11_2026/`, o la
  doble `16_11_2026/16_11_2026/` que se ve hoy), se quitan esos niveles de fecha; el contenido
  (carpetas de variedad, `vieja/`) queda directamente bajo `data/<dd_mm_yyyy>/`.
- Solo se guardan `.txt`. Lo demás (`__MACOSX/`, `.DS_Store`, `Thumbs.db`, otros formatos) se lista
  como «ignorado» en la vista previa.
- Seguridad: se rechazan entradas con ruta absoluta o `..`; tope de 500 MB descomprimido y
  5000 archivos (protección contra zips maliciosos o equivocados).
- **Fecha:** se propone la que detecte `parser._find_campaign` en las rutas del zip; si no hay, el
  campo queda vacío y es obligatorio. El nombre de carpeta siempre es `dd_mm_yyyy` (formato vigente
  desde agosto 2026, ya reconocido por el parser).

### 5.3 Vista previa (mismo código que la app)
- `parser._discover_records(tmp/data)` → qué archivos se reconocen (variedad, hoja, punto,
  repetición, susceptibilidad) y cuáles no (`name_recognized == False` o sin variedad).
- `store.build_store(tmp/data, tmp/data_cache)` → índices, espectros ilegibles (`error != ""`) y el
  parquet de la campaña, idéntico al que produciría `scripts/build_cache.py`.
- Avisos (no bloquean; requieren marcar la casilla ⑤):
  - archivos no reconocidos o fuera de una carpeta de variedad (no entrarán al análisis);
  - espectros ilegibles;
  - espectros sin firma de hoja (mismo criterio NDVI ≈ 0 que *Datos y calidad*);
  - hojas con un número de archivos distinto de 9 (p1–p3 × 3 repeticiones).
- Bloquea (no deja subir):
  - fecha vacía o inválida, o fecha **futura**;
  - ya existe en el repo una carpeta `data/<dd_mm_yyyy>/` **o** cualquier campaña con la misma
    fecha (p. ej. `roya_15_07_2026`) — se comprueba contra GitHub, no contra el disco local;
  - el zip no tiene ningún `.txt` reconocido.

Decisión propia (corregible): los no reconocidos **avisan pero no bloquean**, porque hoy hay datos
reales en esa situación (`bourbon/validacion/`) y bloquearlos impediría subir la campaña entera.
Quedan en el repo y aparecen en *Datos y calidad* como ya ocurre.

### 5.4 Commit a GitHub (`src/github_commit.py`, solo `requests`)
API de datos de Git, un único commit:
1. `GET ref heads/<rama>` → commit actual → árbol base.
2. Comprobar en ese árbol que `data/<carpeta>` y `data_cache/<carpeta>.parquet` **no existen**
   (si existen: se detiene, nada cambia).
3. Un blob por archivo (base64, contenido exacto) — hasta 8 en paralelo.
4. Árbol nuevo con `base_tree` = árbol base y **solo rutas nuevas** (nunca modifica ni borra).
5. Commit: «Campaña dd/mm/aaaa subida desde la app (N archivos)» + nombre de quien sube en el cuerpo.
6. `PATCH ref` sin `force`. Si `main` avanzó mientras tanto (422), se repite 2–4 con el nuevo
   commit, hasta 3 veces. Si falla, no se actualizó la rama: no queda nada a medias (los blobs
   sueltos no afectan al repo).
- Errores traducidos a mensajes claros: token inválido o vencido (401), sin permiso (403/404),
  red. Nunca se muestra el token.
- Doble clic: el botón se desactiva tras el primer envío (estado de sesión) y el paso 2 impide
  duplicar aunque se reintente.

### 5.5 Configuración (`secrets`)
```toml
[subida]
clave = "…"                         # la que se le da al compañero
github_token = "github_pat_…"       # token fine-grained: SOLO este repo, Contents: read/write
repo = "NeXM2k4/CafeReflectancia"
rama = "main"                       # para probar: una rama de prueba
```
Sin esta sección la página explica que la subida no está configurada y no muestra nada más
(caso normal al correr en local). Los commits aparecen a nombre de la cuenta dueña del token.
Los tokens fine-grained vencen: anotar la fecha; al vencer, la página lo dice claramente.

### 5.6 Después de subir
- Streamlit Cloud redespliega solo; la campaña aparece en todas las páginas.
- Quien trabaje con el repo en local tiene que hacer `git pull` antes de su próximo commit (no habrá
  conflictos: la subida solo agrega carpetas nuevas). Se documenta en `README.md` y `DEPLOY.md`.
- `tests/test_store.py::test_almacen_versionado_esta_al_dia` debe seguir pasando tras el pull.

## 6. Pruebas y criterios de aceptación
1. Unitarias de `upload.py`: quita envoltorio simple y doble; ignora no-`.txt`; rechaza `..` y
   rutas absolutas; detecta la fecha; respeta los topes.
2. El parquet generado desde el zip es **idéntico** (mismas filas y valores) al que genera
   `build_store` sobre esa campaña copiada en `data/` (probar con `16_11_2026`).
3. Unitarias de `github_commit.py` con la API simulada: camino feliz; carpeta ya existente;
   `main` avanzó (reintento); 401; solo se envían rutas nuevas.
4. `AppTest` de la página: sin secretos; clave incorrecta; zip válido → vista previa; fecha repetida
   → bloqueado.
5. Prueba real contra una **rama de prueba** del repo antes de habilitar `main`, con la campaña
   `16_11_2026` re-empaquetada: el commit contiene exactamente los mismos archivos que hoy.
6. Las 22 pruebas existentes siguen pasando.

## 7. Queda a criterio de quien implemente
Textos exactos de la página, diseño de la tabla de vista previa, nombres de funciones internas y
cómo se muestran las listas largas (expansores, tablas).

## 8. Pasos manuales del usuario (una vez)
1. Crear el token fine-grained en GitHub (solo este repo, *Contents: Read and write*).
2. Pegar la sección `[subida]` en *Settings → Secrets* de la app en Streamlit Cloud.
3. Pasarle la clave al compañero.
