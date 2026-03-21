import base64
import json
import uuid

import httpx
from jose import jwt

from app.core.config import get_settings

settings = get_settings()


async def test_jwt_none_algorithm(client: httpx.AsyncClient) -> None:
    email = f"{uuid.uuid4()}@example.com"

    await client.post(
        "/auth/register/",
        json={"email": email, "username": "nonetest", "password": "test@password123"},
    )

    payload = {"sub": email, "type": "access"}
    try:
        malicious_token = jwt.encode(payload, key="", algorithm="none")
    except Exception:
        malicious_token = (
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0"
            ".eyJzdWIiOiJtYWxpY2lvdXNAZXhhbXBsZS5jb20iLCJ0eXBlIjoiYWNjZXNzIn0."
        )

    client.cookies.set("access_token", malicious_token)

    response = await client.get("/auth/me/")
    assert response.status_code == 401, "Backend must explicitly reject the 'none' algorithm"


async def test_jwt_invalid_signature(client: httpx.AsyncClient) -> None:
    email = f"{uuid.uuid4()}@example.com"

    await client.post(
        "/auth/register/",
        json={"email": email, "username": "sigtest", "password": "test@password123"},
    )
    login = await client.post("/auth/login/", json={"email": email, "password": "test@password123"})
    access_token = login.cookies.get("access_token") or ""

    header, payload, signature = access_token.split(".")

    def b64_decode(s: str) -> bytes:
        rem = len(s) % 4
        if rem > 0:
            s += "=" * (4 - rem)
        return base64.urlsafe_b64decode(s.encode())

    payload_dec = json.loads(b64_decode(payload))
    payload_dec["sub"] = "admin@example.com"
    tampered_payload_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload_dec).encode()).decode().rstrip("=")
    )

    tampered_token = f"{header}.{tampered_payload_b64}.{signature}"
    client.cookies.set("access_token", tampered_token)

    response = await client.get("/auth/me/")
    assert (
        response.status_code == 401
    ), "Backend must reject forged payloads with invalid signatures"
