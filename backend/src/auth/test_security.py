from uuid import uuid4

from cryptography.fernet import Fernet

from .. import config
from . import security


def test_password_hash_roundtrip():
    h = security.hash_password("correct-horse")
    assert security.verify_password("correct-horse", h)
    assert not security.verify_password("wrong", h)


def test_jwt_roundtrip(monkeypatch):
    monkeypatch.setattr(config.settings, "jwt_secret_key", "test-secret")
    user_id = uuid4()
    token = security.create_access_token(user_id)
    assert security.decode_access_token(token) == user_id


def test_jwt_rejects_tampered_token(monkeypatch):
    monkeypatch.setattr(config.settings, "jwt_secret_key", "test-secret")
    token = security.create_access_token(uuid4())
    assert security.decode_access_token(token + "x") is None


def test_fernet_roundtrip(monkeypatch):
    monkeypatch.setattr(config.settings, "field_encryption_key", Fernet.generate_key().decode())
    cipher = security.encrypt_secret("my-binance-secret")
    assert cipher != "my-binance-secret"
    assert security.decrypt_secret(cipher) == "my-binance-secret"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
