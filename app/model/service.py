"""Serviço responsável pelas previsões do modelo."""

from datetime import datetime, timedelta, timezone
from time import sleep
from zoneinfo import ZoneInfo

from app.database.connection import create_connection
from app.database.repository import (
    create_prediction_run,
    get_active_sensors,
    get_hourly_readings,
    insert_predictions,
)

from app.model.aggregation import (
    ensure_hourly_series,
    prepare_hourly_data,
)

from app.model.predictor import (
    forecast_sensor,
    load_model,
    load_model_metadata,
)


LOCAL_ZONE = ZoneInfo(
    "America/Sao_Paulo"
)

FORECAST_HORIZON = 25
HISTORY_HOURS = 24


class ModelService:
    """
    Serviço responsável pela execução do modelo.

    O modelo salvo é carregado uma vez e utilizado
    para gerar novas previsões periodicamente.
    """

    def __init__(self) -> None:
        self.model = load_model()
        self.metadata = load_model_metadata()

        self.model_version = self.metadata[
            "model_version"
        ]

    def collect_history(
        self,
        connection,
    ):
        """
        Busca as últimas 24 horas completas
        para alimentar o modelo.
        """

        now_local = datetime.now(
            LOCAL_ZONE
        )

        end_local = now_local.replace(
            minute=0,
            second=0,
            microsecond=0,
        )

        start_local = (
            end_local
            - timedelta(
                hours=HISTORY_HOURS
            )
        )

        start_utc = (
            start_local
            .astimezone(timezone.utc)
        )

        end_utc = (
            end_local
            .astimezone(timezone.utc)
        )

        rows = get_hourly_readings(
            connection,
            start_utc,
            end_utc,
        )

        hourly = prepare_hourly_data(
            rows
        )

        return ensure_hourly_series(
            hourly
        )

    def predict_once(self) -> None:
        """
        Executa uma rodada completa de previsão
        e salva os resultados no PostgreSQL.
        """

        print(
            "\nIniciando nova rodada de previsão..."
        )

        with create_connection() as connection:

            sensors = get_active_sensors(
                connection
            )

            if not sensors:
                raise RuntimeError(
                    "Nenhum sensor ativo encontrado."
                )

            hourly = self.collect_history(
                connection
            )

            all_predictions = []

            for sensor in sensors:

                sensor_data = hourly[
                    hourly["sensor_id"]
                    == sensor.sensor_id
                ]

                predictions = forecast_sensor(
                    model=self.model,
                    sensor_id=sensor.sensor_id,
                    region=sensor.region,
                    hourly_history=sensor_data,
                    horizon=FORECAST_HORIZON,
                )

                all_predictions.extend(
                    predictions
                )

            if not all_predictions:
                raise RuntimeError(
                    "Nenhuma previsão foi gerada."
                )

            run_id = create_prediction_run(
                connection=connection,
                model_version=self.model_version,
            )

            insert_predictions(
                connection=connection,
                run_id=run_id,
                model_version=self.model_version,
                predictions=all_predictions,
            )

            print(
                f"Previsão concluída."
            )

            print(
                f"Run ID: {run_id}"
            )

            print(
                f"Modelo: {self.model_version}"
            )

            print(
                f"Total de previsões: "
                f"{len(all_predictions)}"
            )

    def wait_until_next_hour(self) -> None:
        """
        Aguarda até o início da próxima hora.
        """

        now = datetime.now(
            LOCAL_ZONE
        )

        next_hour = (
            now.replace(
                minute=0,
                second=0,
                microsecond=0,
            )
            + timedelta(hours=1)
        )

        seconds_to_wait = (
            next_hour - now
        ).total_seconds()

        print(
            f"Próxima previsão em "
            f"{seconds_to_wait:.0f} segundos."
        )

        sleep(
            seconds_to_wait
        )

    def run(self) -> None:
        """
        Mantém o serviço de previsão em execução.

        A primeira rodada acontece imediatamente.
        Depois, uma nova rodada acontece a cada hora.
        """

        print(
            "ModelService iniciado."
        )

        print(
            f"Modelo carregado: "
            f"{self.model_version}"
        )

        while True:

            try:
                self.predict_once()

            except Exception as error:
                print(
                    "\nErro durante a previsão:"
                )

                print(error)

            self.wait_until_next_hour()


if __name__ == "__main__":
    service = ModelService()
    service.run()
