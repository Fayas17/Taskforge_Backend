import uuid


# create and login to return access token
def create_and_login_access(client):
    email = f"{uuid.uuid4()}@example.com"

    response = client.post(
        "/auth/register/",
        json={"email": email, "username": "TestUser", "password": "test@password123"},
    )
    assert response.status_code == 200

    response = client.post("/auth/login/", json={"email": email, "password": "test@password123"})
    assert response.status_code == 200
    access_token = response.cookies.get("access_token")
    return access_token, email


# test get current user
def test_get_current_user(client):
    _access_token, email = create_and_login_access(client)

    response = client.get("/auth/me/")
    assert response.status_code == 200
    data = response.json()

    assert data["email"] == email


# test get current user with invalid token
def test_get_current_user_invalid_token(client):
    response = client.get("/auth/me/")
    assert response.status_code == 401


# test get current user with missing token
def test_get_current_user_missing_token(client):
    response = client.get("/auth/me/")
    assert response.status_code == 401
