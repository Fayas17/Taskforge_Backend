import httpx

from app.core.rate_limiter import limiter


async def test_rate_limiter_blocks_requests(client: httpx.AsyncClient) -> None:
    limiter.enabled = True

    status_codes = []
    for _ in range(50):
        response = await client.post(
            "/auth/login/",
            json={"email": "rate_limit_test@example.com", "password": "wrong_password"},
        )
        status_codes.append(response.status_code)
        if response.status_code == 429:
            break

    limiter.enabled = False

    assert (
        429 in status_codes
    ), "Rate limiter did not block excessive requests. Ensure REDIS is running and limits are set."
