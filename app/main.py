"""Ponto de entrada e orquestrador principal da aplicação."""

import threading
import time

from app.database.connection import create_connection
from app.dashboard.service import DashboardService
from app.model.service import ModelService
from app.simulator.service import SimulatorService


COLLECTION_INTERVAL_SECONDS = 1


def run_simulator() -> None:
    """Executa o simulador."""

    with create_connection() as connection:
        simulator = SimulatorService(
            connection=connection,
            collection_interval=COLLECTION_INTERVAL_SECONDS,
        )

        simulator.run()


def run_model() -> None:
    """Executa o serviço de previsão."""

    model_service = ModelService()
    model_service.run()


def run_dashboard() -> None:
    """Executa o dashboard."""

    dashboard = DashboardService(
        host="127.0.0.1",
        port=8000,
    )

    dashboard.run()


def main() -> None:
    """Inicia todos os serviços da aplicação."""

    print("==============================")
    print("      NoiseSensor")
    print("==============================")

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

    dashboard_thread = threading.Thread(
        target=run_dashboard,
        name="dashboard",
        daemon=True,
    )

    simulator_thread.start()
    model_thread.start()
    dashboard_thread.start()

    print("Simulador iniciado.")
    print("Modelo iniciado.")
    print("Dashboard iniciado.")
    print("Aplicação em execução.")
    print("Dashboard: http://127.0.0.1:8000")

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nEncerrando aplicação...")


if __name__ == "__main__":
    main()
