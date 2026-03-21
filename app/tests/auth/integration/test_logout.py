import uuid

import httpx


async def _create_and_login(client: httpx.AsyncClient) -> dict[str, str | None]:
    email = f"{uuid.uuid4()}@example.com"

    await client.post(
        "/auth/register/",
        json={"email": email, "username": "logoutuser", "password": "test@password123"},
    )
    login = await client.post("/auth/login/", json={"email": email, "password": "test@password123"})
    return {
        "access_token": login.cookies.get("access_token"),
        "refresh_token": login.cookies.get("refresh_token"),
    }


async def test_logout_user(client: httpx.AsyncClient) -> None:
    await _create_and_login(client)

    response = await client.post("/auth/logout/")
    assert response.status_code == 200


async def test_logout_with_access_token(client: httpx.AsyncClient) -> None:
    tokens = await _create_and_login(client)

    client.cookies.set("refresh_token", tokens["access_token"] or "")

    response = await client.post("/auth/logout/")
    assert response.status_code == 401


async def test_logout_with_invalid_token(client: httpx.AsyncClient) -> None:
    response = await client.post("/auth/logout/", headers={"Authorization": "Bearer invalid.token"})
    assert response.status_code == 401


async def test_logout_with_missing_token(client: httpx.AsyncClient) -> None:
    response = await client.post("/auth/logout/")
    assert response.status_code in [401, 403]
