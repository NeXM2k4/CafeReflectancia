"""Descubrimiento y parseo de los archivos .txt de SpectraSuite en data/.

El dataset crece con cada nueva campaña de muestreo: este modulo escanea
data/ de forma recursiva y tolera variaciones de nombre (mayusculas,
errores de ortografia en "susceptible", archivos sueltos que no siguen
el patron esperado) sin romper el resto del pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import (
    DATA_DIR,
    EXCLUDED_SPECIES,
    LEAF_MATURITY_CANONICAL,
    ROYA_LABEL,
    SANA_LABEL,
    SPECIES_CANONICAL,
    SPECIES_PENDING_LABEL,
    SUSCEPTIBILITY_CANONICAL,
)

# Patron generico {prefijo}_dd_mm_yyyy para el nombre de carpeta de una campaña
# (cubre tanto "Reflectancia_ISC_C1_29_06_2026" como "roya_15_07_2026" y futuras campañas)
_CAMPAIGN_RE = re.compile(r"^(?P<prefix>.+?)_(?P<dd>\d{2})_(?P<mm>\d{2})_(?P<yyyy>\d{4})$")
# Variante sin prefijo, vista desde agosto 2026 (p. ej. "10_08_2026", "07_09_2026"): solo
# dd_mm_yyyy, sin ningun texto antes. _CAMPAIGN_RE no la reconoce porque exige un prefijo.
_CAMPAIGN_BARE_RE = re.compile(r"^(?P<dd>\d{2})_(?P<mm>\d{2})_(?P<yyyy>\d{4})$")
_CAMPAIGN_CODE_RE = re.compile(r"C(\d+)$", re.IGNORECASE)

# M = hoja madura, T = hoja tierna, R = hoja con roya, V = hoja vieja (agregada 2026-09-11)
_PREFIX_RE = re.compile(r"^([MTRV])(\d+)p(\d+)", re.IGNORECASE)
# Variante con la palabra "roya" en vez de la letra R, vista en la campaña 17_08_2026
# (ej. "roya1p1bourbon1.txt").
_ROYA_WORD_RE = re.compile(r"^roya(\d+)p(\d+)", re.IGNORECASE)
# Variante punto-primero sin numero de hoja ni especie en el nombre, vista en varias campañas
# de agosto/septiembre 2026 (ej. "p1roya1.txt", "p1vieja1.txt"). Se asume una sola hoja ("1"),
# igual que el diseño de muestreo ya documentado para roya (una hoja R1 por campaña).
_POINT_FIRST_RE = re.compile(r"^p(\d+)(roya|vieja)(\d+)$", re.IGNORECASE)
_POINT_FIRST_SESSION = {"roya": "R", "vieja": "V"}
_SUSCEPTIBILITY_SUFFIX_RE = re.compile(r"(ns|s)\d*$", re.IGNORECASE)


def _normalize_key(name: str) -> str:
    return name.strip().lower()


def _find_campaign(parts: tuple[str, ...]) -> tuple[str | None, str | None]:
    """Busca en las partes de la ruta el patron {prefijo}_dd_mm_yyyy (o la variante sin prefijo)."""
    for part in parts:
        m = _CAMPAIGN_RE.match(part)
        if m:
            dd, mm, yyyy = m.group("dd"), m.group("mm"), m.group("yyyy")
            date = f"{yyyy}-{mm}-{dd}"
            prefix = m.group("prefix")
            code = _CAMPAIGN_CODE_RE.search(prefix)
            if code:
                base = f"C{int(code.group(1))}"
            else:
                base = prefix.rsplit("_", 1)[-1].capitalize()
            # Incluir la fecha en el id para que dos campañas con el mismo prefijo
            # (p. ej. roya_15_07_2026 y roya_21_07_2026) no se colapsen en una sola columna.
            campaign_id = f"{base}_{dd}_{mm}"
            return campaign_id, date

        m_bare = _CAMPAIGN_BARE_RE.match(part)
        if m_bare:
            dd, mm, yyyy = m_bare.group("dd"), m_bare.group("mm"), m_bare.group("yyyy")
            date = f"{yyyy}-{mm}-{dd}"
            campaign_id = f"Campaña_{dd}_{mm}"
            return campaign_id, date
    return None, None


def _detect_susceptibility_suffix(rest_lower: str) -> str | None:
    """Fallback cuando no hay subcarpeta Susceptible/No_susceptible: sufijo NS/S en el nombre."""
    m = _SUSCEPTIBILITY_SUFFIX_RE.search(rest_lower)
    if not m:
        return None
    return "No susceptible" if m.group(1) == "ns" else "Susceptible"


def _parse_filename(stem: str, species_folder: str, species: str) -> dict:
    """Extrae madurez/roya/vieja (M/T/R/V), numero de grupo, punto, repeticion y susceptibilidad.

    Ademas del patron estandar {M|T|R|V}{n}p{punto}{especie}{medida}, reconoce dos variantes
    de nombre sin numero de hoja explicito, vistas en campañas de roya/hoja vieja desde
    agosto 2026 (ver comentarios de los regex mas arriba): "roya{n}p{punto}{especie}{medida}"
    y "p{punto}roya{medida}" / "p{punto}vieja{medida}" (se asume hoja unica "1").
    """
    point_first = _POINT_FIRST_RE.match(stem)
    if point_first:
        point, category, repetition = point_first.groups()
        session = _POINT_FIRST_SESSION[category.lower()]
        return {
            "session": session,
            "session_num": 1,
            "point": int(point),
            "repetition": int(repetition),
            "name_recognized": True,
            "leaf_maturity": LEAF_MATURITY_CANONICAL.get(session),
            "has_roya": session == "R",
            "susceptibility_suffix": None,
        }

    m = _PREFIX_RE.match(stem)
    if m:
        session, session_num, point = m.groups()
        session = session.upper()
        rest = stem[m.end():]
    else:
        m_word = _ROYA_WORD_RE.match(stem)
        if not m_word:
            return {
                "session": None,
                "session_num": None,
                "point": None,
                "repetition": None,
                "name_recognized": False,
                "leaf_maturity": None,
                "has_roya": None,
                "susceptibility_suffix": None,
            }
        session_num, point = m_word.groups()
        session = "R"
        rest = stem[m_word.end():]

    species_key = _normalize_key(species_folder)
    rest_lower = rest.lower()
    if rest_lower.startswith(species_key):
        rest = rest[len(species_key):]
        rest_lower = rest.lower()

    rep_match = re.search(r"(\d+)$", rest)
    repetition = int(rep_match.group(1)) if rep_match else 1

    susceptibility_suffix = None
    if species == "Pacamara":
        susceptibility_suffix = _detect_susceptibility_suffix(rest_lower)

    return {
        "session": session,
        "session_num": int(session_num),
        "point": int(point),
        "repetition": repetition,
        "name_recognized": True,
        "leaf_maturity": LEAF_MATURITY_CANONICAL.get(session),
        "has_roya": session == "R",
        "susceptibility_suffix": susceptibility_suffix,
    }


def leaf_label(session, session_num) -> str:
    """Etiqueta de hoja para mostrar ("M1", "T2", "R1").

    `session_num` se guarda como entero, pero al armar el DataFrame la columna queda float
    (los archivos de nombre no reconocido aportan NaN), asi que sin normalizar aqui la hoja
    se mostraria como "M1.0".
    """
    if pd.isna(session):
        return "?"
    if pd.isna(session_num):
        return str(session)
    return f"{session}{int(session_num)}"


def sorted_campaigns(df: pd.DataFrame) -> list:
    """Ids de campaña presentes en `df`, en orden cronologico real (por `campaign_date`).

    El id de campaña no ordena igual que la fecha (ej. "Campaña_07_09", de septiembre, ordena
    alfabeticamente antes que "Campaña_10_08", de agosto), asi que no alcanza con hacer
    sorted() sobre la columna `campaign_id` directamente.
    """
    return (
        df[["campaign_id", "campaign_date"]]
        .dropna(subset=["campaign_id"])
        .drop_duplicates()
        .sort_values("campaign_date")["campaign_id"]
        .tolist()
    )


@dataclass(frozen=True)
class FileRecord:
    path: str
    filename: str
    campaign_id: str | None
    campaign_date: str | None
    species: str
    susceptibility: str | None
    session: str | None
    session_num: int | None
    point: int | None
    repetition: int | None
    name_recognized: bool
    mtime_ns: int
    size: int
    leaf_maturity: str | None
    has_roya: bool | None
    health_status: str | None


def _dir_fingerprint(data_dir: Path) -> tuple:
    """Firma liviana de la carpeta de datos: cambia si se agregan/editan archivos.

    Se usa como argumento de la funcion cacheada para que Streamlit
    invalide el cache automaticamente cuando llegan mediciones nuevas.
    """
    if not data_dir.exists():
        return ()
    entries = []
    for path in sorted(data_dir.rglob("*.txt")):
        try:
            stat = path.stat()
            entries.append((str(path.relative_to(data_dir)), stat.st_mtime_ns, stat.st_size))
        except OSError:
            continue
    return tuple(entries)


def _discover_records(data_dir: Path) -> list[FileRecord]:
    records: list[FileRecord] = []

    for path in sorted(data_dir.rglob("*.txt")):
        rel_parts = path.relative_to(data_dir).parts
        if len(rel_parts) < 2:
            continue  # archivo suelto en la raiz de data/, sin especie identificable

        campaign_id, campaign_date = _find_campaign(rel_parts)

        # La especie es la primera carpeta que coincide con SPECIES_CANONICAL
        species = None
        species_folder_raw = None
        susceptibility = None
        for i, part in enumerate(rel_parts[:-1]):
            key = _normalize_key(part)
            if key in SPECIES_CANONICAL:
                species = SPECIES_CANONICAL[key]
                species_folder_raw = part
                # La carpeta siguiente (si existe y no es la del archivo) puede indicar susceptibilidad
                if i + 1 < len(rel_parts) - 1:
                    sub_key = _normalize_key(rel_parts[i + 1])
                    susceptibility = SUSCEPTIBILITY_CANONICAL.get(sub_key)
                break

        if species is None:
            # Fallback: especie no encontrada en subcarpeta → intentar detectarla desde el nombre del archivo.
            # Cubre carpetas de prueba donde los .txt van sueltos sin subcarpeta de especie
            # (p. ej. prueba_17_07_2026/M9p1bourbon1.txt).
            stem_m = _PREFIX_RE.match(path.stem)
            if stem_m:
                rest_lower_fb = path.stem[stem_m.end():].lower()
                for key, canonical in SPECIES_CANONICAL.items():
                    if rest_lower_fb.startswith(key):
                        species = canonical
                        species_folder_raw = key
                        break

        if species is None and any(_normalize_key(part) == "vieja" for part in rel_parts[:-1]):
            # Carpeta "vieja" (hoja vieja) sin especie identificable en el nombre del archivo
            # (ver SPECIES_PENDING_LABEL en config.py): se agrupan aparte en vez de perderse.
            species = SPECIES_PENDING_LABEL
            species_folder_raw = "vieja"

        if species is None:
            continue  # carpeta no reconocida como especie; se ignora del dataset

        meta = _parse_filename(path.stem, species_folder_raw, species)
        # Si no vino de una subcarpeta, usar el sufijo NS/S detectado en el nombre (Pacamara)
        susceptibility_suffix = meta.pop("susceptibility_suffix")
        susceptibility = susceptibility or susceptibility_suffix

        has_roya = meta["has_roya"]
        if has_roya is None:
            health_status = None
        else:
            health_status = ROYA_LABEL if has_roya else SANA_LABEL

        try:
            stat = path.stat()
        except OSError:
            continue

        records.append(
            FileRecord(
                path=str(path),
                filename=path.name,
                campaign_id=campaign_id,
                campaign_date=campaign_date,
                species=species,
                susceptibility=susceptibility,
                mtime_ns=stat.st_mtime_ns,
                size=stat.st_size,
                health_status=health_status,
                **meta,
            )
        )

    return records


@st.cache_data(show_spinner="Escaneando data/...")
def scan_dataset(_fingerprint: tuple) -> pd.DataFrame:
    """Devuelve un DataFrame con un registro por archivo .txt encontrado en data/.

    _fingerprint se usa solo para invalidar el cache de Streamlit cuando
    cambia el contenido de la carpeta; no se usa dentro de la funcion.
    """
    records = _discover_records(DATA_DIR)
    if not records:
        return pd.DataFrame(
            columns=[
                "path", "filename", "campaign_id", "campaign_date", "species",
                "susceptibility", "session", "session_num", "point",
                "repetition", "name_recognized", "mtime_ns", "size",
                "leaf_maturity", "has_roya", "health_status",
            ]
        )
    return pd.DataFrame([r.__dict__ for r in records])


def get_dataset(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Punto de entrada: escanea data/ (con cache automatico segun su contenido).

    Aplica los dos filtros del proyecto antes de entregar el DataFrame:

    - **Pacamara No susceptible**: esas hojas no participan del analisis (el foco son las
      plantas susceptibles a roya). Las Susceptible o sin susceptibilidad clasificada se
      conservan.
    - **EXCLUDED_SPECIES**: especies sin permiso de uso de datos (ver `config.py`).

    Es el unico punto donde se filtra, asi que las 4 paginas del dashboard y
    `make_ieee_figures.py` lo heredan sin tener que repetir la condicion. Si se necesita el
    dataset crudo, usar `_discover_records(DATA_DIR)`.
    """
    fingerprint = _dir_fingerprint(data_dir)
    df = scan_dataset(fingerprint)
    if df.empty:
        return df
    mask_excluir = (df["species"] == "Pacamara") & (df["susceptibility"] == "No susceptible")
    mask_excluir |= df["species"].isin(EXCLUDED_SPECIES)
    return df[~mask_excluir].reset_index(drop=True)


