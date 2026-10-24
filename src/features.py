"""Construcción del set de features.

Regla anti-fuga: make_X excluye el campo del que proviene la etiqueta
(config.EXCLUDE_BY_TARGET) y además siempre excluye cualquier otra columna
derivada/carpetas de metadatos del target.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

COLUMNAS_ETIQUETAS = {"nivel_impacto", "confianza_deteccion"}
COLUMNAS_EXCLUIDAS = {
    "confidence_raw", "confidence_level", "confidence_score",
    "acq_date", "acq_time", "source", "year",
}


def add_feature_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega fechas numéricas y franja horaria a partir de acq_date/acq_time."""
    df = df.copy()
    fecha = pd.to_datetime(df["acq_date"], errors="coerce")
    df["day_of_year"] = fecha.dt.dayofyear.astype("float64")
    df["month"] = fecha.dt.month.astype("float64")
    df["year"] = fecha.dt.year.astype("int64")

    hora_txt = df["acq_time"].astype(str).str.zfill(4)
    hora_num = pd.to_numeric(hora_txt, errors="coerce")
    df["acq_hour"] = (hora_num // 100 + (hora_num % 100) / 60.0).clip(0, 24)
    df["is_noche"] = (df["daynight"].str.upper() == "N").astype("float64")
    return df


def make_X(df: pd.DataFrame, target: str) -> pd.DataFrame:
    """Devuelve la matriz de features numéricas consistentes con el target."""
    excluir = COLUMNAS_ETIQUETAS | COLUMNAS_EXCLUIDAS | set(config.EXCLUDE_BY_TARGET.get(target, set()))
    features = [c for c in config.BASE_FEATURES if c not in excluir]
    X = df[features].apply(pd.to_numeric, errors="coerce")
    return X.fillna(X.median(numeric_only=True))
