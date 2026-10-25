import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base
from google.oauth2 import id_token
import random
import string

client = TestClient(app)

def random_email():
    return "".join(random.choices(string.ascii_lowercase, k=10)) + "@example.com"

def test_athlete_register_and_login():
    email = random_email()
    password = "securepassword"
    
    # Register
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test Athlete", "role": "administrator"}
    )
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == email
    # Athlete accounts cannot grant themselves Administrator privileges without key
    assert user_data["role"] == "athlete"
    
    # Login
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password}
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    token = token_data["access_token"]
    
    # Protected route check
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == email

def test_login_invalid_password():
    email = random_email()
    password = "correctpassword"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "User"}
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_role_based_access():
    email = random_email()
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass", "role": "athlete"}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "pass"}
    )
    token = login_resp.json()["access_token"]
    
    # Athlete trying to access admin route
    response = client.get(
        "/api/v1/users/admin-only",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403

def test_invalid_token():
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert response.status_code == 401

# --- Google OAuth2 Tests ---

def test_google_auth_invalid_credential():
    response = client.post(
        "/api/v1/auth/google",
        json={"credential": "invalid-forged-jwt"}
    )
    assert response.status_code in [400, 401]

def test_google_auth_unverified_email(monkeypatch):
    mock_email = random_email()
    def mock_verify(*args, **kwargs):
        return {
            "email": mock_email,
            "email_verified": False,
            "sub": "google-unverified-12345",
            "name": "Unverified User"
        }
    monkeypatch.setattr(id_token, "verify_oauth2_token", mock_verify)
    
    response = client.post(
        "/api/v1/auth/google",
        json={"credential": "mock-unverified-token", "role": "athlete"}
    )
    assert response.status_code == 400
    assert "not verified" in response.json()["detail"].lower()

def test_google_auth_new_user_registration(monkeypatch):
    mock_email = random_email()
    def mock_verify(*args, **kwargs):
        return {
            "email": mock_email,
            "email_verified": True,
            "sub": f"google-sub-{mock_email}",
            "name": "Sarah Connor"
        }
    monkeypatch.setattr(id_token, "verify_oauth2_token", mock_verify)
    
    response = client.post(
        "/api/v1/auth/google",
        json={"credential": "mock-valid-token", "role": "physiotherapist"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == mock_email
    assert data["user"]["role"] == "physiotherapist"
    assert data["user"]["full_name"] == "Sarah Connor"

def test_google_auth_account_linking_existing_user(monkeypatch):
    email = random_email()
    password = "mypassword123"
    
    # 1. Register user with local password
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Original Name", "role": "coach"}
    )
    assert reg_resp.status_code == 200
    
    # 2. User logs in with Google using matching verified email
    google_sub = f"sub-{random_email()}"
    def mock_verify(*args, **kwargs):
        return {
            "email": email,
            "email_verified": True,
            "sub": google_sub,
            "name": "Original Name Google"
        }
    monkeypatch.setattr(id_token, "verify_oauth2_token", mock_verify)
    
    google_resp = client.post(
        "/api/v1/auth/google",
        json={"credential": "mock-link-token", "role": "athlete"}
    )
    assert google_resp.status_code == 200
    data = google_resp.json()
    # Preserves existing role
    assert data["user"]["role"] == "coach"
    assert data["user"]["email"] == email
    
    # 3. Verify user can STILL log in with their original password!
    local_login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password}
    )
    assert local_login.status_code == 200
    assert local_login.json()["user"]["email"] == email

def test_google_auth_conflicting_google_id(monkeypatch):
    email = random_email()
    first_sub = "first-google-sub"
    second_sub = "second-different-google-sub"
    
    # 1. First Google login sets google_id
    def mock_verify_first(*args, **kwargs):
        return {
            "email": email,
            "email_verified": True,
            "sub": first_sub,
            "name": "First Login"
        }
    monkeypatch.setattr(id_token, "verify_oauth2_token", mock_verify_first)
    resp1 = client.post("/api/v1/auth/google", json={"credential": "t1", "role": "athlete"})
    assert resp1.status_code == 200
    
    # 2. Second Google login with SAME email but DIFFERENT sub should be rejected
    def mock_verify_second(*args, **kwargs):
        return {
            "email": email,
            "email_verified": True,
            "sub": second_sub,
            "name": "Different Sub Attacker"
        }
    monkeypatch.setattr(id_token, "verify_oauth2_token", mock_verify_second)
    resp2 = client.post("/api/v1/auth/google", json={"credential": "t2", "role": "athlete"})
    assert resp2.status_code == 409
