"""Ponto de entrada do simulador."""

from app.database.connection import create_connection
from app.simulator.service import SimulatorService

# Intervalo entre os ciclos de coleta.
COLLECTION_INTERVAL_SECONDS = 10

def main() -> None:
    """
    Inicializa o simulador.
    """

    with create_connection() as connection:

        simulator = SimulatorService(
            connection=connection,
            collection_interval=COLLECTION_INTERVAL_SECONDS,
        )

        simulator.run()

if __name__ == "__main__":
    main()
