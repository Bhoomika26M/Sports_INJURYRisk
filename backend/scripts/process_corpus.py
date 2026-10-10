"""Upload + process the data/ and test-assets/ clips through the REAL HTTP API, then report, per movement,
how many baseline videos and athletes exist against the 10-video / 3-athlete floor.

    python backend/scripts/process_corpus.py [--base http://localhost:8000] [--email admin@demo.com] [--timeout 3600]

Needs the stack up (backend + arq worker + postgres + redis), a seeded DB, and the clips in data/ and test-assets/.
Labels (movement, camera view, expected outcome) come from the catalogs verify_data_videos.py and
verify_test_assets.py already use. Safe to re-run: a clip whose filename is already uploaded is not uploaded again,
so a re-run cannot inflate a baseline. Counts come from the backend's own baseline recompute, never from this script.
Also prints what the movement classifier said about every completed clip against its known label (false alarms, and what
Auto-detect would have done): the numbers to read before trusting the classifier's thresholds, which are synthetic-only.
Exit code: 0 if every clip ended as its catalog expects, 1 if not, 2 if a clip file is missing.
"""
import argparse
import os
import sys
import time

import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_data_videos as data_catalog  # noqa: E402  (EXPECTED_CATALOG, DATA_DIR)
import verify_test_assets as asset_catalog  # noqa: E402  (TEST_ASSETS, ASSETS_DIR)
from app.modules.biomechanics.classification import WARN_MIN_CONF  # noqa: E402  (verify_data_videos put backend/ on sys.path)

FLOOR_VIDEOS, FLOOR_ATHLETES = 10, 3
# Same recording in another container (frame-identical VP9 transcode). It is processed to prove the format works,
# then deleted, so one performance can never count twice toward a baseline.
TWINS = {"squat_demo.webm": "squat_sample.mp4"}


def plan() -> list[dict]:
    rows = [(os.path.join(data_catalog.DATA_DIR, c["file"]), c) for c in data_catalog.EXPECTED_CATALOG]
    rows += [(os.path.join(asset_catalog.ASSETS_DIR, c["file"]), c) for c in asset_catalog.TEST_ASSETS]
    return [
        {
            "path": path, "name": os.path.basename(path), "movement": c["movement"], "view": c["view"],
            "expect": c["expected_gate"], "reject_code": c.get("reject_code"),
            # One athlete per distinct source recording (the project's convention, see real_clip_validation.py).
            # Assumed from the clip descriptions, not verified: athlete counts are only as good as this.
            "athlete": "corpus:" + os.path.splitext(TWINS.get(os.path.basename(path), os.path.basename(path)))[0],
            "twin": os.path.basename(path) in TWINS,
        }
        for path, c in rows
    ]


def verdict(clip: dict, rec: dict) -> bool:
    if clip["expect"] == "pass":
        return rec["status"] == "completed"
    return rec["status"] == "failed" and (not clip["reject_code"] or rec.get("error_code") == clip["reject_code"])


def auto_outcome(clip: dict, c: dict | None) -> str:
    """What Auto-detect would do with this clip, judged against its known labels: 'right', 'WRONG' or 'declined'.
    The backend labels a clip only when both verdicts are known and the confidence reaches WARN_MIN_CONF."""
    if not c or "unknown" in (c["movement_type"], c["camera_view"]) or c["confidence"] < WARN_MIN_CONF:
        return "declined"
    return "right" if (c["movement_type"], c["camera_view"]) == (clip["movement"], clip["view"]) else "WRONG"


def classification_line(clip: dict, c: dict | None) -> str:
    """One row of the classifier-vs-known-label table. `agrees` is the backend's own verdict (True / False / None = unsure)."""
    if not c:
        return f"{clip['name']:<44} {clip['movement'] + '/' + clip['view']:<22} no classification (processed before it existed: reprocess)"
    ok = {True: "agrees", False: "DIFFERS", None: "unsure"}
    saw = f"{c['movement_type']}/{c['camera_view']}"
    return (f"{clip['name']:<44} {clip['movement'] + '/' + clip['view']:<22} {saw:<22} {c['confidence']:>4.2f}  "
            f"{ok[c['agrees']['movement_type']]:<8} {ok[c['agrees']['camera_view']]:<8} {auto_outcome(clip, c)}")


def baseline_counts(details: dict) -> tuple[int, int, bool]:
    """(videos, athletes, athletes_exact) from the backend's recompute payload. Athletes are counted per feature,
    so the figure is exact only when some feature is present in every baseline video; otherwise it is a floor."""
    videos, feats = details["videos"], details["features"]
    athletes = max((f["athletes"] for f in feats), default=0)
    return videos, athletes, (not videos) or any(f["sample_size"] == videos for f in feats)


def why(r: httpx.Response) -> str:
    try:
        e = r.json()["detail"]["error"]
        return f"{r.status_code} {e.get('code')}: {e.get('message')}"
    except Exception:  # noqa: BLE001 - any non-envelope body (HTML, pydantic list): show it raw
        return f"{r.status_code} {r.text[:100]}"


