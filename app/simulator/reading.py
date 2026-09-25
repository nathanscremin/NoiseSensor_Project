"""Modelo que representa uma leitura de um sensor."""

from dataclasses import dataclass
from datetime import datetime

@dataclass
class SensorReading:
    """
    Representa uma única leitura produzida por um sensor.
    """

    sensor_id: int
    timestamp: datetime
    noise_db: float
