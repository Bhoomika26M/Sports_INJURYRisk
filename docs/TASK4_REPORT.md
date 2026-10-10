# Task 4 — Corpus baselines + results UI (2026-10-08)

Scope: `backend/scripts/process_corpus.py`, the frontend results and upload pages. Nothing else was edited.

## 1. What was done

| File | Change |
|---|---|
| `backend/scripts/process_corpus.py` (new) | Uploads and processes every clip from the `verify_data_videos.py` and `verify_test_assets.py` catalogs through the real HTTP API with those catalogs' labels, waits for the worker, checks each outcome against the catalog's expectation, then asks the backend for per-movement baseline videos/athletes and prints them against 10 / 3. |
| `backend/tests/test_process_corpus.py` (new) | Offline self-check, 4 tests: every label is one the API accepts, no recording can count twice, verdict logic, baseline-count logic. |
| `frontend/src/app/(authenticated)/videos/[id]/results/page.tsx` | New "What the clip shows" card: detected movement and camera angle next to the labels, a warning when they disagree. |
| `frontend/src/app/(authenticated)/videos/upload/page.tsx` | "Auto-detect" option; a failed upload can now be retried (see 4). |
| `frontend/src/lib/types.ts`, `frontend/src/lib/format.ts` | `VideoClassification` / `VideoAnalysis` types; the `AUTO_DETECT` constant. |
| `frontend/e2e/part4_classification.mjs` (new) | The browser check, repeatable. |
| `docs/DECISIONS.md` | Four entries, 2026-10-08. |

`STATE.md` was not touched (four agents are editing in parallel; the integrator should update it once).

Behaviour worth knowing:

- **Counts are the backend's.** The script never counts baselines itself; it calls `POST /baselines/recompute` and reads `videos` and per-feature `athletes`. If the backend's own gate differs from 10 / 3 it says so.
- **No fabricated baselines.** Athlete = one per source recording (the `real_clip_validation.py` convention), assumed from the clip descriptions and not verified. `squat_demo.webm` is a frame-identical twin of `squat_sample.mp4`, so it is processed and then deleted: one performance never counts twice. A clip whose filename is already on the server is not uploaded again, so re-runs do not inflate anything.
- **Results card.** Reads `analysis.classification.detected_movement` and `.detected_view`. Null or absent means "couldn't tell"; with both absent (older videos) nothing is shown. The comparison is done in the browser against the video's own labels. The "other" camera angle is a catch-all and is never contradicted. No confidence number is shown, because none has been calibrated.
- **Auto-detect.** Selecting it hides the camera-angle picker and sends `movement_type: "auto"`, `camera_view: "auto"`.

## 2. How it was verified, and what was not real

The zip has no `data/` or `test-assets/` clips, no Docker is available in my sandbox, and the ML stack (torch, the Google-hosted MediaPipe model) cannot be installed. So:

| Real | Simulated (harness only, not in the zip) |
|---|---|
| The repo's FastAPI app, Alembic migrations, seed, Postgres 16, Redis 7, the arq queue, ffprobe limits, the HTTP upload flow, baseline recompute, the production `next build`, headless Chromium | The ML worker (a stand-in writes the outcome each catalog documents: pass or the gate code); the 14 clips (ffmpeg test patterns with the catalog filenames, 854x480, 3 s); `analysis.classification` (this backend does not write it yet, so the browser check writes it into `videos.analysis` and restores it) |

