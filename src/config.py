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

# --- Especies excluidas del analisis ---
# Entre el 2026-08-03 y el 2026-09-11 esta tupla traia ("Canefora", "Cuscatleco") por falta de
# permiso de uso de sus datos. Se vacio el 2026-09-11 a pedido del usuario para volver a
# mostrar las 4 especies en el dashboard. El punto de reversion sigue siendo esta tupla: si en
# el futuro hay que excluir alguna especie de nuevo, basta con agregarla aqui.
EXCLUDED_SPECIES = ()

# --- Especie "pendiente" para hojas viejas sin especie identificable (agregada 2026-09-11) ---
# Desde las campañas de agosto/septiembre 2026 aparece una carpeta "vieja" (hoja vieja) al mismo
# nivel que las carpetas de especie. Solo la campaña 17_08_2026 especifica la especie en el
# nombre de archivo (canefora); el resto de campañas con hojas viejas no trae especie en
# absoluto. Mientras se confirma con el equipo de campo, esos archivos se agrupan bajo esta
# etiqueta generica (ver `parser._discover_records`) en vez de perderse o asignarse a una
# especie real por error. Cuando se sepa la especie correcta hay que reclasificar esos archivos
# (o el parser) y esta etiqueta puede dejar de usarse.
SPECIES_PENDING_LABEL = "Vieja (especie pendiente)"

# --- Susceptibilidad (solo aplica a Pacamara por ahora) ---
SUSCEPTIBILITY_CANONICAL = {
    "susceptible": "Susceptible",
    "suseptible": "Susceptible",
    "suseptibles": "Susceptible",
    "suceptible": "Susceptible",
    "no_susceptible": "No susceptible",
    "no_suceptible": "No susceptible",
    "no_suseptible": "No susceptible",
    "nosusceptible": "No susceptible",
    "no susceptible": "No susceptible",
    "no suceptible": "No susceptible",
    "no suseptible": "No susceptible",
    "no suceptibles": "No susceptible",
}

# --- Madurez de la hoja: prefijo M/T/V del nombre de archivo ---
# "V" = hoja vieja, categoria agregada 2026-09-11 (ver SPECIES_PENDING_LABEL para el problema
# de especie sin identificar que trae esta categoria en varias campañas).
LEAF_MATURITY_CANONICAL = {
    "M": "Madura",
    "T": "Tierna",
    "V": "Vieja",
}

# --- Estado sanitario: prefijo R/r del nombre de archivo indica roya ---
ROYA_LABEL = "Con roya"
SANA_LABEL = "Sana"

# --- Tipo de hoja: fuente unica de verdad para color y etiqueta (F1.5 de plan_mejora_app.md) ---
# Antes de esta sesion de pulido, "Madura"/"Tierna" tenian un color en `GROUP_COLORS` (paginas
# 2-4) y otro distinto en `LEAF_TYPE_COLORS` (pagina 5) — el mismo concepto se veia de dos
# colores segun la pagina. Ahora todo el codigo lee de aqui. Paleta validada contra daltonismo
# (ver `evoluciontemporal.md` seccion 11: ΔE deutan 9.4 sobre fondo oscuro #0E1117) para M/T/R;
# "V" usa un cuarto tono que no se probo formalmente (categoria minoritaria, sin serie temporal).
#
# IMPORTANTE: "Madura" y "Tierna" son el estado sanitario **desconocido**, no "sano" — la app
# nunca debe mostrarlas como si equivalieran a "sana" (ver diagnostico de plan_mejora_app.md).
LEAF_TYPE_COLORS = {"M": "#3987E5", "T": "#199E70", "R": "#D95926", "V": "#9085E9"}
LEAF_TYPE_LABELS = {"M": "Madura", "T": "Tierna", "R": "Con roya", "V": "Vieja"}
LEAF_TYPE_HELP = {
    "M": "Hoja madura: sin sintomas visibles, pero su estado sanitario real no se conoce.",
    "T": "Hoja tierna: tejido nuevo, la roya no ha tenido tiempo de manifestarse. Referencia sana.",
    "R": "Hoja con roya confirmada visualmente.",
    "V": "Hoja vieja (madurez adicional a M/T); en varias campañas no se registro su especie.",
}
LEAF_NUM_DASH = {1: "solid", 2: "dash"}


def leaf_type_label(code: str, short: bool = False) -> str:
    """Etiqueta para mostrar de un tipo de hoja ('M' -> 'Madura', o 'Madura (M)' si short=False)."""
    nombre = LEAF_TYPE_LABELS.get(code, str(code))
    return nombre if short else f"{nombre} ({code})"

# --- Escala de similitud con roya: 4 clases (rediseñada 2026-09-28, ver plan_mejora_app.md D4) ---
# Hasta el 2026-09-27 eran 11 clases con descripciones de **planta entera** ("defoliacion",
# "muerte de la planta"), calculadas a partir de 3 puntos de **una sola hoja** con roya por
# especie. Una escala tan fina no se puede sostener con ese tamaño de muestra (n=1), y las
# descripciones de sintomas de planta no corresponden a lo que en realidad se mide (reflectancia
# de una hoja). Las 4 clases describen **similitud espectral**, no severidad de la planta. Los
# nombres van en español (la alerta de Telegram pasa a español, ver D1); `level` es el valor
# nominal de la clase y un score se asigna a la clase cuyo nivel tiene mas cerca
# (ver `rust_risk_class`).
RUST_RISK_CLASSES = [
    (0.0, "Sin señal de roya", "🟢", "Espectro similar al de una hoja tierna sana de referencia."),
    (1 / 3, "Vigilar", "🟡", "Alguna similitud con la hoja de referencia con roya, todavia debil."),
    (2 / 3, "Revisar en campo", "🟠", "Similitud considerable con la hoja de referencia con roya."),
    (1.0, "Alta similitud con roya", "🔴", "El espectro se parece mucho al de la hoja con roya confirmada."),
]

