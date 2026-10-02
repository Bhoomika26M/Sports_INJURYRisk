import { BASE, API, results, sql, launch, newPage, step, sleep, text, waitText, clickText, path, shot, login, simulateComplete } from "./lib.mjs";

const setVal = (page, sel, val) => page.$eval(sel, (el, v) => {
  const proto = el.tagName === "SELECT" ? HTMLSelectElement.prototype : el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, "value").set.call(el, v);
  el.dispatchEvent(new Event("input", { bubbles: true })); el.dispatchEvent(new Event("change", { bubbles: true }));
}, val);
const first = (q) => sql(q).split("\n")[0];

// ---- seed states the (unrunnable) worker would produce
const base = first("select id from videos where original_filename='good.mp4' order by created_at desc limit 1");
if (!base) throw new Error("run part1 first");
const athlete = sql(`select athlete_id from videos where id='${base}'`), uploader = sql(`select uploaded_by from videos where id='${base}'`);
const mk = (status, extra = "") => first(`insert into videos(athlete_id,uploaded_by,movement_type,storage_key,original_filename,camera_view,processing_status,progress_pct${extra ? "," + extra.split("|")[0] : ""}) values ('${athlete}','${uploader}','landing','x/seed.mp4','seed-${status}.mp4','sagittal','${status}',${status === "failed" ? 0 : 100}${extra ? "," + extra.split("|")[1] : ""}) returning id`);
sql("delete from videos where original_filename like 'seed-%'");
const failedId = mk("failed", "error_code,error_message|'no_person_detected','No person detected in any frame.'");
const noScoreId = mk("completed"); simulateComplete(noScoreId, { score: false });
const coachId = first("select id from users where email='coach@demo.com'");
sql("delete from notifications where title like 'E2E%'");
sql(`insert into notifications(user_id,type,title,body,related_athlete_id) values ('${coachId}','analysis_ready','E2E first alert','Something happened.','${athlete}'),('${coachId}','analysis_ready','E2E second alert','Another thing.',null)`);

let browser = await launch(); let page = await newPage(browser);
const mocks = {};
await page.setRequestInterception(true);
page.on("request", (r) => {
  const k = Object.keys(mocks).find((k) => r.url().includes(k));
  if (!k) return r.continue();
  r.respond({ status: mocks[k].status, contentType: "application/json", headers: { "access-control-allow-origin": BASE, "access-control-allow-credentials": "true" }, body: JSON.stringify(mocks[k].body) });
});
console.log("\n=== COACH: STATES, LISTS, REPORTS ===");
await login(page, "coach@demo.com");
await page.waitForFunction(() => location.pathname.startsWith("/dashboard"), { timeout: 20000 });
await step("coach dashboard loads with athletes list and stats", async () => { await waitText(page, "Your team at a glance"); await waitText(page, "Athletes"); });
await shot(page, "10-dashboard-coach");

