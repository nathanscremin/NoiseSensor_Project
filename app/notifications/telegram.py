"""Integração com o Bot API do Telegram."""

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from app.auth.repository import complete_telegram_link
from app.auth.security import hash_token
from app.database.connection import create_connection


load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "").lstrip("@").strip()
TELEGRAM_API_BASE = (
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    if TELEGRAM_BOT_TOKEN
    else None
)

POLL_TIMEOUT_SECONDS = 25
RETRY_DELAY_SECONDS = 5


def is_configured() -> bool:
    """Informa se o token do bot foi configurado."""

    return bool(
        TELEGRAM_BOT_TOKEN
        and TELEGRAM_BOT_USERNAME
        and TELEGRAM_API_BASE
    )


def get_connection_url(token: str) -> str:
    """Gera o deep link usado para vincular o Telegram à conta."""

    if not TELEGRAM_BOT_USERNAME:
        raise RuntimeError(
            "TELEGRAM_BOT_USERNAME não foi configurado."
        )

    return (
        f"https://t.me/{TELEGRAM_BOT_USERNAME}"
        f"?start={token}"
    )


def _api_request(
    method: str,
    payload: dict | None = None,
    http_timeout: float = 35,
) -> dict:
    """Executa uma chamada HTTP simples à Bot API."""

    if TELEGRAM_API_BASE is None:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN não foi configurado."
        )

    url = f"{TELEGRAM_API_BASE}/{method}"

    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        url=url,
        data=data,
        headers=headers,
        method="POST" if payload is not None else "GET",
    )

    with urlopen(
        request,
        timeout=http_timeout,
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    if not result.get("ok"):
        raise RuntimeError(
            result.get(
                "description",
                "Erro desconhecido na Bot API.",
            )
        )

    return result


def send_message(
    chat_id: int,
    text: str,
) -> None:
    """Envia uma mensagem para um chat do Telegram."""

    _api_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
        },
        http_timeout=15,
    )


def _handle_update(
    update: dict,
) -> None:
    """Processa um update e procura um comando /start de vinculação."""

    message = update.get("message")

    if not isinstance(message, dict):
        return

    chat = message.get("chat")
    text = message.get("text")

    if not isinstance(chat, dict) or not isinstance(text, str):
        return

    if chat.get("type") != "private":
        return

    parts = text.strip().split(maxsplit=1)

    if not parts:
        return

    command = parts[0].split("@", maxsplit=1)[0].lower()

    if command != "/start" or len(parts) != 2:
        return

    link_token = parts[1].strip()

    if not link_token:
        return

    link_result = "invalid"
    chat_id = chat.get("id")

    if not isinstance(chat_id, int):
        return

    with create_connection() as connection:
        link_result, _ = complete_telegram_link(
            connection=connection,
            token_hash=hash_token(link_token),
            chat_id=chat_id,
        )

    if link_result == "linked":
        send_message(
            chat_id=chat_id,
            text=(
                "Telegram vinculado com sucesso ao NoiseSensor.\n\n"
                "Você receberá aqui os alertas de ruído da sua conta."
            ),
        )
        return

    if link_result == "already_linked":
        send_message(
            chat_id=chat_id,
            text=(
                "Este Telegram já está vinculado a outra conta do "
                "NoiseSensor."
            ),
        )
        return

    # Token inexistente, expirado ou já utilizado.
    send_message(
        chat_id=chat_id,
        text=(
            "Não foi possível vincular este Telegram. "
            "Gere um novo link pelo dashboard e tente novamente."
        ),
    )


def _poll_updates(offset: int | None) -> int | None:
    """Busca e processa os updates pendentes do bot."""

    result = _api_request(
        "getUpdates",
        {
            "timeout": POLL_TIMEOUT_SECONDS,
            "allowed_updates": ["message"],
            **(
                {"offset": offset}
                if offset is not None
                else {}
            ),
        },
        http_timeout=POLL_TIMEOUT_SECONDS + 10,
    )

    next_offset = offset

    for update in result.get("result", []):
        update_id = update.get("update_id")

        if isinstance(update_id, int):
            next_offset = update_id + 1

        try:
            _handle_update(update)
        except Exception as error:
            print(
                "[TELEGRAM] Erro ao processar update: "
                f"{error}"
            )

    return next_offset


class TelegramPollingService:
    """Mantém o long polling do bot para receber /start de vinculação."""

    def run(self) -> None:
        """Executa continuamente o recebimento de atualizações."""

        if not is_configured():
            print(
                "[TELEGRAM] Integração desativada: "
                "configure TELEGRAM_BOT_TOKEN e TELEGRAM_BOT_USERNAME."
            )
            return

        print(
            f"[TELEGRAM] Bot @{TELEGRAM_BOT_USERNAME} iniciado."
        )

        offset = None

        while True:
            try:
                offset = _poll_updates(offset)

            except (HTTPError, URLError, TimeoutError) as error:
                print(
                    "[TELEGRAM] Erro de comunicação: "
                    f"{error}"
                )
                time.sleep(RETRY_DELAY_SECONDS)

            except Exception as error:
                print(
                    "[TELEGRAM] Erro inesperado: "
                    f"{error}"
                )
                time.sleep(RETRY_DELAY_SECONDS)
