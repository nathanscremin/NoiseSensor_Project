"""Coordenação dos canais de notificação do NoiseSensor."""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
import threading

import psycopg

from app.alerts.models import AlertEvent, AlertEventType
from app.notifications.email import send_alert_email
from app.notifications.telegram import send_message


LOCAL_ZONE = ZoneInfo("America/Sao_Paulo")


@dataclass(frozen=True)
class NotificationTarget:
    """Dados necessários para notificar o proprietário de um sensor."""

    name: str
    email: str
    email_verified: bool
    telegram_chat_id: int | None
    sensor_name: str
    region: str


def _get_notification_targets(
    connection: psycopg.Connection,
    sensor_id: int,
) -> list[NotificationTarget]:
    """Busca todos os usuários vinculados ao sensor."""

    rows = connection.execute(
        """
        SELECT
            u.name,
            u.email,
            u.email_verified,
            u.telegram_chat_id,
            s.name,
            s.region
        FROM sensors AS s
        INNER JOIN sensor_users AS su
            ON su.sensor_id = s.sensor_id
        INNER JOIN users AS u
            ON u.user_id = su.user_id
        WHERE s.sensor_id = %s
        ORDER BY u.user_id;
        """,
        (sensor_id,),
    ).fetchall()

    return [
        NotificationTarget(
            name=row[0],
            email=row[1],
            email_verified=row[2],
            telegram_chat_id=row[3],
            sensor_name=row[4],
            region=row[5],
        )
        for row in rows
    ]


def _format_timestamp(timestamp: datetime | None) -> str:
    """Formata timestamps de alerta para as mensagens."""

    if timestamp is None:
        return "Não informado"

    return timestamp.astimezone(LOCAL_ZONE).strftime(
        "%d/%m/%Y %H:%M:%S"
    )


def _format_duration_seconds(
    started_at: datetime,
    ended_at: datetime | None,
) -> str:
    """Retorna a duração do episódio de alerta em segundos."""

    if ended_at is None:
        return "Em andamento"

    seconds = max(
        0,
        int((ended_at - started_at).total_seconds()),
    )

    minutes, remainder = divmod(seconds, 60)

    if minutes:
        return f"{minutes} min {remainder} s"

    return f"{remainder} s"


def _build_notification(
    event: AlertEvent,
    target: NotificationTarget,
) -> tuple[str, str]:
    """Monta assunto e corpo comuns aos canais de notificação."""

    alert = event.alert

    if event.event_type == AlertEventType.STARTED:
        title = "Alerta de ruído ativado"
        body = f"""Um novo alerta de ruído foi ativado.

Início: {_format_timestamp(alert.started_at)}
Limite: {alert.threshold_db:.2f} dB
Pico registrado: {alert.peak_noise_db:.2f} dB
"""
        return title, body

    title = "Alerta de ruído encerrado"
    body = f"""O alerta de ruído foi encerrado.

Início: {_format_timestamp(alert.started_at)}
Fim: {_format_timestamp(alert.ended_at)}
Duração: {_format_duration_seconds(alert.started_at, alert.ended_at)}
Limite: {alert.threshold_db:.2f} dB
Pico registrado: {alert.peak_noise_db:.2f} dB
"""
    return title, body


def _send_notifications(
    target: NotificationTarget,
    title: str,
    body: str,
) -> None:
    """Entrega a mesma notificação pelos canais configurados."""

    if target.email_verified:
        try:
            send_alert_email(
                recipient=target.email,
                name=target.name,
                sensor_name=target.sensor_name,
                region=target.region,
                event_title=title,
                event_body=body,
            )
        except Exception as error:
            print(
                "[NOTIFICAÇÃO] Erro ao enviar e-mail: "
                f"{error}"
            )

    if target.telegram_chat_id is not None:
        try:
            send_message(
                chat_id=target.telegram_chat_id,
                text=(
                    f"{title}\n\n"
                    f"{body}\n"
                    f"Sensor: {target.sensor_name}\n"
                    f"Região: {target.region}"
                ),
            )
        except Exception as error:
            print(
                "[NOTIFICAÇÃO] Erro ao enviar Telegram: "
                f"{error}"
            )


class NotificationService:
    """Dispara notificações quando um alerta muda de estado."""

    def notify_alert_event(
        self,
        connection: psycopg.Connection,
        event: AlertEvent,
    ) -> None:
        """Prepara e envia a notificação sem bloquear o simulador."""

        targets = _get_notification_targets(
            connection,
            event.alert.sensor_id,
        )

        if not targets:
            print(
                "[NOTIFICAÇÃO] Sensor sem usuários associados: "
                f"{event.alert.sensor_id}"
            )
            return

        for target in targets:
            title, body = _build_notification(
                event,
                target,
            )

            thread = threading.Thread(
                target=_send_notifications,
                args=(target, title, body),
                name="notification",
                daemon=True,
            )
            thread.start()
