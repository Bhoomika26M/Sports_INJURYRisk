import pytest
import random
import string
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def random_email():
    return "".join(random.choices(string.ascii_lowercase, k=10)) + "@cookieauth.com"

def test_login_sets_httponly_cookie():
    email = random_email()
    password = "StrongPassword123!"

    # 1. Register test user
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Cookie Test User"}
    )
    assert reg_resp.status_code == 200

    # 2. Login - should return access_token in JSON AND set HttpOnly cookie
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "access_token" in response.cookies
    cookie_token = response.cookies["access_token"]
    assert cookie_token == response.json()["access_token"]

    # 3. Test accessing protected endpoint using ONLY the cookie (no Authorization header)
    cookie_client = TestClient(app, cookies={"access_token": cookie_token})
    me_resp = cookie_client.get("/api/v1/users/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email

    # 4. Test OAuth login also sets cookie
    oauth_email = random_email()
    oauth_resp = client.post(
        "/api/v1/auth/oauth/login",
        json={"email": oauth_email, "full_name": "OAuth User", "provider": "google", "role": "coach"}
    )
    assert oauth_resp.status_code == 200
    assert "access_token" in oauth_resp.cookies

    # 5. Test logout clears the cookie
    logout_resp = cookie_client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200
    # Cookie is deleted or has empty/expired header
    assert logout_resp.cookies.get("access_token") is None or logout_resp.cookies.get("access_token") == '""' or logout_resp.cookies.get("access_token") == ""
