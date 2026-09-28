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

    A leitura é explicitamente vinculada ao sensor
    através do sensor_id.
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


def get_hourly_readings(
    connection: psycopg.Connection,
    start: datetime,
    end: datetime,
) -> list[tuple]:
    """
    Busca estatísticas horárias das leituras dos sensores.

    O intervalo considera:

        start -> inclusivo
        end   -> exclusivo
    """

    query = """
        SELECT
            sr.sensor_id,
            s.region,

            DATE_TRUNC(
                'hour',
                sr.read_timestamp AT TIME ZONE 'America/Sao_Paulo'
            ) AS hour,

            AVG(sr.noise_db)::double precision
                AS avg_noise_db,

            MIN(sr.noise_db)::double precision
                AS min_noise_db,

            MAX(sr.noise_db)::double precision
                AS max_noise_db,

            STDDEV_POP(sr.noise_db)::double precision
                AS std_noise_db,

            COUNT(*) AS reading_count

        FROM sensors_readings AS sr

        INNER JOIN sensors AS s
            ON s.sensor_id = sr.sensor_id

        WHERE sr.read_timestamp >= %s
          AND sr.read_timestamp < %s

        GROUP BY
            sr.sensor_id,
            s.region,
            hour

        ORDER BY
            sr.sensor_id,
            hour;
    """

    return connection.execute(
        query,
        (start, end),
    ).fetchall()


def create_prediction_run(
    connection: psycopg.Connection,
    model_version: str,
) -> int:
    """
    Cria um registro representando uma execução do modelo
    e retorna o ID dessa execução.
    """

    query = """
        INSERT INTO prediction_runs (
            model_version
        )
        VALUES (%s)
        RETURNING run_id;
    """

    row = connection.execute(
        query,
        (model_version,),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            "Não foi possível criar a execução de previsão."
        )

    return row[0]
