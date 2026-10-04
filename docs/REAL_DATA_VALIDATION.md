# Real-data validation

The merged engine run on **real footage**, end to end, with the real models (YOLOv8n-pose tracking, MediaPipe pose),
the real worker code path and the real risk engine. Nothing in this report is synthetic.

> **What this does and does not show.** It shows the pipeline runs on messy real video, refuses junk, and that the
> scoring engine behaves sensibly (and it exposed three real defects, all fixed). It does **not** show that the angles are
> accurate (no ground truth) or that any score predicts injury (no injury labels). See *Limits*.

## Corpus

24 clips from public GitHub repositories, each capped at 45 s and downscaled to ≤1280 px so CPU pose estimation finishes.
**The clips are not in this repo**: licences are unknown and some are stock footage. `real-data/manifest.json` lists every file,
its labelled camera view and its source; `scripts/real_clip_validation.py` reproduces the run. Camera views were labelled by eye
from three frames per clip, not from file names (a file called `bodyweight_squat.mp4` is a clinic logo card and a coaching intro).

Deliberately **excluded** so the corpus stays honest: a second copy of `ErayBD squat_2` (in `MichistaLin/mediapipe-Fitness-counter`) and of
`imustitanveer squats` (in `ayazmhmd/pose-estimation-using-yolov8`) — same footage, would inflate the baseline; three 224×224 clips in
`aminuabdusalam/AI-FitnessTrainer/Archives/SmallFrameVideos` — **CGI avatars**, not people; front-facing and non-squat clips (walking, deadlift, push-up, lunge).

## Results — 19 completed, 5 refused by the quality gates

Production floors: **10 videos from ≥3 athletes**. "Demo floor" = 8 videos (athlete floor unchanged), shown only so real scores can be
inspected; it is not the product default. Every score here is **provisional** (fewer than 30 baseline videos).

| clip | movement | view | pipeline | athlete tracked | people seen | caveat | video quality | score @ production floor | score @ demo floor 8 |
|---|---|---|---|---|---|---|---|---|---|
| `thillai-c__squat.mp4` | squatting | sagittal | completed | 100% | 2 | — | good | 202 — 9/10 videos | 0.2 low |
| `rohanx01__squat.mp4` | squatting | sagittal | completed | 100% | 3 | — | fair | 0.0 low | 0.0 low |
| `jordanmargolis__demo-squat.mp4` | squatting | sagittal | completed | 100% | 1 | — | fair | 0.0 low | 0.0 low |
| `guptabhishekumar__home_squat_realtime.mp4` | squatting | sagittal | completed | 99% | 1 | — | fair | 202 — 9/10 videos | 0.0 low |
| `guptabhishekumar__woman_bodyweight_squats.mp4` | squatting | sagittal | completed | 100% | 1 | — | good | 202 — 9/10 videos | 0.0 low |
| `guptabhishekumar__woman_squats_side_view.mp4` | squatting | sagittal | completed | 88% | 1 | — | poor | 0.0 low | 0.0 low |
| `Johannes0Horn__squats.mp4` | squatting | sagittal | completed | 100% | 2 | yes | fair | 0.0 low | 0.0 low |
| `itertius__squat_sample.mp4` | squatting | other | completed | 100% | 2 | — | fair | 202 — 9/10 videos | 49.1 moderate |
| `imustitanveer__squats.mp4` | squatting | other | completed | 94% | 5 | — | fair | 202 — 9/10 videos | 4.2 low |
| `RiccardoRiccio__squat_form.mp4` | squatting | frontal | completed | 100% | 1 | — | poor | cannot score (front/rear view) | — |
| `guptabhishekumar__couple_squat_exercise.mp4` | squatting | frontal | completed | 100% | 2 | yes | poor | cannot score (front/rear view) | — |
| `guptabhishekumar__squat_proper_form.mp4` | squatting | frontal | REFUSED `multiple_people_subject_unstable` | 66% | 2 | — | — | — | — |
| `guptabhishekumar__webcam_squat_front.mp4` | squatting | frontal | REFUSED `multiple_people_subject_unstable` | 25% | 4 | — | — | — | — |
| `guptabhishekumar__bodyweight_squat.mp4` | squatting | frontal | REFUSED `multiple_people_subject_unstable` | 35% | 7 | — | — | — | — |
| `guptabhishekumar__laptop_squat_facing.mp4` | squatting | frontal | REFUSED `subject_too_small` | 19% | 6 | — | — | — | — |
| `guptabhishekumar__squat_mistakes.mp4` | squatting | frontal | REFUSED `multiple_people_subject_unstable` | 9% | 5 | — | — | — | — |
| `laura-szczerbowska__running_side.mp4` | running | sagittal | completed | 89% | 3 | yes | poor | 202 — 0/10 videos | — |
| `laura-szczerbowska__running_rear.mp4` | running | frontal | completed | 100% | 1 | — | poor | cannot score (front/rear view) | — |
| `ZiyueWangUoB__isaiah_jump.mp4` | jumping | sagittal | completed | 79% | 2 | yes | fair | 202 — 0/10 videos | — |
| `ErayBD__squat_1.mp4` | squatting | sagittal | completed | 100% | 1 | — | fair | 0.0 low | 0.0 low |
| `ErayBD__squat_2.mp4` | squatting | sagittal | completed | 100% | 1 | — | good | 202 — 9/10 videos | 0.0 low |
| `ErayBD__squat_3.mp4` | squatting | sagittal | completed | 100% | 1 | — | good | 202 — 9/10 videos | 22.1 low |
| `aminuabdusalam__squats.mp4` | squatting | sagittal | completed | 100% | 2 | yes | poor | 0.0 low | 0.0 low |
| `Pradnya1208__youTube_video.mp4` | squatting | sagittal | completed | 100% | 1 | — | fair | 202 — 9/10 videos | 28.6 moderate |

