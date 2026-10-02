import chromium from "@sparticuz/chromium";
import puppeteer from "puppeteer-core";
import { execSync } from "node:child_process";
import fs from "node:fs";

export const BASE = "http://localhost:3000";
export const API = "http://localhost:8000/api/v1";
export const SHOTS = "./shots";
export const results = [];
fs.mkdirSync(SHOTS, { recursive: true });

export function sql(q) {
  return execSync(`psql -h localhost -U injury_user injury_detection -tA -c "${q.replace(/"/g, '\\"')}"`, {
    env: { ...process.env, PGPASSWORD: "changeme_in_production" },
  }).toString().trim();
}

export async function launch() {
  return puppeteer.launch({ args: [...chromium.args, "--no-sandbox"], executablePath: await chromium.executablePath(), headless: "shell" });
}

export async function newPage(browser, { mobile = false } = {}) {
  const page = await browser.newPage();
  await page.setViewport(mobile ? { width: 390, height: 844, isMobile: true, hasTouch: true } : { width: 1280, height: 860 });
  page.consoleErrors = [];
  page.on("pageerror", (e) => page.consoleErrors.push("pageerror: " + e.message));
  page.on("console", (m) => { if (m.type() === "error") page.consoleErrors.push(m.text()); });
  return page;
}

export async function step(name, fn) {
  try {
    const detail = await fn();
    results.push({ name, ok: true, detail });
    console.log(`PASS  ${name}${detail ? "  — " + detail : ""}`);
  } catch (e) {
    results.push({ name, ok: false, detail: e.message });
    console.log(`FAIL  ${name}  — ${e.message.split("\n")[0]}`);
  }
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
export const text = (page) => page.evaluate(() => document.body.innerText);
export async function waitText(page, t, timeout = 15000) {
  await page.waitForFunction((s) => document.body.innerText.includes(s), { timeout }, t)
    .catch(async () => { throw new Error(`text not found: "${t}". Page shows: ${(await text(page)).slice(0, 200).replace(/\n/g, " | ")}`); });
}
export async function clickText(page, selector, t) {
  const ok = await page.evaluate((sel, s) => {
    const el = [...document.querySelectorAll(sel)].find((e) => e.innerText.trim().includes(s));
    if (el) { el.click(); return true; } return false;
  }, selector, t);
  if (!ok) throw new Error(`no ${selector} containing "${t}"`);
}
export const path = (page) => new URL(page.url()).pathname + new URL(page.url()).search;
export async function shot(page, name) { await page.screenshot({ path: `${SHOTS}/${name}.png` }); }

export async function login(page, email, password = "demo123", url = "/login") {
  await page.goto(BASE + url, { waitUntil: "networkidle2" });
  await page.waitForSelector("button[type=submit]:not([disabled])", { timeout: 15000 });
  await page.type("input[type=email]", email);
  await page.type("input[type=password]", password);
  await page.click("button[type=submit]");
}

/** Stand-in for the ML worker (which can't run in this sandbox): writes what pose/biomech/risk would write. */
export function simulateComplete(videoId, { score = true } = {}) {
  sql(`update videos set processing_status='completed', progress_pct=100, duration_seconds=4, fps=30, resolution_width=1280, resolution_height=720, detection_rate=0.93, processing_completed_at=now() where id='${videoId}'`);
  const metric = (name, plane, conf, expr) =>
    `insert into biomechanical_metrics(video_id,frame_number,metric_name,metric_value,plane,confidence) select '${videoId}', g, '${name}', ${expr}, '${plane}', '${conf}' from generate_series(0,119) g;`;
  sql(
    metric("knee_flexion_angle_left", "sagittal", "validated", "95 + 40*sin(g/12.0)") +
    metric("knee_flexion_angle_right", "sagittal", "validated", "92.4 + 38*sin(g/12.0)") +
    metric("trunk_lean_angle", "sagittal", "validated", "20 + 6.3*sin(g/9.0)") +
    metric("knee_valgus_deviation_left", "frontal", "qualitative", "7.77 + 3*sin(g/7.0)"),
  );
  if (score) {
    const athlete = sql(`select athlete_id from videos where id='${videoId}'`);
    sql(`insert into risk_scores(video_id,athlete_id,overall_score,risk_category,score_breakdown) values ('${videoId}','${athlete}',42.6,'moderate','{"anomaly":{"points":24,"max":70},"symmetry":{"points":8.5,"max":15},"prior_injury":{"points":10,"max":15}}')`);
    const rid = sql(`select id from risk_scores where video_id='${videoId}'`);
    sql(`insert into recommendations(risk_score_id,category,title,description,priority) values ('${rid}','mobility','Add ankle mobility work','Limited dorsiflexion can shift load to the knee. Include calf and ankle mobility before sessions.',1),('${rid}','strengthening','Single-leg strength','Build single-leg control to even out left and right.',2)`);
  }
}
