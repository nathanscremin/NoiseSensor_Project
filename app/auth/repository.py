"""Operações de persistência relacionadas à autenticação."""

from datetime import datetime

import psycopg

from app.auth.models import User


USER_COLUMNS = """
    user_id,
    name,
    email,
    password_hash,
    email_verified,
    telegram_chat_id,
    created_at
"""


def _user_from_row(row: tuple) -> User:
    """Converte uma linha do banco em um objeto User."""

    return User(
        user_id=row[0],
        name=row[1],
        email=row[2],
        password_hash=row[3],
        email_verified=row[4],
        telegram_chat_id=row[5],
        created_at=row[6],
    )


def get_user_by_email(
    connection: psycopg.Connection,
    email: str,
) -> User | None:
    """Busca um usuário pelo e-mail."""

    query = f"""
        SELECT
            {USER_COLUMNS}
        FROM users
        WHERE email = %s;
    """

    row = connection.execute(
        query,
        (email,),
    ).fetchone()

    if row is None:
        return None

    return _user_from_row(row)


def get_user_by_id(
    connection: psycopg.Connection,
    user_id: int,
) -> User | None:
    """Busca um usuário pelo ID."""

    query = f"""
        SELECT
            {USER_COLUMNS}
        FROM users
        WHERE user_id = %s;
    """

    row = connection.execute(
        query,
        (user_id,),
    ).fetchone()

    if row is None:
        return None

    return _user_from_row(row)


def create_user(
    connection: psycopg.Connection,
    name: str,
    email: str,
    password_hash: str,
) -> User:
    """Cria um usuário no banco."""

    query = f"""
        INSERT INTO users (
            name,
            email,
            password_hash,
            email_verified
        )
        VALUES (
            %s,
            %s,
            %s,
            FALSE
        )
        RETURNING
            {USER_COLUMNS};
    """

    row = connection.execute(
        query,
        (
            name,
            email,
            password_hash,
        ),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            "Não foi possível criar o usuário."
        )

    connection.commit()

    return _user_from_row(row)


def create_email_verification_token(
    connection: psycopg.Connection,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
) -> None:
    """Salva um token de verificação de e-mail."""

    query = """
        INSERT INTO email_verification_tokens (
            user_id,
            token_hash,
            expires_at
        )
        VALUES (
            %s,
            %s,
            %s
        );
    """

    connection.execute(
        query,
        (
            user_id,
            token_hash,
            expires_at,
        ),
    )

    connection.commit()


def consume_email_verification_token(
    connection: psycopg.Connection,
    token_hash: str,
) -> int | None:
    """
    Consome um token de verificação.

    Retorna o ID do usuário se o token for válido.
    """

    query = """
        UPDATE email_verification_tokens
        SET used_at = NOW()
        WHERE token_hash = %s
          AND used_at IS NULL
          AND expires_at > NOW()
        RETURNING user_id;
    """

    row = connection.execute(
        query,
        (token_hash,),
    ).fetchone()

    if row is None:
        connection.rollback()
        return None

    connection.execute(
        """
        UPDATE users
        SET email_verified = TRUE
        WHERE user_id = %s;
        """,
        (row[0],),
    )

    connection.commit()

    return row[0]


def create_session(
    connection: psycopg.Connection,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
) -> None:
    """Cria uma sessão autenticada."""

    query = """
        INSERT INTO sessions (
            user_id,
            token_hash,
            expires_at
        )
        VALUES (
            %s,
            %s,
            %s
        );
    """

    connection.execute(
        query,
        (
            user_id,
            token_hash,
            expires_at,
        ),
    )

    connection.commit()


def get_user_by_session_token_hash(
    connection: psycopg.Connection,
    token_hash: str,
) -> User | None:
    """Obtém o usuário associado a uma sessão válida."""

    query = f"""
        SELECT
            {', '.join(
                f"u.{column.strip()}"
                for column in USER_COLUMNS.split(',')
            )}
        FROM sessions AS s
        INNER JOIN users AS u
            ON u.user_id = s.user_id
        WHERE s.token_hash = %s
          AND s.revoked_at IS NULL
          AND s.expires_at > NOW();
    """

    row = connection.execute(
        query,
        (token_hash,),
    ).fetchone()

    if row is None:
        return None

    return _user_from_row(row)


def revoke_session(
    connection: psycopg.Connection,
    token_hash: str,
) -> None:
    """Invalida uma sessão."""

    query = """
        UPDATE sessions
        SET revoked_at = NOW()
        WHERE token_hash = %s
          AND revoked_at IS NULL;
    """

    connection.execute(
        query,
        (token_hash,),
    )

    connection.commit()