class Api:
    def __init__(self, base: str, email: str, password: str):
        self.base, self.email, self.password = base.rstrip("/"), email, password
        self.http = httpx.Client(timeout=120)
        self.login()

    def login(self) -> None:
        r = self.http.post(f"{self.base}/api/v1/auth/login", json={"email": self.email, "password": self.password})
        r.raise_for_status()
        self.http.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    def call(self, method: str, path: str, **kw) -> httpx.Response:
        url = path if path.startswith("http") else f"{self.base}/api/v1{path}"
        r = self.http.request(method, url, **kw)
        if r.status_code == 401:  # the 30-minute access token expired during a long run
            self.login()
            r = self.http.request(method, url, **kw)
        return r

    def listing(self, path: str) -> list[dict]:
        items, page = [], 1
        while True:
            body = self.call("GET", path, params={"page": page, "page_size": 100}).raise_for_status().json()
            items += body["items"]
            if not body["items"] or len(items) >= body["total"]:
                return items
            page += 1


def upload(api: Api, clip: dict, athlete_id: str) -> dict:
    """upload-url -> PUT -> confirm-upload. Returns the record; status 'refused' if the API said no."""
    rec = {"name": clip["name"], "status": "refused", "id": None}
    r = api.call("POST", "/videos/upload-url", json={
        "athlete_id": athlete_id, "movement_type": clip["movement"], "camera_view": clip["view"],
        "original_filename": clip["name"]})
    if r.status_code != 200:
        return {**rec, "note": f"upload-url {why(r)}"}
    ticket = r.json()
    with open(clip["path"], "rb") as f:
        put = api.call("PUT", ticket["upload_url"], content=f.read())
    if not put.is_success:
        api.call("DELETE", f"/videos/{ticket['video_id']}")  # don't leave a pending_upload record behind
        return {**rec, "note": f"storage PUT {why(put)}"}
    conf = api.call("POST", f"/videos/{ticket['video_id']}/confirm-upload")
    if conf.status_code != 200:  # the API deletes the record itself when it refuses a file
        return {**rec, "note": f"confirm-upload {why(conf)}"}
    return {**rec, "id": ticket["video_id"], "status": "processing"}


