# test logout user
def test_logout_user(client):
    response = client.post("/auth/register/", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "test@password123"
    })
    login = client.post("/auth/login/", json={
        "email": "test@example.com",
        "password": "test@password123"
    })
    return login.json()

def logout_user(client):
    refresh_token = test_logout_user(client)

    response = client.get("/auth/logout/", headers={
        "Authorization": f"Bearer {refresh_token}"}
    )  
    assert response.status_code == 200

#logout with access token
def logout_user_access_token(client):
    access_token = test_logout_user(client)
    response = client.post("/auth/logout/", headers={
        "Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 401

# test logout with invalid token
def logout_user_invalid_token(client):

    response = client.get("/auth/logout/", headers={
        "Authorization": "Bearer invalid.token"}
    )   
    assert response.status_code == 401

# test logout with missing token
def logout_user_missing_token(client):  
    response = client.get("/auth/logout/")
    assert response.status_code == 401