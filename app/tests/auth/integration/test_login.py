import uuid


# test user creation
def create_user(client):
    email = f"{uuid.uuid4()}@example.com"

    response = client.post(
        "/auth/register/",
        json={"email": email, "username": "TestUser", "password": "test@password123"},
    )
    assert response.status_code == 200
    return response.json()["email"]


# test user login
def test_login_success(client):
    email = create_user(client)

    response = client.post("/auth/login/", json={"email": email, "password": "test@password123"})
    assert response.status_code == 200
    access_token = response.cookies.get("access_token")
    refresh_token = response.cookies.get("refresh_token")

    assert access_token is not None
    assert refresh_token is not None


# test login with wrong password
def test_login_wrong_password(client):
    email = create_user(client)

    response = client.post("/auth/login/", json={"email": email, "password": "wrongpassword"})
    assert response.status_code == 401


# test login with non-existent user
def test_login_non_user(client):
    create_user(client)

    response = client.post(
        "/auth/login/", json={"email": "nonexistent@example.com", "password": "test@password123"}
    )
    assert response.status_code == 401
