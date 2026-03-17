import uuid


# create user and login
def create_and_login(client):
    email = f"{uuid.uuid4()}@example.com"

    response = client.post(
        "/auth/register/",
        json={"email": email, "username": "TestUser", "password": "test@password123"},
    )
    assert response.status_code == 200

    response = client.post("/auth/login/", json={"email": email, "password": "test@password123"})
    assert response.status_code == 200
    return {
        "access_token": response.cookies.get("access_token"),
        "refresh_token": response.cookies.get("refresh_token"),
    }


# test refresh token success
def test_refresh_success(client):
    create_and_login(client)

    response = client.post("/auth/refresh/")
    assert response.status_code == 200

    access_token = response.cookies.get("access_token")
    refresh_token = response.cookies.get("refresh_token")

    assert access_token is not None
    assert refresh_token is not None


# test refresh with invalid token
def test_refresh_invalid_token(client):
    response = client.post("/auth/refresh/", headers={"Authorization": "Bearer invalid.token"})
    assert response.status_code == 401


# test refresh missing token
def test_refresh_missing_token(client):
    response = client.post("/auth/refresh/")
    assert response.status_code == 401


# test refresh token rotation
def test_refresh_token_rotation(client):
    tokens = create_and_login(client)
    old_refresh = tokens["refresh_token"]

    first = client.post("/auth/refresh/")
    assert first.status_code == 200

    # restore old refresh token
    client.cookies.set("refresh_token", old_refresh)

    second = client.post("/auth/refresh/")
    assert second.status_code == 401
