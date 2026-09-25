"""Operações de leitura e escrita no PostgreSQL."""

from datetime import datetime
import psycopg
from app.simulator.sensor import Sensor


def get_active_sensors(
    connection: psycopg.Connection,
) -> list[Sensor]:
    """
    Busca todos os sensores ativos cadastrados no banco.
    """

    query = """
        SELECT
            sensor_id,
            name,
            latitude,
            longitude,
            region,
            status,
            user_id
        FROM sensors
        WHERE status = 'active'
        ORDER BY sensor_id;
    """

    rows = connection.execute(query).fetchall()

    sensors = []

    for row in rows:
        sensors.append(
            Sensor(
                sensor_id=row[0],
                name=row[1],
                latitude=float(row[2]),
                longitude=float(row[3]),
                region=row[4],
                status=row[5],
                user_id=row[6],
            )
        )

    return sensors


def insert_reading(
    connection: psycopg.Connection,
    sensor_id: int,
    read_timestamp: datetime,
    noise_db: float,
) -> None:
    """
    Salva uma leitura no banco.

    A leitura é explicitamente vinculada ao sensor através
    do sensor_id.
    """

    query = """
        INSERT INTO sensors_readings (
            sensor_id,
            read_timestamp,
            noise_db
        )
        VALUES (%s, %s, %s);
    """

    connection.execute(
        query,
        (
            sensor_id,
            read_timestamp,
            noise_db,
        ),
    )

    connection.commit()