Scored at the production floor: **6** · at the demo floor: **14**.

## Findings

1. **The gates refuse junk.** All 5 refused clips are unusable for athlete analysis (a lecture, a slide deck, a clinic intro with 7 people,
   a stock edit with cuts) except one: `squat_proper_form` looks like a single woman but was tracked in 66% of frames, just under the 70% floor
   — a second person registered somewhere. Not investigated; possible over-rejection.
2. **Multi-person clips complete but are caveated and kept out of baselines.** 5 completed clips carry a coverage caveat
   (`Johannes0Horn__squats`, `guptabhishekumar__couple_squat_exercise`, `laura-szczerbowska__running_side`, `ZiyueWangUoB__isaiah_jump`, `aminuabdusalam__squats`). They can still be scored but never feed the population.
3. **Defect 1 — occlusion drove a "high" score.** `jordanmargolis` (5 s, side-on) had its far leg visible in 13.5% of frames. Three left-leg angles
   from those few frames sat far outside the population and it scored **63.6 "high"**. Features from a leg below the 60% visibility floor are now
   excluded from the comparison (engine 2.1). Same clip: **0.0 "low"**.
4. **Defect 2 — the score depended on database row order.** Found when one test passed alone and failed in a full run. The baseline arrives from a
   `GROUP BY` with no `ORDER BY`; the forest and its cross-fit folds depend on row order, so a perfectly normal video could score 0 or 100 depending only on
   how Postgres returned the rows (2 of 8 simulated populations flipped). The engine now sorts the baseline canonically (engine 2.2); shuffling no longer changes anything.
5. **Defect 3 — small baselines are noisy, so scores are now labelled.** With the 10-video floor, ~10% of *perfectly normal* simulated videos score as strongly
   anomalous (~2% at 30 videos; 8 normal simulated videos at n=10 gave 2 deterministic false 100s). The response now carries `baseline.provisional` for fewer than 30
   baseline videos and the results page says so. **Recommendation: set `MIN_BASELINE_VIDEOS=30` for anything beyond a demo.**
6. **A moderate score here means "unlike this population", not "bad technique".** The barbell back squats (`itertius`, `Pradnya1208`) score moderate against a
   baseline that is mostly bodyweight/goblet squats. Squat variant and exact camera angle are not baseline dimensions.
7. **Only squatting has a baseline.** Running and jumping have no other usable videos. Front/rear views correctly return "cannot score": sagittal angles cannot be measured from the front.
8. **The squat baseline is one clip short of the production floor.** Clips inside the population see 0, 9 *other* usable videos against 10 needed, so most
   return HTTP 202 "baseline building" by design. One more clean, side-on, single-person squat from a new person closes it (and 20 more would make scores trustworthy).

## Limits (read before quoting any of this)

- **No ground truth.** "Completed" means it passed the gates and produced metrics, not that the angles are right.
- **No injury labels.** Scores flag movement that differs from a reference population; they do not estimate injury probability.
- **Clips are not athletes.** One athlete record per source (`ErayBD` = three clearly different women → three athletes; one couple clip = one athlete although two people). Athlete counts are a best guess.
- 24 clips, one movement with a usable baseline, mostly demo footage: enough to find bugs, not enough to claim accuracy.
