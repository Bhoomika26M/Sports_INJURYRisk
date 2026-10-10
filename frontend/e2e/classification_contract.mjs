// Contract check: the results page's "What the clip shows" card reads the classification the BACKEND really stores.
//
//   node e2e/classification_contract.mjs        (no build, no browser, any Node: the TS helper is transpiled
//                                               with the project's own typescript into a temp dir first)
//
// fixtures/classification_contract.json is written by backend/tests/test_classification_contract.py from real analyze_frames
// output (and that test fails if the backend's shape drifts), so this checks the page against the real thing. T4's card was
// first built on guessed field names and silently rendered nothing on real data.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

// format.ts carries only a type-only import, so it transpiles standalone: no alias config, no build step.
const root = fileURLToPath(new URL("..", import.meta.url));
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "contract-"));
// npx is a .cmd shim on Windows (needs a shell), so run the project's tsc JS on this Node directly.
const tsc = path.join(root, "node_modules", "typescript", "bin", "tsc");
assert.ok(fs.existsSync(tsc), "typescript is not installed: run `npm install` in frontend/ first");
try {
  execFileSync(process.execPath, [tsc, "src/lib/format.ts", "--outDir", tmp, "--module", "es2022", "--target", "es2022", "--moduleResolution", "bundler", "--skipLibCheck"], { cwd: root, stdio: "pipe" });
} catch (e) {
  // tsc exits non-zero on type-resolution noise (@types, path aliases); the JS is still emitted — proceed iff it is.
}
const built = path.join(tmp, "format.js");
assert.ok(fs.existsSync(built), "could not transpile src/lib/format.ts with the project's typescript");
const { classificationRows } = await import(pathToFileURL(built).href);

const cases = JSON.parse(fs.readFileSync(new URL("./fixtures/classification_contract.json", import.meta.url), "utf8"));
const row = (label, found, labelled, same, suggests) => ({ label, found, labelled, same, suggests });
const mv = (...a) => row("Movement", ...a), cam = (...a) => row("Camera angle", ...a);
const EXPECTED = {
  squat_matches: { auto: false, rows: [mv("Squatting", "Squatting", true, false), cam("Side view", "Side view", true, false)] },
  // different movement group: a confident mismatch -> the warning card
  run_labelled_squat: { auto: false, rows: [mv("Running", "Squatting", false, true), cam("Side view", "Side view", true, false)] },
  // same group (running / sprinting): suggested, never a warning
  run_labelled_sprinting: { auto: false, rows: [mv("Running", "Sprinting", null, true), cam("Side view", "Side view", true, false)] },
  squat_labelled_frontal: { auto: false, rows: [mv("Squatting", "Squatting", true, false), cam("Side view", "Front view", false, true)] },
  // the classifier could not tell the movement: say so, do not guess
  standing_still: { auto: false, rows: [mv(null, "Squatting", null, false), cam("Side view", "Side view", true, false)] },
  // an auto upload: identified from the footage, nothing declared, nothing to disagree with
  squat_auto: { auto: true, rows: [mv("Squatting", null, null, false), cam("Side view", null, null, false)] },
};

let failed = 0;
for (const c of cases) {
  try {
    assert.ok(c.name in EXPECTED, `no expectation for ${c.name}: add one`);
    assert.deepEqual(classificationRows(c.classification, c.video), EXPECTED[c.name]);
    console.log(`PASS  ${c.name}`);
  } catch (e) {
    failed++;
    console.log(`FAIL  ${c.name}  — ${e.message.split("\n")[0]}`);
  }
}
for (const missing of Object.keys(EXPECTED).filter((n) => !cases.some((c) => c.name === n))) { failed++; console.log(`FAIL  ${missing}  — not in the fixture`); }
// an older video has no classification at all: nothing to show
assert.equal(classificationRows(null, { movement_type: "squatting", camera_view: "sagittal" }), null);
console.log(failed ? `\n${failed} FAILED` : "\nall cases passed");
process.exit(failed ? 1 : 0);
