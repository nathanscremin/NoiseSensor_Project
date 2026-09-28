"""Geração de histórico sintético para treinamento do modelo."""

import random
from datetime import datetime, timedelta, timezone

import psycopg

from app.database.connection import create_connection
from app.database.repository import get_active_sensors


HISTORY_DAYS = 365

SAMPLES_PER_HOUR = 6

MINUTES_BETWEEN_SAMPLES = 10

RANDOM_SEED = 42

INSERT_BATCH_SIZE = 5000


def calculate_noise(
    sensor_name: str,
    timestamp: datetime,
) -> float:
    """
    Gera um valor sintético de ruído baseado
    no horário, dia da semana e sensor.

    O resultado não representa medições reais.
    Seu objetivo é criar padrões úteis para testar
    o pipeline de machine learning.
    """

    hour = timestamp.hour

    weekday = timestamp.weekday()

    # --------------------------------------------------
    # Nível base por sensor
    # --------------------------------------------------

    base_by_sensor = {
        "Sensor Centro": 66.0,
        "Sensor Industrial": 72.0,
        "Sensor Residencial": 58.0,
    }

    base_noise = base_by_sensor.get(
        sensor_name,
        62.0,
    )

    # --------------------------------------------------
    # Padrão diário
    # --------------------------------------------------

    daily_effect = 0.0

    # Madrugada
    if 0 <= hour < 6:
        daily_effect = -8.0

    # Manhã
    elif 6 <= hour < 9:
        daily_effect = 5.0

    # Horário comercial
    elif 9 <= hour < 12:
        daily_effect = 2.0

    # Almoço
    elif 12 <= hour < 14:
        daily_effect = 4.0

    # Tarde
    elif 14 <= hour < 18:
        daily_effect = 3.0

    # Fim do dia
    elif 18 <= hour < 22:
        daily_effect = 5.0

    # Noite
    else:
        daily_effect = -2.0

    # --------------------------------------------------
    # Padrão semanal
    # --------------------------------------------------

    weekly_effect = 0.0

    if weekday >= 5:
        # Fim de semana
        weekly_effect = -3.0

    # --------------------------------------------------
    # Particularidades por sensor
    # --------------------------------------------------

    sensor_effect = 0.0

    if sensor_name == "Sensor Industrial":

        if weekday < 5 and 7 <= hour < 18:
            sensor_effect += 5.0

        if weekday >= 5:
            sensor_effect -= 4.0

    elif sensor_name == "Sensor Residencial":

        if 18 <= hour < 23:
            sensor_effect += 4.0

        if 0 <= hour < 6:
            sensor_effect -= 2.0

    elif sensor_name == "Sensor Centro":

        if 7 <= hour < 20:
            sensor_effect += 3.0

    # --------------------------------------------------
    # Ruído aleatório
    # --------------------------------------------------

    random_effect = random.gauss(
        mu=0.0,
        sigma=2.0,
    )

    noise = (
        base_noise
        + daily_effect
        + weekly_effect
        + sensor_effect
        + random_effect
    )

    # Mantém os valores dentro de uma faixa razoável
    noise = max(
        35.0,
        min(noise, 95.0),
    )

    return round(
        noise,
        2,
    )


def generate_rows(
    sensors,
    start: datetime,
    end: datetime,
):
    """
    Gera as leituras sintéticas no intervalo informado.
    """

    timestamp = start

    while timestamp < end:

        for sensor in sensors:

            noise = calculate_noise(
                sensor_name=sensor.name,
                timestamp=timestamp,
            )

            yield (
                sensor.sensor_id,
                timestamp,
                noise,
            )

        timestamp += timedelta(
            minutes=MINUTES_BETWEEN_SAMPLES
        )


def insert_historical_data(
    connection: psycopg.Connection,
    rows,
) -> int:
    """
    Insere as leituras em lotes no PostgreSQL.
    """

    query = """
        INSERT INTO sensors_readings (
            sensor_id,
            read_timestamp,
            noise_db
        )
        VALUES (%s, %s, %s);
    """

    total_inserted = 0

    batch = []

    with connection.cursor() as cursor:

        for row in rows:

            batch.append(row)

            if len(batch) >= INSERT_BATCH_SIZE:

                cursor.executemany(
                    query,
                    batch,
                )

                total_inserted += len(batch)

                batch.clear()

                print(
                    f"{total_inserted} "
                    "leituras inseridas..."
                )

        if batch:

            cursor.executemany(
                query,
                batch,
            )

            total_inserted += len(batch)

    connection.commit()

    return total_inserted


def main() -> None:
    """
    Gera e salva o histórico sintético.
    """

    random.seed(
        RANDOM_SEED
    )

    end = datetime.now(
        timezone.utc
    )

    start = (
        end
        - timedelta(
            days=HISTORY_DAYS
        )
    )

    print(
        "Gerando histórico sintético."
    )

    print(
        f"Início: {start}"
    )

    print(
        f"Fim:    {end}"
    )

    with create_connection() as connection:

        sensors = get_active_sensors(
            connection
        )

        if not sensors:

            raise RuntimeError(
                "Nenhum sensor ativo encontrado."
            )

        print(
            f"\nSensores encontrados: "
            f"{len(sensors)}"
        )

        for sensor in sensors:

            print(
                f"- {sensor.sensor_id}: "
                f"{sensor.name}"
            )

        rows = generate_rows(
            sensors=sensors,
            start=start,
            end=end,
        )

        total = insert_historical_data(
            connection,
            rows,
        )

    print(
        f"\nConcluído. "
        f"{total} leituras inseridas."
    )


if __name__ == "__main__":
    main()