# Accion sugerida por clase (una por clase: con solo 4 no hace falta agrupar en tramos).
RUST_RISK_ACTIONS = [
    (1 / 6, "Sin accion necesaria: mantener el monitoreo habitual."),
    (0.5, "Revisar esta hoja/planta en la proxima visita de campo."),
    (5 / 6, "Inspeccionar esta hoja en campo lo antes posible."),
    (1.01, "Inspeccionar de inmediato y evaluar manejo/tratamiento contra la roya."),
]


def rust_risk_class(score: float) -> tuple[float, str, str, str]:
    """Clase de similitud mas cercana al score (0-1). Devuelve (nivel, nombre, emoji, descripcion).

    Se asigna por cercania (no por tramo inferior) para que cada clase quede centrada en su
    valor nominal.
    """
    return min(RUST_RISK_CLASSES, key=lambda clase: abs(clase[0] - score))


def rust_risk_action(score: float) -> str:
    """Accion sugerida para esa similitud."""
    return next(texto for limite, texto in RUST_RISK_ACTIONS if score < limite)

# --- Longitudes de onda usadas en los indices espectrales ---
WL_NDVI = (800, 670)
WL_PRI = (531, 570)
WL_PSRI = (678, 500, 750)
WL_RCI = (510, 550)
WL_EDI = (705, 750)
WL_NDRE = (790, 720)
WL_MNDVI705 = (750, 705, 445)
WL_FSR = WL_NDVI  # mismas bandas que NDVI (NIR 800 / Rojo 670); nombre distinto para reporte de estres foliar

# --- Paleta de colores para curvas individuales ---
PALETTE = [
    "#E63946", "#F4A261", "#2A9D8F", "#457B9D", "#9B5DE5", "#F15BB5",
    "#00B4D8", "#FFBE0B", "#06D6A0", "#FB5607", "#6A0572", "#C9F030",
    "#FF595E", "#1982C4", "#8AC926", "#FF924C", "#4CC9F0", "#B5179E",
    "#3A86FF", "#CAFFBF",
]

COLOR_AVG = "#FAFAFA"  # claro y neutro para maxima legibilidad sobre el tema oscuro

# Colores estables por grupo (madurez, susceptibilidad, estado sanitario) para graficas
# comparativas. Madura/Tierna/Vieja/Con roya se toman de LEAF_TYPE_COLORS (fuente unica, ver
# arriba); "Sana" y la susceptibilidad de variedad son dimensiones distintas sin equivalente ahi.
GROUP_COLORS = {
    "Madura": LEAF_TYPE_COLORS["M"],
    "Tierna": LEAF_TYPE_COLORS["T"],
    "Vieja": LEAF_TYPE_COLORS["V"],
    "Susceptible": "#F4A261",
    "No susceptible": "#2A9D8F",
    SANA_LABEL: "#0CA30C",
    ROYA_LABEL: LEAF_TYPE_COLORS["R"],
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
    SPECIES_PENDING_LABEL: "#8A8A8A",
}

# Descripciones breves de cada indice espectral, para la leyenda en las paginas de indices
INDEX_DEFINITIONS = {
    "NDVI": "Vigor/verdor general de la hoja (clorofila vs. infrarrojo cercano).",
    "PRI": "Eficiencia fotosintetica / estres, via el ciclo de xantofilas.",
    "PSRI": "Senescencia: sube cuando el tejido foliar se degrada.",
    "RCI": "Rust Carotenoid Index: carotenoides asociados a estres por roya.",
    "EDI": "Early Detection Index: shift del borde rojo (red-edge).",
    "FSR": "Foliar Stress Ratio (mismas bandas que NDVI en la formulacion actual).",
    "NDRE": "Normalized Difference Red Edge: clorofila via borde rojo (790/720 nm).",
    "mNDVI705": "NDVI modificado del borde rojo, corregido por dispersion foliar con R445.",
}

ALPHA_SIGNIFICANCE = 0.05

# --- Evolucion temporal por hoja (ver evoluciontemporal.md) ---
# Los puntos no son ubicaciones fijas entre campañas y solo p1-p3 son validos (decision del
# usuario 2026-09-27); p4-p6 aparecen en algunas campañas y se excluyen del analisis temporal.
TEMPORAL_VALID_POINTS = (1, 2, 3)
TEMPORAL_LEAF_TYPES = ("M", "T", "R")
TEMPORAL_BASELINE_CAMPAIGNS = 2  # las hojas T envejecen: el ancla sana usa solo las primeras fechas
TEMPORAL_MIN_FECHAS_TENDENCIA = 5
TEMPORAL_WL_MIN = 440  # por debajo, ~13 % de los espectros con roya da reflectancia negativa
TEMPORAL_GRID_POINTS = 300

# LEAF_TYPE_COLORS / LEAF_TYPE_LABELS / LEAF_NUM_DASH: definidas una sola vez, mas arriba
# (bloque "Tipo de hoja: fuente unica de verdad"), para que valgan lo mismo en toda la app.

INDEX_WAVELENGTHS = sorted(set(
    WL_NDVI + WL_PRI + WL_PSRI + WL_RCI + WL_EDI + WL_NDRE + WL_MNDVI705
))
