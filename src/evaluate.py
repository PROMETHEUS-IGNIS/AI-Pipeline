"""Evaluación: métricas por clase, matrices de confusión e importancias."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin pantalla; figuras a archivo
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import ConfusionMatrixDisplay, classification_report, confusion_matrix

from . import config


def reporte(y_true, y_pred) -> str:
    """Reporte de clasificación por clase (sin warnings por clases vacías)."""
    return classification_report(y_true, y_pred, zero_division=0)


def matriz_confusion_png(y_true, y_pred, etiquetas, titulo: str, nombre_archivo: str) -> Path:
    out = config.OUTPUTS_DIR / nombre_archivo
    out.parent.mkdir(parents=True, exist_ok=True)
    cm = confusion_matrix(y_true, y_pred, labels=etiquetas)
    fig, ax = plt.subplots(figsize=(6.2, 5.2), dpi=130)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=etiquetas)
    disp.plot(ax=ax, cmap="Oranges", colorbar=False, values_format="d")
    ax.set_title(titulo, fontsize=11)
    ax.set_xlabel("Predicción")
    ax.set_ylabel("Real")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def importancias(modelo, X_test: pd.DataFrame, y_test: pd.Series, top: int = 12) -> str:
    """Importancia por permutación (más honesta que los pesos del bosque)."""
    try:
        r = permutation_importance(
            modelo, X_test, y_test, n_repeats=5, random_state=config.SEED, n_jobs=-1
        )
        serie = pd.Series(r.importances_mean, index=X_test.columns).sort_values(ascending=False).head(top)
    except Exception:
        serie = pd.Series(modelo.feature_importances_, index=X_test.columns).nlargest(top)
    return "\n".join(f"- {c}: {v:.4f}" for c, v in serie.items())
