"""Predição utilizando o modelo previamente treinado."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isnan
from pathlib import Path
from zoneinfo import ZoneInfo

import json
import joblib
import pandas as pd

from app.model.features import (
    HISTORY_HOURS,
    build_inference_row,
)


LOCAL_ZONE = ZoneInfo(
    "America/Sao_Paulo"
)


PROJECT_ROOT = Path(
    __file__
).resolve().parents[2]

MODEL_PATH = (
    PROJECT_ROOT /
    "models" /
    "noise_model.joblib"
)

METADATA_PATH = (
    PROJECT_ROOT
    / "models"
    / "metadata.json"
)

@dataclass
class Prediction:
    """
    Representa uma previsão individual.
    """

    sensor_id: int
    target_timestamp: datetime
    horizon_hours: int
    predicted_noise_db: float


def load_model():
    """
    Carrega o modelo salvo em disco.
    """

    if not MODEL_PATH.exists():

        raise FileNotFoundError(
            "Modelo treinado não encontrado em: "
            f"{MODEL_PATH}"
        )

    return joblib.load(
        MODEL_PATH
    )

def load_model_metadata() -> dict:
    """
    Carrega os metadados do modelo salvo.
    """

    if not METADATA_PATH.exists():
        raise FileNotFoundError(
            "Metadados do modelo não encontrados em: "
            f"{METADATA_PATH}"
        )

    with open(
        METADATA_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)

def forecast_sensor(
    model,
    sensor_id: int,
    region: str,
    hourly_history: pd.DataFrame,
    horizon: int = 24,
) -> list[Prediction]:
    """
    Realiza previsão recursiva para um sensor.
    """

    history = (
        hourly_history
        .sort_values("hour")
        ["avg_noise_db"]
        .tolist()
    )

    if len(history) < HISTORY_HOURS:
        raise ValueError(
            f"Sensor {sensor_id} possui somente "
            f"{len(history)} horas disponíveis. "
            f"São necessárias "
            f"{HISTORY_HOURS}."
        )

    if any(
        isnan(float(value))
        for value in history[-HISTORY_HOURS:]
    ):
        raise ValueError(
            f"Sensor {sensor_id} possui "
            "horas faltantes no histórico recente."
        )

    last_hour = (
        hourly_history["hour"]
        .max()
    )

    # Gera também a hora corrente. O dashboard a remove da visualização
    # para manter exatamente 24 horas realmente futuras.
    target_timestamp = (
        last_hour
        .replace(
            tzinfo=LOCAL_ZONE
        )
        + timedelta(hours=1)
    )

    predictions = []

    for step in range(
        1,
        horizon + 1,
    ):

        model_input = build_inference_row(
            history=history[-HISTORY_HOURS:],
            target_timestamp=target_timestamp,
            sensor_id=sensor_id,
            region=region,
        )

        prediction = float(
            model.predict(
                model_input
            )[0]
        )

        predictions.append(
            Prediction(
                sensor_id=sensor_id,
                target_timestamp=target_timestamp,
                horizon_hours=step,
                predicted_noise_db=prediction,
            )
        )

        # --------------------------------------------------
        # A previsão entra no histórico.
        # --------------------------------------------------

        history.append(
            prediction
        )

        target_timestamp += timedelta(
            hours=1
        )

    return predictions

