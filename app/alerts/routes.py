"""Rotas HTTP de configuração e histórico dos alertas."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.alerts.models import AlertState
from app.alerts.repository import (
    get_alert_history,
    get_or_create_alert_settings,
    get_or_create_alert_state,
    sensor_belongs_to_user,
    update_alert_settings,
)
from app.alerts.schemas import (
    AlertHistoryItem,
    AlertSettingsRequest,
    AlertSettingsResponse,
)
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.database.connection import create_connection


router = APIRouter(tags=["alerts"])


def _ensure_sensor_access(
    connection,
    sensor_id: int,
    user_id: int,
) -> None:
    if not sensor_belongs_to_user(
        connection,
        sensor_id,
        user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sensor não encontrado.",
        )


def _build_settings_response(
    settings,
    state,
) -> AlertSettingsResponse:
    return AlertSettingsResponse(
        sensor_id=settings.sensor_id,
        threshold_db=settings.threshold_db,
        trigger_duration_seconds=settings.trigger_duration_seconds,
        recovery_duration_seconds=settings.recovery_duration_seconds,
        state=state.state,
        condition_started_at=state.condition_started_at,
        recovery_started_at=state.recovery_started_at,
        current_alert_id=state.current_alert_id,
    )


@router.get(
    "/api/sensors/{sensor_id}/alert-settings",
    response_model=AlertSettingsResponse,
)
def get_settings(
    sensor_id: int,
    current_user: User = Depends(get_current_user),
) -> AlertSettingsResponse:
    """Retorna a configuração e o estado atual do alerta."""

    with create_connection() as connection:
        _ensure_sensor_access(
            connection,
            sensor_id,
            current_user.user_id,
        )

        settings = get_or_create_alert_settings(
            connection,
            sensor_id,
        )
        state = get_or_create_alert_state(
            connection,
            sensor_id,
        )

        return _build_settings_response(
            settings,
            state,
        )


@router.put(
    "/api/sensors/{sensor_id}/alert-settings",
    response_model=AlertSettingsResponse,
)
def save_settings(
    sensor_id: int,
    data: AlertSettingsRequest,
    current_user: User = Depends(get_current_user),
) -> AlertSettingsResponse:
    """Atualiza a configuração de alerta do sensor."""

    with create_connection() as connection:
        _ensure_sensor_access(
            connection,
            sensor_id,
            current_user.user_id,
        )

        get_or_create_alert_settings(
            connection,
            sensor_id,
        )

        settings = update_alert_settings(
            connection,
            sensor_id=sensor_id,
            threshold_db=data.threshold_db,
            trigger_duration_seconds=data.trigger_duration_seconds,
            recovery_duration_seconds=data.recovery_duration_seconds,
        )

        state = get_or_create_alert_state(
            connection,
            sensor_id,
        )

        return _build_settings_response(
            settings,
            state,
        )


@router.get(
    "/api/sensors/{sensor_id}/alerts",
    response_model=list[AlertHistoryItem],
)
def get_history(
    sensor_id: int,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    current_user: User = Depends(get_current_user),
) -> list[AlertHistoryItem]:
    """Retorna o histórico recente de alertas do sensor."""

    with create_connection() as connection:
        _ensure_sensor_access(
            connection,
            sensor_id,
            current_user.user_id,
        )

        alerts = get_alert_history(
            connection,
            sensor_id,
            limit,
        )

    return [
        AlertHistoryItem(
            alert_id=alert.alert_id,
            sensor_id=alert.sensor_id,
            threshold_db=alert.threshold_db,
            started_at=alert.started_at,
            ended_at=alert.ended_at,
            peak_noise_db=alert.peak_noise_db,
        )
        for alert in alerts
    ]
