"""Responsável pela geração das leituras simuladas."""

import random
from datetime import datetime, timezone
from app.simulator.reading import SensorReading
from app.simulator.sensor import Sensor

def generate_reading(sensor: Sensor) -> SensorReading:
    """
    Gera uma leitura simples para o sensor informado.
    O sensor recebido determina o sensor_id da leitura.
    """

    noise_db = round(random.uniform(40.0, 80.0), 2)

    return SensorReading(
        sensor_id=sensor.sensor_id,
        timestamp=datetime.now(timezone.utc),
        noise_db=noise_db,
    )