await step("videos library lists all videos with status badges", async () => {
  await page.goto(BASE + "/videos", { waitUntil: "networkidle2" }); await waitText(page, "Needs attention");
  const rows = await page.$$eval("ul li a.row", (a) => a.length);
  if (rows < 3) throw new Error("only " + rows + " rows"); return rows + " rows";
});
await shot(page, "11-videos-list");
await step("'Needs attention' filter narrows to the failed video", async () => {
  await clickText(page, "button[role=tab]", "Needs attention"); await sleep(300);
  const rows = await page.$$eval("ul li a.row", (a) => a.length);
  if (rows < 1) throw new Error("no failed rows"); return rows + " row(s)";
});
await step("failed video explains what went wrong in plain words", async () => {
  await page.goto(`${BASE}/videos/${failedId}`, { waitUntil: "networkidle2" });
  await waitText(page, "couldn't find a person"); await waitText(page, "Try another video");
});
await shot(page, "12-video-failed");
await step("results with no baseline [risk-score response MOCKED to the backend's 202 shape]: measurements + clear notice", async () => {
  mocks[`/videos/${noScoreId}/risk-score`] = { status: 202, body: { status: "insufficient_baseline_data", metric_name: "knee_flexion_angle_left", have: 3, need: 10 } };
  await page.goto(`${BASE}/videos/${noScoreId}/results`, { waitUntil: "networkidle2" });
  await waitText(page, "Key numbers", 15000);
  const t = await text(page);
  if (!/3 of 10 so far/.test(t)) throw new Error("no explanatory notice. Page: " + t.replace(/\n+/g, " | ").slice(120, 400));
  if (/Something went wrong/.test(t)) throw new Error("error state shown");
  delete mocks[`/videos/${noScoreId}/risk-score`];
});
await shot(page, "13-results-no-baseline");
await step("reports page lists finished analyses with download buttons", async () => {
  await page.goto(BASE + "/reports", { waitUntil: "networkidle2" }); await waitText(page, "Download any finished analysis");
  const pdfs = await page.$$eval("button", (b) => b.filter((x) => x.innerText.trim() === "PDF").length);
  if (pdfs < 2) throw new Error(pdfs + " PDF buttons"); return pdfs + " reports";
});
await step("downloading a report that isn't scored yet shows a friendly toast [report.pdf response MOCKED to backend's 404 shape]", async () => {
  mocks[`/videos/${noScoreId}/report.pdf`] = { status: 404, body: { detail: { error: { code: "NOT_FOUND", message: "Video not yet scored" } } } };
  const idx = await page.$$eval("ul li", (lis, id) => lis.findIndex((l) => l.querySelector(`a[href="/videos/${id}/results"]`)), noScoreId);
  await page.evaluate((i) => [...document.querySelectorAll("ul li")][i].querySelectorAll("button")[0].click(), idx);
  await page.waitForSelector(".toast--error", { timeout: 8000 });
  const msg = await page.$eval(".toast--error", (e) => e.innerText);
  if (!/isn't ready/.test(msg)) throw new Error("toast said: " + msg); delete mocks[`/videos/${noScoreId}/report.pdf`]; return msg.slice(0, 70);
});

console.log("\n=== COACH: ATHLETES (add/edit/injury/training were 404s before) ===");
await step("athletes list renders rows", async () => {
  await page.goto(BASE + "/athletes", { waitUntil: "networkidle2" }); await waitText(page, "Add athlete");
  const rows = await page.$$eval("ul li a.row", (a) => a.length); if (rows < 3) throw new Error(rows + " rows");
});
await step("create athlete → lands on detail with fallback name", async () => {
  await clickText(page, "a", "Add athlete"); await page.waitForSelector("select");
  await setVal(page, "select", "volleyball"); await setVal(page, "input[type=date]", "2001-05-17");
  await clickText(page, "button[type=submit]", "Create athlete");
  await page.waitForFunction(() => /^\/athletes\/[0-9a-f-]{36}$/.test(location.pathname), { timeout: 15000 });
  await waitText(page, "Volleyball athlete");
});
await step("add injury via modal → appears in list", async () => {
  await clickText(page, "button[role=tab]", "Injuries"); await clickText(page, "button", "Add injury");
  await page.waitForSelector("dialog[open]");
  await page.type("dialog input[placeholder='e.g. Ankle sprain']", "Hamstring strain");
  await page.type("dialog input[placeholder='e.g. Left ankle']", "Right hamstring");
  await setVal(page, "dialog input[type=date]", "2026-03-10");
  await clickText(page, "dialog button[type=submit]", "Add injury");
  await waitText(page, "Hamstring strain"); await page.waitForFunction(() => !document.querySelector("dialog[open]"));
});
await step("injury recovery before injury date is blocked with a clear message", async () => {
  await clickText(page, "button", "Add injury"); await page.waitForSelector("dialog[open]");
  await page.type("dialog input[placeholder='e.g. Ankle sprain']", "X"); await page.type("dialog input[placeholder='e.g. Left ankle']", "Y");
  await page.$$eval("dialog input[type=date]", (els) => { const set = (el, v) => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(el, v); el.dispatchEvent(new Event("input", { bubbles: true })); }; set(els[0], "2026-04-10"); set(els[1], "2026-04-01"); });
  // native min= validation blocks submit first; either that or our own message is acceptable
  await page.evaluate(() => document.querySelector("dialog button[type=submit]").click()); await sleep(500);
  const open = await page.$("dialog[open]"); if (!open) throw new Error("invalid dates were accepted");
  await clickText(page, "dialog button", "Cancel");
});
await step("log training session via modal → appears with load", async () => {
  await clickText(page, "button[role=tab]", "Training"); await clickText(page, "button", "Log session"); await page.waitForSelector("dialog[open]");
  await setVal(page, "dialog input[type=number]", "60"); await setVal(page, "dialog select", "7");
  await clickText(page, "dialog button[type=submit]", "Log session");
  await waitText(page, "Load 420"); await page.waitForFunction(() => !document.querySelector("dialog[open]"), { timeout: 8000 });
});
await step("edit profile via modal persists", async () => {
  await clickText(page, "button", "Edit"); await page.waitForSelector("dialog[open]");
  await setVal(page, "dialog input[placeholder='e.g. Guard']", "Setter");
  await clickText(page, "dialog button[type=submit]", "Save changes");
  await waitText(page, "Setter"); await waitText(page, "Profile updated"); await page.waitForFunction(() => !document.querySelector("dialog[open]"), { timeout: 8000 });
});
await shot(page, "14-athlete-detail");
await step("deleting an injury asks for confirmation first", async () => {
  await clickText(page, "button[role=tab]", "Injuries");
  await page.evaluate(() => document.querySelector("button[aria-label^='Remove Hamstring']").click());
  await waitText(page, "Remove this injury?"); await clickText(page, "dialog button", "Remove");
  await page.waitForFunction(() => !document.body.innerText.includes("Hamstring strain"), { timeout: 8000 });
});
await step("coach does NOT see 'Delete athlete' (the API is admin-only, so offering it would 403)", async () => {
  const has = await page.$("button[aria-label='Delete athlete']");
  if (has) throw new Error("delete button shown to coach");
});

