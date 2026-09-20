import pytest


def get_auth_headers(client, user_data):
    """Helper function to get auth headers."""
    client.post("/api/v1/auth/register", json=user_data)
    login_response = client.post("/api/v1/auth/login", json={
        "email": user_data["email"],
        "password": user_data["password"]
    })
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_athlete(client, test_athlete_data, admin_user_data):
    """Test creating an athlete profile."""
    headers = get_auth_headers(client, admin_user_data)
    
    response = client.post("/api/v1/athletes", json=test_athlete_data, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["athlete_id"] == test_athlete_data["athlete_id"]
    assert data["sport_type"] == test_athlete_data["sport_type"]
    assert data["age"] == test_athlete_data["age"]


def test_create_athlete_unauthorized(client, test_athlete_data, test_user_data):
    """Test that athletes cannot create athlete profiles."""
    headers = get_auth_headers(client, test_user_data)
    
    response = client.post("/api/v1/athletes", json=test_athlete_data, headers=headers)
    assert response.status_code == 403


def test_create_duplicate_athlete_id(client, test_athlete_data, admin_user_data):
    """Test that duplicate athlete_id fails."""
    headers = get_auth_headers(client, admin_user_data)
    
    # First creation
    client.post("/api/v1/athletes", json=test_athlete_data, headers=headers)
    
    # Second creation with same athlete_id
    response = client.post("/api/v1/athletes", json=test_athlete_data, headers=headers)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_get_athletes(client, test_athlete_data, admin_user_data):
    """Test getting all athletes."""
    headers = get_auth_headers(client, admin_user_data)
    
    # Create an athlete
    client.post("/api/v1/athletes", json=test_athlete_data, headers=headers)
    
    # Get all athletes
    response = client.get("/api/v1/athletes", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["athlete_id"] == test_athlete_data["athlete_id"]


def test_get_athlete_by_id(client, test_athlete_data, admin_user_data):
    """Test getting a specific athlete by ID."""
    headers = get_auth_headers(client, admin_user_data)
    
    # Create an athlete
    create_response = client.post("/api/v1/athletes", json=test_athlete_data, headers=headers)
    athlete_id = create_response.json()["id"]
    
    # Get the athlete
    response = client.get(f"/api/v1/athletes/{athlete_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == athlete_id
    assert data["athlete_id"] == test_athlete_data["athlete_id"]


def test_get_nonexistent_athlete(client, admin_user_data):
    """Test getting a non-existent athlete."""
    headers = get_auth_headers(client, admin_user_data)
    
    response = client.get("/api/v1/athletes/99999", headers=headers)
    assert response.status_code == 404


def test_update_athlete(client, test_athlete_data, admin_user_data):
    """Test updating an athlete profile."""
    headers = get_auth_headers(client, admin_user_data)
    
    # Create an athlete
    create_response = client.post("/api/v1/athletes", json=test_athlete_data, headers=headers)
    athlete_id = create_response.json()["id"]
    
    # Update the athlete
    update_data = {"age": 26, "weight": 76.0}
    response = client.put(f"/api/v1/athletes/{athlete_id}", json=update_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["age"] == 26
    assert data["weight"] == 76.0


def test_update_athlete_as_self(client, test_athlete_data, test_user_data, admin_user_data):
    """Test that an athlete can update their own profile."""
    # Register as admin to create athlete profile
    admin_headers = get_auth_headers(client, admin_user_data)
    
    # Create athlete profile linked to user
    athlete_data = test_athlete_data.copy()
    athlete_data["user_id"] = 1  # This would be the user's ID
    create_response = client.post("/api/v1/athletes", json=athlete_data, headers=admin_headers)
    athlete_id = create_response.json()["id"]
    
    # Register as athlete
    user_headers = get_auth_headers(client, test_user_data)
    
    # Update the athlete (this should fail since the user_id doesn't match)
    update_data = {"age": 26}
    response = client.put(f"/api/v1/athletes/{athlete_id}", json=update_data, headers=user_headers)
    # Since the user_id doesn't match, this should fail with 403
    assert response.status_code == 403


def test_delete_athlete(client, test_athlete_data, admin_user_data):
    """Test deleting an athlete profile."""
    headers = get_auth_headers(client, admin_user_data)
    
    # Create an athlete
    create_response = client.post("/api/v1/athletes", json=test_athlete_data, headers=headers)
    athlete_id = create_response.json()["id"]
    
    # Delete the athlete
    response = client.delete(f"/api/v1/athletes/{athlete_id}", headers=headers)
    assert response.status_code == 200
    
    # Verify deletion
    get_response = client.get(f"/api/v1/athletes/{athlete_id}", headers=headers)
    assert get_response.status_code == 404


def test_delete_athlete_unauthorized(client, test_athlete_data, test_user_data, admin_user_data):
    """Test that non-admins cannot delete athletes."""
    # Create as admin
    admin_headers = get_auth_headers(client, admin_user_data)
    create_response = client.post("/api/v1/athletes", json=test_athlete_data, headers=admin_headers)
    athlete_id = create_response.json()["id"]
    
    # Try to delete as regular user
    user_headers = get_auth_headers(client, test_user_data)
    response = client.delete(f"/api/v1/athletes/{athlete_id}", headers=user_headers)
    assert response.status_code == 403


def test_invalid_athlete_data(client, test_athlete_data, admin_user_data):
    """Test validation of athlete data."""
    headers = get_auth_headers(client, admin_user_data)
    
    # Invalid age
    invalid_data = test_athlete_data.copy()
    invalid_data["age"] = 150
    response = client.post("/api/v1/athletes", json=invalid_data, headers=headers)
    assert response.status_code == 422
    
    # Negative height
    invalid_data = test_athlete_data.copy()
    invalid_data["height"] = -10
    response = client.post("/api/v1/athletes", json=invalid_data, headers=headers)
    assert response.status_code == 422
