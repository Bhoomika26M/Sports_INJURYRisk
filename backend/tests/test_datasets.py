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


def test_get_datasets(client, test_user_data):
    """Test getting registered datasets."""
    headers = get_auth_headers(client, test_user_data)
    
    response = client.get("/api/v1/datasets", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # The dataset file might not be available in test environment, so we just check the endpoint works
    # If datasets are available, validate structure
    if len(data) > 0:
        # Check that datasets have required fields
        for dataset in data:
            assert "name" in dataset
            assert "status" in dataset


def test_get_datasets_without_auth(client):
    """Test that datasets endpoint requires authentication."""
    response = client.get("/api/v1/datasets")
    assert response.status_code == 401
