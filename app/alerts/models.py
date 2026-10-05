"""Modelos usados pelo sistema de alertas."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AlertState(str, Enum):
    """Estados possíveis do ciclo de alerta de um sensor."""

    NORMAL = "normal"
    PENDING_ALERT = "pending_alert"
    ALERT = "alert"
    PENDING_RECOVERY = "pending_recovery"


class AlertEventType(str, Enum):
    """Eventos gerados quando o estado de alerta muda."""

    STARTED = "started"
    ENDED = "ended"


@dataclass(frozen=True)
class AlertSettings:
    """Configurações de alerta de um sensor."""

    sensor_id: int
    threshold_db: float
    trigger_duration_seconds: int
    recovery_duration_seconds: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class AlertStateRecord:
    """Estado atual do ciclo de alerta de um sensor."""

    sensor_id: int
    state: AlertState
    condition_started_at: datetime | None
    recovery_started_at: datetime | None
    current_alert_id: int | None
    updated_at: datetime


@dataclass(frozen=True)
class AlertRecord:
    """Representa um episódio completo de alerta."""

    alert_id: int
    sensor_id: int
    threshold_db: float
    started_at: datetime
    ended_at: datetime | None
    peak_noise_db: float
    created_at: datetime


@dataclass(frozen=True)
class AlertEvent:
    """Evento de entrada ou saída de um alerta."""

    event_type: AlertEventType
    alert: AlertRecord
