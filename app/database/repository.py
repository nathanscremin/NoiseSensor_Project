"""Operações de leitura e escrita relacionadas aos sensores."""

from datetime import datetime
import psycopg

def get_sensor_by_id(
    connection: psycopg.Connection,
    sensor_id: int,
):
    """
    Busca um sensor pelo seu ID.
    Retorna os dados do sensor quando encontrado.
    Caso contrário, retorna None.
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
        WHERE sensor_id = %s;
    """

    result = connection.execute(query, (sensor_id,)).fetchone()
    return result

def insert_reading(
    connection: psycopg.Connection,
    sensor_id: int,
    read_timestamp: datetime,
    noise_db: float,
) -> None:
    """
    Insere uma nova leitura vinculada a um sensor.
    O sensor_id recebido aqui é justamente o identificador
    do sensor que originou a coleta.
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
