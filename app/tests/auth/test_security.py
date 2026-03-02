#JWT tampering test
def test_jwt_tampering(client):
    response = client.post("/auth/register/", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "test@password123"
    })
    login = client.post("/auth/login/", json={
        "email": "test@example.com",
        "password": "test@password123"
    })
    access_token = login.json()["access_token"]
    tampered_token = access_token + "sanvdsdvdsfj"

    response = client.get("/auth/me/", headers={
        "Authorization": f"Bearer {tampered_token}"}
    )  
    assert response.status_code == 401

# access cannot be used to refresh
def test_access_token_not_refresh(client):
    response = client.post("/auth/register/", json={
        "email": "test@example.com",
        "username": "testuser", 
        "password": "test@password123"
    })
    login = client.post("/auth/login/", json={
        "email": "test@example.com",
        "password": "test@password123"
    })

    access_token = login.json()["access_token"]

    response = client.post("/auth/refresh/", headers={
        "Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 401

