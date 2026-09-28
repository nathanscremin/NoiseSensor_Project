"""Serviço de inferência do modelo."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.database.connection import create_connection
from app.database.repository import (
    get_active_sensors,
    get_hourly_readings,
)

from app.model.aggregation import (
    ensure_hourly_series,
    prepare_hourly_data,
)

from app.model.predictor import (
    load_model,
    forecast_sensor,
)


LOCAL_ZONE = ZoneInfo(
    "America/Sao_Paulo"
)

FORECAST_HORIZON = 24
HISTORY_HOURS = 24


class ModelService:
    """
    Serviço responsável pela execução periódica
    das previsões.
    """

    def __init__(self):
        self.model = load_model()

    def collect_history(self, connection):
        """
        Busca as últimas 24 horas completas.
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
            - timedelta(hours=HISTORY_HOURS)
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

    def predict(self):
        """
        Executa uma rodada completa de previsão.
        """

        with create_connection() as connection:

            sensors = get_active_sensors(
                connection
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

            return all_predictions


def main():
    """
    Ponto de entrada do serviço de inferência.
    """

    service = ModelService()

    print(
        "Serviço de previsão iniciado."
    )

    # Inicialmente faremos uma única execução
    # para testar toda a integração.
    predictions = service.predict()

    for prediction in predictions:

        print(
            f"Sensor {prediction.sensor_id} | "
            f"{prediction.target_timestamp} | "
            f"+{prediction.horizon_hours}h | "
            f"{prediction.predicted_noise_db:.2f} dB"
        )


if __name__ == "__main__":
    main()
