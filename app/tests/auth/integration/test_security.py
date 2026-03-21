import uuid

import httpx


async def test_jwt_tampering(client: httpx.AsyncClient) -> None:
    email = f"{uuid.uuid4()}@example.com"

    await client.post(
        "/auth/register/",
        json={"email": email, "username": "testuser", "password": "test@password123"},
    )
    login = await client.post("/auth/login/", json={"email": email, "password": "test@password123"})
    access_token = login.cookies.get("access_token") or ""
    tampered_token = access_token + "sanvdsdvdsfj"

    client.cookies.set("access_token", tampered_token)

    response = await client.get("/auth/me/")
    assert response.status_code == 401


async def test_access_token_not_refresh(client: httpx.AsyncClient) -> None:
    email = f"{uuid.uuid4()}@example.com"

    await client.post(
        "/auth/register/",
        json={"email": email, "username": "testuser", "password": "test@password123"},
    )
    login = await client.post("/auth/login/", json={"email": email, "password": "test@password123"})
    access_token = login.cookies.get("access_token") or ""

    client.cookies.set("refresh_token", access_token)

    response = await client.post("/auth/refresh/")
    assert response.status_code == 401
