import uuid


# user registration test
def test_register_success(client):

    email = f"{uuid.uuid4()}@example.com"

    response = client.post("/auth/register/", json={
        "email": email,
        "username": "testuser",
        "password": "test@password123"
    })
    print(response.json())
    assert response.status_code == 200
    assert response.json()["email"] == email
    assert response.json()["username"] == "testuser"

# test duplicate email registration
def test_register_duplicate_email(client):

    email = f"{uuid.uuid4()}@example.com"

    # First registration should succeed
    response = client.post("/auth/register/", json={
        "email": email,
        "username": "duplicateuser",
        "password": "test@password123"
    })
    assert response.status_code == 200

    # Second registration with same email should fail
    response = client.post("/auth/register/", json={
        "email": email,
        "username": "anotheruser",
        "password": "test@password123"
    })
    assert response.status_code == 400

# test duplicate invalid email registration
def test_register_invalid_email(client):
    response = client.post("/auth/register/", json={
        "email": "invalid-email",
        "username": "invalidemailuser",
        "password": "test@password123"
    })
    assert response.status_code == 422

# test weak password registration
def test_register_weak_password(client):

    email = f"{uuid.uuid4()}@example.com"

    response = client.post("/auth/register/", json={
        "email": email,
        "username": "weakuser",
        "password": "123456"
    })
    assert response.status_code == 400