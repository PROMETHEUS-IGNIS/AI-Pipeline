"""Configuración global del pipeline AI-Pipeline.

Centraliza rutas, constantes de sensores FIRMS, el bounding box de Colombia
y los umbrales documentados que construyen las etiquetas del modelo.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------- rutas ----
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = BASE_DIR / "outputs"
NOTEBOOKS_DIR = BASE_DIR / "notebooks"


def _load_env_file(path: Path) -> None:
    """Carga un archivo .env simple (KEY=VALUE) sin dependencias externas."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file(BASE_DIR / ".env")
FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "").strip()

# ---------------------------------------------------------------- FIRMS ----
FIRMS_API_BASE = "https://firms.modaps.eosdis.nasa.gov/api"

# Bounding box de Colombia (incluye islas: San Andrés, Malpelo).
# Orden del Area API: west, south, east, north.
AREA_COORDS = "-82.6,-5.0,-65.5,14.0"
BBOX = {
    "west": -82.6,
    "south": -5.0,
    "east": -65.5,
    "north": 14.0,
}

# Fuentes FIRMS con archivo histórico (SP = Standard Processing).
# sensor_local -> id de la API
SOURCES = {
    "viirs_snpp": "VIIRS_SNPP_SP",
    "viirs_noaa20": "VIIRS_NOAA20_SP",
    "modis": "MODIS_SP",
}
SOURCES_NRT = {
    "viirs_snpp": "VIIRS_SNPP_NRT",
    "viirs_noaa20": "VIIRS_NOAA20_NRT",
    "modis": "MODIS_NRT",
}

# ------------------------------------------------------------------ ML -----
SEED = 42
TEST_SIZE = 0.2
CV_FOLDS = 5

# Umbrales documentados para las etiquetas.
# IMPORTANTE: si la etiqueta se deriva de un campo, ese campo se excluye
# de las features al entrenar (EXCLUDE_BY_TARGET) para evitar fuga de datos.
# - nivel_impacto: fuego con potencia radiativa alta (FRP en MW) o
#   temperatura de brillo 4 µm alta (K).
FRP_IMPACTO_ALTO = 10.0
BRIGHT_IMPACTO_ALTO = 330.0

# Bins para homogenizar 'confidence' entre sensores:
#   VIIRS: l / n / h  ->  baja / nominal / alta
#   MODIS: 0-100      ->  <30 baja, 30-80 nominal, >=80 alta
CONF_UMBRAL_BAJA = 30.0
CONF_UMBRAL_ALTA = 80.0

# Features base y exclusiones por objetivo (anti-fuga)
BASE_FEATURES = [
    "latitude",
    "longitude",
    "day_of_year",
    "month",
    "acq_hour",
    "is_noche",
    "frp",
    "brightness_k",
]
EXCLUDE_BY_TARGET = {
    "nivel_impacto": {"frp", "brightness_k"},
    "confianza_deteccion": set(),
}

TARGET_NAME_LABELS = {
    "nivel_impacto": "Nivel de impacto térmico",
    "confianza_deteccion": "Confianza de detección FIRMS",
}
