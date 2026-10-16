# Gemini video observation: build plan, implementation plan, test plan

Status (2026-10-14): **built, offline-verified, and partly verified live** on a free-tier key (section 7). Whole-clip runs and model probing work. The chunked run, a frontal-view valgus run and the token check are still to be run on the build in this zip.

Scope: one standalone script, `backend/scripts/gemini_video.py`, that sends a downscaled clip to Gemini and returns *qualitative* observations (joints visible, knee-valgus flag, trunk lean, asymmetry, quality grade). It touches no table, route, worker or frontend file and never feeds scoring.

## 1. What changed from the handover (read this first)

All of this was checked against Google's own docs on 2026-10-13, not recalled.

| Handover / mentor said | What is actually true | What we do |
|---|---|---|
| Use **Omni** | `gemini-omni-1.1-flash` is a video **generation and editing** model. Google's video-understanding guide points analysis at the regular Gemini models. | Use `gemini-3.8-flash` (stable). Fall back, failing fast, through `3.7-flash`, `3.6-flash`, `3.5-flash`, `3.5-flash-lite`, `3.1-flash-lite`. Omni names are refused in code. |
| `gemini-1.5-flash` / `2.0-flash` | 2.0 is listed as shut down. 1.5 is not in the lineup. 2.5 is limited to people who already used it. | Don't build on any of them. |
| `google-generativeai`, `genai.upload_file` | Old SDK. The new `google-genai` 2.30 requires `websockets>=13` and `pydantic>=2.12.5`; this repo pins `websockets==12.0` and `pydantic==2.11.7`, so installing it would break the existing install. | Call the REST API with `httpx` (already pinned). **No new dependency.** |
| `generateContent` | The Interactions API went GA in June 2026 and is what the docs now recommend for new projects. | Use `/v1beta/interactions`. |
| Decimate to 1-2 FPS in ffmpeg to save tokens | Gemini samples frames itself (1 FPS default, `processing.fps` configurable). Video frames cost roughly 70 tokens (low) or 280 (high) each, so a 10 s clip at 4 FPS and high resolution is about 11k tokens: tokens are not the constraint, accuracy is. A squat descent lasts 1-2 s, so 1 FPS gives 1-2 frames of it. ffmpeg decimation would also silently cap whatever `--fps` asks for. | ffmpeg downscales only. Default `--fps 4`, high media resolution. |
| Chunk with ffmpeg segments | Gemini can clip server-side (`start_offset`/`end_offset`), so one upload serves every window. | One upload, one request per window, 1 s overlap so a rep cut at a boundary is whole in one window. |

## 2. Files

| File | Purpose |
|---|---|
| `backend/scripts/gemini_video.py` | Everything: schema, prompt, ffmpeg, REST client, orchestration, CLI. |
| `backend/tests/test_gemini_video.py` | 65 offline tests (fake Gemini server, real ffmpeg). |
| `backend/scripts/gemini_corpus_table.py`, `backend/tests/test_gemini_corpus_table.py` | Turns a folder of reports into a table checked against the repo's clip labels, plus 20 offline tests. No API calls. |
| `docs/GEMINI_VIDEO_PLAN.md` | This file. |
| `docs/DECISIONS.md` | Entry dated 2026-10-13. |
| `.env.example`, `.gitignore` | `GEMINI_API_KEY=` placeholder; `gemini_out/` ignored. |

`requirements.txt`, `app/`, `alembic/`, `frontend/` are unchanged.

## 3. Pipeline

1. **Validate input.** Missing file, bad `--fps` (0.1-30), odd or tiny `--height`, omni model: exit 2, nothing sent anywhere.
2. **Preprocess (ffmpeg).** Height at most `--height` (default 480), never upscaled, even sizes, audio removed, H.264 yuv420p, source frame rate kept. Rejects unreadable files and clips under 1 s.
3. **Window.** `--chunk-seconds N` gives overlapping windows (1 s overlap, no sliver tail, at most 30). Without it, the whole clip is one window. Offsets go out as duration strings (`"7.5s"`), which is what the API reference specifies; bare numbers are not accepted by a raw-REST call.
4. **Upload** via the resumable Files protocol. The file is named `clip`; the athlete's filename is never sent. The upload URL must be on `*.googleapis.com` before the API key is sent to it.
5. **Poll** until `ACTIVE`. `FAILED` or a timeout (about 3 min) is an error.
6. **One interaction per window.** Video part first, prompt text after it, structured JSON response. `--media-resolution default` omits the resolution field entirely. If a model is missing, forbidden, over quota or overloaded (403, 404, 429, 5xx), the next candidate is tried at once with no backoff and a note on stderr says which model answered; only the last candidate (or a pinned `--model`) gets retries with backoff. After one succeeds, later windows stick to it. Requests carry `store: false`: interactions are otherwise kept by default (1 day on the free tier, 55 days on paid).
7. **Validate and scrub.** Responses must match the schema. Degree figures and "N% ... injury" claims are removed from all free text.
8. **Roll up** worst case across windows. Windows the model could not assess are ignored; if none could be assessed the rollup is `null`.
9. **Delete the uploaded file**, on success and on every failure after upload.
10. **Report** to `gemini_out/<clip>.json` and the terminal. Exit 0 if at least one window was analysed, 1 if none were, 2 for bad input or missing key.

