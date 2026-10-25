import pytest
import random
import string
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def random_email():
    return "".join(random.choices(string.ascii_lowercase, k=10)) + "@example.com"

def test_role_registration():
    roles = ["athlete", "coach", "physiotherapist", "sports_scientist"]
    for role in roles:
        email = random_email()
        pwd = "testpassword123"
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": pwd, "full_name": f"Test {role.title()}", "role": role}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == email
        assert data["role"] == role

def test_admin_registration_with_and_without_code():
    # Without code -> should fall back to athlete
    email1 = random_email()
    resp1 = client.post(
        "/api/v1/auth/register",
        json={"email": email1, "password": "password123", "full_name": "Fake Admin", "role": "administrator"}
    )
    assert resp1.status_code == 200
    assert resp1.json()["role"] == "athlete"

    # With valid admin_code -> should be granted administrator
    email2 = random_email()
    resp2 = client.post(
        "/api/v1/auth/register",
        json={
            "email": email2,
            "password": "password123",
            "full_name": "True Admin",
            "role": "administrator",
            "admin_code": settings.SECRET_KEY
        }
    )
    assert resp2.status_code == 200
    assert resp2.json()["role"] == "administrator"

def test_oauth_login():
    email = random_email()
    # 1. OAuth register/login as Coach
    resp = client.post(
        "/api/v1/auth/oauth/login",
        json={
            "provider": "google",
            "email": email,
            "full_name": "OAuth Coach",
            "role": "coach"
        }
    )
    assert resp.status_code == 200
    token_data = resp.json()
    assert "access_token" in token_data
    assert token_data["user"]["role"] == "coach"
    assert token_data["user"]["email"] == email

    # 2. Subsequent OAuth login with same email
    resp2 = client.post(
        "/api/v1/auth/oauth/login",
        json={
            "provider": "google",
            "email": email
        }
    )
    assert resp2.status_code == 200
    assert resp2.json()["user"]["role"] == "coach"

def test_user_profile_management():
    email = random_email()
    pwd = "oldpassword123"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pwd, "full_name": "Original Name", "role": "physiotherapist"}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": pwd}
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Get profile
    me_resp = client.get("/api/v1/users/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["full_name"] == "Original Name"

    # 2. Update profile
    update_resp = client.put(
        "/api/v1/users/me",
        json={
            "full_name": "Updated Name",
            "bio": "Specialist in ACL rehab",
            "phone_number": "+1234567890",
            "organization": "Sports Rehab Clinic",
            "specialization": "Lower Extremities"
        },
        headers=headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["full_name"] == "Updated Name"
    assert update_resp.json()["bio"] == "Specialist in ACL rehab"
    assert update_resp.json()["organization"] == "Sports Rehab Clinic"

    # 3. Change password - failure with incorrect current password
    pwd_fail = client.put(
        "/api/v1/users/me/password",
        json={"current_password": "wrongpassword", "new_password": "newpassword456"},
        headers=headers
    )
    assert pwd_fail.status_code == 400

    # 4. Change password - success
    pwd_succ = client.put(
        "/api/v1/users/me/password",
        json={"current_password": pwd, "new_password": "newpassword456"},
        headers=headers
    )
    assert pwd_succ.status_code == 200

    # 5. Login with new password
    new_login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "newpassword456"}
    )
    assert new_login.status_code == 200

def test_roles_metadata_endpoint():
    resp = client.get("/api/v1/users/roles")
    assert resp.status_code == 200
    roles = resp.json()
    role_keys = [r["key"] for r in roles]
    assert "athlete" in role_keys
    assert "coach" in role_keys
    assert "physiotherapist" in role_keys
    assert "sports_scientist" in role_keys
    assert "administrator" in role_keys

