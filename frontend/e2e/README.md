# End-to-end checks (headless Chrome, real backend)

These are the 56 browser checks used to verify the frontend rebuild (`part1.mjs` = 22, `part2.mjs` = 34).
They are **not** wired into `npm test` — they need a running stack and two extra dev dependencies.

## Requirements
- Postgres + Redis + the real API on `localhost:8000` (seeded: `python -m app.seed`), frontend on `localhost:3000`
- `npm i -D puppeteer-core @sparticuz/chromium` (or point `launch()` in `lib.mjs` at any Chrome)
- `ffmpeg`, and these files in `./media/` (generate with ffmpeg / `truncate`): `good.mp4` (4 s, 1280x720 h264),
  `short.mp4` (1 s), `fake.mp4` (a text file), `big.mp4` (`truncate -s 201M`)
- `psql` reachable with the creds in `lib.mjs` (`sql()`), used to reset test data and to **simulate the ML worker**

## What is simulated / mocked (be aware when reading results)
- The ML worker is **not run**: `simulateComplete()` in `lib.mjs` writes the rows the worker would write
  (completed status, biomechanical metrics, a risk score, recommendations). Real video analysis is unverified here.
- Two checks (`part2`) intercept a single response to reproduce a backend state that is hard to create
  (`risk-score` → 202 `insufficient_baseline_data`; `report.pdf` → 404 "Video not yet scored").
  They are labelled `MOCKED` in the step name.
- The data reset at the top of `part1.mjs` **deletes all videos** — only run it against a throwaway dev database.

Run: `node part1.mjs && node part2.mjs`
