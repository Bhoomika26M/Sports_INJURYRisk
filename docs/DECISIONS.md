# DECISIONS.md

Append-only. New entries go at the top of their section, dated, never edited or deleted after the fact.

## Format for new entries

```
### YYYY-MM-DD — Short title
**Decision:** what was decided
**Why:** the reasoning
**Alternatives considered:** what else was on the table, if relevant
```

---

## Decisions log

### 2026-07-11 — YOLO26-pose confirmed unavailable, yolov8n-pose.pt is the real decision
**Decision:** use `yolov8n-pose.pt`, not YOLO26-pose as originally logged.
**Why:** yolo26n-pose.pt is not available as a downloadable checkpoint in the installed
`ultralytics` version at build time. yolov8n-pose.pt is a mature, well-tested model and
fully adequate for this project's person-count pre-check use case.

### 2026-07-11 — Isolation Forest over an autoencoder for anomaly detection
**Decision:** `modules/risk_scoring/anomaly.py` uses `sklearn.ensemble.IsolationForest`.
**Why:** a pilot with a handful to a few dozen videos per movement type doesn't have enough data for a deep autoencoder to learn a meaningful reconstruction. Isolation Forest is meaningful with small samples, fast, interpretable, and already implied by the original brief's own tech stack (scikit-learn).

### 2026-07-11 — Anomaly score rescaling: percentile rank against baseline, not a fixed formula
**Decision:** anomaly scores are computed as the percentile rank of a sample's `decision_function` value against the baseline's own `decision_function` distribution.
**Why:** tested in a sandbox before building: a fixed linear formula assuming a universal `decision_function` range produced an uninformative narrow spread (43 vs. 65 for clearly-normal vs. clearly-anomalous test samples). Percentile rank against the baseline's own distribution self-calibrates and produced a real spread (16 vs. 96) on identical test data.
**Alternatives considered:** fixed linear rescaling — tested and rejected, see above.

### 2026-07-11 — Population-level baselines only, per-athlete deferred
**Decision:** `movement_baselines.athlete_id` is NULL for every row built in Milestone 3 — no per-athlete baselines yet.
**Why:** per-athlete baselines need multiple videos of the same athlete doing the same movement, which a new pilot won't have. Population-level only needs enough videos of that movement type across all athletes — achievable much sooner.

### 2026-07-11 — Minimum 10 baseline samples before any score is computed
**Decision:** requesting a risk score for a movement_type with fewer than 10 validated-metric samples returns `202 insufficient_baseline_data`, never a fabricated score.
**Why:** below this floor, a "baseline" is noise, not a distribution — scoring against it would be actively misleading rather than just imprecise.

### 2026-07-11 — LSI included as a bounded, caveated flag — not a pass/fail rule
**Decision:** the risk-score formula adds a fixed 15 points if LSI < 90%, always alongside the documented caveat that this threshold has known predictive-validity problems (see `docs/SCIENCE_CONSTRAINTS.md`).
**Why:** research for this milestone found a study directly titled "Return-to-Sport Criteria... Fail to Identify the Risk of Second ACL Injury" — 22% of athletes who passed the 90% LSI criteria still sustained a second ACL injury. Treating 90% as a hard safety line would misrepresent what the literature actually shows. Using it as one bounded, labeled input among three is honest; using it as the score's foundation would not have been.

### 2026-07-11 — Prior injury as a simple flag, not a weighted formula
**Decision:** `has_prior_relevant_injury` adds a fixed 15 points if present, no attempt at a more granular weighting.
**Why:** "previous injury" is a well-established risk factor generally, but there's no single citable number for exactly how much weight it deserves in a composite score — a fabricated precise percentage would be less honest than a simple, bounded flag. Same discipline applied to the original brief's invented 35/20/20/15/10 weighting, which was never adopted.

### 2026-07-11 — ACWR (training load) deferred, not built in Milestone 3
**Decision:** acute:chronic workload ratio is not part of the v1 risk score.
**Why:** needs weeks of consistent `training_load_entries` history a new pilot won't have; also, ACWR itself has faced credible methodological criticism in recent sports-science literature and shouldn't be adopted uncritically just because it's commonly referenced — the same standard applied to LSI above.

