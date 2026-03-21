import uuid

import httpx


async def _create_and_login(client: httpx.AsyncClient) -> dict[str, str | None]:
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
    return {
        "access_token": response.cookies.get("access_token"),
        "refresh_token": response.cookies.get("refresh_token"),
    }


async def test_refresh_success(client: httpx.AsyncClient) -> None:
    await _create_and_login(client)

    response = await client.post("/auth/refresh/")
    assert response.status_code == 200
    assert response.cookies.get("access_token") is not None
    assert response.cookies.get("refresh_token") is not None


async def test_refresh_invalid_token(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/auth/refresh/", headers={"Authorization": "Bearer invalid.token"}
    )
    assert response.status_code == 401


async def test_refresh_missing_token(client: httpx.AsyncClient) -> None:
    response = await client.post("/auth/refresh/")
    assert response.status_code == 401


async def test_refresh_token_rotation(client: httpx.AsyncClient) -> None:
    tokens = await _create_and_login(client)
    old_refresh = tokens["refresh_token"] or ""

    first = await client.post("/auth/refresh/")
    assert first.status_code == 200

    # Restore the old (now-revoked) refresh token
    client.cookies.set("refresh_token", old_refresh)

    second = await client.post("/auth/refresh/")
    assert second.status_code == 401
