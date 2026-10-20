"""Train the optional injury-risk model.

The platform works without it (rule-based scoring). When a model file exists at
MODEL_PATH, its probability is blended with the rule-based one.

Usage:
    python -m ml.train_injury_model --csv data/injury_dataset.csv
    python -m ml.train_injury_model --synthetic      # demo only

CSV format: one row per athlete assessment, columns = app.services.injury_risk.FEATURE_NAMES
plus a binary `injured` column (1 = sustained a related injury within your follow-up window).

Do NOT use --synthetic output for real decisions. The synthetic labels are generated from
the same heuristics the app already uses, so the model just reproduces them. Train on real,
outcome-labelled data (for example your own athletes' follow-up records) and validate it
properly before trusting it.
"""

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split

from app.core.config import settings
from app.services.injury_risk import FEATURE_NAMES


def make_synthetic(n: int = 2000, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "knee_valgus_peak_deg": rng.gamma(3, 2.0, n),
            "landing_knee_flexion_deg": rng.normal(32, 10, n).clip(5, 70),
            "trunk_lean_max_deg": rng.gamma(4, 4.0, n),
            "hip_stability_pelvic_drop_deg": rng.gamma(2, 2.0, n),
            "knee_flexion_rom_si": rng.gamma(2, 4.0, n),
            "hip_flexion_rom_si": rng.gamma(2, 4.0, n),
            "ankle_angle_rom_si": rng.gamma(2, 4.0, n),
            "shoulder_elevation_rom_si": rng.gamma(2, 4.0, n),
            "balance_sway_ml_norm": rng.gamma(2, 0.015, n),
            "stride_variability_pct": rng.gamma(2, 3.5, n),
            "fatigue_index": rng.beta(1.5, 5, n),
            "acwr": rng.normal(1.1, 0.3, n).clip(0.4, 2.2),
            "prior_injury_load": rng.beta(1, 4, n),
        }
    )
    logit = (
        0.25 * (df.knee_valgus_peak_deg - 6)
        - 0.06 * (df.landing_knee_flexion_deg - 32)
        + 0.05 * (df.trunk_lean_max_deg - 16)
        + 0.12 * (df.hip_stability_pelvic_drop_deg - 4)
        + 0.05 * (df.knee_flexion_rom_si - 8)
        + 2.5 * (df.fatigue_index - 0.25)
        + 1.5 * (df.acwr - 1.3).clip(0)
        + 1.8 * df.prior_injury_load
        - 1.2
    )
    df["injured"] = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--out", type=Path, default=Path(settings.MODEL_PATH))
    args = parser.parse_args()

    if args.synthetic:
        print("WARNING: using synthetic data. The resulting model is for pipeline testing only.")
        df = make_synthetic()
    elif args.csv:
        df = pd.read_csv(args.csv)
    else:
        parser.error("provide --csv or --synthetic")

    missing = [c for c in FEATURE_NAMES + ["injured"] if c not in df.columns]
    if missing:
        raise SystemExit(f"CSV is missing columns: {missing}")

    X, y = df[FEATURE_NAMES], df["injured"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    try:
        from xgboost import XGBClassifier

        model = XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, eval_metric="logloss")
    except ImportError:
        model = GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05)
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]
    print(f"ROC AUC: {roc_auc_score(y_test, proba):.3f}   PR AUC: {average_precision_score(y_test, proba):.3f}")
    print(f"Positive rate: {y.mean():.2%}  (n={len(df)})")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURE_NAMES}, args.out)
    print(f"Saved model to {args.out}")


if __name__ == "__main__":
    main()
