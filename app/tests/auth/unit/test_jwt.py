from jose import jwt

from app.core.config import get_settings
from app.modules.auth.utils import create_access_token, create_refresh_token

setting = get_settings()


# access token creation test
def test_create_access_token():
    data = {"sub": "123", "type": "access"}
    token = create_access_token(data)

    payload = jwt.decode(token, setting.SECRET_KEY, algorithms=[setting.ALGORITHM])

    assert payload["sub"] == "123"
    assert payload["type"] == "access"


# refresh token creation test
def test_create_refresh_token():
    data = {"sub": "566", "type": "refresh"}
    token, _jti = create_refresh_token(data)

    payload = jwt.decode(token, setting.SECRET_KEY, algorithms=[setting.ALGORITHM])

    assert payload["sub"] == "566"
    assert payload["type"] == "refresh"
