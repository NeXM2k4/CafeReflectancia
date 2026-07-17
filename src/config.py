"""Parametros por defecto del pipeline de analisis de reflectancia."""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# --- Savitzky-Golay ---
SG_WINDOW = 41
SG_POLYORDER = 2

# --- Rango de longitud de onda util (nm) ---
X_MIN, X_MAX = 420, 1000

# --- Especies canonicas (nombre de carpeta normalizado -> nombre para mostrar) ---
SPECIES_CANONICAL = {
    "bourbon": "Bourbon",
    "canefora": "Canefora",
    "cuscatleco": "Cuscatleco",
    "pacamara": "Pacamara",
}

# --- Susceptibilidad (solo aplica a Pacamara por ahora) ---
SUSCEPTIBILITY_CANONICAL = {
    "susceptible": "Susceptible",
    "suseptibles": "Susceptible",
    "suceptible": "Susceptible",
    "no_susceptible": "No susceptible",
    "no_suceptible": "No susceptible",
    "nosusceptible": "No susceptible",
}

# --- Madurez de la hoja: prefijo M/T del nombre de archivo ---
LEAF_MATURITY_CANONICAL = {
    "M": "Madura",
    "T": "Tierna",
}

# --- Estado sanitario: prefijo R/r del nombre de archivo indica roya ---
ROYA_LABEL = "Con roya"
SANA_LABEL = "Sana"

# --- Longitudes de onda usadas en los indices espectrales ---
WL_NDVI = (800, 670)
WL_PRI = (531, 570)
WL_PSRI = (678, 500, 750)
WL_CARI = (550, 670, 700)
WL_RCI = (510, 550)
WL_EDI = (705, 750)
WL_FSR = WL_NDVI  # mismas bandas que NDVI (NIR 800 / Rojo 670); nombre distinto para reporte de estres foliar

# --- Paleta de colores para curvas individuales ---
PALETTE = [
    "#E63946", "#F4A261", "#2A9D8F", "#457B9D", "#9B5DE5", "#F15BB5",
    "#00B4D8", "#FFBE0B", "#06D6A0", "#FB5607", "#6A0572", "#C9F030",
    "#FF595E", "#1982C4", "#8AC926", "#FF924C", "#4CC9F0", "#B5179E",
    "#3A86FF", "#CAFFBF",
]

COLOR_AVG = "#FAFAFA"  # claro y neutro para maxima legibilidad sobre el tema oscuro

# Colores estables por grupo (madurez, susceptibilidad, estado sanitario) para graficas comparativas
GROUP_COLORS = {
    "Madura": "#2A9D8F",
    "Tierna": "#457B9D",
    "Susceptible": "#F4A261",
    "No susceptible": "#2A9D8F",
    SANA_LABEL: "#0CA30C",
    ROYA_LABEL: "#D03B3B",
}

# Paleta reducida y de alto contraste para agrupar curvas de espectros por "Hoja"
# (mismo set validado de 8 tonos usado para SPECIES_COLORS, en el mismo orden)
SPECTRA_GROUP_PALETTE = [
    "#3987E5", "#008300", "#D55181", "#C98500",
    "#199E70", "#D95926", "#9085E9", "#E66767",
]

# Paleta categorica fija por especie (misma asignacion en todas las paginas/graficas)
SPECIES_COLORS = {
    "Bourbon": "#3987E5",
    "Canefora": "#008300",
    "Cuscatleco": "#D55181",
    "Pacamara": "#C98500",
}

# Descripciones breves de cada indice espectral, para la leyenda en las paginas de indices
INDEX_DEFINITIONS = {
    "NDVI": "Vigor/verdor general de la hoja (clorofila vs. infrarrojo cercano).",
    "PRI": "Eficiencia fotosintetica / estres, via el ciclo de xantofilas.",
    "PSRI": "Senescencia: sube cuando el tejido foliar se degrada.",
    "CARI": "Concentracion relativa de clorofila, corregida por linea base.",
    "RCI": "Rust Carotenoid Index: carotenoides asociados a estres por roya.",
    "EDI": "Early Detection Index: shift del borde rojo (red-edge).",
    "FSR": "Foliar Stress Ratio (mismas bandas que NDVI en la formulacion actual).",
}

ALPHA_SIGNIFICANCE = 0.05
