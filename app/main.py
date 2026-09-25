"""Ponto de entrada do simulador inicial."""

import time
from datetime import datetime, timezone

from app.database.connection import create_connection
from app.database.repository import get_sensor_by_id, insert_reading
from app.simulator.generator import generate_noise


# ID do sensor que será utilizado durante esta primeira versão.
SENSOR_ID = 1

# Intervalo entre as coletas simuladas.
COLLECTION_INTERVAL_SECONDS = 10


def main() -> None:
    """Executa o ciclo principal do simulador."""

    # Abre uma conexão com o PostgreSQL.
    with create_connection() as connection:

        # Busca o sensor definido pela configuração.
        sensor = get_sensor_by_id(
            connection,
            SENSOR_ID,
        )

        # Verifica se o sensor realmente existe.
        if sensor is None:
            raise RuntimeError(
                f"Sensor {SENSOR_ID} não encontrado no banco."
            )

        print(
            f"Sensor selecionado: "
            f"{sensor[1]} (ID: {sensor[0]})"
        )

        # Mantemos explicitamente o ID do sensor.
        sensor_id = sensor[0]

        print("Simulador iniciado.")

        while True:
            # Gera uma nova medição.
            noise_db = generate_noise()

            # Obtém o horário atual com timezone.
            read_timestamp = datetime.now(timezone.utc)

            # Salva a leitura vinculada ao sensor.
            insert_reading(
                connection,
                sensor_id=sensor_id,
                read_timestamp=read_timestamp,
                noise_db=noise_db,
            )

            print(
                f"[{read_timestamp.isoformat()}] "
                f"Sensor {sensor_id} → "
                f"{noise_db:.2f} dB"
            )

            # Aguarda até a próxima coleta.
            time.sleep(COLLECTION_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