## 4. Output and science constraints

The schema has no angle, score or probability field. Knee valgus is `none | mild | marked | not_assessable` plus a sentence; from a pure side view the prompt tells the model to answer `not_assessable`. Every report carries `confidence: "qualitative"` and a disclaimer. This honours `AGENTS.md` (valgus is qualitative, no injury prediction) and `SCIENCE_CONSTRAINTS.md`.

Each judgement depends on the camera view, and the prompt says so: knee valgus needs a front, back or oblique view; forward trunk lean needs a side or oblique view and sideways tilt a front or back view; asymmetry needs both legs clearly visible. Otherwise the answer must be `not_assessable`. `reps_seen` is the model's best count and nobody has checked it.

The degree/percentage scrub is a regex, so it is a backstop, not a guarantee: "fifteen degrees" in words would pass. The prompt and the schema are the first line of defence. Error messages never echo the model's own words (pydantic does by default; we strip it).

What the output is: an AI model's visual opinion of a downscaled video. It has not been checked against ground truth. Do not cite it as validated, do not compare it to the pose pipeline's numbers as if both were measurements, and do not store it in `videos.analysis` or feed it to risk scoring.

## 5. Failure behaviour

| Condition | Behaviour |
|---|---|
| 429 / 500 / 502 / 503 / 504 on the last (or pinned) model; network error on any model | Up to 5 attempts, honours `Retry-After`, otherwise 1, 2, 4, 8 s. |
| 400 / 401 (bad key, bad field) | Not retried, no fallback, run aborts with Google's message. File still deleted. |
| 403 / 404 / 429 / 5xx while fallback models remain | Next model immediately, no backoff. A pinned `--model` never falls back. |
| Window returns empty, non-JSON, or off-schema | Recorded as that window's error; other windows continue. |
| Every window fails | Report still written, exit 1. |
| File state `FAILED` or never `ACTIVE` | Error, file deleted, no model call made. |

Known ceiling: requests are synchronous, so keep windows around 60 s or less (`--chunk-seconds`). Streaming and background execution are deliberately not implemented.

## 6. Test plan

`cd backend && pytest tests/test_gemini_video.py` needs no Postgres, no key and no network. ffmpeg must be present (system or `static-ffmpeg`); if it is not, tests **fail loudly** rather than skip, per the repo's zero-skip rule.

| Risk | How it is covered |
|---|---|
| Wrong or stale model (Omni, 1.5, 2.0) | Omni refused in code and CLI; default list pinned to `gemini-3.x` flash names. |
| Breaking the existing stack | `app/` contains no "gemini"; the module imports nothing from `app` or the SDK; `requirements.txt` must not gain the SDK. |
| Bad preprocessing | Real ffmpeg: 720p becomes 854x480, no audio stream, H.264, frame rate unchanged, smaller file; small clips not upscaled; odd-height 4:4:4 source still encodes to even sizes in yuv420p; garbage, missing and sub-1 s files fail cleanly. |
| Wrong windows | Property test (300 cases): full coverage, order, exact 1 s overlap, no sliver tail, bounded length. |
| Request shape drift | Exact assertion on every request: headers, upload protocol, body keys, video part, text after video, schema, no undocumented fields, key never in a URL, athlete filename never sent. |
| Retries, fallback, cleanup | Fake server returns 429/5xx/400/404/network errors; assertions on sleep times, call counts, model order, stickiness, and that the uploaded file is gone every time. |
| Fabricated precision | Schema has no banned field names; degrees and injury percentages never reach the report, including through error messages. |
| CLI behaviour | Exit codes 0/1/2, dry run needs no key and no network, `GEMINI_API_KEY` read from `.env` (and the real environment wins), `--list-models` sends one 1-token request per visible candidate and reports which actually answer. |

**Mutation check.** The main module was broken on purpose in 55 ways (dropping `-an`, decimating fps, skipping the delete, putting the key in the URL, swapping or un-stringing offsets, ignoring Retry-After, retrying on non-last candidates, dropping `store: false`, trusting visibility in `--list-models`, and so on). 54 are caught. The 55th flips a pydantic flag whose output the code never reads, so no test can see it. The table script was broken in 15 ways and all 15 are caught. Earlier rounds let several through, which exposed weak tests (a fixture that could not trip a mutant, a summary test where every row had a label, a CLI test that failed for the wrong reason, one ffmpeg-build-dependent behaviour); those were fixed.

**What the tests cannot prove.** They assert that our requests match the shapes Google *documents* (pages dated September and October 2026), and the fake server was written from those same pages, so a wrong reading of the docs is invisible to them. If a documented shape is wrong or has changed, only the live gate finds it. Verified on Linux with ffmpeg 6.1.1 and under the repo's own `conftest.py` and `pytest.ini`; the Windows `static-ffmpeg` build has not been run.

