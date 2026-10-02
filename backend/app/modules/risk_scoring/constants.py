"""Risk-scoring constants. Every count carries its UNIT in the name.

History: this module replaces the single ``MIN_BASELINE_SAMPLES = 10``, which
counted per-frame metric ROWS. One 7-second clip of one athlete yields hundreds
of rows, so that gate was satisfied by a single video of a single person and the
``insufficient_baseline_data`` guard effectively never fired. See
docs/DECISIONS.md (2026-10-02, "Baseline sufficiency counts videos and athletes").
"""

# --- Baseline sufficiency (the gate that stops us fabricating a score) --------
# A "baseline" is a population of distinct completed videos, not a pile of
# frames. All three floors must hold, counted EXCLUDING the video being scored.
#
# These are floors against fabrication, not statistical guarantees of adequacy:
# below them the "population" is one or two people. They are conventions (there
# is no outcome data to derive them from) and should be raised as data grows.
MIN_BASELINE_VIDEOS = 5      # distinct completed videos of this movement_type
MIN_BASELINE_ATHLETES = 3    # distinct athletes across those videos
MIN_BASELINE_FRAMES = 100    # per-metric validated frame rows; estimator floor only

# --- Anomaly severity calibration (see anomaly.py module docstring) -----------
# Fraction of the baseline's own frames that Isolation Forest is allowed to call
# "outside the normal envelope" by construction. 0.05 => the 5% least-normal
# baseline frames. Frames at least as normal as that cut score exactly 0.
NORMAL_ENVELOPE_QUANTILE = 0.05

# Half-saturation distance, in baseline robust standard deviations measured
# OUTSIDE the normal envelope: a frame this far outside scores 50/100.
HALF_SATURATION_SIGMA = 2.0

# 1.4826 * MAD estimates the standard deviation of a normal distribution.
MAD_TO_SIGMA = 1.4826

# --- Composite cut-points (scoring.py) ----------------------------------------
# Upper bounds (inclusive) of each category on the 0-100 composite. With the
# anomaly component now anchored at 0, these read as plain quarter bands.
RISK_CATEGORY_UPPER_BOUNDS = (("low", 25.0), ("moderate", 50.0), ("high", 75.0))
RISK_CATEGORY_TOP = "critical"

# Recommendation triggers on the movement_anomaly component (points out of 70),
# aligned to the moderate / high band floors above.
ANOMALY_REVIEW_POINTS = 25.0
ANOMALY_SIGNIFICANT_POINTS = 50.0
