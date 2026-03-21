from app.modules.auth.service import hash_password, verify_password


# password hashing tests
def test_hash_password():
    password = "Strong123!"
    hashed = hash_password(password)

    assert hashed != password


# hashed pasword verify test
def test_verify_password():
    password = "Strong123!"
    hashed = hash_password(password)

    assert verify_password(password, hashed)


# Wrong password verify test
def test_verify_wrong_password():
    password = "Strong123!"
    wrong_password = "WrongPass123!"
    hashed = hash_password(password)

    assert not verify_password(wrong_password, hashed)
