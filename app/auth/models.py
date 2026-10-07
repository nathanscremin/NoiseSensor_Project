"""Modelos utilizados pelo sistema de autenticação."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class User:
    """Representa um usuário do NoiseSensor."""

    user_id: int
    name: str
    email: str
    password_hash: str
    email_verified: bool
    telegram_chat_id: int | None
    created_at: datetime
    role: str
