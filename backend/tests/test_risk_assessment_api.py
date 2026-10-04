"""End-to-end engine tests: synthetic motion -> real analysis pipeline -> Postgres -> HTTP API."""

import functools
import uuid
from datetime import date, timedelta

import numpy as np
import pytest
from sqlalchemy import insert, select

from app.config import settings
from app.modules.athletes.models import Athlete, InjuryHistory, TrainingLoadEntry
from app.modules.notifications.models import Notification
from app.modules.pose.processing import analyze_frames
from app.modules.recommendations.models import Recommendation
from app.modules.risk_scoring.models import AnomalyScore, RiskScore
from app.modules.risk_scoring.scoring import ENGINE_VERSION
from app.modules.users.models import User
from app.modules.video.models import BiomechanicalMetric, Video, VideoProcessingStatus
from tests.conftest import auth_header, register_and_login
from tests.synth import occlude_leg, run_frames, squat_frames

MIN = 10


async def _user(db, email):
    return await db.scalar(select(User).where(User.email == email))


async def _athlete(db, coach_id, user_id=None):
    a = Athlete(coach_id=coach_id, user_id=user_id, sport_type="football", date_of_birth=date(2001, 1, 1))
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


@functools.lru_cache(maxsize=None)
def _analysed(key, movement, view):
    """Memoised: the same synthetic clip is analysed once per test session, not once per test."""
    return analyze_frames(_FRAMES[key], movement, view, 30)


_FRAMES: dict = {}