def wait(api: Api, recs: list[dict], timeout: float) -> None:
    pending = {r["id"]: r for r in recs if r["id"]}
    start = last_beat = time.time()
    while pending and time.time() - start < timeout:
        for vid, rec in list(pending.items()):
            v = api.call("GET", f"/videos/{vid}").raise_for_status().json()
            rec["status"] = v["processing_status"]
            if rec["status"] in ("completed", "failed"):
                quality = (v.get("analysis") or {}).get("quality") or {}
                rec.update(error_code=v["error_code"], detection_rate=v["detection_rate"], persons=v["person_count_detected"],
                           caveat=v["coverage_caveat"], grade=quality.get("grade"),
                           cls=(v.get("analysis") or {}).get("classification"))
                print(f"  {rec['name']}: {rec['status']} {rec['error_code'] or ''}", flush=True)
                del pending[vid]
        if pending and time.time() - last_beat > 30:
            last_beat = time.time()
            print(f"  ... waiting on {len(pending)} clip(s), {int(last_beat - start)}s elapsed", flush=True)
        if pending:
            time.sleep(5)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", default=os.environ.get("API_BASE", "http://localhost:8000"))
    ap.add_argument("--email", default=os.environ.get("CORPUS_EMAIL", "admin@demo.com"))
    ap.add_argument("--password", default=os.environ.get("CORPUS_PASSWORD", "demo123"))
    ap.add_argument("--timeout", type=float, default=3600, help="seconds to wait for the worker, in total")
    args = ap.parse_args()

    clips = plan()
    print(f"{'clip':<44} {'labels':<22} {'expect':<7} athlete")
    for c in clips:
        print(f"{c['name']:<44} {c['movement'] + '/' + c['view']:<22} {c['expect']:<7} {c['athlete']}{'  (twin: removed after processing)' if c['twin'] else ''}")
    missing = [c["path"] for c in clips if not os.path.exists(c["path"])]
    if missing:
        print("\nMissing clip files (nothing was uploaded):\n  " + "\n  ".join(missing))
        return 2

    api = Api(args.base, args.email, args.password)
    athletes = {a["position"]: a["id"] for a in api.listing("/athletes") if a.get("position")}
    videos = api.listing("/videos")  # newest first
    have = {v["original_filename"]: v for v in reversed(videos)}
    for c in clips:
        copies = sum(v["original_filename"] == c["name"] for v in videos)
        if copies > 1:
            print(f"WARNING: {c['name']} is on the server {copies} times; the baselines below count every copy.")

    print("\nUploading...")
    recs = []
    for c in clips:
        old = have.get(c["name"])
        if old and old["processing_status"] == "pending_upload":  # an earlier run died mid-upload
            api.call("DELETE", f"/videos/{old['id']}")
            old = None
        if old and (old["movement_type"], old["camera_view"]) != (c["movement"], c["view"]):
            rec = {"name": c["name"], "id": None, "status": "refused",
                   "note": f"already uploaded as {old['movement_type']}/{old['camera_view']}; delete that video and re-run"}
        elif old:
            rec = {"name": c["name"], "id": old["id"], "status": old["processing_status"], "note": "already uploaded"}
        else:
            if c["athlete"] not in athletes:
                r = api.call("POST", "/athletes", json={"sport_type": "mixed", "position": c["athlete"], "date_of_birth": "1995-01-01"})
                athletes[c["athlete"]] = r.raise_for_status().json()["id"]
            rec = upload(api, c, athletes[c["athlete"]])
        print(f"  {c['name']}: {rec['status']} {rec.get('note', '')}", flush=True)
        recs.append(rec)

    print("\nWaiting for the worker...")
    wait(api, recs, args.timeout)

    print("\nPer clip")
    print(f"{'clip':<44} {'result':<50} {'tracked':>7} {'validated':>9}  expected")
    ok_all = True
    for c, rec in zip(clips, recs):
        validated = ""
        if rec["status"] == "completed":
            validated = len(api.call("GET", f"/videos/{rec['id']}/biomechanics").raise_for_status().json()["summary"])
        ok = verdict(c, rec)
        ok_all &= ok
        result = rec["status"] + (f" {rec.get('error_code')}" if rec.get("error_code") else "") + (f" [{rec['note']}]" if rec["status"] == "refused" else "")
        tracked = f"{rec['detection_rate']:.0%}" if rec.get("detection_rate") is not None else ""
        print(f"{c['name']:<44} {result[:50]:<50} {tracked:>7} {validated!s:>9}  {c['expect']}{'' if ok else '  <-- MISMATCH'}")
        if c["twin"] and rec["id"]:
            api.call("DELETE", f"/videos/{rec['id']}")
            print(f"{'':<44} (twin of {TWINS[c['name']]}: deleted so it does not count twice)")

    done = [(c, rec) for c, rec in zip(clips, recs) if rec["status"] == "completed"]
    if done:
        print("\nClassifier vs the known labels. The labels above are known-right, so every DIFFERS is a false alarm and every WRONG a bad auto-label.")
        print(f"{'clip':<44} {'labelled':<22} {'classifier saw':<22} {'conf':>4}  {'movement':<8} {'view':<8} auto-detect")
        outcomes = {"right": 0, "WRONG": 0, "declined": 0}
        for c, rec in done:
            print(classification_line(c, rec.get("cls")))
            outcomes[auto_outcome(c, rec.get("cls"))] += 1
        alarms = sum(1 for _, rec in done if rec.get("cls") and False in rec["cls"]["agrees"].values())
        print(f"false alarms (the label would be flagged as wrong): {alarms} of {len(done)} completed clips")
        print(f"Auto-detect would label {outcomes['right']} right, {outcomes['WRONG']} WRONG, and decline {outcomes['declined']} (declined clips are safe: the user chooses).")

    print(f"\nBaselines vs floor ({FLOOR_VIDEOS} videos, {FLOOR_ATHLETES} athletes). Counted by the backend: completed, no coverage caveat, validated metrics.")
    print(f"{'movement':<12} {'videos':>8} {'athletes':>9}  status")
    for m in [t["code"] for t in api.call("GET", "/videos/movement-types").raise_for_status().json()]:
        r = api.call("POST", "/baselines/recompute", json={"movement_type": m})
        if r.status_code == 429:  # the backend debounces recompute to once a minute per movement
            time.sleep(61)
            r = api.call("POST", "/baselines/recompute", json={"movement_type": m})
        if r.status_code != 200:
            print(f"{m:<12} {'?':>8} {'?':>9}  could not recompute: {why(r)}")
            continue
        details = r.json()["details"]
        n_vid, n_ath, exact = baseline_counts(details)
        need_v, need_a = max(FLOOR_VIDEOS - n_vid, 0), max(FLOOR_ATHLETES - n_ath, 0)
        status = "meets floor" if not need_v and not need_a else f"building: needs {need_v} more video(s), {need_a} more athlete(s)"
        vids_txt, ath_txt = f"{n_vid}/{FLOOR_VIDEOS}", ("" if exact else ">=") + f"{n_ath}/{FLOOR_ATHLETES}"
        print(f"{m:<12} {vids_txt:>8} {ath_txt:>9}  {status}")
        if (details["need"], details["need_athletes"]) != (FLOOR_VIDEOS, FLOOR_ATHLETES):
            print(f"{'':<12} note: this backend's own gate is {details['need']} videos / {details['need_athletes']} athletes")
    print("\nAthlete = one per source recording, assumed from the clip descriptions (not verified).")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
