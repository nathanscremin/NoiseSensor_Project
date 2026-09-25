"""Serviço responsável pelo ciclo de simulação."""

import time
import psycopg
from app.database.repository import (
    get_active_sensors,
    insert_reading,
)
from app.simulator.generator import generate_reading
from app.simulator.sensor import Sensor

class SimulatorService:
    """
    Controla a execução do simulador.
    Nesta primeira versão, todos os sensores ativos
    realizam uma coleta a cada 10 segundos.
    """

    def __init__(
        self,
        connection: psycopg.Connection,
        collection_interval: int = 10,
    ) -> None:
        """
        Inicializa o serviço.
        Args:
            connection: conexão com o PostgreSQL.
            collection_interval: intervalo entre ciclos de coleta.
        """

        self.connection = connection
        self.collection_interval = collection_interval
        self.sensors: list[Sensor] = []

    def load_sensors(self) -> None:
        """
        Busca no banco os sensores que estão ativos.
        """

        self.sensors = get_active_sensors(
            self.connection
        )

        if not self.sensors:
            raise RuntimeError(
                "Nenhum sensor ativo foi encontrado no banco."
            )

        print(
            f"{len(self.sensors)} sensor(es) carregado(s)."
        )

        for sensor in self.sensors:
            print(
                f"- Sensor {sensor.sensor_id}: "
                f"{sensor.name}"
            )

    def collect(self) -> None:
        """
        Executa uma rodada de coleta para todos os sensores.
        """

        for sensor in self.sensors:

            reading = generate_reading(sensor)

            insert_reading(
                self.connection,
                sensor_id=reading.sensor_id,
                read_timestamp=reading.timestamp,
                noise_db=reading.noise_db,
            )

            print(
                f"Sensor {reading.sensor_id} → "
                f"{reading.noise_db:.2f} dB"
            )

    def run(self) -> None:
        """
        Executa continuamente o ciclo de coleta.
        """

        self.load_sensors()

        print(
            f"\nSimulador iniciado. "
            f"Intervalo: {self.collection_interval}s\n"
        )

        while True:
            self.collect()

            time.sleep(
                self.collection_interval
            )
