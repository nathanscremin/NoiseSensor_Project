"""Serviço responsável pelo ciclo de simulação."""

import time
import psycopg
from app.database.repository import (
    get_active_sensors,
    insert_reading,
)
from app.alerts.models import AlertEventType
from app.alerts.service import AlertService
from app.simulator.generator import generate_reading
from app.simulator.sensor import Sensor

class SimulatorService:
    """
    Controla a execução do simulador.
    Nesta primeira versão, todos os sensores ativos
    realizam uma coleta a cada segundo.
    """

    def __init__(
        self,
        connection: psycopg.Connection,
        collection_interval: float = 1.0,
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
        self.alert_service = AlertService()

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

            alert_event = self.alert_service.process_reading(
                self.connection,
                reading,
            )

            print(
                f"Sensor {reading.sensor_id} → "
                f"{reading.noise_db:.2f} dB"
            )

            if alert_event is not None:
                if alert_event.event_type == AlertEventType.STARTED:
                    print(
                        f"[ALERTA] Sensor {reading.sensor_id} entrou em alerta. "
                        f"Limite: {alert_event.alert.threshold_db:.2f} dB | "
                        f"Pico: {alert_event.alert.peak_noise_db:.2f} dB"
                    )
                elif alert_event.event_type == AlertEventType.ENDED:
                    print(
                        f"[ALERTA] Sensor {reading.sensor_id} saiu do alerta. "
                        f"Pico: {alert_event.alert.peak_noise_db:.2f} dB"
                    )

    def run(self) -> None:
        """
        Executa continuamente o ciclo de coleta.
        """

        self.load_sensors()

        print(
            f"\nSimulador iniciado. "
            f"Intervalo: {self.collection_interval:g}s\n"
        )

        while True:
            cycle_started = time.monotonic()

            self.collect()

            next_cycle = (
                cycle_started
                + self.collection_interval
            )
            sleep_time = next_cycle - time.monotonic()

            if sleep_time > 0:
                time.sleep(sleep_time)
