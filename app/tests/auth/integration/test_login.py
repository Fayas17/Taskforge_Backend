import uuid

import httpx


async def _create_user(client: httpx.AsyncClient) -> str:
    email = f"{uuid.uuid4()}@example.com"
    response = await client.post(
        "/auth/register/",
        json={"email": email, "username": "TestUser", "password": "test@password123"},
    )
    assert response.status_code == 200
    return str(response.json()["email"])


async def test_login_success(client: httpx.AsyncClient) -> None:
    email = await _create_user(client)

    response = await client.post(
        "/auth/login/", json={"email": email, "password": "test@password123"}
    )
    assert response.status_code == 200
    assert response.cookies.get("access_token") is not None
    assert response.cookies.get("refresh_token") is not None


async def test_login_wrong_password(client: httpx.AsyncClient) -> None:
    email = await _create_user(client)

    response = await client.post("/auth/login/", json={"email": email, "password": "wrongpassword"})
    assert response.status_code == 401


async def test_login_non_user(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/auth/login/",
        json={"email": "nonexistent@example.com", "password": "test@password123"},
    )
    assert response.status_code == 401
