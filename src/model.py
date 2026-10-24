"""Entrenamiento del RandomForest con reglas anti-fuga aplicadas.

Mejoras respecto al notebook original:
- split estratificado (desbalance real, no accuracy engañoso),
- class_weight='balanced' en el clasificador,
- validación cruzada estratificada de 5 folds como métrica primaria,
- incluye un baseline DummyClassifier como referencia mínima.
"""
from __future__ import annotations

import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold, train_test_split

from . import config


def _modelo(random_state: int = config.SEED) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_leaf=2,
        class_weight="balanced",
        n_jobs=-1,
        random_state=random_state,
    )


def entrenar(X: pd.DataFrame, y: pd.Series) -> dict:
    """Entrena RF + baseline y devuelve modelo, splits y métrica de CV."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=config.TEST_SIZE, stratify=y, random_state=config.SEED
    )
    modelo = _modelo().fit(X_train, y_train)

    baseline = DummyClassifier(strategy="most_frequent").fit(X_train, y_train)

    cv = StratifiedKFold(n_splits=config.CV_FOLDS, shuffle=True, random_state=config.SEED)
    cv_acc, cv_f1 = _cruz(modelo, X, y, cv)

    return {
        "modelo": modelo,
        "baseline": baseline,
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "baseline_acc_test": baseline.score(X_test, y_test),
        "cv_accuracy": cv_acc,
        "cv_f1_weighted": cv_f1,
    }


def _cruz(modelo, X: pd.DataFrame, y: pd.Series, cv: StratifiedKFold) -> tuple[float, float]:
    accs, f1s = [], []
    for tr, te in cv.split(X, y):
        m = _modelo().fit(X.iloc[tr], y.iloc[tr])
        pred = m.predict(X.iloc[te])
        accs.append(accuracy_score(y.iloc[te], pred))
        f1s.append(f1_score(y.iloc[te], pred, average="weighted"))
    return float(sum(accs) / len(accs)), float(sum(f1s) / len(f1s))


def alinear_features(X_nuevo: pd.DataFrame, X_train_cols: list[str]) -> pd.DataFrame:
    """Asegura el mismo esquema de columnas que en el entrenamiento."""
    X = X_nuevo.copy()
    for col in X_train_cols:
        if col not in X.columns:
            X[col] = 0.0
    return X[X_train_cols]
