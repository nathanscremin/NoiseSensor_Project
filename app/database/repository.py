"""Operações de leitura e escrita no PostgreSQL."""

from datetime import datetime

import psycopg

from app.simulator.sensor import Sensor


def sensor_belongs_to_user(
    connection: psycopg.Connection,
    sensor_id: int,
    user_id: int,
) -> bool:
    """Verifica se um sensor pertence ao usuário informado."""

    row = connection.execute(
        """
        SELECT 1
        FROM sensors
        WHERE sensor_id = %s
          AND user_id = %s;
        """,
        (sensor_id, user_id),
    ).fetchone()

    return row is not None


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


def insert_predictions(
    connection: psycopg.Connection,
    run_id: int,
    model_version: str,
    predictions,
) -> None:
    """
    Salva o histórico e substitui atomicamente as previsões atuais.

    O histórico permanece em ``predictions``. A tabela
    ``current_predictions`` representa somente a execução mais recente,
    evitando que rodadas antigas continuem sendo exibidas no dashboard.
    """

    history_query = """
        INSERT INTO predictions (
            run_id,
            sensor_id,
            target_timestamp,
            horizon_hours,
            predicted_noise_db
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s
        );
    """

    current_query = """
        INSERT INTO current_predictions (
            run_id,
            sensor_id,
            target_timestamp,
            horizon_hours,
            predicted_noise_db,
            run_timestamp,
            model_version
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            NOW(),
            %s
        );
    """

    rows = [
        (
            run_id,
            prediction.sensor_id,
            prediction.target_timestamp,
            prediction.horizon_hours,
            prediction.predicted_noise_db,
        )
        for prediction in predictions
    ]

    if not rows:
        raise ValueError(
            "Nenhuma previsão foi fornecida para salvar."
        )

    # A exclusão e a nova inserção acontecem antes do commit.
    # Requisições do dashboard continuam vendo o conjunto anterior
    # até que o novo conjunto esteja completamente pronto.
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM current_predictions;")
        cursor.executemany(history_query, rows)
        current_rows = [
            row + (model_version,)
            for row in rows
        ]
        cursor.executemany(current_query, current_rows)

    connection.commit()

def get_latest_sensor_readings(
    connection: psycopg.Connection,
    user_id: int,
) -> list[tuple]:
    """Retorna os sensores ativos do usuário e suas últimas leituras."""

    query = """
        SELECT
            s.sensor_id,
            s.name,
            s.latitude,
            s.longitude,
            s.region,
            s.status,
            sr.noise_db,
            sr.read_timestamp,
            COALESCE(sas.state, 'normal') AS alert_state
        FROM sensors AS s
        LEFT JOIN LATERAL (
            SELECT
                sr2.noise_db,
                sr2.read_timestamp
            FROM sensors_readings AS sr2
            WHERE sr2.sensor_id = s.sensor_id
            ORDER BY sr2.read_timestamp DESC
            LIMIT 1
        ) AS sr ON TRUE
        LEFT JOIN sensor_alert_states AS sas
            ON sas.sensor_id = s.sensor_id
        WHERE s.status = 'active'
          AND s.user_id = %s
        ORDER BY s.sensor_id;
    """

    return connection.execute(
        query,
        (user_id,),
    ).fetchall()

def get_sensor_history(
    connection: psycopg.Connection,
    sensor_id: int,
    start: datetime,
    end: datetime,
) -> list[tuple]:
    """Retorna o histórico horário de um sensor."""

    query = """
        SELECT
            DATE_TRUNC(
                'hour',
                read_timestamp AT TIME ZONE 'America/Sao_Paulo'
            ) AS hour,
            AVG(noise_db)::double precision AS avg_noise_db,
            MIN(noise_db)::double precision AS min_noise_db,
            MAX(noise_db)::double precision AS max_noise_db,
            COUNT(*) AS reading_count
        FROM sensors_readings
        WHERE sensor_id = %s
          AND read_timestamp >= %s
          AND read_timestamp < %s
        GROUP BY hour
        ORDER BY hour;
    """

    return connection.execute(
        query,
        (sensor_id, start, end),
    ).fetchall()

def get_sensor_predictions(
    connection: psycopg.Connection,
    sensor_id: int,
) -> list[tuple]:
    """Retorna somente as próximas 24 horas futuras do sensor."""

    query = """
        SELECT
            target_timestamp,
            horizon_hours,
            predicted_noise_db
        FROM current_predictions
        WHERE sensor_id = %s
          AND target_timestamp > (
              DATE_TRUNC(
                  'hour',
                  NOW() AT TIME ZONE 'America/Sao_Paulo'
              ) AT TIME ZONE 'America/Sao_Paulo'
          )
        ORDER BY target_timestamp
        LIMIT 24;
    """

    return connection.execute(
        query,
        (sensor_id,),
    ).fetchall()