@st.cache_data(show_spinner=False)
def read_spectrasuite(path: str, _mtime: float) -> pd.DataFrame:
    """Parsea un archivo .txt exportado por SpectraSuite.

    _mtime solo se usa para invalidar el cache si el archivo se sobrescribe.
    """
    with open(path, "r", encoding="latin-1", errors="replace") as f:
        lineas = f.read().splitlines()

    inicio = None
    for i, linea in enumerate(lineas):
        if "Comienza Data" in linea or "Begin Spectral" in linea:
            inicio = i + 1
            break
    if inicio is None:
        raise ValueError(f"No se encontro el marcador de inicio de datos en {path}")

    filas = []
    for linea in lineas[inicio:]:
        linea = linea.strip()
        if not linea:
            continue
        partes = linea.replace(",", ".").split()
        if len(partes) >= 2:
            try:
                filas.append((float(partes[0]), float(partes[1])))
            except ValueError:
                continue

    if not filas:
        raise ValueError(f"Sin datos numericos validos en {path}")

    df = pd.DataFrame(filas, columns=["wavelength", "reflectance"])
    df = df.drop_duplicates(subset="wavelength").sort_values("wavelength").reset_index(drop=True)
    return df


def load_spectrum(path: str) -> pd.DataFrame:
    """Lee un espectro reusando el cache si el archivo no ha cambiado en disco."""
    mtime = Path(path).stat().st_mtime
    return read_spectrasuite(path, mtime)
