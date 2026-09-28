"""Treinamento e seleção do modelo."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

import joblib
import pandas as pd
import sklearn

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.database.connection import create_connection
from app.database.repository import get_hourly_readings

from app.model.aggregation import (
    ensure_hourly_series,
    prepare_hourly_data,
)

from app.model.evaluation import (
    evaluate_baseline,
    evaluate_model,
)

from app.model.features import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
    build_supervised_dataset,
)


PROJECT_ROOT = Path(
    __file__
).resolve().parents[2]

MODEL_DIRECTORY = (
    PROJECT_ROOT / "models"
)

MODEL_PATH = (
    MODEL_DIRECTORY /
    "noise_model.joblib"
)

METADATA_PATH = (
    MODEL_DIRECTORY /
    "metadata.json"
)


TRAINING_DAYS = 365


def create_preprocessor() -> ColumnTransformer:
    """
    Cria o pré-processamento das features.
    """

    return ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
                CATEGORICAL_FEATURES,
            ),
            (
                "numeric",
                "passthrough",
                NUMERIC_FEATURES,
            ),
        ]
    )


def create_candidates() -> dict:
    """
    Cria os modelos candidatos da primeira rodada.
    """

    return {
        "random_forest": Pipeline(
            [
                (
                    "preprocessor",
                    create_preprocessor(),
                ),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=300,
                        min_samples_leaf=2,
                        random_state=42,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),

        "hist_gradient_boosting": Pipeline(
            [
                (
                    "preprocessor",
                    create_preprocessor(),
                ),
                (
                    "model",
                    HistGradientBoostingRegressor(
                        max_iter=300,
                        learning_rate=0.05,
                        max_leaf_nodes=31,
                        l2_regularization=1.0,
                        random_state=42,
                    ),
                ),
            ]
        ),
    }


def temporal_split(
    dataframe: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Divide os dados cronologicamente:

        70% treino
        15% validação
        15% teste
    """

    timestamps = sorted(
        dataframe[
            "target_timestamp"
        ].unique()
    )

    train_end = int(
        len(timestamps) * 0.70
    )

    validation_end = int(
        len(timestamps) * 0.85
    )

    train_cutoff = (
        timestamps[train_end]
    )

    validation_cutoff = (
        timestamps[validation_end]
    )

    train = dataframe[
        dataframe["target_timestamp"]
        < train_cutoff
    ]

    validation = dataframe[
        (
            dataframe["target_timestamp"]
            >= train_cutoff
        )
        &
        (
            dataframe["target_timestamp"]
            < validation_cutoff
        )
    ]

    test = dataframe[
        dataframe["target_timestamp"]
        >= validation_cutoff
    ]

    return train, validation, test


def load_training_data() -> pd.DataFrame:
    """
    Carrega o histórico utilizado no treinamento.
    """

    end = datetime.now(
        timezone.utc
    )

    start = end - timedelta(
        days=TRAINING_DAYS
    )

    with create_connection() as connection:

        rows = get_hourly_readings(
            connection,
            start,
            end,
        )

    hourly = prepare_hourly_data(
        rows
    )

    hourly = ensure_hourly_series(
        hourly
    )

    return build_supervised_dataset(
        hourly
    )


def save_model(
    model,
    validation_metrics: dict,
    test_metrics: dict,
    baseline_metrics: dict,
) -> None:
    """
    Salva o modelo final e seus metadados.
    """

    MODEL_DIRECTORY.mkdir(
        exist_ok=True
    )

    joblib.dump(
        model,
        MODEL_PATH,
    )

    metadata = {
        "model_version": "v1",
        "trained_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "algorithm": type(
            model.named_steps["model"]
        ).__name__,

        "sklearn_version":
            sklearn.__version__,

        "training_days":
            TRAINING_DAYS,

        "history_hours":
            24,

        "forecast_horizon_hours":
            24,

        "validation_metrics":
            validation_metrics,

        "test_metrics":
            test_metrics,

        "baseline_metrics":
            baseline_metrics,

        "features":
            FEATURE_COLUMNS,
    }

    with open(
        METADATA_PATH,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            metadata,
            file,
            indent=4,
            ensure_ascii=False,
        )


