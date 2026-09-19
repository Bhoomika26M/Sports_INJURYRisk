import numpy as np
from app.modules.risk_scoring.anomaly import compute_anomaly_scores, InsufficientBaselineError

def test_anomaly_score_spread_is_meaningful():
    rng = np.random.default_rng(42)
    baseline = rng.normal(loc=90, scale=8, size=(50, 1))
    normal_sample = np.array([[92.0]])
    anomalous_sample = np.array([[40.0]])

    normal_score = compute_anomaly_scores(normal_sample, baseline, min_samples=10)[0]
    anomalous_score = compute_anomaly_scores(anomalous_sample, baseline, min_samples=10)[0]

    assert normal_score < 30, f"Normal sample scored {normal_score}, expected low"
    assert anomalous_score > 70, f"Anomalous sample scored {anomalous_score}, expected high"
    assert anomalous_score > normal_score + 30, "Spread too narrow to be useful — check the rescaling"

def test_insufficient_baseline_raises():
    tiny_baseline = np.random.normal(90, 8, size=(3, 1))
    try:
        compute_anomaly_scores(np.array([[90.0]]), tiny_baseline, min_samples=10)
        assert False, "Should have raised InsufficientBaselineError"
    except InsufficientBaselineError:
        pass
