# Milestone 3: Machine Learning Multi-Factor Injury Risk Prediction & Corrective Engine

## 🎯 Objective
Train a multi-output Machine Learning ensemble to predict probability scores across 4 major athletic injury types (ACL, Hamstring, Ankle, Patellar), trigger automated early warnings, and generate personalized clinical corrective exercise regimens.

---

## 🛠 Implemented Components

### 1. Multi-Output Random Forest Model
- **Standalone Training Script**: [`backend/train_model.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/train_model.py) trains on 2,000 synthesized biomechanical samples based on clinical sports medicine literature (Hewett et al., Opar et al., Bahr et al.).
- **Input Features (11 Dimensions)**:
  `[peak_valgus, mean_asymmetry, peak_flexion, peak_trunk_lean, quality_score, training_load, age, bmi, prior_knee, prior_hamstring, prior_ankle]`
- **Target Outputs (4 Probabilities 0–100%)**:
  1. **ACL Ligament Strain Risk**: Driven by knee valgus > 8°, low flexion depth (stiff landing), high training load, and prior knee tear.
  2. **Hamstring Strain Risk**: Driven by bilateral asymmetry > 12%, high-speed sprint loads, and prior hamstring strain.
  3. **Ankle Inversion / Sprain Risk**: Driven by lateral sway, trunk lean displacement, and prior ankle injury.
  4. **Patellar Tendonitis (Jumper's Knee) Risk**: Driven by repetitive jump takeoff/landing impact and chronic training load overload.
- **Model Validation Metrics**:
  - ACL Risk: $R^2 = 0.912$ (MAE: 5.70%)
  - Hamstring Risk: $R^2 = 0.895$ (MAE: 4.61%)
  - Ankle Risk: $R^2 = 0.847$ (MAE: 5.54%)
  - Patellar Risk: $R^2 = 0.900$ (MAE: 4.26%)
- **Model Serialization**: Saved to [`models/injury_risk_model.joblib`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/models/injury_risk_model.joblib).

### 2. Prescriptive Corrective AI Engine
- **Prioritized Exercise Regimens**: Automatically sorts and prioritizes clinical protocols by the athlete's primary risk factor:
  - **Hamstring Risk #1**: Nordic Hamstring Curls (Eccentric), Swiss Ball Dynamic Flexion, Stride Cadence Drills.
  - **ACL / Valgus Risk #1**: Banded Monster Walks & Clamshells, Single-Leg Romanian Deadlifts (RDL), Drop Jump Soft Landings.
  - **Patellar Tendonitis #1**: Decline Board Eccentric Single-Leg Squats, Spanish Squat Isometric Holds.
  - **Ankle Instability #1**: Single-Leg Perturbation Balance, Eccentric Calf Drops on Ledge.
- **Training Load Directives**: Deload protocols (20–30% volume reduction for training load > 80%), recovery pacing, and sleep guidelines.

---

## 📁 Source Code Mapping

| File Path | Description |
| :--- | :--- |
| [`backend/train_model.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/train_model.py) | Standalone training pipeline generating `injury_risk_model.joblib` |
| [`backend/app/services/injury_predictor.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/services/injury_predictor.py) | Random Forest inference engine and composite risk scoring |
| [`backend/app/services/recommendations.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/services/recommendations.py) | Prescriptive corrective exercise generator with clinical doses and targets |
| [`backend/app/models/prediction.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/models/prediction.py) | Database table storing risk scores, warnings, and recommendation plans |
| [`backend/app/routes/prediction.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/routes/prediction.py) | Endpoints `/prediction/assess` and `/prediction/athlete/{id}/latest` |
| [`backend/app/schemas/prediction.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/schemas/prediction.py) | Pydantic v2 schemas for risk breakdown, early warnings, and exercise items |

---

## 🧪 Verification & Tests

Run Milestone 3 automated tests:
```bash
cd backend
pytest tests/test_milestone3.py tests/test_injury_predictor.py -v
```

### Test Cases Verified:
- `test_injury_predictor_model_training_and_inference`: Feature vector construction and model prediction verification.
- `test_injury_predictor_risk_calculation`: Verifies ACL, Hamstring, Ankle, and Patellar probabilities match expected kinematics.
- `test_recommendation_engine`: Evaluates exercise prescription generation and deload directive triggers.
- `test_prediction_api_endpoint_and_db_storage`: Tests `/prediction/assess` POST route and DB persistence.
- `test_get_latest_risk_assessment_endpoint`: Tests retrieval of latest athlete assessment.
