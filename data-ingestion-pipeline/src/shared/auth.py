import hashlib
import hmac
import secrets

def generate_approval_token(secret_key: str) -> (str, str):
    """
    Generates a cryptographically secure token and its hash.
    Returns: (token, token_hash)
    """
    token = secrets.token_urlsafe(32)
    token_hash = hash_approval_token(secret_key, token)
    return token, token_hash

def hash_approval_token(secret_key: str, token: str) -> str:
    """
    Hashes a token using HMAC-SHA256.
    """
    return hmac.new(
        secret_key.encode('utf-8'),
        token.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def verify_approval_token(secret_key: str, token: str, expected_hash: str) -> bool:
    """
    Verifies if the token matches the expected hash.
    """
    computed_hash = hash_approval_token(secret_key, token)
    return hmac.compare_digest(computed_hash, expected_hash)
