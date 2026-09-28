"""Construção das features utilizadas pelo modelo."""

import pandas as pd


HISTORY_HOURS = 24


CATEGORICAL_FEATURES = [
    "sensor_id",
    "region",
    "target_hour",
    "target_weekday",
    "target_month",
    "is_weekend",
]


NUMERIC_FEATURES = [
    *[
        f"noise_{hours}h_ago"
        for hours in range(1, HISTORY_HOURS + 1)
    ],
    "rolling_mean_3",
    "rolling_mean_6",
    "rolling_mean_24",
    "rolling_std_6",
]


FEATURE_COLUMNS = (
    CATEGORICAL_FEATURES
    + NUMERIC_FEATURES
)


TARGET_COLUMN = "target_noise_db"


def build_supervised_dataset(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Constrói o dataset supervisionado.

    Cada linha representa:

        últimas 24 horas
                ↓
          próxima hora
    """

    dataframe = dataframe.copy()

    dataframe = dataframe.sort_values(
        ["sensor_id", "hour"]
    )

    grouped = dataframe.groupby(
        "sensor_id"
    )["avg_noise_db"]

    # --------------------------------------------------
    # Histórico
    # --------------------------------------------------

    for hours in range(1, HISTORY_HOURS + 1):

        dataframe[
            f"noise_{hours}h_ago"
        ] = grouped.shift(hours - 1)

    # --------------------------------------------------
    # Estatísticas recentes
    # --------------------------------------------------

    dataframe["rolling_mean_3"] = (
        grouped
        .transform(
            lambda values:
            values
            .rolling(3, min_periods=3)
            .mean()
        )
    )

    dataframe["rolling_mean_6"] = (
        grouped
        .transform(
            lambda values:
            values
            .rolling(6, min_periods=6)
            .mean()
        )
    )

    dataframe["rolling_mean_24"] = (
        grouped
        .transform(
            lambda values:
            values
            .rolling(24, min_periods=24)
            .mean()
        )
    )

    dataframe["rolling_std_6"] = (
        grouped
        .transform(
            lambda values:
            values
            .rolling(6, min_periods=6)
            .std(ddof=0)
        )
    )

    # --------------------------------------------------
    # Target
    # --------------------------------------------------

    dataframe[TARGET_COLUMN] = grouped.shift(-1)

    dataframe["target_timestamp"] = (
        dataframe["hour"]
        + pd.Timedelta(hours=1)
    )

    # --------------------------------------------------
    # Informações conhecidas do futuro
    # --------------------------------------------------

    dataframe["target_hour"] = (
        dataframe["target_timestamp"].dt.hour
    )

    dataframe["target_weekday"] = (
        dataframe["target_timestamp"].dt.dayofweek
    )

    dataframe["target_month"] = (
        dataframe["target_timestamp"].dt.month
    )

    dataframe["is_weekend"] = (
        dataframe["target_weekday"] >= 5
    ).astype(int)

    # --------------------------------------------------
    # Remove exemplos incompletos
    # --------------------------------------------------

    required_columns = (
        FEATURE_COLUMNS
        + [TARGET_COLUMN]
    )

    dataframe = dataframe.dropna(
        subset=required_columns
    )

    return dataframe[
        FEATURE_COLUMNS
        + [
            "hour",
            "target_timestamp",
            TARGET_COLUMN,
        ]
    ].reset_index(drop=True)


def build_inference_row(
    history: list[float],
    target_timestamp,
    sensor_id: int,
    region: str,
) -> pd.DataFrame:
    """
    Constrói uma única linha de entrada para previsão.

    history deve estar ordenado do mais antigo
    para o mais recente.
    """

    if len(history) < HISTORY_HOURS:
        raise ValueError(
            "São necessárias pelo menos "
            f"{HISTORY_HOURS} horas de histórico."
        )

    history = history[-HISTORY_HOURS:]

    row = {
        "sensor_id": sensor_id,
        "region": region,
        "target_hour": target_timestamp.hour,
        "target_weekday": target_timestamp.weekday(),
        "target_month": target_timestamp.month,
        "is_weekend": int(
            target_timestamp.weekday() >= 5
        ),
    }

    # Mais recente = 1h atrás
    for hours in range(1, HISTORY_HOURS + 1):

        row[
            f"noise_{hours}h_ago"
        ] = history[-hours]

    recent_3 = history[-3:]
    recent_6 = history[-6:]
    recent_24 = history[-24:]

    row["rolling_mean_3"] = (
        sum(recent_3) / len(recent_3)
    )

    row["rolling_mean_6"] = (
        sum(recent_6) / len(recent_6)
    )

    row["rolling_mean_24"] = (
        sum(recent_24) / len(recent_24)
    )

    row["rolling_std_6"] = (
        pd.Series(recent_6).std(ddof=0)
    )

    return pd.DataFrame(
        [row],
        columns=FEATURE_COLUMNS,
    )
