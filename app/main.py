"""Ponto de entrada e orquestrador principal da aplicação."""

import threading
import time

from app.database.connection import create_connection
from app.model.service import ModelService
from app.simulator.service import SimulatorService


COLLECTION_INTERVAL_SECONDS = 10


def run_simulator() -> None:
    """
    Inicializa o serviço de simulação.
    """

    with create_connection() as connection:

        simulator = SimulatorService(
            connection=connection,
            collection_interval=COLLECTION_INTERVAL_SECONDS,
        )

        simulator.run()


def run_model() -> None:
    """
    Inicializa o serviço de previsão.
    """

    model_service = ModelService()

    model_service.run()


def main() -> None:
    """
    Inicializa e coordena os serviços da aplicação.
    """

    print(
        "=============================="
    )

    print(
        " NoiseSensor iniciado"
    )

    print(
        "=============================="
    )

    simulator_thread = threading.Thread(
        target=run_simulator,
        name="simulator",
        daemon=True,
    )

    model_thread = threading.Thread(
        target=run_model,
        name="model",
        daemon=True,
    )

    simulator_thread.start()
    model_thread.start()

    print(
        "Simulador iniciado."
    )

    print(
        "Modelo iniciado."
    )

    print(
        "Aplicação em execução."
    )

    try:

        while True:
            time.sleep(1)

    except KeyboardInterrupt:

        print(
            "\nEncerrando aplicação..."
        )


if __name__ == "__main__":
    main()
