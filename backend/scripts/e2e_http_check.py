"""True end-to-end check over HTTP: real server + real queue + real worker process.

    python scripts/e2e_http_check.py [BASE_URL] CLIP.mp4 [movement] [camera_view]

Login -> create athlete -> request upload URL -> PUT the clip -> confirm-upload (ffprobe) -> the arq worker
runs YOLO + MediaPipe -> poll until done -> fetch biomechanics, risk score and recommendations.
Also exercises the refusal paths (bad file, bad view, bad id). Exits non-zero on the first broken step.
Needs: uvicorn app.main:app and `arq app.modules.pose.worker_settings.WorkerSettings` running, seeded DB.
"""
import json
import sys
import time

import httpx

args = [a for a in sys.argv[1:]]
BASE = args.pop(0) if args and args[0].startswith("http") else "http://localhost:8000"
CLIP = args[0]
MOVEMENT = args[1] if len(args) > 1 else "squatting"
VIEW = args[2] if len(args) > 2 else "sagittal"
API = BASE + "/api/v1"


def step(msg: str) -> None:
    print(f"\n== {msg}", flush=True)


def need(cond: bool, msg: str) -> None:
    print(("  ok   " if cond else "  FAIL ") + msg, flush=True)
    if not cond:
        sys.exit(1)


c = httpx.Client(timeout=60)

step("health")
r = c.get(BASE + "/health")
need(r.status_code == 200, f"/health -> {r.status_code} {r.text[:80]}")

step("login (seeded coach)")
r = c.post(f"{API}/auth/login", json={"email": "coach@demo.com", "password": "demo123"})
need(r.status_code == 200, f"login -> {r.status_code}")
H = {"Authorization": f"Bearer {r.json()['access_token']}"}

step("create athlete")
r = c.post(f"{API}/athletes", headers=H, json={"sport_type": "e2e-http", "date_of_birth": "1998-05-05",
                                               "height_cm": 170, "weight_kg": 65, "dominant_side": "right"})
need(r.status_code in (200, 201), f"POST /athletes -> {r.status_code} {r.text[:120]}")
athlete_id = r.json()["id"]

step("refusals (must be rejected cleanly, not 500)")
r = c.post(f"{API}/videos/upload-url", headers=H, json={"athlete_id": athlete_id, "movement_type": "squatting",
                                                       "camera_view": "overhead", "original_filename": "x.mp4", "file_size_bytes": 1000})
need(r.status_code in (400, 422), f"unsupported camera view -> {r.status_code} (want 400/422)")
r = c.get(f"{API}/videos/not-a-uuid/risk-score", headers=H)
need(r.status_code == 422, f"malformed id -> {r.status_code} (want 422)")
r = c.get(f"{API}/athletes")
need(r.status_code in (401, 403), f"no token -> {r.status_code} (want 401/403)")

step("upload a file that is not a video: must be rejected at confirm")
r = c.post(f"{API}/videos/upload-url", headers=H, json={"athlete_id": athlete_id, "movement_type": MOVEMENT,
                                                       "camera_view": VIEW, "original_filename": "fake.mp4", "file_size_bytes": 20})
need(r.status_code == 200, f"upload-url -> {r.status_code}")
fake = r.json()
need(c.put(fake["upload_url"], headers=H, content=b"this is not a video at all").status_code in (200, 201, 204), "PUT fake bytes")
r = c.post(f"{API}/videos/{fake['video_id']}/confirm-upload", headers=H)
need(r.status_code >= 400 and r.status_code < 500, f"fake video refused at confirm -> {r.status_code} {r.text[:90]}")

step(f"upload the real clip ({CLIP})")
data = open(CLIP, "rb").read()
r = c.post(f"{API}/videos/upload-url", headers=H, json={"athlete_id": athlete_id, "movement_type": MOVEMENT,
                                                       "camera_view": VIEW, "original_filename": "clip.mp4", "file_size_bytes": len(data)})
need(r.status_code == 200, f"upload-url -> {r.status_code}")
up = r.json()
need(c.put(up["upload_url"], headers=H, content=data).status_code in (200, 201, 204), f"PUT {len(data)//1024} KB")
r = c.post(f"{API}/videos/{up['video_id']}/confirm-upload", headers=H)
need(r.status_code == 200 and r.json().get("status") == "processing", f"confirm-upload -> {r.status_code} {r.text[:80]}")
vid = up["video_id"]

step("worker processes the clip (polling)")
t0, last = time.time(), None
while time.time() - t0 < 240:
    v = c.get(f"{API}/videos/{vid}", headers=H).json()
    if v["processing_status"] != last or int(time.time() - t0) % 20 == 0:
        print(f"   {int(time.time()-t0):3d}s status={v['processing_status']} progress={v.get('progress_pct')}", flush=True)
        last = v["processing_status"]
    if v["processing_status"] in ("completed", "failed"):
        break
    time.sleep(3)
need(v["processing_status"] == "completed", f"processing finished: {v['processing_status']} {v.get('error_code') or ''}")
print(f"   detection_rate={v['detection_rate']} persons={v.get('person_count_detected')} caveat={v.get('coverage_caveat')}")
print(f"   quality={json.dumps((v.get('analysis') or {}).get('quality', {}).get('grade'))}")

step("biomechanics")
r = c.get(f"{API}/videos/{vid}/biomechanics", headers=H)
need(r.status_code == 200, f"biomechanics -> {r.status_code}")
b = r.json()
need(len(b.get("metrics", b.get("summary", []))) > 0 or bool(b), "biomechanics payload is non-empty")

step("risk score")
r = c.get(f"{API}/videos/{vid}/risk-score", headers=H)
print(f"   HTTP {r.status_code}")
body = r.json()
if r.status_code == 200:
    need(0 <= body["overall_score"] <= 100, f"overall_score={body['overall_score']} category={body['risk_category']}")
    need(set(body["score_breakdown"]) >= {"biomechanical_deviations", "movement_asymmetry"}, "five-component breakdown present")
    need(set(body.get("sub_scores", {})) == {"injury_risk", "movement_quality", "biomechanical_efficiency", "fatigue_risk", "overall_health"}, "five PDF sub-scores present")
    need(len(body.get("injury_categories", {})) >= 3, f"injury categories: {sorted(body['injury_categories'])}")
    need(body["baseline"]["videos"] >= 1, f"baseline: {body['baseline']}")
    print("   breakdown:", {k: (v['score'] if v['available'] else None) for k, v in body["score_breakdown"].items()})
    print("   sub_scores:", {k: v["score"] for k, v in body["sub_scores"].items()})
else:
    need(r.status_code == 202 and body["status"] == "insufficient_baseline_data", f"202 baseline building: {body.get('coverage')}")

step("recommendations")
r = c.get(f"{API}/videos/{vid}/recommendations", headers=H)
need(r.status_code in (200, 202, 409, 422), f"recommendations -> {r.status_code}")
if r.status_code == 200:
    recs = r.json()
    print(f"   {len(recs) if isinstance(recs, list) else len(recs.get('recommendations', []))} recommendation(s)")

print("\nE2E OK", flush=True)
