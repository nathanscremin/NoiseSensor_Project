"""Regras de negócio do sistema de autenticação."""

from datetime import datetime, timedelta, timezone

import psycopg

from app.auth.mailer import send_verification_email
from app.auth.models import User
from app.auth.repository import (
    consume_email_verification_token,
    create_email_verification_token,
    create_session,
    create_user,
    get_user_by_email,
    get_user_by_session_token_hash,
    revoke_session,
)
from app.auth.security import (
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)


SESSION_LIFETIME = timedelta(days=7)
VERIFICATION_TOKEN_LIFETIME = timedelta(hours=24)


class AuthService:
    """Coordena as regras de autenticação."""

    def register(
        self,
        connection: psycopg.Connection,
        name: str,
        email: str,
        password: str,
        confirm_password: str,
    ) -> User:
        """Cria uma nova conta."""

        name = name.strip()
        email = email.strip().lower()

        if not name:
            raise ValueError(
                "O nome não pode estar vazio."
            )

        if password != confirm_password:
            raise ValueError(
                "As senhas não coincidem."
            )

        existing_user = get_user_by_email(
            connection,
            email,
        )

        if existing_user is not None:
            raise ValueError(
                "Já existe uma conta com esse e-mail."
            )

        password_hash = hash_password(
            password
        )

        user = create_user(
            connection=connection,
            name=name,
            email=email,
            password_hash=password_hash,
        )

        verification_token = generate_token()
        verification_token_hash = hash_token(
            verification_token
        )

        expires_at = (
            datetime.now(timezone.utc)
            + VERIFICATION_TOKEN_LIFETIME
        )

        create_email_verification_token(
            connection=connection,
            user_id=user.user_id,
            token_hash=verification_token_hash,
            expires_at=expires_at,
        )

        send_verification_email(
            email=user.email,
            name=user.name,
            token=verification_token,
        )

        return user

    def verify_email(
        self,
        connection: psycopg.Connection,
        token: str,
    ) -> bool:
        """Verifica o e-mail usando o token recebido."""

        token_hash = hash_token(token)

        user_id = consume_email_verification_token(
            connection,
            token_hash,
        )

        return user_id is not None

    def login(
        self,
        connection: psycopg.Connection,
        email: str,
        password: str,
    ) -> tuple[str, User]:
        """Autentica o usuário e cria uma sessão."""

        email = email.strip().lower()

        user = get_user_by_email(
            connection,
            email,
        )

        if user is None:
            raise ValueError(
                "E-mail ou senha inválidos."
            )

        if not verify_password(
            password,
            user.password_hash,
        ):
            raise ValueError(
                "E-mail ou senha inválidos."
            )

        if not user.email_verified:
            raise ValueError(
                "Verifique seu e-mail antes de fazer login."
            )

        session_token = generate_token()
        session_token_hash = hash_token(
            session_token
        )

        expires_at = (
            datetime.now(timezone.utc)
            + SESSION_LIFETIME
        )

        create_session(
            connection=connection,
            user_id=user.user_id,
            token_hash=session_token_hash,
            expires_at=expires_at,
        )

        return session_token, user

    def authenticate_session(
        self,
        connection: psycopg.Connection,
        session_token: str,
    ) -> User | None:
        """Obtém o usuário de uma sessão válida."""

        session_token_hash = hash_token(
            session_token
        )

        return get_user_by_session_token_hash(
            connection,
            session_token_hash,
        )

    def logout(
        self,
        connection: psycopg.Connection,
        session_token: str,
    ) -> None:
        """Invalida uma sessão."""

        session_token_hash = hash_token(
            session_token
        )

        revoke_session(
            connection,
            session_token_hash,
        )
