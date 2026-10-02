"""Envio de e-mails relacionados à autenticação."""

import os
import smtplib
import ssl

from email.message import EmailMessage
from urllib.parse import quote

from dotenv import load_dotenv


load_dotenv()


APP_BASE_URL = os.getenv(
    "APP_BASE_URL",
    "http://127.0.0.1:8000",
)

SMTP_HOST = os.getenv("SMTP_HOST")

SMTP_PORT = int(
    os.getenv(
        "SMTP_PORT",
        "587",
    )
)

SMTP_USER = os.getenv("SMTP_USER")

SMTP_PASSWORD = os.getenv(
    "SMTP_PASSWORD"
)

MAIL_FROM = os.getenv(
    "MAIL_FROM"
)


def send_verification_email(
    email: str,
    name: str,
    token: str,
) -> None:
    """
    Envia um e-mail de verificação.

    Durante o desenvolvimento local, caso o SMTP não
    esteja configurado, o link é exibido no terminal.
    """

    verification_url = (
        f"{APP_BASE_URL}/api/auth/verify"
        f"?token={quote(token)}"
    )

    # ------------------------------------------------
    # Modo de desenvolvimento
    # ------------------------------------------------

    if not all(
        (
            SMTP_HOST,
            SMTP_USER,
            SMTP_PASSWORD,
            MAIL_FROM,
        )
    ):
        print("\n==============================")
        print("   VERIFICAÇÃO DE E-MAIL")
        print("==============================")
        print(f"Usuário: {name}")
        print(f"E-mail: {email}")
        print(f"Link: {verification_url}")
        print("==============================\n")

        return

    # ------------------------------------------------
    # Depois da validação acima, o Python consegue
    # tratar essas variáveis como valores existentes.
    # ------------------------------------------------

    assert SMTP_HOST is not None
    assert SMTP_USER is not None
    assert SMTP_PASSWORD is not None
    assert MAIL_FROM is not None

    # ------------------------------------------------
    # Montagem da mensagem
    # ------------------------------------------------

    message = EmailMessage()

    message["Subject"] = (
        "Verifique sua conta no NoiseSensor"
    )

    message["From"] = MAIL_FROM

    message["To"] = email

    message.set_content(
        f"""
Olá, {name}!

Obrigado por criar sua conta no NoiseSensor.

Clique no link abaixo para verificar seu e-mail:

{verification_url}

Esse link possui validade limitada.

Se você não criou essa conta, ignore esta mensagem.
"""
    )

    # ------------------------------------------------
    # Conexão com o servidor SMTP
    # ------------------------------------------------

    context = ssl.create_default_context()

    with smtplib.SMTP(
        SMTP_HOST,
        SMTP_PORT,
        timeout=10,
    ) as smtp:

        smtp.starttls(
            context=context
        )

        smtp.login(
            SMTP_USER,
            SMTP_PASSWORD,
        )

        smtp.send_message(
            message
        )
