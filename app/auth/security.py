"""Funções relacionadas à segurança da autenticação."""

import hashlib
import secrets

from pwdlib import PasswordHash


PASSWORD_HASH = PasswordHash.recommended()

SESSION_COOKIE_NAME = "noisesensor_session"


def hash_password(password: str) -> str:
    """
    Gera um hash seguro para uma senha.

    A senha original nunca é armazenada.
    """

    return PASSWORD_HASH.hash(password)


def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    """
    Verifica se uma senha corresponde ao hash armazenado.
    """

    return PASSWORD_HASH.verify(
        password,
        password_hash,
    )


def generate_token() -> str:
    """
    Gera um token aleatório seguro.

    Usado para sessões e verificação de e-mail.
    """

    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """
    Gera o hash SHA-256 de um token.

    O token original pode ficar no cliente,
    enquanto seu hash fica no banco.
    """

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()
