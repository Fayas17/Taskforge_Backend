import uuid


# create user and login
def create_and_login(client):
    
    email = f"{uuid.uuid4()}@example.com"

    response = client.post("/auth/register/", json={
        "email": email,
        "username": "TestUser",
        "password": "test@password123"
    })
    assert response.status_code == 200

    response = client.post("/auth/login/", json={
        "email": email,
        "password": "test@password123"
    })
    assert response.status_code == 200
    return response.json()

# test refresh token success
def test_refresh_success(client):
    tokens = create_and_login(client)

    response = client.post("/auth/refresh/", headers={
        "Authorization": f"Bearer {tokens['refresh_token']}"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()

# test refresh with invalid token
def test_refresh_invalid_token(client):
    response = client.post("/auth/refresh/", headers={
        "Authorization": "Bearer invalid.token"})
    assert response.status_code == 401

# test refresh missing token
def test_refresh_missing_token(client):
    response = client.post("/auth/refresh/")
    assert response.status_code == 401

# test refresh token rotation
def test_refresh_token_rotation(client):
    tokens = create_and_login(client)
    refresh_token = tokens["refresh_token"]

    # First refresh
    first_refresh = client.post(
        "/auth/refresh/",
        headers={"Authorization": f"Bearer {refresh_token}"}
    )

    assert first_refresh.status_code == 200

    # Try using OLD refresh token again
    second_refresh = client.post(
        "/auth/refresh/",
        headers={"Authorization": f"Bearer {refresh_token}"}
    )

    assert second_refresh.status_code == 401