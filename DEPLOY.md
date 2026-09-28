# Publicar la rama y desplegar

## A. Subir el trabajo a una rama nueva del repo

Repo remoto: `https://github.com/NeXM2k4/CafeReflectancia.git` (`origin`).
Rama con el trabajo: `mejora-app` (ya existe local; `main` no se tocó).

```bash
git status                            # debe estar limpio (todo commiteado)
git log --oneline main..mejora-app    # los commits que se van a publicar
git push -u origin mejora-app         # crea la rama en GitHub y la enlaza
```
Si prefieres otro nombre en el remoto: `git push -u origin mejora-app:app-pulida`.

Luego, en GitHub: **Compare & pull request** (base `main`, compare `mejora-app`), revisa el diff y
haz **Merge**. Para poder volver atrás existe el tag `app-antes-de-pulir`
(`git push origin app-antes-de-pulir` si quieres publicarlo también).

Después del merge, localmente: `git switch main && git pull`.

> ⚠️ **Antes de publicar:** `data/` está versionado (~130 MB, ~2200 archivos) e incluye Canefora y
> Cuscatleco, cuyos datos en algún momento se excluyeron por falta de permiso de uso. Si el repo es
> **público**, confirma que puedes publicarlos; si no, hazlo privado. Nunca subas
> `.streamlit/secrets.toml` (ya está en `.gitignore`).

## B. Desplegar en Streamlit Community Cloud (opción más simple)

1. Entra a <https://share.streamlit.io> con tu cuenta de GitHub y autoriza el acceso al repo.
2. **Create app → Deploy from GitHub**: repo `NeXM2k4/CafeReflectancia`, rama `main` (o
   `mejora-app` si quieres probarla antes del merge), archivo principal `app.py`.
3. **Advanced settings → Python version**: 3.11 o 3.12 (localmente se probó con 3.10; las
   dependencias de `requirements.txt` funcionan en ambas).
4. **Advanced settings → Secrets**: pega
   ```toml
   [telegram]
   bot_token = "TU_TOKEN"
   chat_id = "TU_CHAT_ID"
   ```
   (se obtienen como indica `.streamlit/secrets.toml.example`). Sin esto la app funciona, pero el
   botón de Telegram avisa que faltan credenciales.
5. **Deploy**. La primera carga tarda unos minutos (instala dependencias y calcula los índices de
   ~2000 archivos); las siguientes son rápidas.
6. Para restringir el acceso: **Settings → Sharing → Only specific people** (por correo).

### Limitaciones del hosting gratuito que conviene conocer
- **Disco efímero:** `.state/` (registro de archivos ya avisados y cachés) se pierde cuando la app
  se reinicia o "duerme". Consecuencia: la primera verificación de Telegram tras un reinicio verá
  *todo* como novedad. Usa **"🧹 Marcar todo como visto (sin avisar)"** antes de agregar campañas
  nuevas y no pulses "Enviar" si la vista previa muestra cientos de archivos. Para un registro
  persistente habría que moverlo a un almacenamiento externo (no implementado).
- **Datos nuevos = commit nuevo:** en la nube la app lee `data/` del repo; para agregar una campaña
  copia la carpeta, `git add data/ && git commit && git push`, y la app se redespliega sola.
- **Memoria:** ~1 GB. Si se queda corta, despliega en un servidor propio (sección C).

## C. Alternativa: servidor propio / Docker (control total y disco persistente)

```bash
git clone https://github.com/NeXM2k4/CafeReflectancia.git && cd CafeReflectancia
git switch main
python -m venv .venv && source .venv/bin/activate     # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
mkdir -p .streamlit && cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # edita tus valores
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```
Para dejarlo corriendo: `systemd`, o Docker con un `Dockerfile` mínimo
(`FROM python:3.11-slim`, `COPY . /app`, `WORKDIR /app`, `RUN pip install -r requirements.txt`,
`CMD ["streamlit","run","app.py","--server.address=0.0.0.0"]`), montando `.state/` como volumen y
poniendo delante un proxy con HTTPS y contraseña (Streamlit no trae autenticación propia).

## D. Verificación tras desplegar
1. Inicio carga y "Calidad de datos" no muestra archivos sin reconocer inesperados.
2. Recorre las 5 pestañas de la página 5 y cambia de especie 3–4 veces seguidas.
3. "Verificar y analizar nueva data" → mira la vista previa; **no** envíes si no esperas novedades.
