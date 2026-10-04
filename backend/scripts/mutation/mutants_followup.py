# Mutants added during hardening (code that did not exist when the first catalogue was written).
MUTANTS = [
 {
  "id": "B03",
  "file": "app/modules/biomechanics/calculations.py",
  "old": "trunk_axis = (pt(\"left_shoulder\") + pt(\"right_shoulder\")) / 2 - (pt(\"left_hip\") + pt(\"right_hip\")) / 2",
  "new": "trunk_axis = pt(f\"{side}_shoulder\") - pt(f\"{side}_hip\")",
  "desc": "hip flexion uses same-side shoulder (lateral leak)",
  "tests": "tests/test_hardening_unit.py tests/test_properties.py"
 },
 {
  "id": "J01",
  "file": "app/modules/pose/analysis.py",
  "old": "raw_obs[~np.isfinite(cleaned[obs])] = np.nan",
  "new": "pass",
  "desc": "jitter counts hidden-limb garbage",
  "tests": "tests/test_hardening_unit.py tests/test_properties.py"
 },
 {
  "id": "J02",
  "file": "app/modules/pose/analysis.py",
  "old": "d2 = d2[np.isfinite(d2)]\n    if len(d2) < 10:",
  "new": "d2 = d2[np.isfinite(d2)]\n    if len(d2) < 1:",
  "desc": "jitter min-sample guard",
  "tests": "tests/test_hardening_unit.py tests/test_properties.py"
 },
 {
  "id": "K01",
  "file": "app/modules/pose/analysis.py",
  "old": "num = np.convolve(filled[:, c], k, mode=\"full\")[radius:radius + len(x)]\n        den = np.convolve(valid[:, c], k, mode=\"full\")[radius:radius + len(x)]",
  "new": "num = np.convolve(filled[:, c], k, mode=\"same\")\n        den = np.convolve(valid[:, c], k, mode=\"same\")",
  "desc": "convolution breaks on short clips",
  "tests": "tests/test_hardening_unit.py tests/test_properties.py"
 },
 {
  "id": "T01",
  "file": "app/modules/biomechanics/movement_analysis.py",
  "old": "np.mean(np.diff([r.peak_idx for r in reps]))",
  "new": "np.max(np.diff([r.peak_idx for r in reps]))",
  "desc": "cycle time uses max spacing",
  "tests": "tests/test_hardening_unit.py tests/test_properties.py"
 },
 {
  "id": "T02",
  "file": "app/modules/biomechanics/movement_analysis.py",
  "old": "if len(reps) >= 2:  # ...so",
  "new": "if len(reps) >= 1:  # ...so",
  "desc": "cycle time from 1 rep",
  "tests": "tests/test_hardening_unit.py tests/test_properties.py"
 },
 {
  "id": "N01",
  "file": "app/modules/pose/analysis.py",
  "old": "xyz[~np.isfinite(xyz)] = np.nan  # NaN/inf",
  "new": "pass  # NaN/inf",
  "desc": "non-finite coords not sanitised",
  "tests": "tests/test_hardening_unit.py tests/test_properties.py"
 },
 {
  "id": "M06",
  "file": "app/modules/biomechanics/movement_analysis.py",
  "old": "band = GAIT_CONFIRM_BAND * rng",
  "new": "band = 0.0 * rng",
  "desc": "no confirmation band in gait",
  "tests": "tests/test_hardening_unit.py tests/test_properties.py"
 },
 {
  "id": "M11",
  "file": "app/modules/biomechanics/movement_analysis.py",
  "old": "signal = _smooth(centred @ vt[0])",
  "new": "signal = _smooth(centred[:, 0])",
  "desc": "gait uses x axis not PCA",
  "tests": "tests/test_hardening_unit.py tests/test_properties.py"
 },
 {
  "id": "M16",
  "file": "app/modules/biomechanics/movement_analysis.py",
  "old": "GAIT_CONFIRM_BAND = 0.15",
  "new": "GAIT_CONFIRM_BAND = 0.9",
  "desc": "gait band 15%->90% (overly strict)",
  "tests": "tests/test_hardening_unit.py tests/test_properties.py"
 }
]
