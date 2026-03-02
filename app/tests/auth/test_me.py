#create and login to return access token
def create_and_login_access(client):
    response = client.post("/auth/register/", json={
        "email": "test@example.com",
        "username": "TestUser",
        "password": "test@password123"
    })
    assert response.status_code == 200

    response = client.post("/auth/login/", json={
        "email": "test@example.com",
        "password": "test@password123"
    })
    assert response.status_code == 200
    return response.json()["access_token"]

# test get current user
def test_get_current_user(client):
    access_token = create_and_login_access(client)

    response = client.get("/auth/me/", headers={
        "Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()

    assert data["email"] == "test@example.com"

# test get current user with invalid token
def test_get_current_user_invalid_token(client):
    response = client.get("/auth/me/", headers={
        "Authorization": "Bearer invalid.token"}
    )
    assert response.status_code == 401

# test get current user with missing token
def test_get_current_user_missing_token(client):
    response = client.get("/auth/me/")
    assert response.status_code == 401
