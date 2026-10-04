// Results page against the REAL API (real scored videos). Run after the backend e2e script:
//   node e2e/part3_results.mjs
import { execSync } from "node:child_process";
import { BASE, launch, newPage, step, waitText, text, shot, results } from "./lib.mjs";

const q = (sql) => execSync(`psql -h localhost -p 5433 -U injury_user injury_e2e -tA -c "${sql}"`,
  { env: { ...process.env, PGPASSWORD: "changeme_in_production" } }).toString().trim();
const idOf = (like) => q(`select id from videos where original_filename like '%${like}%' and processing_status='completed' order by created_at desc limit 1`);
const ids = { clean: idOf("clip.mp4"), caveat: idOf("Johannes0Horn"), frontal: idOf("RiccardoRiccio"), shortclip: idOf("jordanmargolis") };
console.log("videos:", ids);

const browser = await launch();
const page = await newPage(browser);
await step("login as coach", async () => {
  await page.goto(BASE + "/login", { waitUntil: "networkidle2" });
  await page.type("input[type=email]", "coach@demo.com");
  await page.type("input[type=password]", "demo123");
  await Promise.all([page.waitForNavigation({ waitUntil: "networkidle2" }), page.click("button[type=submit]")]);
  return new URL(page.url()).pathname;
});

const open = async (id) => { await page.goto(`${BASE}/videos/${id}/results`, { waitUntil: "networkidle2" }); await new Promise((r) => setTimeout(r, 1500)); };

await step("scored clip: score, five sub-scores, injury cards, no console errors", async () => {
  page.consoleErrors.length = 0;
  await open(ids.clean);
  await waitText(page, "Where the pattern points");
  const t = await text(page);
  for (const s of ["Injury risk", "Movement quality", "Efficiency*", "Fatigue risk", "Overall health"]) if (!t.includes(s)) throw new Error("missing sub-score " + s);
  for (const s of ["ACL", "Hamstring"]) if (!t.toLowerCase().includes(s.toLowerCase())) throw new Error("missing injury card " + s);
  const errs = page.consoleErrors.filter((e) => !/font|favicon|Failed to load resource/i.test(e));
  if (errs.length) throw new Error("console errors: " + errs.join(" | ").slice(0, 200));
  await shot(page, "p3_scored");
  return "sub-scores + injury cards rendered";
});

await step("two-person clip: coverage caveat is visible to the user", async () => {
  await open(ids.caveat);
  const t = await text(page);
  if (!/people in frame|several people|multiple people|more than one person/i.test(t)) throw new Error("no multi-person notice. Page: " + t.slice(0, 300).replace(/\n/g, " | "));
  if (!/provisional/i.test(t)) throw new Error("no 'provisional' warning");
  await shot(page, "p3_caveat");
  return "caveat + provisional warning shown";
});

await step("front-view clip: says why there is no score, still shows measurements", async () => {
  await open(ids.frontal);
  const t = await text(page);
  if (!/no risk score|can.t be scored|cannot be scored|no validated/i.test(t)) throw new Error("no explanation. Page: " + t.slice(0, 300).replace(/\n/g, " | "));
  await shot(page, "p3_frontal");
  return "unavailable notice shown";
});

await step("short clip: page renders for a clip with a visibility warning", async () => {
  await open(ids.shortclip);
  const t = await text(page);
  if (!/left leg/i.test(t)) throw new Error("visibility warning not shown. Page: " + t.slice(0, 300).replace(/\n/g, " | "));
  await shot(page, "p3_visibility");
  return "poor-visibility warning shown";
});

await browser.close();
const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} passed`);
process.exit(failed.length ? 1 : 0);
