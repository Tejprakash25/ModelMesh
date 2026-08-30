import hashlib
import secrets


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    raw = f"sk-{secrets.token_urlsafe(32)}"
    return raw, hash_api_key(raw), raw[:10]
