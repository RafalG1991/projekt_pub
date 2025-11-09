import secrets
from datetime import datetime, timedelta

def generate_activation_token() -> str:
    # 43-urlsafe znaków, w praktyce ~256 bitów entropii
    return secrets.token_urlsafe(32)

def expiry(hours: int = 24) -> datetime:
    return datetime.utcnow() + timedelta(hours=hours)