console.log("\n=== NOTIFICATIONS ===");
await step("notifications: unread badge, mark one read, mark all read", async () => {
  await page.goto(BASE + "/notifications", { waitUntil: "networkidle2" }); await waitText(page, "E2E first alert");
  const badge = async () => page.$eval("a[href='/notifications']", (a) => a.getAttribute("aria-label"));
  const before = await badge(); if (!/unread/.test(before)) throw new Error("no unread badge: " + before);
  await page.evaluate(() => document.querySelector("button[aria-label^='Mark \"E2E first']").click());
  await page.waitForFunction(() => !document.querySelector("button[aria-label^='Mark \"E2E first']"), { timeout: 8000 });
  await clickText(page, "button", "Mark all as read"); await waitText(page, "all caught up");
  await page.waitForFunction(() => document.querySelector("a[href='/notifications']").getAttribute("aria-label") === "Notifications", { timeout: 8000 });
  return "badge: " + before + " → cleared";
});
await shot(page, "15-notifications");

console.log("\n=== SIGN OUT ===");
await step("sign out ends the session for real (not just a client-side cookie wipe)", async () => {
  await page.goto(BASE + "/dashboard", { waitUntil: "networkidle2" }); await page.waitForSelector("button[aria-label='Account menu']");
  await page.click("button[aria-label='Account menu']"); await clickText(page, "button[role=menuitem]", "Sign out");
  await page.waitForFunction(() => location.pathname === "/login", { timeout: 10000 });
  await page.goto(BASE + "/dashboard", { waitUntil: "networkidle2" });
  if (!path(page).startsWith("/login")) throw new Error("could still reach /dashboard: " + path(page));
  const status = await page.evaluate((api) => fetch(api + "/auth/refresh", { method: "POST", credentials: "include" }).then((r) => r.status), API);
  if (status !== 401) throw new Error("refresh still works after logout: " + status);
  return "/dashboard → /login, refresh → 401";
});
await browser.close();

