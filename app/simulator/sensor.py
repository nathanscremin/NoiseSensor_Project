"""Modelo que representa um sensor do sistema."""

from dataclasses import dataclass


@dataclass
class Sensor:
    """Representa um sensor cadastrado no banco de dados."""

    sensor_id: int
    name: str
    latitude: float
    longitude: float
    region: str
    status: str