async def _video(db, coach_id, athlete_id, frames, movement="squatting", view="sagittal", status=VideoProcessingStatus.completed):
    """Run frames through the REAL analysis pipeline and store exactly what the worker would."""
    key = id(frames) if not isinstance(frames, tuple) else frames
    key = (len(frames), frames[0]["world_landmarks"]["25"][0], frames[len(frames) // 2]["world_landmarks"]["25"][1],
           frames[len(frames) // 2]["world_landmarks"]["26"][1], movement, view)
    _FRAMES[key] = frames
    metrics, analysis = _analysed(key, movement, view)
    v = Video(athlete_id=athlete_id, uploaded_by=coach_id, movement_type=movement, storage_key="k.mp4",
              original_filename="k.mp4", camera_view=view, fps=30, processing_status=status, analysis=analysis)
    db.add(v)
    await db.commit()
    await db.refresh(v)
    if metrics:
        await db.execute(insert(BiomechanicalMetric), [
            {"video_id": v.id, "frame_number": m["frame_number"], "metric_name": m["name"],
             "metric_value": m["value"], "plane": m["plane"], "confidence": m["confidence"]} for m in metrics])
        await db.commit()
    return v


def _normal(seed):
    r = np.random.default_rng(seed)
    return squat_frames(n_reps=4, depth=float(r.normal(102, 6)), lean_top=float(r.normal(6, 1.5)),
                        lean_bottom=float(r.normal(36, 4)), noise_m=0.004, seed=seed)


async def _setup(client, db, n_baseline=MIN + 2):
    token = await register_and_login(client, "coach@t.com", "coach")
    coach = await _user(db, "coach@t.com")
    ath = await _athlete(db, coach.id)
    # The population must span several ATHLETES (settings.min_baseline_athletes): a baseline of one
    # athlete's clips is that athlete's personal envelope, not a population.
    pool = [ath] + [await _athlete(db, coach.id) for _ in range(settings.min_baseline_athletes - 1)]
    for i in range(n_baseline):
        await _video(db, coach.id, pool[i % len(pool)].id, _normal(100 + i))
    return token, coach, ath


async def _score(client, token, vid, **params):
    return await client.get(f"/api/v1/videos/{vid}/risk-score", headers=auth_header(token), params=params)


# ---------------------------------- the original bug ---------------------------------------

@pytest.mark.asyncio
async def test_a_lone_video_is_never_scored_against_itself(client, db_session):
    """REGRESSION. Before: 1 video = hundreds of per-frame 'samples' = baseline met = HTTP 200 with a
    meaningless ~35-50 score for ANY video (a textbook squat and a terrible one alike)."""
    token = await register_and_login(client, "coach@t.com", "coach")
    coach = await _user(db_session, "coach@t.com")
    ath = await _athlete(db_session, coach.id)
    v = await _video(db_session, coach.id, ath.id, squat_frames(depth=100))
    r = await _score(client, token, v.id)
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "insufficient_baseline_data"
    assert (body["have"], body["need"], body["unit"]) == (0, MIN, "videos")
    assert await db_session.scalar(select(RiskScore)) is None  # nothing fabricated and persisted


@pytest.mark.asyncio
async def test_the_scored_video_is_excluded_from_its_own_baseline(client, db_session):
    """MIN videos in total -> only MIN-1 OTHER videos -> still insufficient."""
    token, coach, ath = await _setup(client, db_session, n_baseline=MIN - 1)
    r = await _score(client, token, (await db_session.scalar(select(Video).limit(1))).id)
    assert r.status_code == 202 and r.json()["have"] == MIN - 2


# ---------------------------------- discrimination -----------------------------------------

@pytest.mark.asyncio
async def test_normal_squat_scores_low_and_shallow_leaning_squat_scores_much_higher(client, db_session):
    token, coach, ath = await _setup(client, db_session)
    good = await _video(db_session, coach.id, ath.id, _normal(900))
    bad = await _video(db_session, coach.id, ath.id,
                       squat_frames(n_reps=4, depth=45, lean_top=40, lean_bottom=62, noise_m=0.004, seed=77))

    g = (await _score(client, token, good.id))
    b = (await _score(client, token, bad.id))
    assert g.status_code == 200 and b.status_code == 200
    g, b = g.json(), b.json()

    assert g["risk_category"] == "low" and g["overall_score"] < 25
    assert b["overall_score"] > g["overall_score"] + 20
    assert b["risk_category"] in ("moderate", "high", "critical")
    dev = b["score_breakdown"]["biomechanical_deviations"]
    assert dev["score"] >= 70
    flagged = {f["feature"] for f in dev["detail"]["deviating_features"]}
    assert "knee_flexion_angle_left.p95" in flagged or "trunk_lean_angle.p95" in flagged
    assert b["sub_scores"]["movement_quality"]["score"] < g["sub_scores"]["movement_quality"]["score"]


@pytest.mark.asyncio
async def test_response_contract_has_everything_the_spec_asks_for(client, db_session):
    token, coach, ath = await _setup(client, db_session)
    v = await _video(db_session, coach.id, ath.id, _normal(901))
    j = (await _score(client, token, v.id)).json()

    assert set(j["score_breakdown"]) == {"biomechanical_deviations", "historical_injury_factors", "movement_asymmetry",
                                         "training_load_indicators", "fatigue_indicators"}
    assert j["score_breakdown"]["biomechanical_deviations"]["weight"] == 0.35
    assert set(j["sub_scores"]) == {"injury_risk", "movement_quality", "biomechanical_efficiency", "fatigue_risk", "overall_health"}
    assert set(j["injury_categories"]) == {"acl", "hamstring", "ankle_sprain", "shoulder", "lower_back", "overuse"}
    assert j["engine_version"] == ENGINE_VERSION and j["baseline"]["videos"] >= MIN
    assert j["quality"]["grade"] in ("good", "fair", "poor") and j["reliability"] == j["quality"]["grade"]
    assert "not a trained injury-prediction model" in j["methodology_note"].lower()
    assert 0 <= j["data_completeness"] <= 1
    # no training log in this athlete: honestly reported as unavailable, not as zero risk
    assert "training_load_indicators" in j["missing_components"]
    assert j["score_breakdown"]["training_load_indicators"]["available"] is False
    # every frontend-rendered component has points/max
    assert all("points" in c and "max" in c for c in j["score_breakdown"].values())
    # video-level anomaly row is persisted (analytics anomaly_distribution was always empty before)
    assert await db_session.scalar(select(AnomalyScore).where(AnomalyScore.video_id == uuid.UUID(v.id))) is not None


@pytest.mark.asyncio
async def test_history_load_and_fatigue_flow_into_the_composite(client, db_session):
    token, coach, ath = await _setup(client, db_session)
    db_session.add(InjuryHistory(athlete_id=ath.id, injury_type="ACL tear", body_part="Left knee",
                                 injury_date=date.today() - timedelta(days=200), severity="severe"))
    # 40 days of history, with a recent load spike -> ACWR well above 1.5
    for d in range(40, 7, -1):
        if d % 3 == 0:
            db_session.add(TrainingLoadEntry(athlete_id=ath.id, entry_date=date.today() - timedelta(days=d),
                                             duration_minutes=60, rpe=5, session_load=300))
    for d in range(0, 7):
        db_session.add(TrainingLoadEntry(athlete_id=ath.id, entry_date=date.today() - timedelta(days=d),
                                         duration_minutes=90, rpe=9, session_load=810))
    await db_session.commit()

    v = await _video(db_session, coach.id, ath.id, _normal(902))
    j = (await _score(client, token, v.id)).json()
    bd = j["score_breakdown"]
    assert bd["historical_injury_factors"]["score"] == 100  # unresolved knee injury, relevant to squatting
    assert bd["training_load_indicators"]["available"] and bd["training_load_indicators"]["detail"]["acwr"] > 1.5
    assert bd["fatigue_indicators"]["detail"]["rpe_trend"]["rpe_trend"] > 2
    assert j["data_completeness"] == 1.0 and not j["missing_components"]
    assert j["injury_categories"]["acl"]["level"] in ("moderate", "high", "critical")
    assert j["injury_categories"]["overuse"]["level"] in ("high", "critical")

    recs = (await client.get(f"/api/v1/videos/{v.id}/recommendations", headers=auth_header(token))).json()
    titles = " | ".join(r["title"] for r in recs)
    assert "physiotherapist" in titles.lower()          # unresolved injury
    assert "load" in titles.lower()                     # ACWR spike
    assert [r["priority"] for r in recs] == sorted(r["priority"] for r in recs)


@pytest.mark.asyncio
async def test_one_occluded_leg_makes_asymmetry_unavailable_and_says_why(client, db_session):
    token, coach, ath = await _setup(client, db_session)
    v = await _video(db_session, coach.id, ath.id, occlude_leg(_normal(903), "right"))
    j = (await _score(client, token, v.id))
    # right-leg metrics were dropped, so this video lacks features the baseline has -> not comparable
    # on those features, and must not crash or fabricate a left/right comparison
    assert j.status_code in (200, 202)
    if j.status_code == 200:
        assert j.json()["score_breakdown"]["movement_asymmetry"]["available"] is False
        assert j.json()["quality"]["grade"] != "good"


@pytest.mark.asyncio
async def test_real_asymmetry_is_scored(client, db_session):
    token, coach, ath = await _setup(client, db_session)
    v = await _video(db_session, coach.id, ath.id,
                     squat_frames(n_reps=4, depth=102, depth_r=70, noise_m=0.004, seed=5))
    j = (await _score(client, token, v.id)).json()
    asym = j["score_breakdown"]["movement_asymmetry"]
    assert asym["available"] and asym["detail"]["lsi_pct"] == pytest.approx(70, abs=6)
    assert asym["score"] > 70


# ---------------------------------- other conditions ---------------------------------------

@pytest.mark.asyncio
async def test_frontal_view_gets_a_clear_422_with_guidance(client, db_session):
    token = await register_and_login(client, "coach@t.com", "coach")
    coach = await _user(db_session, "coach@t.com")
    ath = await _athlete(db_session, coach.id)
    v = await _video(db_session, coach.id, ath.id, squat_frames(), view="frontal")
    r = await _score(client, token, v.id)
    assert r.status_code == 422
    err = r.json()
    msg = str(err)
    assert "NO_VALIDATED_METRICS" in msg and "side-on" in msg


@pytest.mark.asyncio
async def test_running_videos_are_scored_against_running_baselines_only(client, db_session):
    token, coach, ath = await _setup(client, db_session)  # baseline is all squats
    v = await _video(db_session, coach.id, ath.id, run_frames(seconds=6), movement="running")
    r = await _score(client, token, v.id)
    assert r.status_code == 202 and r.json()["movement_type"] == "running" and r.json()["have"] == 0


@pytest.mark.asyncio
async def test_every_movement_type_can_be_scored_end_to_end(client, db_session):
    token = await register_and_login(client, "coach@t.com", "coach")
    coach = await _user(db_session, "coach@t.com")
    ath = await _athlete(db_session, coach.id)
    pool = [ath] + [await _athlete(db_session, coach.id) for _ in range(settings.min_baseline_athletes - 1)]
    for mv in ("running", "sprinting", "cutting"):
        for i in range(MIN + 1):
            await _video(db_session, coach.id, pool[i % len(pool)].id, run_frames(cadence_spm=165 + i, seconds=5, noise_m=0.004, seed=i), movement=mv)
        v = await _video(db_session, coach.id, ath.id, run_frames(cadence_spm=170, seconds=5, noise_m=0.004, seed=50), movement=mv)
        r = await _score(client, token, v.id)
        assert r.status_code == 200, (mv, r.text)
        assert r.json()["baseline"]["movement_type"] == mv


@pytest.mark.asyncio
async def test_video_not_ready_is_409(client, db_session):
    token = await register_and_login(client, "coach@t.com", "coach")
    coach = await _user(db_session, "coach@t.com")
    ath = await _athlete(db_session, coach.id)
    v = await _video(db_session, coach.id, ath.id, squat_frames(), status=VideoProcessingStatus.processing)
    assert (await _score(client, token, v.id)).status_code == 409


# ---------------------------------- caching, versions, permissions -------------------------

@pytest.mark.asyncio
async def test_cached_until_recompute_and_stale_engine_versions_self_heal(client, db_session):
    token, coach, ath = await _setup(client, db_session)
    v = await _video(db_session, coach.id, ath.id, _normal(904))
    first = (await _score(client, token, v.id)).json()
    assert (await _score(client, token, v.id)).json() == first                      # cached
    assert (await _score(client, token, v.id, recompute="true")).json()["overall_score"] == first["overall_score"]

    row = await db_session.scalar(select(RiskScore))
    row.assessment = {**row.assessment, "engine_version": "1.0"}                    # score from an older engine
    row.overall_score = 99.0
    await db_session.commit()
    healed = (await _score(client, token, v.id)).json()
    assert healed["engine_version"] == ENGINE_VERSION and healed["overall_score"] != 99.0
    assert await db_session.scalar(select(RiskScore).where(RiskScore.id == row.id)) is not None


@pytest.mark.asyncio
async def test_legacy_rows_without_an_assessment_are_recomputed(client, db_session):
    token, coach, ath = await _setup(client, db_session)
    v = await _video(db_session, coach.id, ath.id, _normal(905))
    db_session.add(RiskScore(video_id=uuid.UUID(v.id), athlete_id=uuid.UUID(ath.id), overall_score=44.7,
                             risk_category="moderate",
                             score_breakdown={"movement_anomaly": {"points": 31.3, "max": 70}}))
    await db_session.commit()
    j = (await _score(client, token, v.id)).json()
    assert j["engine_version"] == ENGINE_VERSION and "biomechanical_deviations" in j["score_breakdown"]


@pytest.mark.asyncio
async def test_recompute_replaces_recommendations_and_anomaly_row(client, db_session):
    token, coach, ath = await _setup(client, db_session)
    v = await _video(db_session, coach.id, ath.id, _normal(906))
    for _ in range(3):
        assert (await _score(client, token, v.id, recompute="true")).status_code == 200
    rs = await db_session.scalar(select(RiskScore))
    n_recs = len((await db_session.scalars(select(Recommendation).where(Recommendation.risk_score_id == rs.id))).all())
    n_anom = len((await db_session.scalars(select(AnomalyScore).where(AnomalyScore.video_id == uuid.UUID(v.id)))).all())
    assert 1 <= n_recs <= 8 and n_anom == 1                                          # no accumulation


@pytest.mark.asyncio
async def test_other_coaches_cannot_read_an_athletes_score(client, db_session):
    token, coach, ath = await _setup(client, db_session)
    v = await _video(db_session, coach.id, ath.id, _normal(907))
    other = await register_and_login(client, "other@t.com", "coach")
    assert (await _score(client, other, v.id)).status_code == 403
    assert (await client.get(f"/api/v1/videos/{v.id}/recommendations", headers=auth_header(other))).status_code == 403


# ---------------------------------- notifications ------------------------------------------

async def _make_high(db, coach, ath):
    db.add(InjuryHistory(athlete_id=ath.id, injury_type="ACL", body_part="knee",
                         injury_date=date.today() - timedelta(days=100), severity="severe"))
    await db.commit()
    return await _video(db, coach.id, ath.id,
                        squat_frames(n_reps=4, depth=40, depth_r=28, lean_top=45, lean_bottom=65, noise_m=0.004, seed=9))


@pytest.mark.asyncio
async def test_alerts_go_only_to_people_entitled_to_the_athlete_and_never_duplicate(client, db_session):
    token, coach, ath = await _setup(client, db_session)
    await register_and_login(client, "other@t.com", "coach")
    await register_and_login(client, "physio@t.com", "physiotherapist")
    other, physio = await _user(db_session, "other@t.com"), await _user(db_session, "physio@t.com")

    v = await _make_high(db_session, coach, ath)
    j = (await _score(client, token, v.id)).json()
    assert j["risk_category"] in ("high", "critical")

    rows = (await db_session.scalars(select(Notification))).all()
    recipients = {str(n.user_id) for n in rows}
    assert str(coach.id) in recipients and str(physio.id) in recipients
    assert str(other.id) not in recipients, "another coach's athlete alert leaked to an unrelated coach"

    n_before = len(rows)
    for _ in range(2):
        await _score(client, token, v.id, recompute="true")
    assert len((await db_session.scalars(select(Notification))).all()) == n_before, "recompute re-sent the alert"


@pytest.mark.asyncio
async def test_poor_quality_alerts_are_marked_provisional(client, db_session):
    token, coach, ath = await _setup(client, db_session)
    v = await _make_high(db_session, coach, ath)
    v.analysis = {**v.analysis, "quality": {**v.analysis["quality"], "grade": "poor"}}
    await db_session.commit()
    await _score(client, token, v.id)
    n = (await db_session.scalars(select(Notification).limit(1))).first()
    assert n is not None and "provisional" in n.title.lower()


# ---------------------------------- analytics & baselines ----------------------------------

@pytest.mark.asyncio
async def test_trends_report_the_real_movement_type_and_direction(client, db_session):
    token, coach, ath = await _setup(client, db_session)
    for s in range(5):
        v = await _video(db_session, coach.id, ath.id, _normal(950 + s))
        assert (await _score(client, token, v.id)).status_code == 200
    t = (await client.get(f"/api/v1/analytics/athletes/{ath.id}/trends", headers=auth_header(token))).json()
    assert t["total"] == 5 and {p["movement_type"] for p in t["points"]} == {"squatting"}  # was always "unknown"
    assert t["trend"]["direction"] in ("improving", "stable", "worsening")
    assert "not a trained injury-prediction model" in t["methodology_note"].lower()


@pytest.mark.asyncio
async def test_report_exports_use_the_new_components(client, db_session):
    token, coach, ath = await _setup(client, db_session)
    v = await _video(db_session, coach.id, ath.id, _normal(960))
    await _score(client, token, v.id)
    pdf = await client.get(f"/api/v1/videos/{v.id}/report.pdf", headers=auth_header(token))
    xlsx = await client.get(f"/api/v1/videos/{v.id}/report.xlsx", headers=auth_header(token))
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    assert xlsx.status_code == 200
    import io
    from openpyxl import load_workbook
    ws = load_workbook(io.BytesIO(xlsx.content)).active
    keys = [r[0].value for r in ws.iter_rows()]
    assert "biomechanical_deviations" in keys and "movement_anomaly" not in keys


@pytest.mark.asyncio
async def test_baseline_recompute_counts_videos_not_frames(client, db_session):
    await _setup(client, db_session, n_baseline=MIN + 1)
    admin = await register_and_login(client, "admin@t.com", "admin")
    r = await client.post("/api/v1/baselines/recompute", json={"movement_type": "squatting"}, headers=auth_header(admin))
    assert r.status_code == 200, r.text
    d = r.json()["details"]
    assert d["videos"] == MIN + 1
    knee = next(f for f in d["features"] if f["feature"] == "knee_flexion_angle_left.p95")
    assert knee["sample_size"] == MIN + 1 and knee["sufficient"] and 90 < knee["mean"] < 115
