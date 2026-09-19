# SCIENCE_CONSTRAINTS.md

Read this before writing or modifying any code in `modules/pose/`, `modules/biomechanics/`, or `modules/risk_scoring/`. Every claim below is sourced; do not soften or override these without new evidence logged in `/docs/DECISIONS.md`.

## What monocular video can validly measure

**Sagittal-plane joint angles (knee/hip flexion, trunk lean) are usable, with a real and movement-dependent margin of error — not a single precise number.** General markerless-vs-marker-based motion capture comparisons show RMSE of 5.86–6.80° and correlation of 0.83–0.93 for hip and knee joint angle waveforms. A 2026 study validating a markerless pipeline specifically during squatting found a larger systematic bias — a consistent tendency to overestimate joint angles by roughly 17° compared to marker-based capture. These are not contradictory: one measures moment-to-moment tracking noise (RMSE), the other a consistent offset (bias) for a specific movement. Together they mean: treat any single absolute sagittal angle as an estimate with meaningful uncertainty, not a clinical measurement — round to whole degrees in any UI, and prefer within-session comparisons (this athlete's own trend across reps, or left vs. right symmetry via `limb_symmetry_index`) over an absolute number compared to an outside standard. Tag these `confidence: 'validated'` in `biomechanical_metrics` — validated means "usable as a relative/trend signal," not "clinically precise."

**Frontal-plane knee valgus is NOT valid as a precise angle, at any tested bias or RMSE level.** Tested directly against Vicon 3D motion capture during single-leg jump-landings, MediaPipe Pose's calculated knee valgus angle differed from the 3D system by 18.83–19.68°, with no significant concurrent validity for the absolute value. A broader 2026 systematic review found correlation as low as r=0.008 to 0.590 for absolute knee valgus angle against gold-standard capture. Tag these `confidence: 'qualitative'` — a visual flag, never a rendered number with false precision.

**Real dynamics (forces, not just positions) need 2+ synchronized cameras, not one.** Stanford's OpenCap computes both kinematics and dynamics from smartphone video, but requires two or more synchronized phones.

## Why the foundational injury-biomechanics research is cited carefully, not treated as settled

Hewett et al. (2005) is real and foundational: 205 female athletes were prospectively measured with 3D kinematics and kinetics during a jump-landing task; knee valgus loading predicted subsequent ACL injury. But only 9 of 205 athletes were later injured, and later studies using similar methodology (Krosshaug et al. 2016, Leppänen et al. 2017) did not replicate the original finding. Hewett's strongest predictor was knee valgus **moment**, not the angle alone — video-only pipelines can't produce moment without significant additional modeling. Cite this research as motivation for tracking knee valgus, never as proof that this system's valgus flag predicts injury.

## Limb Symmetry Index (LSI) — same pattern, different metric (added for Milestone 3)

The ≥90% LSI threshold used in return-to-sport testing is real, widely cited, and used as clinical practice (University of Delaware RTS criteria, among others). It is **also documented to fail at its stated job.** A study titled, directly, "Return-to-Sport Criteria After Anterior Cruciate Ligament Reconstruction Fail to Identify the Risk of Second Anterior Cruciate Ligament Injury" found that of athletes who passed all 6 RTS tests at ≥90% LSI, 22% still sustained a second ACL injury within 24 months. Separately: only ~23–26% of post-surgical patients even meet the 90% threshold in practice (many return to play anyway, meaning it's frequently not enforced as a hard gate); and only ~24% of *healthy, uninjured* athletes meet 90% symmetry naturally, which raises real questions about whether 90% reflects a meaningful "normal" baseline at all. The "healthy" reference limb itself isn't stable — it adapts post-injury in ways that can inflate the ratio (Schmitt et al., 2012), and real-world clearance-time LSI has been measured averaging as low as 77% in some cohorts, well under the nominal threshold.

**Practical rule:** LSI is included in this system as a bounded, clearly-labeled contribution to a composite score (see `docs/DECISIONS.md`, Milestone 3 entries) — never as a standalone pass/fail safety determination, and never presented to a user without the caveat that the 90% convention has documented predictive-validity problems.

## Prior art — what's actually been achieved, for calibration

- **VAIR** (Harvard) — visual analytics research system for ACL/Achilles injury-risk exploration in basketball. Research-lab output, a conceptual reference, not a timeline comparison.
- **Baseball pitching injury screening** (University of Waterloo) — sub-degree accuracy on 16 of 18 biomechanics metrics, AUC 0.811–0.825 for real injury outcomes — but required **7,348 pitchers** with confirmed injury labels. The clearest evidence the gap is data, not algorithms.
- **Rugby tackle head-position risk** — narrow, single, well-defined mechanical indicator. The pattern this project follows.

## The resulting rule for `risk_scoring` and `recommendations`

Every risk score is a **transparent composite**, never a single unexplained number:
1. A movement-anomaly component from unsupervised Isolation Forest scoring against a population baseline (Milestone 3) — a pattern-deviation signal, not an injury probability.
2. A bounded, caveated asymmetry flag (LSI vs. the 90% convention, with its documented limitations stated).
3. A bounded prior-injury flag (presence/absence, not a fabricated precise weight).

Every component's contribution is visible in `score_breakdown`. `methodology_note` on every `risk_scores` row states plainly that this is not a trained injury-prediction model.