### 2026-07-11 — M2 audit applied: CHECK constraints included in M3's schema from the start
**Decision:** `docs/SCHEMA.md`'s Milestone 3 tables include `CHECK` constraints in the initial design, not added retroactively.
**Why:** `IMPLEMENTATION_REVIEW.md` finding H2 found the M2 migration silently omitted three constraints that were specified in `SCHEMA.md` at the time. Don't repeat it.

### 2026-07-10 — Presigned-URL upload, not backend-proxied upload
**Decision:** browsers upload video files directly to object storage using a presigned URL; the backend never streams the raw file through itself.
**Why:** keeps the API process free to handle other requests while a multi-MB video uploads.
**Status update (2026-07-10, post-audit):** the actual Milestone 2 build implemented a local-disk mock instead — see the audit's Medium finding M1 in `IMPLEMENTATION_REVIEW.md`. This decision's *intent* (interface shape) still stands; the *implementation* diverged and needs a real S3/R2 swap before deployment.

### 2026-07-10 — YOLO26-pose for person-count pre-check, MediaPipe for keypoints
**Decision:** every video runs a YOLO26-pose person-count pass before MediaPipe extracts keypoints.
**Status update (2026-07-10, post-audit):** the actual build used `yolov8n-pose.pt`, undocumented at the time — see `IMPLEMENTATION_REVIEW.md` Medium finding M2. The person-count *logic* is correct; the model version needs reconciling.

### 2026-07-10 — World landmarks, not image landmarks, for all angle math
**Decision:** `compute_biomechanics` uses MediaPipe's `pose_world_landmarks` exclusively.
**Why:** image-space landmarks are distorted by camera distance and aspect ratio in ways that corrupt angle geometry.
**Status:** confirmed correctly implemented in the actual M2 build.

### 2026-07-10 — `videos` table upgraded from Milestone 1's placeholder
**Decision:** added `pending_upload` status plus diagnostic fields (`person_count_detected`, `detection_rate`, `error_code`, `error_message`, `job_id`, timestamps).
**Why:** the original placeholder had no way to represent an incomplete upload or explain a failure.

### 2026-07-10 — Sagittal-plane accuracy figure revised, not treated as a single fixed number
**Decision:** `docs/SCIENCE_CONSTRAINTS.md` presents a range rather than one precise figure; the system leans on trends and symmetry over absolute values.
**Why:** a newer, movement-specific study found more bias than the general-gait figure originally cited.

### 2026-07-09 — Modular monolith, not microservices
**Decision:** one deployable backend, module folders mirror the original diagram's service boundaries.
**Why:** 12 separately-networked services is 6–12 months of ops work for a student team in 8 weeks.

### 2026-07-09 — PostgreSQL only, no MongoDB/vector DB/data warehouse
**Decision:** single database engine; time-series/vector needs via Postgres extensions if they ever arise.

### 2026-07-09 — No supervised injury prediction
**Decision:** risk output is a cited heuristic score or unsupervised anomaly detection, never a trained "injury probability" claim.
**Why:** no public dataset links video biomechanics to confirmed injury outcomes at usable scale.

### 2026-07-09 — Frontal-plane knee valgus is qualitative only, never a precise angle
**Decision:** encoded structurally via `biomechanical_metrics.confidence`.

### 2026-07-09 — snake_case everywhere, including JSON wire keys
**Decision:** Python, SQL, and JSON response keys are all snake_case.
**Why:** removes a class of bugs from inconsistent camelCase conversion.

### 2026-07-09 — MediaPipe Pose + Ultralytics YOLO, pretrained only
**Decision:** no training a pose model from scratch.

### 2026-07-09 — Rate limiting and formal audit logging deferred to Milestone 4
**Decision:** not built in Milestone 1, deliberately.

### 2026-07-09 — OAuth2 login deferred, JWT-only for v1
**Decision:** email + password + JWT for Milestone 1.

---

## Open questions

- **Storage:** local-disk mock (M2) needs a real S3/R2 swap before any deployment beyond local dev/demo — see `IMPLEMENTATION_REVIEW.md` M1.