def train() -> None:
    """
    Executa todo o processo de treinamento.
    """

    print(
        "Carregando dados históricos..."
    )

    dataframe = load_training_data()

    print(
        f"{len(dataframe)} exemplos "
        "de treinamento disponíveis."
    )

    train_data, validation_data, test_data = (
        temporal_split(dataframe)
    )

    print(
        "\nDivisão temporal:"
    )

    print(
        f"Treino: {len(train_data)}"
    )

    print(
        f"Validação: {len(validation_data)}"
    )

    print(
        f"Teste: {len(test_data)}"
    )

    # --------------------------------------------------
    # Baseline
    # --------------------------------------------------

    baseline_metrics = (
        evaluate_baseline(
            validation_data
        )
    )

    print(
        "\nBaseline:"
    )

    print(
        f"MAE: "
        f"{baseline_metrics['mae']:.3f}"
    )

    print(
        f"RMSE: "
        f"{baseline_metrics['rmse']:.3f}"
    )

    X_train = train_data[
        FEATURE_COLUMNS
    ]

    y_train = train_data[
        TARGET_COLUMN
    ]

    X_validation = validation_data[
        FEATURE_COLUMNS
    ]

    y_validation = validation_data[
        TARGET_COLUMN
    ]

    candidates = create_candidates()

    validation_results = {}

    # --------------------------------------------------
    # Treina candidatos
    # --------------------------------------------------

    for name, model in candidates.items():

        print(
            f"\nTreinando: {name}"
        )

        model.fit(
            X_train,
            y_train,
        )

        metrics = evaluate_model(
            model,
            validation_data,
            FEATURE_COLUMNS,
        )

        validation_results[name] = metrics

        print(
            f"MAE: {metrics['mae']:.3f}"
        )

        print(
            f"RMSE: {metrics['rmse']:.3f}"
        )

    # --------------------------------------------------
    # Escolha baseada na validação
    # --------------------------------------------------

    best_name = min(
        validation_results,
        key=lambda name:
        validation_results[name]["mae"],
    )

    best_validation_metrics = (
        validation_results[best_name]
    )

    if (
        best_validation_metrics["mae"]
        >=
        baseline_metrics["mae"]
    ):
        raise RuntimeError(
            "Nenhum modelo candidato "
            "superou o baseline na validação."
        )

    print(
        f"\nModelo selecionado: {best_name}"
    )

    # --------------------------------------------------
    # Re-treina com treino + validação
    # --------------------------------------------------

    training_and_validation = pd.concat(
        [
            train_data,
            validation_data,
        ],
        ignore_index=True,
    )

    final_model = create_candidates()[
        best_name
    ]

    final_model.fit(
        training_and_validation[
            FEATURE_COLUMNS
        ],
        training_and_validation[
            TARGET_COLUMN
        ],
    )

    # --------------------------------------------------
    # Avaliação final no teste
    # --------------------------------------------------

    test_metrics = evaluate_model(
        final_model,
        test_data,
        FEATURE_COLUMNS,
    )

    print(
        "\nTeste final:"
    )

    print(
        f"MAE: "
        f"{test_metrics['mae']:.3f}"
    )

    print(
        f"RMSE: "
        f"{test_metrics['rmse']:.3f}"
    )

    # --------------------------------------------------
    # Persistência
    # --------------------------------------------------

    save_model(
        final_model,
        validation_metrics={
            best_name:
            best_validation_metrics
        },
        test_metrics=test_metrics,
        baseline_metrics=baseline_metrics,
    )

    print(
        f"\nModelo salvo em:"
        f"\n{MODEL_PATH}"
    )


if __name__ == "__main__":
    train()
