"""Representação de um sensor utilizado pelo simulador."""

from dataclasses import dataclass

@dataclass
class SimulatedSensor:
    """
    Representa um sensor que está sendo simulado.
    O sensor_id é sua identidade dentro do banco.
    Todas as leituras produzidas por este objeto utilizarão
    esse mesmo identificador.
    """

    sensor_id: int
    name: str
    latitude: float
    longitude: float
    region: str
    status: str
    user_id: int
