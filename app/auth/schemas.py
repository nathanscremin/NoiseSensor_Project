"""Schemas utilizados nas requisições e respostas da autenticação."""

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Dados enviados para criar uma nova conta."""

    name: str = Field(
        min_length=1,
        max_length=100,
    )

    email: str = Field(
        min_length=3,
        max_length=320,
    )

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    confirm_password: str = Field(
        min_length=8,
        max_length=128,
    )


class LoginRequest(BaseModel):
    """Dados enviados para realizar login."""

    email: str = Field(
        min_length=3,
        max_length=320,
    )

    password: str = Field(
        min_length=1,
        max_length=128,
    )


class UserResponse(BaseModel):
    """Dados públicos do usuário."""

    user_id: int
    name: str
    email: str
    email_verified: bool
    telegram_chat_id: int | None


class MessageResponse(BaseModel):
    """Resposta simples contendo uma mensagem."""

    message: str