def test_admin_user_management():
    # Create admin
    admin_email = random_email()
    client.post(
        "/api/v1/auth/register",
        json={
            "email": admin_email,
            "password": "adminpassword",
            "full_name": "Super Admin",
            "role": "administrator",
            "admin_code": settings.SECRET_KEY
        }
    )
    admin_token = client.post(
        "/api/v1/auth/login",
        data={"username": admin_email, "password": "adminpassword"}
    ).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create target user
    user_email = random_email()
    user_resp = client.post(
        "/api/v1/auth/register",
        json={"email": user_email, "password": "userpassword", "full_name": "Target User", "role": "athlete"}
    )
    user_id = user_resp.json()["id"]

    # 1. Admin lists users
    list_resp = client.get("/api/v1/users/", headers=admin_headers)
    assert list_resp.status_code == 200
    assert any(u["id"] == user_id for u in list_resp.json())

    # 2. Admin promotes user to sports_scientist
    role_update = client.put(
        f"/api/v1/users/{user_id}/role",
        json={"role": "sports_scientist", "is_active": True},
        headers=admin_headers
    )
    assert role_update.status_code == 200
    assert role_update.json()["role"] == "sports_scientist"

def test_staff_athlete_assignment_lifecycle():
    # Create admin
    admin_email = random_email()
    client.post(
        "/api/v1/auth/register",
        json={
            "email": admin_email,
            "password": "adminpassword",
            "full_name": "System Admin",
            "role": "administrator",
            "admin_code": settings.SECRET_KEY
        }
    )
    admin_token = client.post(
        "/api/v1/auth/login",
        data={"username": admin_email, "password": "adminpassword"}
    ).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create Coach
    coach_email = random_email()
    coach_resp = client.post(
        "/api/v1/auth/register",
        json={"email": coach_email, "password": "coachpassword", "full_name": "Head Coach", "role": "coach"}
    )
    coach_id = coach_resp.json()["id"]
    coach_token = client.post(
        "/api/v1/auth/login",
        data={"username": coach_email, "password": "coachpassword"}
    ).json()["access_token"]
    coach_headers = {"Authorization": f"Bearer {coach_token}"}

    # Create Athlete and Profile
    athlete_email = random_email()
    client.post(
        "/api/v1/auth/register",
        json={"email": athlete_email, "password": "athletepassword", "full_name": "Pro Athlete", "role": "athlete"}
    )
    athlete_token = client.post(
        "/api/v1/auth/login",
        data={"username": athlete_email, "password": "athletepassword"}
    ).json()["access_token"]
    athlete_headers = {"Authorization": f"Bearer {athlete_token}"}

    prof_resp = client.post(
        "/api/v1/athletes/me",
        json={"sport_type": "Track & Field", "age": 21},
        headers=athlete_headers
    )
    athlete_profile_id = prof_resp.json()["id"]

    # Before assignment: Coach cannot access athlete
    resp_before = client.get(f"/api/v1/athletes/{athlete_profile_id}", headers=coach_headers)
    assert resp_before.status_code == 403

    # Admin assigns Coach to Athlete
    assign_resp = client.post(
        f"/api/v1/athletes/{athlete_profile_id}/assign?staff_id={coach_id}",
        headers=admin_headers
    )
    assert assign_resp.status_code == 200

    # After assignment: Coach can access athlete!
    resp_after = client.get(f"/api/v1/athletes/{athlete_profile_id}", headers=coach_headers)
    assert resp_after.status_code == 200
    assert resp_after.json()["sport_type"] == "Track & Field"

    # List assigned staff
    staff_list_resp = client.get(f"/api/v1/athletes/{athlete_profile_id}/staff", headers=coach_headers)
    assert staff_list_resp.status_code == 200
    assert any(s["id"] == coach_id for s in staff_list_resp.json())

    # Admin unassigns coach
    unassign_resp = client.delete(
        f"/api/v1/athletes/{athlete_profile_id}/assign/{coach_id}",
        headers=admin_headers
    )
    assert unassign_resp.status_code == 200

    # After unassign: Coach blocked again
    resp_blocked = client.get(f"/api/v1/athletes/{athlete_profile_id}", headers=coach_headers)
    assert resp_blocked.status_code == 403
