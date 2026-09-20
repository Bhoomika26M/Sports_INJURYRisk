import pytest


def test_register_user(client, test_user_data):
    """Test user registration."""
    response = client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert data["full_name"] == test_user_data["full_name"]
    assert data["role"] == test_user_data["role"]
    assert "password_hash" not in data  # Password should not be exposed


def test_register_duplicate_email(client, test_user_data):
    """Test that duplicate email registration fails."""
    # First registration
    client.post("/api/v1/auth/register", json=test_user_data)
    
    # Second registration with same email
    response = client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_register_invalid_role(client, test_user_data):
    """Test that invalid role registration fails."""
    invalid_data = test_user_data.copy()
    invalid_data["role"] = "invalid_role"
    
    response = client.post("/api/v1/auth/register", json=invalid_data)
    assert response.status_code == 400
    assert "Invalid role" in response.json()["detail"]


def test_login_success(client, test_user_data):
    """Test successful login."""
    # Register user first
    client.post("/api/v1/auth/register", json=test_user_data)
    
    # Login
    login_data = {
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_email(client, test_user_data):
    """Test login with invalid email."""
    login_data = {
        "email": "nonexistent@example.com",
        "password": test_user_data["password"]
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_invalid_password(client, test_user_data):
    """Test login with invalid password."""
    # Register user first
    client.post("/api/v1/auth/register", json=test_user_data)
    
    # Login with wrong password
    login_data = {
        "email": test_user_data["email"],
        "password": "wrongpassword"
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_get_me_without_token(client):
    """Test that /auth/me requires authentication."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_get_me_with_valid_token(client, test_user_data):
    """Test that /auth/me works with valid token."""
    # Register and login
    client.post("/api/v1/auth/register", json=test_user_data)
    login_response = client.post("/api/v1/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    })
    token = login_response.json()["access_token"]
    
    # Get current user info
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert data["full_name"] == test_user_data["full_name"]


def test_get_me_with_invalid_token(client):
    """Test that /auth/me fails with invalid token."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
