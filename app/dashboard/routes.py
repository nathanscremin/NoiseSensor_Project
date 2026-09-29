"""Rotas HTTP do dashboard."""

from fastapi import APIRouter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.database.connection import create_connection
from app.database.repository import (
    get_latest_sensor_readings,
    get_sensor_history,
    get_sensor_predictions,
)

router = APIRouter()

LOCAL_ZONE = ZoneInfo("America/Sao_Paulo")

@router.get("/api/sensors")
def get_sensors():
    """Retorna a leitura mais recente de cada sensor."""

    with create_connection() as connection:
        rows = get_latest_sensor_readings(connection)

    sensors = []

    for row in rows:
        sensors.append(
            {
                "sensor_id": row[0],
                "name": row[1],
                "region": row[2],
                "status": row[3],
                "noise_db": float(row[4]),
                "read_timestamp": row[5].isoformat(),
            }
        )

    return sensors

@router.get("/api/sensors/{sensor_id}/history")
def get_history(sensor_id: int):
    """Retorna o histórico das últimas 24 horas."""

    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=24)

    with create_connection() as connection:
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

@router.get("/api/sensors/{sensor_id}/predictions")
def get_predictions(sensor_id: int):
    """Retorna as previsões atuais de um sensor."""

    with create_connection() as connection:
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
