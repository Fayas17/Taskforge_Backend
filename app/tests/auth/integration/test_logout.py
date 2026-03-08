import uuid

# Helper function
def create_and_login_user(client):

    email = f"{uuid.uuid4()}@example.com"

    client.post("/auth/register/", json={
        "email": email,
        "username": "logoutuser",
        "password": "test@password123"
    })

    login = client.post("/auth/login/", json={
        "email": email,
        "password": "test@password123"
    })

    return {
        "access_token": login.cookies.get("access_token"),
        "refresh_token": login.cookies.get("refresh_token")
    }


#  Test logout success
def test_logout_user(client):
    tokens = create_and_login_user(client)
    refresh_token = tokens["refresh_token"]

    response = client.post(
        "/auth/logout/"
        )

    assert response.status_code == 200


#  Logout using access token should fail
def test_logout_with_access_token(client):
    tokens = create_and_login_user(client)
    access_token = tokens["access_token"]

    client.cookies.set("refresh_token",tokens["access_token"])

    response = client.post(
        "/auth/logout/"
        )

    assert response.status_code == 401


#  Logout with invalid token
def test_logout_with_invalid_token(client):
    response = client.post(
        "/auth/logout/",
        headers={"Authorization": "Bearer invalid.token"}
    )

    assert response.status_code == 401


#  Logout with missing token
def test_logout_with_missing_token(client):
    response = client.post("/auth/logout/")
    assert response.status_code in [401, 403]