## 7. Live gate

First live run: 2026-10-14, free-tier key, Windows 11, the previous build. Results as reported by the person who ran them. The offline suite also passed there (59 tests, `static-ffmpeg` build).

| Step | Result |
|---|---|
| `--list-models` | `gemini-3.5-flash-lite` and `gemini-3.1-flash-lite` answered. `gemini-3.8-flash` returned 503 (high demand), `gemini-3.6-flash` returned 429 (quota). |
| Side-view barbell squat, whole clip, `--model gemini-3.5-flash-lite` | Exit 0. Sagittal, valgus `not_assessable`, trunk lean mild, quality good, 6 reps (not yet counted against the clip). |
| Single-leg drop landing, same flags | Exit 0. Valgus `not_assessable`, which is **correct**: the repo's catalog labels this clip sagittal. The model called it a "single-leg squat" in an "oblique view" although told `--movement landing`: unexplained, see below. |
| Dry run (does the prepared clip play?) | Not reported. |
| Chunked run | Not reported. |
| Frontal clip: is valgus judged? | Not run (see the correction). |
| `could not delete uploaded file` on stderr | Not reported. |

**Correction.** An earlier version of this section demanded a non-`not_assessable` valgus on `landing_single_leg_drop_soft_landing.mp4`. That was wrong: the handover called the clip frontal, but `verify_data_videos.py` says sagittal (a test now pins this). Frontal clips in the repo's own catalogs: `data/cutting_aquabag_punch_cod.mp4`, `test-assets/sample-clips/test_figure.mp4`, `test-assets/internet-clips/Px4cyTAHrWc.mp4` and `7a6W56OeU8w.mp4`.

**Bugs the live run exposed, now fixed.** (1) With the top model returning 503 the run aborted after about 15 s of backoff instead of falling back, because only 403/404/429 counted as fall-back-able; unavailable models now fail fast. (2) The terminal summary showed levels but not the notes or limitations, so "why `not_assessable`?" was unanswerable; it now prints them. While re-reading Google's API reference I also found (3) chunk offsets must be strings like `"7s"`, not numbers, and (4) interactions are stored by default; both are fixed (`store: false`).

**Re-run on this build** (PowerShell; replace paths):

```
python backend/scripts/gemini_video.py data/squatting_barbell_back_squat_side_view.mp4 --dry-run     # open gemini_out\*.prepared.mp4 and watch it
python backend/scripts/gemini_video.py data/cutting_aquabag_punch_cod.mp4                              # frontal: is valgus judged now?
python backend/scripts/gemini_video.py <a clip longer than 16 s> --chunk-seconds 8                     # 3+ windows, offsets sent as "7s"
python backend/scripts/gemini_video.py data/landing_single_leg_drop_soft_landing.mp4                   # no --movement hint
python backend/scripts/gemini_video.py data/landing_single_leg_drop_soft_landing.mp4 --fps 10          # does a faster sample fix "single-leg squat"?
```

Pass when: the prepared clip plays; the frontal run exits 0 and judges valgus; the chunked run exits 0 with 3 or more windows; stderr never prints `could not delete uploaded file`; and the token line shows the settings took effect. Each window prints `tokens: input=N video=N ~M per requested frame`. M near 280 means `--fps` and high resolution were applied; M near 70 means Gemini sampled at 1 FPS or used low resolution, and `--fps` is being accepted but ignored.

| Unknown | If it fails | Fix |
|---|---|---|
| Offsets accepted as `"7s"` strings | 400 mentioning offsets | Paste the error; the format follows the API reference, so the reference or the server would be at fault. |
| `--fps` applied, not just accepted | Token line shows ~70 per requested frame | Report it. |
| Landing called "single-leg squat" despite `--movement landing` | The model's `movement` and `limitations` (now printed) | Compare the two `--fps` runs above. If still wrong, the clip may be too fast for sampling at this size, or the lite model is too weak: retry when a full-size Flash model is available. |
| Output quality | Nothing automated | Run the corpus table (below). |

**Corpus table.** After the gate, run every clip twice WITHOUT `--movement` and with one pinned `--model`, then tabulate (loop and flags are in the docstring of `gemini_corpus_table.py`). It reports, per clip and overall: whether movement and camera view agree with the repo's catalog, whether the view rules held (valgus judged from a view the model itself called sagittal; frontal clips where valgus was not judged), how often each flag is `not_assessable`, and whether repeat runs agree with each other. That last number is the cheapest honest reliability check available without a physio. It does not say whether any valgus call is right.

## 8. Rollback

Delete `gemini_video.py`, `test_gemini_video.py`, this file, the DECISIONS entry and the two config lines. Nothing else depends on them.

## 9. Not built, on purpose

Database storage, an API route, frontend, scoring integration, the `google-genai` SDK, streaming or background execution, agentic video mode (Google supports custom fps and clipping only in static mode), a `system_instruction` field (it exists, but the prompt works without it), numeric joint angles of any kind.
