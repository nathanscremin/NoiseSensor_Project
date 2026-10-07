"""Dependências utilizadas para autenticar requisições."""

from fastapi import Cookie, Depends, HTTPException, status

from app.auth.models import User
from app.auth.service import AuthService
from app.auth.security import SESSION_COOKIE_NAME
from app.database.connection import create_connection


auth_service = AuthService()


def get_current_user(
    session_token: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> User:
    """Retorna o usuário autenticado da sessão atual."""

    if session_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não autenticado.",
        )

    with create_connection() as connection:
        user = auth_service.authenticate_session(
            connection,
            session_token,
        )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada.",
        )

    return user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Retorna o usuário atual somente quando ele é administrador."""

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores.",
        )

    return current_user


def get_optional_current_user(
    session_token: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> User | None:
    """Retorna o usuário autenticado quando existe uma sessão válida."""

    if session_token is None:
        return None

    with create_connection() as connection:
        return auth_service.authenticate_session(
            connection,
            session_token,
        )
