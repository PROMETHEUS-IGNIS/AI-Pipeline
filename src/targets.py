"""Definición de objetivos (etiquetas) honestos, sin fuga de datos.

Los dos objetivos que reemplazan al confuso 'Origen_Fuego' del notebook
original (que derivaba el supuesto 'origen antrópico' de la confianza de
detección, mezclando conceptos):
- nivel_impacto: intensidad térmica del foco (FRP alto o brillo 4 µm alto).
- confianza_deteccion: nivel de confianza de FIRMS homogenizado entre sensores.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

TARGETS = ("nivel_impacto", "confianza_deteccion")


def add_targets(df: pd.DataFrame) -> pd.DataFrame:
    """Añade columnas de etiquetas al dataset unificado."""
    df = df.copy()

    impacto_alto = (df["frp"] >= config.FRP_IMPACTO_ALTO) | (
        df["brightness_k"] >= config.BRIGHT_IMPACTO_ALTO
    )
    df["nivel_impacto"] = np.where(impacto_alto, "alto", "bajo_moderado")

    df["confianza_deteccion"] = df["confidence_level"]
    return df
