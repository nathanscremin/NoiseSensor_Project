"""Rotas HTTP do dashboard."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.database.connection import create_connection
from app.database.repository import (
    get_latest_sensor_readings,
    get_sensor_history,
    get_sensor_predictions,
    sensor_belongs_to_user,
)


router = APIRouter()

LOCAL_ZONE = ZoneInfo("America/Sao_Paulo")


@router.get("/api/sensors")
def get_sensors(
    current_user: User = Depends(
        get_current_user
    ),
):
    """Retorna os sensores ativos vinculados ao usuário."""

    with create_connection() as connection:
        rows = get_latest_sensor_readings(
            connection,
            current_user.user_id,
        )

    sensors = []

    for row in rows:
        sensors.append(
            {
                "sensor_id": row[0],
                "name": row[1],
                "latitude": float(row[2]),
                "longitude": float(row[3]),
                "region": row[4],
                "status": row[5],
                "noise_db": (
                    float(row[6])
                    if row[6] is not None
                    else None
                ),
                "read_timestamp": (
                    row[7].isoformat()
                    if row[7] is not None
                    else None
                ),
                "alert_state": row[8],
            }
        )

    return sensors


@router.get(
    "/api/sensors/{sensor_id}/history"
)
def get_history(
    sensor_id: int,
    current_user: User = Depends(
        get_current_user
    ),
):
    """Retorna as últimas 24 horas, incluindo a hora corrente."""

    now_local = datetime.now(LOCAL_ZONE)
    current_hour = now_local.replace(
        minute=0,
        second=0,
        microsecond=0,
    )

    start_local = current_hour - timedelta(hours=23)

    start = start_local.astimezone(timezone.utc)
    end = now_local.astimezone(timezone.utc)

    with create_connection() as connection:
        if not sensor_belongs_to_user(
            connection,
            sensor_id,
            current_user.user_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sensor não encontrado.",
            )

        rows = get_sensor_history(
            connection,
            sensor_id,
            start,
            end,
        )

    history = []

    for row in rows:
        history.append(
            {
                "timestamp": row[0].replace(
                    tzinfo=LOCAL_ZONE
                ).isoformat(),
                "avg_noise_db": float(row[1]),
                "min_noise_db": float(row[2]),
                "max_noise_db": float(row[3]),
                "reading_count": row[4],
            }
        )

    return history


@router.get(
    "/api/sensors/{sensor_id}/predictions"
)
def get_predictions(
    sensor_id: int,
    current_user: User = Depends(
        get_current_user
    ),
):
    """Retorna as próximas 24 horas futuras do sensor."""

    with create_connection() as connection:
        if not sensor_belongs_to_user(
            connection,
            sensor_id,
            current_user.user_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sensor não encontrado.",
            )

        rows = get_sensor_predictions(
            connection,
            sensor_id,
        )

    predictions = []

    for row in rows:
        predictions.append(
            {
                "timestamp": row[0].isoformat(),
                "horizon_hours": row[1],
                "predicted_noise_db": float(row[2]),
            }
        )

    return predictions
