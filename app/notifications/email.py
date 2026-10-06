"""Envio de e-mails do NoiseSensor."""

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

SMTP_HOST = os.getenv(
    "SMTP_HOST",
    "smtp.gmail.com",
)

SMTP_PORT = int(
    os.getenv(
        "SMTP_PORT",
        "587",
    )
)

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM") or SMTP_USER


def _smtp_configured() -> bool:
    """Retorna True quando todas as credenciais SMTP necessárias existem."""

    return all(
        (
            SMTP_HOST,
            SMTP_PORT,
            SMTP_USER,
            SMTP_PASSWORD,
            MAIL_FROM,
        )
    )


def send_email(
    recipient: str,
    subject: str,
    body: str,
) -> bool:
    """
    Envia um e-mail usando SMTP.

    Retorna True quando o e-mail foi realmente enviado.
    Durante o desenvolvimento local, quando o SMTP não está
    configurado, o conteúdo é exibido no terminal.
    """

    if not _smtp_configured():
        print("\n==============================")
        print("   E-MAIL NÃO CONFIGURADO")
        print("==============================")
        print(f"Destinatário: {recipient}")
        print(f"Assunto: {subject}")
        print(body)
        print("==============================\n")
        return False

    assert SMTP_USER is not None
    assert SMTP_PASSWORD is not None
    assert MAIL_FROM is not None

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = MAIL_FROM
    message["To"] = recipient
    message.set_content(body)

    context = ssl.create_default_context()

    with smtplib.SMTP(
        SMTP_HOST,
        SMTP_PORT,
        timeout=10,
    ) as smtp:
        smtp.starttls(context=context)
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(message)

    return True


def send_verification_email(
    email: str,
    name: str,
    token: str,
) -> bool:
    """Envia o e-mail usado para verificar a conta."""

    verification_url = (
        f"{APP_BASE_URL}/api/auth/verify"
        f"?token={quote(token)}"
    )

    body = f"""Olá, {name}!

Obrigado por criar sua conta no NoiseSensor.

Clique no link abaixo para verificar seu e-mail:

{verification_url}

Esse link possui validade limitada.

Se você não criou essa conta, ignore esta mensagem.
"""

    return send_email(
        recipient=email,
        subject="Verifique sua conta no NoiseSensor",
        body=body,
    )


def send_alert_email(
    recipient: str,
    name: str,
    sensor_name: str,
    region: str,
    event_title: str,
    event_body: str,
) -> bool:
    """Envia uma notificação de alerta por e-mail."""

    body = f"""Olá, {name}!

{event_body}

Sensor: {sensor_name}
Região: {region}

Esta mensagem foi enviada automaticamente pelo NoiseSensor.
"""

    return send_email(
        recipient=recipient,
        subject=f"{event_title} - {sensor_name}",
        body=body,
    )
