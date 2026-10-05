"""Responsável pela geração das leituras simuladas."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.model.historical_generator import calculate_noise
from app.simulator.reading import SensorReading
from app.simulator.sensor import Sensor


LOCAL_ZONE = ZoneInfo("America/Sao_Paulo")


def generate_reading(sensor: Sensor) -> SensorReading:
    """Gera uma leitura usando o mesmo padrão sintético do histórico."""

    timestamp = datetime.now(timezone.utc)
    local_timestamp = timestamp.astimezone(LOCAL_ZONE)

    noise_db = calculate_noise(
        sensor_name=sensor.name,
        timestamp=local_timestamp,
    )

    return SensorReading(
        sensor_id=sensor.sensor_id,
        timestamp=timestamp,
        noise_db=noise_db,
    )
