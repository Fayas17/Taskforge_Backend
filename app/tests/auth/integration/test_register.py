import uuid

import httpx


# user registration test
async def test_register_success(client: httpx.AsyncClient) -> None:
    email = f"{uuid.uuid4()}@example.com"

    response = await client.post(
        "/auth/register/",
        json={"email": email, "username": "testuser", "password": "test@password123"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == email
    assert response.json()["username"] == "testuser"


# test duplicate email registration
async def test_register_duplicate_email(client: httpx.AsyncClient) -> None:
    email = f"{uuid.uuid4()}@example.com"

    response = await client.post(
        "/auth/register/",
        json={"email": email, "username": "duplicateuser", "password": "test@password123"},
    )
    assert response.status_code == 200

    response = await client.post(
        "/auth/register/",
        json={"email": email, "username": "anotheruser", "password": "test@password123"},
    )
    assert response.status_code == 400


# test invalid email registration
async def test_register_invalid_email(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/auth/register/",
        json={
            "email": "invalid-email",
            "username": "invalidemailuser",
            "password": "test@password123",
        },
    )
    assert response.status_code == 422


# test weak password registration
async def test_register_weak_password(client: httpx.AsyncClient) -> None:
    email = f"{uuid.uuid4()}@example.com"

    response = await client.post(
        "/auth/register/",
        json={"email": email, "username": "weakuser", "password": "123456"},
    )
    assert response.status_code == 400
