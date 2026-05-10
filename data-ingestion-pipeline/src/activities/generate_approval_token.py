from src.shared.auth import generate_approval_token as gen_token
from src.shared.settings import get_settings

def generate_approval_token(input_data: dict) -> dict:
    settings = get_settings()
    token, token_hash = gen_token(settings.approval_secret_key)
    return {
        "token": token,
        "token_hash": token_hash
    }
