"""
Athlete management endpoint tests – one test per access-control scenario.

Roles exercised:
  - athlete        → can only see/edit own record
  - coach          → only athletes in their assignments
  - physiotherapist → same as coach (assignment-based)
  - sports_scientist → all athletes
  - admin          → all athletes + admin endpoints

All tests use the SQLite in-memory DB injected via conftest.py.
"""
import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.assignment import CoachAthleteAssignment
from app.models.athlete import Athlete
from app.models.enums import BiologicalSex, DominantLeg, UserRole
from app.models.user import User

BASE = "/api/v1"
REGISTER = f"{BASE}/auth/register"
LOGIN = f"{BASE}/auth/login"
ATHLETES = f"{BASE}/athletes"
ADMIN_USERS = f"{BASE}/admin/users"
ADMIN_ASSIGN = f"{BASE}/admin/assignments"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _login(client: AsyncClient, email: str, password: str = "Pass1234") -> str:
    r = await client.post(LOGIN, json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _seed_user(db: AsyncSession, email: str, role: UserRole, password: str = "Pass1234") -> User:
    u = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=f"{role.value} User",
        role=role,
        is_active=True,
        is_verified=True,
    )
    db.add(u)
    await db.flush()
    return u


async def _seed_athlete_profile(db: AsyncSession, user_id: uuid.UUID) -> Athlete:
    a = Athlete(
        user_id=user_id,
        date_of_birth=date(1995, 6, 15),
        biological_sex=BiologicalSex.MALE,
        height_cm=180,
        weight_kg=75,
        dominant_leg=DominantLeg.RIGHT,
        primary_sport="Soccer",
        competitive_level="collegiate",
    )
    db.add(a)
    await db.flush()
    return a


_ATHLETE_PAYLOAD = {
    "date_of_birth": "1995-06-15",
    "biological_sex": "male",
    "height_cm": "175.5",
    "weight_kg": "72.0",
    "dominant_leg": "right",
    "primary_sport": "Basketball",
    "competitive_level": "collegiate",
}


# ===========================================================================
# Athlete CRUD Tests
# ===========================================================================

# ---------------------------------------------------------------------------
# POST /athletes – athlete creates own profile
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_athlete_creates_own_profile(client: AsyncClient):
    await client.post(REGISTER, json={"email": "ath_new@t.com", "password": "Pass1234", "full_name": "Ath New"})
    token = await _login(client, "ath_new@t.com")
    resp = await client.post(ATHLETES, headers={"Authorization": f"Bearer {token}"}, json=_ATHLETE_PAYLOAD)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["primary_sport"] == "Basketball"