console.log("\n=== ALL FIVE ROLES ===");
const roles = [["athlete@demo.com", "athlete"], ["physio@demo.com", "physio"], ["scientist@demo.com", "scientist"], ["admin@demo.com", "admin"]];
for (const [email, key] of roles) {
  browser = await launch(); page = await newPage(browser);
  await login(page, email);
  await step(`${key}: dashboard loads without an error state`, async () => {
    await page.waitForFunction((k) => location.pathname === "/dashboard/" + k, { timeout: 20000 }, key);
    await sleep(2500); const t = await text(page);
    if (/Something went wrong|Couldn't load/.test(t)) throw new Error("error state: " + t.replace(/\n+/g, " | ").slice(150, 330));
    return t.replace(/\n+/g, " | ").split("| New analysis")[1]?.slice(0, 70) ?? "";
  });
  await shot(page, `20-dashboard-${key}`);
  if (key === "athlete") {
    await step("athlete: nav says 'Profile', /athletes jumps to own profile, no manage buttons", async () => {
      const nav = await page.$$eval("aside a", (a) => a.map((x) => x.innerText.trim()));
      if (!nav.includes("Profile")) throw new Error("nav: " + nav);
      await page.goto(BASE + "/athletes", { waitUntil: "networkidle2" });
      await page.waitForFunction(() => /^\/athletes\/[0-9a-f-]{36}$/.test(location.pathname), { timeout: 10000 });
      await waitText(page, "Analyze video");
      const btns = await page.$$eval("button, a", (b) => b.map((x) => x.innerText.trim()));
      if (btns.includes("Edit") || btns.includes("Add athlete")) throw new Error("manage controls visible to athlete");
    });
  }
  if (key === "admin") {
    await step("admin: can delete an athlete — with confirmation — and returns to the list", async () => {
      await page.goto(BASE + "/athletes", { waitUntil: "networkidle2" });
      const countBefore = await page.$$eval("a.row", (a) => a.filter((x) => x.innerText.includes("Volleyball athlete")).length);
      if (countBefore !== 1) throw new Error("expected exactly 1 test athlete, found " + countBefore);
      await page.evaluate(() => [...document.querySelectorAll("a.row")].find((a) => a.innerText.includes("Volleyball athlete"))?.click());
      await page.waitForFunction(() => /^\/athletes\/[0-9a-f-]{36}$/.test(location.pathname), { timeout: 10000 });
      await page.waitForSelector("button[aria-label='Delete athlete']");
      await page.click("button[aria-label='Delete athlete']");
      await waitText(page, "Delete this athlete?"); await clickText(page, "dialog button", "Delete athlete");
      await page.waitForFunction(() => location.pathname === "/athletes", { timeout: 10000 });
      await sleep(800); if ((await text(page)).includes("Volleyball athlete")) throw new Error("athlete still listed");
    });
  }
  if (key === "scientist") {
    await step("scientist: movement picker switches analytics without error", async () => {
      await page.select("select", "landing"); await sleep(1500);
      if (/Something went wrong/.test(await text(page))) throw new Error("error after switching");
      const t = await text(page); if (/valgus|deviation/i.test(t)) throw new Error("qualitative metric leaked into baselines");
    });
  }
  await browser.close();
}

console.log("\n=== REGISTER ===");
browser = await launch(); page = await newPage(browser);
const email = `e2e${Date.now()}@test.com`;
await page.goto(BASE + "/register", { waitUntil: "networkidle2" });
await step("register offers no self-service Admin role", async () => {
  const roles = await page.$$eval("input[name=role]", (i) => i.map((x) => x.value));
  if (roles.includes("admin")) throw new Error("admin offered"); return roles.join(", ");
});
await step("register → auto sign-in → athlete with no profile sees an explanation", async () => {
  await page.waitForSelector("button[type=submit]:not([disabled])");
  await page.type("input[name=name]", "E2E Tester"); await page.type("input[name=email]", email); await page.type("input[name=password]", "longenough1");
  await page.$eval("input[name=role][value=athlete]", (e) => e.click());
  await page.click("button[type=submit]");
  await page.waitForFunction(() => location.pathname === "/dashboard/athlete", { timeout: 20000 });
  await waitText(page, "isn't set up yet");
});
await shot(page, "21-athlete-no-profile");
await step("upload page for a profile-less athlete explains instead of showing an empty form", async () => {
  await page.goto(BASE + "/videos/upload", { waitUntil: "networkidle2" }); await waitText(page, "isn't set up yet");
});
await browser.close();
browser = await launch(); page = await newPage(browser);
await page.goto(BASE + "/register", { waitUntil: "networkidle2" });
await step("registering an existing email shows a field-level message", async () => {
  await page.waitForSelector("button[type=submit]:not([disabled])");
  await page.type("input[name=name]", "Dup"); await page.type("input[name=email]", email); await page.type("input[name=password]", "longenough1");
  await page.click("button[type=submit]"); await waitText(page, "already an account", 10000);
});
await step("wrong password shows a clear inline error and stays on /login", async () => {
  await page.goto(BASE + "/login", { waitUntil: "networkidle2" }); await page.waitForSelector("button[type=submit]:not([disabled])");
  await page.type("input[type=email]", "coach@demo.com"); await page.type("input[type=password]", "nope-nope");
  await page.click("button[type=submit]"); await page.waitForSelector("[role=alert]", { timeout: 8000 });
  const msg = await page.$eval("[role=alert]", (e) => e.innerText); if (path(page) !== "/login") throw new Error("left /login"); return msg.slice(0, 60);
});
await browser.close();

console.log("\n=== MOBILE (390x844) ===");
browser = await launch(); page = await newPage(browser, { mobile: true });
await login(page, "coach@demo.com");
await page.waitForFunction(() => location.pathname.startsWith("/dashboard"), { timeout: 20000 }); await sleep(2000);
await step("mobile: bottom nav visible, sidebar hidden (old app had NO nav here)", async () => {
  const v = await page.evaluate(() => ({ bottom: getComputedStyle(document.querySelector(".bottom-nav")).display, side: getComputedStyle(document.querySelector(".sidebar")).display }));
  if (v.bottom === "none" || v.side !== "none") throw new Error(JSON.stringify(v)); return `bottom-nav=${v.bottom}, sidebar=${v.side}`;
});
for (const [name, url] of [["dashboard", "/dashboard/coach"], ["videos", "/videos"], ["upload", "/videos/upload"], ["athletes", "/athletes"]]) {
  await step(`mobile: ${name} has no horizontal scroll`, async () => {
    await page.goto(BASE + url, { waitUntil: "networkidle2" }); await sleep(1200);
    const w = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth }));
    if (w.sw > w.iw + 1) throw new Error(`scrollWidth ${w.sw} > ${w.iw}`); return `${w.sw}px`;
  });
  await shot(page, `30-mobile-${name}`);
}
await browser.close();

const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} passed`);
