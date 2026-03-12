from app.core.rate_limiter import limiter

def test_rate_limiter_blocks_requests(client):
    limiter.enabled = True
    
    # Send a burst of requests to trigger rate limiting
    # Assume the limit is small like "5/minute", but let's test defensively
    status_codes = []
    
    for _ in range(50):
        response = client.post("/auth/login/", json={
            "email": "rate_limit_test@example.com",
            "password": "wrong_password"
        })
        status_codes.append(response.status_code)
        if response.status_code == 429:
            break
            
    assert 429 in status_codes, "Rate limiter did not block excessive requests. Ensure REDIS is running and limits are set."
    
    limiter.enabled = False
