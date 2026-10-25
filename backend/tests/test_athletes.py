import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base
import random
import string

client = TestClient(app)

def random_email():
    return "".join(random.choices(string.ascii_lowercase, k=10)) + "@example.com"

def create_user_and_get_token(role="athlete"):
    email = random_email()
    password = "securepassword"
    
    # We must mock or manipulate the DB to create non-athlete roles, 
    # since register route forces "athlete".
    # For now, let's just do it directly via DB for other roles.
    # But for "athlete", we can use the API.
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User", "role": "athlete"}
    )
    
    # If we need another role, we'd update it in the DB
    if role != "athlete":
        from app.db.session import SessionLocal
        from app.models.user import User
        db = SessionLocal()
        user = db.query(User).filter(User.email == email).first()
        user.role = role
        db.commit()
        db.close()
        
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password}
    )
    return login_resp.json()["access_token"]

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

def test_create_read_update_athlete_profile():
    token = create_user_and_get_token("athlete")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create profile
    profile_data = {
        "sport_type": "Basketball",
        "position": "Point Guard",
        "age": 25,
        "height_cm": 190.5,
        "weight_kg": 85.0,
        "injury_history": [{"date": "2023-01-01", "type": "Ankle sprain"}]
    }
    
    resp = client.post("/api/v1/athletes/me", json=profile_data, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["sport_type"] == "Basketball"
    
    # Read profile
    resp = client.get("/api/v1/athletes/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["height_cm"] == 190.5
    
    # Update profile
    update_data = {"weight_kg": 86.0}
    resp = client.put("/api/v1/athletes/me", json=update_data, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["weight_kg"] == 86.0

def test_staff_cannot_access_unassigned_athlete():
    # Athlete creates profile
    athlete_token = create_user_and_get_token("athlete")
    athlete_headers = {"Authorization": f"Bearer {athlete_token}"}
    resp = client.post("/api/v1/athletes/me", json={"sport_type": "Soccer", "age": 22}, headers=athlete_headers)
    athlete_profile_id = resp.json()["id"]
    
    # Coach tries to read
    coach_token = create_user_and_get_token("coach")
    coach_headers = {"Authorization": f"Bearer {coach_token}"}
    
    resp = client.get(f"/api/v1/athletes/{athlete_profile_id}", headers=coach_headers)
    assert resp.status_code == 403

def test_admin_can_access_any_athlete():
    # Athlete creates profile
    athlete_token = create_user_and_get_token("athlete")
    athlete_headers = {"Authorization": f"Bearer {athlete_token}"}
    resp = client.post("/api/v1/athletes/me", json={"sport_type": "Tennis", "age": 24}, headers=athlete_headers)
    athlete_profile_id = resp.json()["id"]
    
    # Admin tries to read
    admin_token = create_user_and_get_token("administrator")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    resp = client.get(f"/api/v1/athletes/{athlete_profile_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["sport_type"] == "Tennis"
