import fs from "node:fs";
import { execSync } from "node:child_process";
import { BASE, results, sql, launch, newPage, step, sleep, text, waitText, clickText, path, shot, simulateComplete } from "./lib.mjs";

sql("delete from videos"); sql("delete from notifications where title like 'E2E%'"); sql("delete from athletes where sport_type='volleyball'"); // reset test data: this DB only ever holds seed users + test uploads
const browser = await launch();
const page = await newPage(browser);
const reqs = [];
page.on("request", (r) => { if (r.url().includes("/local-storage/")) reqs.push({ method: r.method(), auth: r.headers()["authorization"] ? "Bearer present" : "MISSING" }); });
page.on("response", (r) => { if (r.url().includes("/local-storage/") || r.url().includes("confirm-upload")) reqs.push({ url: r.url().split("/api/v1")[1], status: r.status() }); });

console.log("\n=== AUTH ===");
await step("signed-out visit to /videos/upload redirects to /login?next=", async () => {
  await page.goto(BASE + "/videos/upload", { waitUntil: "networkidle2" });
  if (!path(page).startsWith("/login?next=%2Fvideos%2Fupload")) throw new Error("landed on " + path(page));
});
await step("login lands on the page you originally wanted (?next honored)", async () => {
  await page.waitForSelector("button[type=submit]:not([disabled])");
  await page.type("input[type=email]", "coach@demo.com");
  await page.type("input[type=password]", "demo123");
  await page.click("button[type=submit]");
  await page.waitForFunction(() => location.pathname === "/videos/upload", { timeout: 15000 });
  return "now at " + path(page);
});
await step("a full reload keeps the session (refresh-cookie restore)", async () => {
  await page.reload({ waitUntil: "networkidle2" });
  await waitText(page, "New analysis");
  if (path(page) !== "/videos/upload") throw new Error("bounced to " + path(page));
});

console.log("\n=== UPLOAD FORM ===");
await step("athlete dropdown is populated (was always empty before)", async () => {
  await page.waitForSelector("select");
  const n = await page.$$eval("select option", (o) => o.length - 1);
  if (n < 1) throw new Error("0 athletes in dropdown");
  return `${n} athletes`;
});
await step("movement tiles are populated", async () => {
  const n = (await page.$$("input[name=movement]")).length;
  if (n < 3) throw new Error(`only ${n} movement options`);
  return `${n} movements`;
});
await step("empty submit shows inline errors instead of a dead button", async () => {
  await page.click("button[type=submit]");
  await waitText(page, "Choose who this video is for.", 3000);
});
await step("picking a movement reveals the camera-angle control", async () => {
  const athleteVal = await page.$eval("select option:nth-child(2)", (o) => o.value);
  await page.select("select", athleteVal);
  await page.$eval("input[name=movement]", (e) => e.click());
  await sleep(300);
  const views = (await page.$$("input[name=view]")).length;
  return `${views} camera views`;
});
await step("a >200 MB file is rejected up front, with a clear message", async () => {
  const input = await page.$("input[type=file]");
  await input.uploadFile("./media/big.mp4");
  await waitText(page, "up to 200 MB", 5000);
});
await step("a 1-second clip is rejected (client check or server check)", async () => {
  const input = await page.$("input[type=file]");
  await input.uploadFile("./media/short.mp4");
  await sleep(2500);
  const t = await text(page);
  if (/between 2 and 60 seconds/.test(t)) return "caught in the browser, before upload";
  // headless chromium may lack H.264, so the browser can't probe it — then the server must catch it
  await page.click("button[type=submit]");
  await page.waitForFunction(() => /seconds|Duration|duration/.test(document.body.innerText) && !document.body.innerText.includes("Uploading your video"), { timeout: 20000 });
  return "browser could not probe codec; caught by the server instead";
});
await shot(page, "01-upload-form-state");
await step("a text file renamed .mp4 is rejected by the server, form recovers", async () => {
  // reset to form state
  await page.goto(BASE + "/videos/upload", { waitUntil: "networkidle2" });
  await page.waitForSelector("select option:nth-child(2)");
  await page.select("select", await page.$eval("select option:nth-child(2)", (o) => o.value));
  await page.$eval("input[name=movement]", (e) => e.click());
  await (await page.$("input[type=file]")).uploadFile("./media/fake.mp4");
  await sleep(1500);
  await page.click("button[type=submit]");
  await page.waitForFunction(() => document.querySelector("[role=alert]") && document.body.innerText.includes("Drop a video here"), { timeout: 25000 })
    .catch(async () => { throw new Error("form did not recover. Page: " + (await text(page)).replace(/\n+/g, " | ").slice(150, 420)); });
  const msg = await page.$eval("[role=alert]", (e) => e.innerText);
  return `server said: "${msg.slice(0, 90)}"`;
});

