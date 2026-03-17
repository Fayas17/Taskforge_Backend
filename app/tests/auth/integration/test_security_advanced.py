import base64
import json
import uuid

from jose import jwt

from app.core.config import get_settings

settings = get_settings()


def test_jwt_none_algorithm(client):
    email = f"{uuid.uuid4()}@example.com"

    # Register a user normally
    client.post(
        "/auth/register/",
        json={"email": email, "username": "nonetest", "password": "test@password123"},
    )

    # Create a malicious JWT using algorithm 'none'
    payload = {"sub": email, "type": "access"}
    try:
        malicious_token = jwt.encode(payload, key="", algorithm="none")
    except Exception:
        # If the library rejects 'none' on encoding, mock it
        # pre-built none-alg token: {"alg":"none"}.{"sub":"malicious@example.com","type":"access"}.
        malicious_token = (
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0"
            ".eyJzdWIiOiJtYWxpY2lvdXNAZXhhbXBsZS5jb20iLCJ0eXBlIjoiYWNjZXNzIn0."
        )

    client.cookies.set("access_token", malicious_token)

    response = client.get("/auth/me/")
    assert response.status_code == 401, "Backend must explicitly reject the 'none' algorithm"


def test_jwt_invalid_signature(client):
    email = f"{uuid.uuid4()}@example.com"

    client.post(
        "/auth/register/",
        json={"email": email, "username": "sigtest", "password": "test@password123"},
    )

    login = client.post("/auth/login/", json={"email": email, "password": "test@password123"})

    access_token = login.cookies.get("access_token")

    # Tamper with the payload (middle part of the token)
    header, payload, signature = access_token.split(".")

    # Change the subject (sub) in the payload to another user
    def b64_decode(s: str):
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

    response = client.get("/auth/me/")
    assert (
        response.status_code == 401
    ), "Backend must reject forged payloads with invalid signatures"
