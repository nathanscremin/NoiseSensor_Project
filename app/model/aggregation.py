"""Preparação dos dados horários para o modelo."""

import pandas as pd

HOURLY_COLUMNS = [
    "sensor_id",
    "region",
    "hour",
    "avg_noise_db",
    "min_noise_db",
    "max_noise_db",
    "std_noise_db",
    "reading_count",
]

def prepare_hourly_data(rows: list[tuple]) -> pd.DataFrame:
    """
    Converte o resultado da consulta do PostgreSQL
    em um DataFrame de dados horários.
    """

    if not rows:
        raise ValueError(
            "Nenhum dado horário foi encontrado."
        )

    dataframe = pd.DataFrame(
        rows,
        columns=HOURLY_COLUMNS,
    )

    dataframe["hour"] = pd.to_datetime(
        dataframe["hour"]
    )

    numeric_columns = [
        "avg_noise_db",
        "min_noise_db",
        "max_noise_db",
        "std_noise_db",
        "reading_count",
    ]

    for column in numeric_columns:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    dataframe = dataframe.sort_values(
        ["sensor_id", "hour"]
    )

    dataframe = dataframe.drop_duplicates(
        subset=["sensor_id", "hour"]
    )

    return dataframe.reset_index(drop=True)


def ensure_hourly_series(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Garante que cada sensor possua uma sequência horária
    contínua.

    Horas sem leitura permanecem como NaN.
    Não realizamos interpolação nesta etapa.
    """

    frames = []

    for sensor_id, group in dataframe.groupby(
        "sensor_id"
    ):
        group = group.sort_values("hour")

        region = group["region"].dropna().iloc[0]

        indexed = group.set_index("hour")

        full_index = pd.date_range(
            start=indexed.index.min(),
            end=indexed.index.max(),
            freq="h",
        )

        indexed = indexed.reindex(full_index)

        indexed.index.name = "hour"

        indexed["sensor_id"] = sensor_id
        indexed["region"] = region

        frames.append(
            indexed.reset_index()
        )

    result = pd.concat(
        frames,
        ignore_index=True,
    )

    return result.sort_values(
        ["sensor_id", "hour"]
    ).reset_index(drop=True)
