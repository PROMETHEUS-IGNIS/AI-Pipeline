"""Carga robusta de los CSV crudos de FIRMS.

Mejoras respecto al notebook original:
- el delimitador se detecta con csv.Sniffer (en vez de try/except ciegos),
- todo se lee como texto y los tipos se convierten en clean.py,
- los archivos vacíos/solo-encabezado no rompen el pipeline.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

# Columnas esperadas por la API FIRMS (Area CSV)
VIIRS_COLUMNS = [
    "latitude", "longitude", "bright_ti4", "scan", "track", "acq_date",
    "acq_time", "satellite", "instrument", "confidence", "version",
    "bright_ti5", "frp", "daynight",
]
MODIS_COLUMNS = [
    "latitude", "longitude", "brightness", "scan", "track", "acq_date",
    "acq_time", "satellite", "instrument", "confidence", "version",
    "bright_t31", "frp", "daynight",
]

COLUMNAS_MINIMAS = {"latitude", "longitude", "acq_date", "confidence", "frp"}


def detect_delimiter(path: Path) -> str:
    """Detecta el delimitador de un CSV (',' ';' tab). Fallback: el más frecuente."""
    sample = ""
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        sample = fh.read(4096)
    if not sample:
        return ","
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ";" if sample.count(";") > sample.count(",") else ","


def load_raw(path: Path) -> pd.DataFrame | None:
    """Carga un CSV crudo de FIRMS como texto bruto de pandas.

    Devuelve pd.DataFrame con todas las columnas como str, más 'source'
    (nombre del archivo). Si es un archivo vacío devuelto PERO solo con un header,
    se devuelve un DataFrame con las columnas y 0 filas; None si no se pudo leer.
    """
    try:
        if not path.exists() or path.stat().st_size == 0:
            return None
        sep = detect_delimiter(path)
        df = pd.read_csv(path, sep=sep, dtype=str, engine="python", on_bad_lines="skip")
        if len(df.columns) <= 1:
            # El sniffer falló: probar con separadores comunes
            for alt in (",", ";", "\t"):
                if alt != sep:
                    df = pd.read_csv(path, sep=alt, dtype=str, engine="python", on_bad_lines="skip")
                    if len(df.columns) > 1:
                        break
        df.columns = [c.strip().lower() for c in df.columns]
        if not COLUMNAS_MINIMAS.issubset(df.columns):
            raise ValueError(f"columnas inesperadas {list(df.columns)[:5]}... en {path.name}")
        df["source"] = path.stem
        return df
    except Exception as exc:  # noqa: BLE001  reportamos y seguimos
        print(f"  ! No se pudo cargar {path.name}: {exc}")
        return None


def load_sensor_dir(dir_path: Path) -> pd.DataFrame | None:
    """Carga y concatena todos los CSV de ventanas de un sensor."""
    if not dir_path.exists():
        return None
    frames = []
    for f in sorted(dir_path.glob("*.csv")):
        df = load_raw(f)
        if df is not None and len(df):
            frames.append(df)
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


def sensor_family(df: pd.DataFrame) -> str:
    """Identifica la familia de columnas: 'viirs' | 'modis'."""
    if "bright_ti5" in df.columns or "bright_ti4" in df.columns:
        return "viirs"
    return "modis"
