import uuid

import httpx


async def _create_and_login_access(client: httpx.AsyncClient) -> tuple[str | None, str]:
    email = f"{uuid.uuid4()}@example.com"

    response = await client.post(
        "/auth/register/",
        json={"email": email, "username": "TestUser", "password": "test@password123"},
    )
    assert response.status_code == 200

    response = await client.post(
        "/auth/login/", json={"email": email, "password": "test@password123"}
    )
    assert response.status_code == 200
    return response.cookies.get("access_token"), email


async def test_get_current_user(client: httpx.AsyncClient) -> None:
    _access_token, email = await _create_and_login_access(client)

    response = await client.get("/auth/me/")
    assert response.status_code == 200
    assert response.json()["email"] == email


async def test_get_current_user_invalid_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/auth/me/")
    assert response.status_code == 401


async def test_get_current_user_missing_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/auth/me/")
    assert response.status_code == 401
