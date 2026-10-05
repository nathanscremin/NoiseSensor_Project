"""Schemas HTTP usados pelas rotas de alertas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.alerts.models import AlertState


class AlertSettingsRequest(BaseModel):
    """Configuração de alerta enviada pelo usuário."""

    threshold_db: float = Field(
        gt=0,
        le=200,
    )

    trigger_duration_seconds: int = Field(
        ge=1,
        le=86400,
    )

    recovery_duration_seconds: int = Field(
        ge=1,
        le=86400,
    )


class AlertSettingsResponse(BaseModel):
    """Configuração e estado atual do sensor."""

    sensor_id: int
    threshold_db: float
    trigger_duration_seconds: int
    recovery_duration_seconds: int
    state: AlertState
    condition_started_at: datetime | None
    recovery_started_at: datetime | None
    current_alert_id: int | None


class AlertHistoryItem(BaseModel):
    """Um episódio do histórico de alertas."""

    alert_id: int
    sensor_id: int
    threshold_db: float
    started_at: datetime
    ended_at: datetime | None
    peak_noise_db: float
