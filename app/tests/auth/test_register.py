

def test_register_success(client):
    response = client.post("/auth/register/", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "test@password123"
    })
    print(response.json())
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
    assert response.json()["username"] == "testuser"