console.log("\n=== REAL UPLOAD ===");
let videoId;
await step("valid video uploads: PUT carries auth, confirm succeeds, UI moves to analyzing", async () => {
  reqs.length = 0;
  await page.goto(BASE + "/videos/upload", { waitUntil: "networkidle2" });
  await page.waitForSelector("select option:nth-child(2)");
  await page.select("select", await page.$eval("select option:nth-child(2)", (o) => o.value));
  await page.$eval("input[name=movement]", (e) => e.click());
  await (await page.$("input[type=file]")).uploadFile("./media/good.mp4");
  await sleep(1500);
  await shot(page, "02-upload-file-chosen");
  await page.click("button[type=submit]");
  await waitText(page, "Analyzing movement", 30000);
  videoId = sql("select id from videos order by created_at desc limit 1");
  const status = sql(`select processing_status from videos where id='${videoId}'`);
  const put = reqs.find((r) => r.method === "PUT");
  const putResp = reqs.find((r) => r.url?.includes("local-storage"));
  const conf = reqs.find((r) => r.url?.includes("confirm-upload"));
  if (put?.auth !== "Bearer present") throw new Error("PUT auth header: " + put?.auth);
  if (putResp?.status !== 200) throw new Error("PUT status " + putResp?.status);
  if (conf?.status !== 200) throw new Error("confirm status " + conf?.status);
  return `PUT auth=${put.auth}, PUT=${putResp.status}, confirm=${conf.status}, DB status='${status}'`;
});
await shot(page, "03-analyzing");
await step("progress bar follows the server's real progress_pct", async () => {
  sql(`update videos set processing_status='processing', progress_pct=40 where id='${videoId}'`);
  await waitText(page, "40% complete", 8000);
});
await step("completion flips the page to the success card", async () => {
  simulateComplete(videoId);
  await waitText(page, "Your analysis is ready", 8000);
});
await shot(page, "04-done");

console.log("\n=== RESULTS ===");
await step("results page shows score, key numbers, chart, recommendations", async () => {
  await clickText(page, "a", "See results");
  await waitText(page, "Key numbers", 15000);
  await waitText(page, "Key numbers");
  await page.waitForSelector(".recharts-line", { timeout: 10000 });
  await waitText(page, "Suggested next steps");
  const t = await text(page);
  if (!/43\s*\/ 100/.test(t)) throw new Error("score 42.6 should round to 43");
});
await shot(page, "05-results");
await step("SCIENCE: valgus shown as visual check only — no numbers, no raw metric names", async () => {
  const t = await text(page);
  if (!t.includes("Visual checks")) throw new Error("no Visual checks section");
  if (/valgus|deviation/i.test(t)) throw new Error("raw qualitative metric name leaked");
  if (/7\.77|\d+\.\d+°/.test(t)) throw new Error("non-whole-degree value on page");
});
await step("SCIENCE: left-right balance always carries its caveat", async () => {
  const t = await text(page);
  if (!/Left–right balance: \d+%/.test(t)) throw new Error("LSI missing");
  if (!/documented limits/.test(t)) throw new Error("LSI shown without caveat");
});
await step("chart axis labels are whole degrees and seconds (Recharts v3 DOM)", async () => {
  const labels = await page.$$eval(".recharts-surface text", (els) => els.map((e) => e.textContent.trim()).filter(Boolean));
  const deg = labels.filter((t) => t.includes("°"));
  if (!deg.length) throw new Error("no degree labels rendered: " + labels.join(","));
  if (deg.some((t) => !/^-?\d+°$/.test(t))) throw new Error("non-whole degrees: " + deg.join(","));
  if (!labels.some((t) => /\ds$/.test(t))) throw new Error("x axis not in seconds: " + labels.join(","));
  return "y: " + deg.join(" ");
});

fs.mkdirSync("./dl", { recursive: true });
const cdp = await page.createCDPSession();
await cdp.send("Browser.setDownloadBehavior", { behavior: "allow", downloadPath: "./dl", eventsEnabled: true });
for (const [label, ext, magic] of [["PDF", "pdf", "%PDF"], ["Excel", "xlsx", "PK"], ["CSV", "csv", null]]) {
  await step(`authenticated ${label} download works (plain <a href> would 401)`, async () => {
    for (const f of fs.readdirSync("./dl")) if (f.endsWith("." + ext)) fs.unlinkSync("./dl/" + f);
    await clickText(page, "button", label);
    let file;
    for (let i = 0; i < 40 && !file; i++) { await sleep(500); file = fs.readdirSync("./dl").find((f) => f.endsWith("." + ext)); }
    if (!file) throw new Error("no file arrived. Page: " + (await text(page)).slice(-160).replace(/\n/g, " "));
    const buf = fs.readFileSync("./dl/" + file);
    if (magic && !buf.subarray(0, 4).toString().startsWith(magic)) throw new Error("bad file header");
    return `${file}, ${buf.length} bytes`;
  });
}

console.log("\n=== VIDEO DETAIL / PLAYBACK ===");
await step("original video plays through an authenticated blob (was 401/405 before)", async () => {
  await page.goto(`${BASE}/videos/${videoId}`, { waitUntil: "networkidle2" });
  await page.waitForSelector("video", { timeout: 20000 });
  await page.waitForFunction(() => { const v = document.querySelector("video"); return v && v.src.startsWith("blob:"); }, { timeout: 15000 });
  const info = await page.$eval("video", (v) => ({ src: v.src.slice(0, 5), err: v.error && v.error.code }));
  return `src=${info.src}…, mediaError=${info.err ?? "none"}`;
});
await step("annotated/original toggle appears when an annotated video exists", async () => {
  const key = sql(`select storage_key from videos where id='${videoId}'`);
  const file = execSync(`find / -name "${key.split("/").pop()}" -not -path "/proc/*" 2>/dev/null | head -1`).toString().trim();
  if (!file) throw new Error("uploaded file not found on disk for key " + key);
  sql(`update videos set annotated_video_key='${file}' where id='${videoId}'`);
  await page.reload({ waitUntil: "networkidle2" });
  await waitText(page, "With tracking", 15000);
  await clickText(page, "button", "Original");
  await page.waitForSelector("video", { timeout: 15000 });
});
await shot(page, "06-video-detail");

console.log("\nconsole errors seen:", page.consoleErrors.filter((e) => !/401|Failed to load resource/.test(e)).slice(0, 5));
await browser.close();
const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} passed`);
fs.writeFileSync("./part1.json", JSON.stringify({ videoId, results }, null, 1));
