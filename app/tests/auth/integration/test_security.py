import uuid

#JWT tampering test
def test_jwt_tampering(client):

    email = f"{uuid.uuid4()}@example.com"

    response = client.post("/auth/register/", json={
        "email": email,
        "username": "testuser",
        "password": "test@password123"
    })
    login = client.post("/auth/login/", json={
        "email": email,
        "password": "test@password123"
    })
    access_token = login.cookies.get("access_token")
    tampered_token = access_token + "sanvdsdvdsfj"

    client.cookies.set("access_token",tampered_token)

    response = client.get("/auth/me/")  
    assert response.status_code == 401

# access cannot be used to refresh
def test_access_token_not_refresh(client):

    email = f"{uuid.uuid4()}@example.com"

    response = client.post("/auth/register/", json={
        "email": email,
        "username": "testuser", 
        "password": "test@password123"
    })
    login = client.post("/auth/login/", json={
        "email": email,
        "password": "test@password123"
    })

    access_token = login.cookies.get("access_token")

    client.cookies.set("refresh_token",access_token)

    response = client.post("/auth/refresh/")
    assert response.status_code == 401

