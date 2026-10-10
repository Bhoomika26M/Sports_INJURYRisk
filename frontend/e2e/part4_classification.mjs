// Part 4 — browser check of (a) the results page's "What the clip shows" card and (b) the upload form's Auto-detect option,
// against the LIVE web app (:3000) and API (:8000).
//
//   CHROME_PATH=/path/to/chrome node e2e/part4_classification.mjs
//
// Needs psql, ffmpeg, the demo admin, and >= 5 completed videos (run backend/scripts/process_corpus.py first).
// The classification each case shows is WRITTEN into videos.analysis by this script (so every case is deterministic) in the
// shape the backend really stores (see e2e/fixtures/classification_contract.json and e2e/classification_contract.mjs), and
// the original is restored afterwards. Everything else (API, DB, auth, web app, the Auto-detect upload) is real.
import puppeteer from "puppeteer-core";
import { execSync } from "node:child_process";
import fs from "node:fs";

const BASE = "http://localhost:3000";
const CLIP = "/tmp/part4_autodetect_check.mp4";
fs.mkdirSync("./shots", { recursive: true });
const sql = (q) => execSync("psql -h localhost -U injury_user injury_detection -tA", { input: q, env: { ...process.env, PGPASSWORD: "changeme_in_production" } }).toString().trim();
const lit = (s) => `'${s.replace(/'/g, "''")}'`;
const text = (page) => page.evaluate(() => document.body.innerText);
const waitText = (page, t, timeout = 20000) => page.waitForFunction((s) => document.body.innerText.includes(s), { timeout }, t)
  .catch(async () => { throw new Error(`text not found: "${t}". Page shows: ${(await text(page)).slice(0, 240).replace(/\n/g, " | ")}`); });
const count = (hay, needle) => hay.split(needle).length - 1;
let failed = 0;
async function step(name, fn) {
  try { const d = await fn(); console.log(`PASS  ${name}${d ? "  — " + d : ""}`); }
  catch (e) { failed++; console.log(`FAIL  ${name}  — ${e.message.split("\n")[0]}`); }
}
const assert = (cond, msg) => { if (!cond) throw new Error(msg); };

const vids = sql("select id, movement_type, camera_view from videos where processing_status='completed' order by created_at limit 5")
  .split("\n").filter(Boolean).map((l) => { const [id, movement, view] = l.split("|"); return { id, movement, view }; });
if (vids.length < 5) { console.log(`need >= 5 completed videos, found ${vids.length}: run backend/scripts/process_corpus.py first`); process.exit(2); }
const original = Object.fromEntries(vids.map((v) => [v.id, sql(`select coalesce(analysis::text, 'null') from videos where id=${lit(v.id)}`)]));
const other = (m) => (m === "running" ? "squatting" : "running");
const flip = (v) => (v === "frontal" ? "sagittal" : "frontal");
// the classification exactly as the backend stores it (agrees / suggested are filled by the classifier, not the page)
const real = (v, found, agrees = {}, suggested = {}, declared = { movement_type: v.movement, camera_view: v.view }) => ({
  movement_type: found.movement, camera_view: found.view, declared,
  agrees: { movement_type: null, camera_view: null, ...agrees }, suggested: { movement_type: null, camera_view: null, ...suggested },
});
const cases = [
  { name: "labels match", cls: (v) => real(v, { movement: v.movement, view: v.view }, { movement_type: true, camera_view: true }), has: ["What the clip shows", "Labelled as"], count: ["Matches the label", 2], not: ["looks different"] },
  { name: "movement differs", cls: (v) => real(v, { movement: other(v.movement), view: v.view }, { movement_type: false, camera_view: true }, { movement_type: other(v.movement) }), has: ["Movement looks different from the label", "Differs from the label", "check it before relying on them"], not: ["Camera angle looks different"] },
  { name: "camera angle differs", cls: (v) => real(v, { movement: v.movement, view: flip(v.view) }, { movement_type: true, camera_view: false }, { camera_view: flip(v.view) }), has: ["Camera angle looks different from the label", "Differs from the label"], not: ["Movement looks different"] },
  { name: "movement undecided", cls: (v) => real(v, { movement: "unknown", view: v.view }, { camera_view: true }), has: ["Couldn't tell", "Matches the label"], not: ["looks different"] },
  { name: "no classification (older video)", cls: () => null, not: ["What the clip shows"] },
  { name: "suggested inside the same group", cls: (v) => real(v, { movement: other(v.movement), view: v.view }, { camera_view: true }, { movement_type: other(v.movement) }), has: ["Suggested instead of the label"], not: ["looks different", "Differs from the label"] },
  { name: "auto upload, identified from the footage", cls: (v) => real(v, { movement: v.movement, view: v.view }, {}, {}, { movement_type: "auto", camera_view: "auto" }), has: ["No labels were given", "Identified from the footage"], not: ["Differs from the label", "Matches the label"] },
];

const browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH, args: ["--no-sandbox"], headless: "shell" });
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 860 });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => { if (m.type() === "error" && !/Failed to load resource/.test(m.text())) errors.push(m.text()); });

try {
  await step("log in as the demo admin", async () => {
    await page.goto(BASE + "/login", { waitUntil: "networkidle2" });
    await page.waitForSelector("button[type=submit]:not([disabled])");
    await page.type("input[type=email]", "admin@demo.com");
    await page.type("input[type=password]", "demo123");
    await page.click("button[type=submit]");
    await page.waitForFunction(() => !location.pathname.startsWith("/login"), { timeout: 20000 });
  });

  for (const [i, c] of cases.entries()) {
    await step(`results page: ${c.name}`, async () => {
      const v = vids[i % vids.length];
      const cls = c.cls(v);
      sql(cls ? `update videos set analysis = coalesce(analysis, '{}'::jsonb) || jsonb_build_object('classification', ${lit(JSON.stringify(cls))}::jsonb) where id=${lit(v.id)}`
              : `update videos set analysis = coalesce(analysis, '{}'::jsonb) - 'classification' where id=${lit(v.id)}`);
      await page.goto(`${BASE}/videos/${v.id}/results`, { waitUntil: "networkidle2" });
      await waitText(page, "Key numbers").catch(() => waitText(page, "measurements"));
      const t = await text(page);
      for (const s of c.has ?? []) assert(t.includes(s), `missing "${s}"`);
      for (const s of c.not ?? []) assert(!t.includes(s), `unexpected "${s}"`);
      if (c.count) assert(count(t, c.count[0]) === c.count[1], `"${c.count[0]}" x${count(t, c.count[0])}, wanted ${c.count[1]}`);
      await page.screenshot({ path: `./shots/part4_results_${i}_${c.name.replace(/\W+/g, "_")}.png`, fullPage: true });
      return `${v.movement}/${v.view} classified as ${cls ? `${cls.movement_type}/${cls.camera_view}` : "nothing"}`;
    });
  }

  await step("upload form: Auto-detect is offered, hides camera angle, explains itself", async () => {
    execSync(`ffmpeg -y -loglevel error -f lavfi -i testsrc2=size=854x480:rate=24:duration=3 -c:v libx264 -pix_fmt yuv420p ${CLIP}`);
    await page.goto(BASE + "/videos/upload", { waitUntil: "networkidle2" });
    await waitText(page, "Auto-detect");
    await page.$eval("input[name=movement][value=squatting]", (el) => el.click());
    await waitText(page, "Camera angle");
    await page.$eval("input[name=movement][value=auto]", (el) => el.click());
    await waitText(page, "work out the movement and camera angle");
    assert(!(await text(page)).includes("Camera angle"), "camera angle picker still shown");
    const checked = await page.$$eval("input[name=movement]:checked", (els) => els.map((e) => e.value));
    assert(checked.length === 1 && checked[0] === "auto", `checked movement radios: ${JSON.stringify(checked)}`);
    await page.mouse.move(0, 0); // keep a hover tint off the screenshot
    await page.screenshot({ path: "./shots/part4_upload_auto_selected.png", fullPage: true });
  });

  await step("upload form: Auto-detect sends auto/auto and the upload goes ahead", async () => {
    const bodies = [];
    page.on("request", (r) => { if (r.method() === "POST" && r.url().endsWith("/videos/upload-url")) bodies.push(JSON.parse(r.postData())); });
    const athlete = await page.$$eval("#section-athlete select option", (os) => os.map((o) => o.value).filter(Boolean)[0]);
    await page.select("#section-athlete select", athlete);
    await (await page.$("input[type=file]")).uploadFile(CLIP);
    await waitText(page, "part4_autodetect_check.mp4");
    await page.evaluate(() => [...document.querySelectorAll("button")].find((b) => b.innerText.includes("Analyze video")).click());
    await waitText(page, "Analyzing movement", 40000);
    assert(bodies[0]?.movement_type === "auto" && bodies[0]?.camera_view === "auto", `sent ${JSON.stringify(bodies[0])}`);
    await page.screenshot({ path: "./shots/part4_upload_auto_goes_ahead.png", fullPage: true });
    return `request ${JSON.stringify(bodies[0])} was accepted and reached "Analyzing movement"`;
  });

  await step("no console errors", async () => assert(errors.length === 0, errors.slice(0, 2).join(" || ")));
} finally {
  for (const v of vids) sql(original[v.id] === "null" ? `update videos set analysis = null where id=${lit(v.id)}` : `update videos set analysis = ${lit(original[v.id])}::jsonb where id=${lit(v.id)}`);
  sql("delete from videos where original_filename = 'part4_autodetect_check.mp4'");
  await browser.close();
}
console.log(failed ? `\n${failed} step(s) FAILED` : "\nall steps passed");
process.exit(failed ? 1 : 0);
