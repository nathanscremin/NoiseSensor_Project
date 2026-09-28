"""Avaliação dos modelos de previsão."""

import pandas as pd

from sklearn.metrics import (
    mean_absolute_error,
    root_mean_squared_error,
)


def calculate_metrics(
    y_true,
    y_pred,
) -> dict[str, float]:
    """
    Calcula métricas de regressão.
    """

    return {
        "mae": float(
            mean_absolute_error(
                y_true,
                y_pred,
            )
        ),
        "rmse": float(
            root_mean_squared_error(
                y_true,
                y_pred,
            )
        ),
    }


def evaluate_baseline(
    dataframe: pd.DataFrame,
) -> dict[str, float]:
    """
    Avalia o baseline baseado no mesmo horário
    do dia anterior.
    """

    y_true = dataframe[
        "target_noise_db"
    ]

    y_pred = dataframe[
        "noise_24h_ago"
    ]

    return calculate_metrics(
        y_true,
        y_pred,
    )


def evaluate_model(
    model,
    dataframe: pd.DataFrame,
    feature_columns: list[str],
) -> dict[str, float]:
    """
    Avalia um modelo treinado.
    """

    X = dataframe[
        feature_columns
    ]

    y_true = dataframe[
        "target_noise_db"
    ]

    y_pred = model.predict(X)

    return calculate_metrics(
        y_true,
        y_pred,
    )
