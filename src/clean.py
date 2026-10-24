"""Limpieza y homogenización del esquema entre sensores.

Mejor estilo respecto al notebook original:
1. Nunca se 'inventan' valores: coordenadas fuera del bbox de Colombia se
   marcan y se eliminan reportando cuántas (antes se ponían en 0.0 a la fuerza).
2. 'confidence' se homogenice explícitamente por sensor:
   VIIRS (l/n/h) y MODIS (0-100) -> nivel categórico + puntaje numérico.
3. Las columnas térmicas quedan con nombres únicos:
   - brightness_k: brillo 4 µm (VIIRS bright_ti4 / MODIS brightness)
   - mid_infrared_k: medio IR 11-12 µm (VIIRS bright_ti5 / MODIS bright_t31)
4. Fechas parseadas sin ambigüedad (YYYY-MM-DD de FIRMS; tolera formatos regionales).
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from . import config

UNIFIED_COLUMNS = [
    "latitude", "longitude", "acq_date", "acq_time", "satellite",
    "instrument", "confidence_raw", "confidence_level", "confidence_score",
    "frp", "brightness_k", "mid_infrared_k", "daynight", "source",
]

VIIRS_NIVEL = {"l": "baja", "n": "nominal", "h": "alta"}
PUNTAJE_VIIRS = {"baja": 30.0, "nominal": 60.0, "alta": 95.0}


def _num(series: pd.Series) -> pd.Series:
    """Texto -> número, tolerando coma decimal ('1,5')."""
    txt = series.astype(str).str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(txt, errors="coerce")


def _parse_acq_date(series: pd.Series) -> pd.Series:
    """FIRMS usa YYYY-MM-DD; algunos exports regionales usan D/MM/YYYY."""
    return pd.to_datetime(series, dayfirst=False, errors="coerce").fillna(
        pd.to_datetime(series, dayfirst=True, errors="coerce")
    )


def _normalizar_confianza(df: pd.DataFrame) -> pd.DataFrame:
    """Homogeniza 'confidence' entre VIIRS (l/n/h) y MODIS (0-100)."""
    raw = df["confidence"].astype(str).str.strip()
    es_viirs = df["instrument"].astype(str).str.upper().str.contains("VIIRS")

    # Puntaje numérico: VIIRS mapea l/n/h; MODIS usa su valor 0-100 directo
    score_num = pd.to_numeric(raw.str.replace(r"[^0-9.]", "", regex=True), errors="coerce")
    score_cat = raw.str.lower().map(PUNTAJE_VIIRS)
    score = pd.Series(np.where(es_viirs, score_cat, score_num), index=df.index, dtype="float64")
    score = score.mask(~score.between(0, 100))  # saneo: puntajes imposibles

    # Nivel categórico: VIIRS por letra; MODIS por bins del config
    nivel_cat = raw.str.lower().map(VIIRS_NIVEL)
    nivel_num = pd.cut(
        score,
        bins=[-np.inf, config.CONF_UMBRAL_BAJA, config.CONF_UMBRAL_ALTA, np.inf],
        labels=["baja", "nominal", "alta"],
        right=False,
    ).astype(object)
    nivel = nivel_cat.where(nivel_cat.notna(), nivel_num)

    df["confidence_raw"] = df["confidence"].astype(str)
    df["confidence_score"] = score
    df["confidence_level"] = nivel.astype(str).str.lower()
    df["confidence_level"] = df["confidence_level"].where(
        df["confidence_level"].isin(["baja", "nominal", "alta"])
    )
    return df


def clean_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Aplica todas las reglas de limpieza y devuelve (df_limpio, reporte)."""
    reporte: dict[str, Any] = {"entrada": len(df)}
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    # --- Coords
    df["latitude"] = _num(df["latitude"])
    df["longitude"] = _num(df["longitude"])

    # --- Validez geográfica (sin reemplazar por ceros, como el original)
    geo_ok = (
        df["latitude"].between(config.BBOX["south"], config.BBOX["north"])
        & df["longitude"].between(config.BBOX["west"], config.BBOX["east"])
    )
    reporte["fuera_bbox"] = int((~geo_ok).sum())
    reporte["coords_nulos"] = int(df["latitude"].isna().sum())
    df = df[geo_ok].copy()

    # --- Confianza
    df = _normalizar_confianza(df)

    # --- Térmicas (unificación de esquemas entre sensores)
    if "brightness" in df.columns:  # MODIS
        df["brightness_k"] = _num(df["brightness"])
        df["mid_infrared_k"] = _num(df.get("bright_t31", pd.Series(np.nan, index=df.index)))
    else:  # VIIRS
        df["brightness_k"] = _num(df.get("bright_ti4", pd.Series(np.nan, index=df.index)))
        df["mid_infrared_k"] = _num(df.get("bright_ti5", pd.Series(np.nan, index=df.index)))
    df["frp"] = _num(df["frp"])

    # --- Valides por rango físico
    term_ok = df["brightness_k"].between(200, 450)
    frp_ok = df["frp"].ge(0)
    reporte["descartes_termicos"] = int((~term_ok).sum())
    df = df[term_ok & frp_ok].copy()

    # --- Fecha y franja
    df["acq_date"] = _parse_acq_date(df["acq_date"])
    reporte["fechas_invalidas"] = int(df["acq_date"].isna().sum())
    df = df[df["acq_date"].notna()].copy()
    df["daynight"] = df["daynight"].astype(str).str.upper().str[0]

    # --- Duplicados exactos (escaneos dobles URT/NRT)
    antes = len(df)
    df = df.drop_duplicates(
        subset=["latitude", "longitude", "acq_date", "acq_time", "instrument", "satellite"],
        keep="first",
    )
    reporte["duplicados_quitados"] = int(antes - len(df))

    reporte["salida"] = len(df)
    df = df[UNIFIED_COLUMNS].reset_index(drop=True)
    return df, reporte


def resumen_calidad(reportes: dict[str, dict]) -> str:
    """Texto de calidad de datos por sensor."""
    lineas = ["### Calidad de datos por sensor", ""]
    for sensor, r in reportes.items():
        margen = r.get("salida", 0)
        ent = r.get("entrada", 0)
        pct = (margen / ent * 100) if ent else 0.0
        lineas.append(
            f"- **{sensor}**: {ent} → {margen} registros ({pct:.1f}%)"
            f" | fuera de bbox: {r.get('fuera_bbox', 0)}"
            f" | térmicas inválidas: {r.get('descartes_termicos', 0)}"
            f" | duplicados: {r.get('duplicados_quitados', 0)}"
            f" | fechas inválidas: {r.get('fechas_invalidas', 0)}"
        )
    return "\n".join(lineas)