# ---------------------------------------------------------------------------
# Validation: age < 10 → 422
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_athlete_age_too_young(client: AsyncClient):
    await client.post(REGISTER, json={"email": "young@t.com", "password": "Pass1234", "full_name": "Young"})
    token = await _login(client, "young@t.com")
    payload = {**_ATHLETE_PAYLOAD, "date_of_birth": "2024-01-01"}  # 2-year-old
    resp = await client.post(ATHLETES, headers={"Authorization": f"Bearer {token}"}, json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Validation: negative height → 422
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_athlete_negative_height(client: AsyncClient):
    await client.post(REGISTER, json={"email": "negheight@t.com", "password": "Pass1234", "full_name": "NegH"})
    token = await _login(client, "negheight@t.com")
    payload = {**_ATHLETE_PAYLOAD, "height_cm": "-10"}
    resp = await client.post(ATHLETES, headers={"Authorization": f"Bearer {token}"}, json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /athletes – athlete sees only own record
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_athlete_sees_only_own_record(client: AsyncClient, db_session: AsyncSession):
    u1 = await _seed_user(db_session, "own1@t.com", UserRole.ATHLETE)
    u2 = await _seed_user(db_session, "own2@t.com", UserRole.ATHLETE)
    await _seed_athlete_profile(db_session, u1.id)
    await _seed_athlete_profile(db_session, u2.id)

    token = await _login(client, "own1@t.com")
    resp = await client.get(ATHLETES, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    # Athlete only gets their own
    for item in body["items"]:
        assert item["user_id"] == str(u1.id)


# ---------------------------------------------------------------------------
# GET /athletes/{id} – athlete cannot view another's record
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_athlete_cannot_view_other_athlete(client: AsyncClient, db_session: AsyncSession):
    u1 = await _seed_user(db_session, "a1view@t.com", UserRole.ATHLETE)
    u2 = await _seed_user(db_session, "a2view@t.com", UserRole.ATHLETE)
    a2 = await _seed_athlete_profile(db_session, u2.id)

    token = await _login(client, "a1view@t.com")
    resp = await client.get(f"{ATHLETES}/{a2.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Coach: can only see assigned athletes
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_coach_sees_only_assigned_athletes(client: AsyncClient, db_session: AsyncSession):
    coach = await _seed_user(db_session, "coach1@t.com", UserRole.COACH)
    ath_assigned = await _seed_user(db_session, "assigned_ath@t.com", UserRole.ATHLETE)
    ath_other = await _seed_user(db_session, "other_ath@t.com", UserRole.ATHLETE)
    ath_profile_assigned = await _seed_athlete_profile(db_session, ath_assigned.id)
    await _seed_athlete_profile(db_session, ath_other.id)

    # Create assignment
    db_session.add(CoachAthleteAssignment(
        coach_id=coach.id,
        athlete_id=ath_profile_assigned.id,
        assignment_role="head_coach",
        is_active=True,
    ))
    await db_session.flush()

    token = await _login(client, "coach1@t.com")
    resp = await client.get(ATHLETES, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert str(ath_profile_assigned.id) in ids
    assert all(i == str(ath_profile_assigned.id) for i in ids), "Coach should only see assigned athletes"


# ---------------------------------------------------------------------------
# Coach: cannot view an unassigned athlete
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_coach_forbidden_for_unassigned_athlete(client: AsyncClient, db_session: AsyncSession):
    coach = await _seed_user(db_session, "coach_unassigned@t.com", UserRole.COACH)
    ath = await _seed_user(db_session, "stranger_ath@t.com", UserRole.ATHLETE)
    stranger_profile = await _seed_athlete_profile(db_session, ath.id)

    token = await _login(client, "coach_unassigned@t.com")
    resp = await client.get(f"{ATHLETES}/{stranger_profile.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Physiotherapist: same assignment-based access as coach
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_physio_sees_only_assigned(client: AsyncClient, db_session: AsyncSession):
    physio = await _seed_user(db_session, "physio1@t.com", UserRole.PHYSIOTHERAPIST)
    ath = await _seed_user(db_session, "physio_ath@t.com", UserRole.ATHLETE)
    ath_profile = await _seed_athlete_profile(db_session, ath.id)
    db_session.add(CoachAthleteAssignment(
        coach_id=physio.id,
        athlete_id=ath_profile.id,
        assignment_role="lead_physio",
        is_active=True,
    ))
    await db_session.flush()

    token = await _login(client, "physio1@t.com")
    resp = await client.get(f"{ATHLETES}/{ath_profile.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Sports Scientist: sees all athletes
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sports_scientist_sees_all(client: AsyncClient, db_session: AsyncSession):
    scientist = await _seed_user(db_session, "sci1@t.com", UserRole.SPORTS_SCIENTIST)
    ath_a = await _seed_user(db_session, "sci_ath_a@t.com", UserRole.ATHLETE)
    ath_b = await _seed_user(db_session, "sci_ath_b@t.com", UserRole.ATHLETE)
    prof_a = await _seed_athlete_profile(db_session, ath_a.id)
    prof_b = await _seed_athlete_profile(db_session, ath_b.id)

    token = await _login(client, "sci1@t.com")
    resp = await client.get(ATHLETES, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert str(prof_a.id) in ids
    assert str(prof_b.id) in ids


# ---------------------------------------------------------------------------
# Admin: sees all athletes
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_sees_all_athletes(client: AsyncClient, db_session: AsyncSession):
    admin = await _seed_user(db_session, "admin_all@t.com", UserRole.ADMIN)
    ath = await _seed_user(db_session, "admin_ath@t.com", UserRole.ATHLETE)
    prof = await _seed_athlete_profile(db_session, ath.id)

    token = await _login(client, "admin_all@t.com")
    resp = await client.get(f"{ATHLETES}/{prof.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Pagination and search
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_athlete_list_search(client: AsyncClient, db_session: AsyncSession):
    sci = await _seed_user(db_session, "sci_search@t.com", UserRole.SPORTS_SCIENTIST)
    u = await _seed_user(db_session, "search_ath@t.com", UserRole.ATHLETE)
    a = Athlete(
        user_id=u.id,
        date_of_birth=date(1998, 3, 10),
        biological_sex=BiologicalSex.FEMALE,
        height_cm=165,
        weight_kg=60,
        dominant_leg=DominantLeg.RIGHT,
        primary_sport="Tennis",
        competitive_level="collegiate",
    )
    db_session.add(a)
    await db_session.flush()

    token = await _login(client, "sci_search@t.com")
    resp = await client.get(f"{ATHLETES}?search=Tennis", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    sports = [i["primary_sport"] for i in resp.json()["items"]]
    assert all(s == "Tennis" for s in sports)


# ===========================================================================
# Sub-resource Tests
# ===========================================================================

# ---------------------------------------------------------------------------
# POST /athletes/{id}/injuries – athlete cannot self-report
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_athlete_cannot_self_report_injury(client: AsyncClient, db_session: AsyncSession):
    u = await _seed_user(db_session, "self_inj@t.com", UserRole.ATHLETE)
    prof = await _seed_athlete_profile(db_session, u.id)
    token = await _login(client, "self_inj@t.com")
    resp = await client.post(
        f"{ATHLETES}/{prof.id}/injuries",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "injury_type": "acl_tear",
            "anatomical_side": "left",
            "injury_date": "2025-01-10",
        },
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /athletes/{id}/injuries – physio can record injury for assigned athlete
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_physio_can_record_injury(client: AsyncClient, db_session: AsyncSession):
    physio = await _seed_user(db_session, "physio_inj@t.com", UserRole.PHYSIOTHERAPIST)
    ath = await _seed_user(db_session, "inj_ath@t.com", UserRole.ATHLETE)
    prof = await _seed_athlete_profile(db_session, ath.id)
    db_session.add(CoachAthleteAssignment(
        coach_id=physio.id, athlete_id=prof.id, assignment_role="lead_physio", is_active=True
    ))
    await db_session.flush()

    token = await _login(client, "physio_inj@t.com")
    resp = await client.post(
        f"{ATHLETES}/{prof.id}/injuries",
        headers={"Authorization": f"Bearer {token}"},
        json={"injury_type": "ankle_sprain", "anatomical_side": "right", "injury_date": "2025-03-01"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["injury_type"] == "ankle_sprain"


# ---------------------------------------------------------------------------
# POST /athletes/{id}/assessments – athlete gets 403
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_athlete_cannot_create_assessment(client: AsyncClient, db_session: AsyncSession):
    u = await _seed_user(db_session, "no_assess@t.com", UserRole.ATHLETE)
    prof = await _seed_athlete_profile(db_session, u.id)
    token = await _login(client, "no_assess@t.com")
    resp = await client.post(
        f"{ATHLETES}/{prof.id}/assessments",
        headers={"Authorization": f"Bearer {token}"},
        json={"assessment_date": "2025-04-01"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /athletes/{id}/training-profile – athlete can read own
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_athlete_reads_own_training_profile(client: AsyncClient, db_session: AsyncSession):
    u = await _seed_user(db_session, "tp_read@t.com", UserRole.ATHLETE)
    prof = await _seed_athlete_profile(db_session, u.id)
    token = await _login(client, "tp_read@t.com")

    # First POST a training profile as sports scientist
    sci = await _seed_user(db_session, "sci_tp@t.com", UserRole.SPORTS_SCIENTIST)
    sci_token = await _login(client, "sci_tp@t.com")
    await client.post(
        f"{ATHLETES}/{prof.id}/training-profile",
        headers={"Authorization": f"Bearer {sci_token}"},
        json={"weekly_training_hours": "12.5", "sessions_per_week": 5},
    )

    # Athlete reads their own training profile
    resp = await client.get(
        f"{ATHLETES}/{prof.id}/training-profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Admin: assign athlete to coach via POST /admin/assignments
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_assigns_athlete_to_coach(client: AsyncClient, db_session: AsyncSession):
    admin = await _seed_user(db_session, "admin_assign@t.com", UserRole.ADMIN)
    coach = await _seed_user(db_session, "coach_assign@t.com", UserRole.COACH)
    ath = await _seed_user(db_session, "ath_assign@t.com", UserRole.ATHLETE)
    prof = await _seed_athlete_profile(db_session, ath.id)

    admin_token = await _login(client, "admin_assign@t.com")
    resp = await client.post(
        ADMIN_ASSIGN,
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"coach_id": str(coach.id), "athlete_id": str(prof.id), "assignment_role": "head_coach"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["coach_id"] == str(coach.id)
    assert body["athlete_id"] == str(prof.id)
    assert body["is_active"] is True


# ---------------------------------------------------------------------------
# Non-admin cannot use /admin/assignments
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_coach_cannot_create_assignment(client: AsyncClient, db_session: AsyncSession):
    coach = await _seed_user(db_session, "coach_noassign@t.com", UserRole.COACH)
    token = await _login(client, "coach_noassign@t.com")
    resp = await client.post(
        ADMIN_ASSIGN,
        headers={"Authorization": f"Bearer {token}"},
        json={"coach_id": str(uuid.uuid4()), "athlete_id": str(uuid.uuid4()), "assignment_role": "head_coach"},
    )
    assert resp.status_code == 403
