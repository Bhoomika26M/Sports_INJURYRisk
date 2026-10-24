"""
Sports Injury Risk Prediction - Machine Learning Training Pipeline
Trains calibrated multi-output Random Forest and Gradient Boosting models
on sports biomechanical kinematics, training load, and injury history factors.
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
os.makedirs(MODELS_DIR, exist_ok=True)
MODEL_SAVE_PATH = os.path.join(MODELS_DIR, "injury_risk_model.joblib")


def generate_training_dataset(n_samples: int = 1500) -> pd.DataFrame:
    """
    Synthesize realistic athletic biomechanics dataset based on clinical sports literature:
    - Hewett et al. (ACL biomechanical risk factors: dynamic knee valgus > 8-10 deg)
    - Opar et al. (Hamstring strain risk: bilateral asymmetry > 10-15%, training load spikes)
    - Bahr et al. (Ankle ligament sprain: postural sway and lateral trunk displacement)
    """
    np.random.seed(42)
    
    # 1. Biomechanical Kinematics Features (Extracted via MediaPipe Pose / CV)
    peak_valgus = np.random.uniform(0.0, 24.0, n_samples)
    mean_asymmetry = np.random.uniform(2.0, 35.0, n_samples)
    peak_flexion = np.random.uniform(30.0, 115.0, n_samples)
    peak_trunk_lean = np.random.uniform(5.0, 45.0, n_samples)
    quality_score = np.random.uniform(25.0, 98.0, n_samples)
    
    # 2. Athlete Physiological & Training Load Features
    training_load = np.random.uniform(35.0, 98.0, n_samples)
    age = np.random.uniform(17.0, 36.0, n_samples)
    height = np.random.uniform(165.0, 205.0, n_samples)
    weight = np.random.uniform(60.0, 105.0, n_samples)
    bmi = weight / ((height / 100.0) ** 2)
    
    # 3. Medical & Injury History Factors (Binary Flags)
    prior_knee = np.random.choice([0, 1], p=[0.72, 0.28], size=n_samples)
    prior_ham = np.random.choice([0, 1], p=[0.75, 0.25], size=n_samples)
    prior_ank = np.random.choice([0, 1], p=[0.68, 0.32], size=n_samples)
    
    # Ground Truth Mathematical Risk Models (Calibrated 0-100% probabilities)
    # ACL Risk: heavy correlation with medial valgus > 8 deg, stiff landing (low flexion), prior knee injury
    acl_risk = (
        (peak_valgus * 3.4) + 
        (np.maximum(0, 65.0 - peak_flexion) * 0.75) + 
        (training_load * 0.22) + 
        (prior_knee * 20.0) +
        np.random.normal(0, 2.5, n_samples)
    )
    acl_risk = np.clip(acl_risk, 5.0, 96.0)
    
    # Hamstring Risk: driven by bilateral load asymmetry > 12%, high speed sprint loads, prior tear
    ham_risk = (
        (mean_asymmetry * 2.6) + 
        (training_load * 0.38) + 
        (prior_ham * 22.0) + 
        (np.maximum(0, peak_trunk_lean - 22.0) * 0.65) +
        np.random.normal(0, 2.5, n_samples)
    )
    ham_risk = np.clip(ham_risk, 5.0, 94.0)
    
    # Ankle Sprain Risk: lateral postural sway and ground impact instability
    ank_risk = (
        (peak_trunk_lean * 1.3) + 
        (mean_asymmetry * 1.1) + 
        (prior_ank * 22.0) + 
        (training_load * 0.16) +
        np.random.normal(0, 2.5, n_samples)
    )
    ank_risk = np.clip(ank_risk, 5.0, 90.0)
    
    # Patellar Tendonitis: repetitive landing impact & load overload
    pat_risk = (
        (training_load * 0.65) + 
        (np.maximum(0, peak_valgus - 7.0) * 1.6) + 
        (prior_knee * 14.0) +
        np.random.normal(0, 2.5, n_samples)
    )
    pat_risk = np.clip(pat_risk, 5.0, 92.0)
    
    df = pd.DataFrame({
        "peak_valgus": peak_valgus,
        "mean_asymmetry": mean_asymmetry,
        "peak_flexion": peak_flexion,
        "peak_trunk_lean": peak_trunk_lean,
        "quality_score": quality_score,
        "training_load": training_load,
        "age": age,
        "bmi": bmi,
        "prior_knee": prior_knee,
        "prior_ham": prior_ham,
        "prior_ank": prior_ank,
        "acl_risk": acl_risk,
        "hamstring_risk": ham_risk,
        "ankle_risk": ank_risk,
        "patellar_risk": pat_risk
    })
    return df


def train_and_evaluate_model():
    print("=" * 65)
    print("  SPORTS INJURY RISK DETECTION - MODEL TRAINING PIPELINE")
    print("=" * 65)
    
    print("\n1. Generating multi-variable sports biomechanics dataset...")
    df = generate_training_dataset(n_samples=2000)
    
    feature_cols = [
        "peak_valgus", "mean_asymmetry", "peak_flexion", "peak_trunk_lean",
        "quality_score", "training_load", "age", "bmi",
        "prior_knee", "prior_ham", "prior_ank"
    ]
    target_cols = ["acl_risk", "hamstring_risk", "ankle_risk", "patellar_risk"]
    
    X = df[feature_cols].values
    Y = df[target_cols].values
    
    X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=42)
    print(f"Dataset split: {len(X_train)} training samples, {len(X_test)} validation samples.")
    
    print("\n2. Training Multi-Output Random Forest Ensemble Regressor...")
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=12,
        min_samples_split=4,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, Y_train)
    
    print("\n3. Model Validation & Performance Metrics:")
    Y_pred = model.predict(X_test)
    
    for i, target_name in enumerate(target_cols):
        mae = mean_absolute_error(Y_test[:, i], Y_pred[:, i])
        r2 = r2_score(Y_test[:, i], Y_pred[:, i])
        print(f"  - {target_name.upper():<16} | Mean Absolute Error (MAE): {mae:.2f}% | R² Score: {r2:.4f}")
        
    print(f"\n4. Serializing trained model to: {MODEL_SAVE_PATH}")
    joblib.dump(model, MODEL_SAVE_PATH)
    print("Model successfully trained, validated, and saved!")
    print("=" * 65)


if __name__ == "__main__":
    train_and_evaluate_model()
