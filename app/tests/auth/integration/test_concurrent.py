import pytest


@pytest.mark.skip(
    reason=(
        "Concurrent race-condition tests require separate DB connections per request. "
        "The shared single-session fixture serializes all requests onto one asyncpg "
        "connection, making true concurrency impossible in this setup. "
        "Test against a running server (e.g. pytest-httpserver or docker) to validate this."
    )
)
async def test_race_condition_registration() -> None:
    pass
