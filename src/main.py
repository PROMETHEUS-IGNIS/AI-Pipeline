"""Orquestador del pipeline: cargar → limpiar → unificar → entrenar → evaluar.

Uso:
    python -m src.main            # pipeline completo
    python -m src.main --targets nivel_impacto
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from . import clean, config, evaluate, features, load, model, targets


def _guardar_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"  → guardado: {path}")


def preparar_datos() -> tuple[dict[str, pd.DataFrame], dict[str, dict], str]:
    """Carga y limpia cada sensor y devuelve (dfs, reportes, resumen)."""
    datasets: dict[str, pd.DataFrame] = {}
    reportes: dict[str, dict] = {}
    for sensor in config.SOURCES:
        raw = load.load_sensor_dir(config.RAW_DIR / sensor)
        if raw is None:
            print(f"  ! {sensor}: no hay datos en {config.RAW_DIR / sensor}")
            continue
        df, rep = clean.clean_dataset(raw)
        df = features.add_feature_columns(df)
        df = targets.add_targets(df)
        datasets[sensor] = df
        reportes[sensor] = rep
        print(f"  {sensor}: {rep['entrada']} → {rep['salida']} registros")
        _guardar_csv(df, config.PROCESSED_DIR / f"{sensor}.csv")

    resumen = clean.resumen_calidad(reportes)
    return datasets, reportes, resumen


def entrenar_target(df_train: pd.DataFrame, datasets: dict[str, pd.DataFrame], target: str) -> str:
    """Entrena con VIIRS SNPP y valida cruzado contra los otros sensores."""
    print(f"\n=== Objetivo: {target} ({config.TARGET_NAME_LABELS[target]}) ===")
    X = features.make_X(df_train, target)
    y = df_train[target].dropna()
    X = X.loc[y.index]

    resultado = model.entrenar(X, y)
    etiquetas = sorted(y.unique())
    print(f"Clases: {etiquetas} | CV acc={resultado['cv_accuracy']:.3f} "
          f"CV f1w={resultado['cv_f1_weighted']:.3f} | baseline acc={resultado['baseline_acc_test']:.3f}")

    rep_test = evaluate.reporte(resultado["y_test"], resultado["modelo"].predict(resultado["X_test"]))
    print(rep_test)

    # --- Validación cruzada entre sensores (como el Colab, pero bien hecha)
    secciones = [f"## Objetivo: {target} — {config.TARGET_NAME_LABELS[target]}",
                 "",
                 f"- CV ({config.CV_FOLDS} folds estratificados, sobre VIIRS SNPP): "
                 f"accuracy={resultado['cv_accuracy']:.3f}, f1_weighted={resultado['cv_f1_weighted']:.3f}",
                 f"- Baseline (clase mayoritaria) accuracy: {resultado['baseline_acc_test']:.3f}",
                 "",
                 "### Test VIIRS SNPP", "", "```", rep_test, "```"]

    for sensor, df_o in datasets.items():
        if sensor == "viirs_snpp":
            continue
        X_o = features.make_X(df_o, target)
        y_o = df_o[target].dropna().loc[X_o.index] if target in df_o else None
        X_al = model.alinear_features(X_o.loc[y_o.index], list(X.columns)) if y_o is not None and len(y_o) else None
        if X_al is None or y_o is None or len(y_o) == 0:
            continue
        preds = resultado["modelo"].predict(X_al)
        rep_o = evaluate.reporte(y_o, preds)
        print(f"\n— Validación sobre {sensor} (n={len(y_o)}) —")
        print(rep_o)
        secciones += [f"### Validación cruzada sobre {sensor} (n={len(y_o)})", "", "```", rep_o, "```"]

    # --- Figuras
    fig = evaluate.matriz_confusion_png(
        resultado["y_test"], resultado["modelo"].predict(resultado["X_test"]), etiquetas,
        f"{config.TARGET_NAME_LABELS[target]} — VIIRS SNPP (test)",
        f"matriz_{target}_snpp.png",
    )
    secciones += ["", f"![matriz]({fig.name})"]

    imp = evaluate.importancias(resultado["modelo"], resultado["X_test"], resultado["y_test"])
    secciones += ["", "### Importancia de features (permutación)", imp, ""]

    return "\n".join(secciones)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", nargs="*", choices=targets.TARGETS, default=list(targets.TARGETS))
    args = ap.parse_args()

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    print("1/4. Cargando y limpiando datos crudos de FIRMS...")
    datasets, _, resumen = preparar_datos()
    if len(datasets) < 2:
        print("Se necesitan ≥2 sensores con datos. Ejecuta primero: python -m src.download")
        return

    print("\n2/4. Unificando dataset...")
    unificado = pd.concat(datasets.values(), ignore_index=True)
    _guardar_csv(unificado, config.PROCESSED_DIR / "dataset_unificado.csv")

    print("\n3/4. Entrenando y validando...")
    secciones = ["# Reporte del modelo — AI-Pipeline Incendios Colombia", "",
                 resumen, ""]
    for target in args.targets:
        train_df = datasets.get("viirs_snpp")
        if train_df is None:
            train_df = next(iter(datasets.values()))
        secciones.append(entrenar_target(train_df, datasets, target))

    print("\n4/4. Escribiendo reporte...")
    reporte_md = config.OUTPUTS_DIR / "reporte_modelo.md"
    reporte_md.write_text("\n".join(secciones), encoding="utf-8")
    print(f"  → {reporte_md}")


if __name__ == "__main__":
    main()