| Check | Result |
|---|---|
| `npx tsc --noEmit` | exit 0 |
| `npx eslint src --max-warnings=0` | exit 0 |
| `npx next build` | compiled and type-checked (Google Fonts mocked: sandbox cannot reach them, so screenshots use a fallback font) |
| `pytest tests/test_process_corpus.py` | 4 passed. Targeted file only; the full suite was not run (one agent at a time). |
| `e2e/part4_classification.mjs`, live API + web app | 9 of 9 steps pass: log in; results page for labels match / movement differs / camera angle differs / movement undecided / no classification; upload form offers Auto-detect, hides the camera angle, exactly one radio checked; refusal message, file kept, request body was `auto`/`auto`, retry reaches "Analyzing movement"; no console errors. DB restored afterwards (0 leftovers). |
| `process_corpus.py` run 1, fresh DB, real API | 13 of 14 clips uploaded and ended as expected; `squat_demo.webm` refused (see 3); exit 1 |
| run 2, immediately again | 0 new uploads. Videos 13 before and after, 0 `pending_upload`, 0 duplicate filenames |
| run 4, throw-away backend copy with both webm fixes | webm uploaded, completed, twin deleted (0 webm rows left), exit 0 |
| runs 5 and 6 back to back | the second waited out the backend's 60 s recompute debounce and still printed the full table |

The baseline table from those runs is **not a baseline fact**: it comes from simulated outcomes (squatting 2/10 videos and 2/3 athletes, landing 2/10 and 2/3, jumping 1/10 and 1/3, throwing 1/10 and 1/3, running, sprinting and cutting 0/10 and 0/3; the frontal aquabag clip has 0 validated metrics so cutting stays 0). It is only what the catalogs' documented outcomes would give. Run the script on your stack for the real numbers. It has never been run on the real clips, so API limits that real files might hit (duration, resolution, 200 MB) are untested here; the script reports such refusals per clip.

## 3. Defects found, not fixed (outside Task 4's files)

`.webm` and `.mkv` uploads cannot succeed through the API, although the 2026-10-07 change added them. Two independent causes, both confirmed live:

1. `backend/app/main.py`: `STORAGE_KEY_PATTERN` ends `\.(mp4|mov)$`, so the storage PUT returns `400 invalid_key`. Fix: `\.(mp4|mov|webm|avi|mkv|m4v)$`.
2. `backend/app/modules/video/router.py` (`confirm_upload`): reads ffprobe `stream=duration`, which WebM/Matroska omit, so it returns `400 invalid_format`. Fix: ask for `stream=width,height,r_frame_rate:format=duration` and read `data["format"]["duration"]`.

Both fixes worked in a throw-away copy. (2) was reproduced on an ffmpeg-made WebM, not on your real `squat_demo.webm`; check with `ffprobe -v error -select_streams v:0 -show_entries stream=duration -of csv=p=0 squat_demo.webm` (empty output means it is affected). Until fixed, `process_corpus.py` correctly exits 1 on that clip.

## 4. Other things you should know

- **Existing bug, fixed in the upload page:** after any failed upload, "Analyze video" did nothing (`start()` returned unless the phase was `form`, and a failure leaves it at `failed`). Found by reading the code; I did not run the old build. With the fix the retry is verified live.
- **Auto-detect needs the backend.** This backend rejects `"auto"`, so today the option shows "Auto-detect isn't available on this server yet" and keeps the file. It starts working when the backend accepts `"auto"` for both fields and resolves them during processing.
- **The classification field names are an assumption.** `detected_movement` and `detected_view` are what I coded to; they are the words from the task, not a confirmed contract. If Task 1 names them differently, `ClassificationNotes` in `results/page.tsx` is the one place to change.
- **Skipped on purpose:** `--manifest`, `--replace`, `--json`; reading classification in the script; any confidence display. To re-process the corpus after Task 1 lands, delete the corpus videos and re-run (classification is written at processing time).

## 5. Run it

```bash
docker compose up -d                                   # backend + worker + postgres + redis, seeded
python backend/scripts/process_corpus.py               # httpx is already in requirements.txt
cd backend && pytest tests/test_process_corpus.py -q
cd frontend && npx tsc --noEmit && npx eslint src && npx next build
CHROME_PATH=/path/to/chrome node e2e/part4_classification.mjs   # needs psql, ffmpeg, >= 5 completed videos
```
