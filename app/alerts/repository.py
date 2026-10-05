"""Operações de persistência relacionadas aos alertas."""

from datetime import datetime

import psycopg

from app.alerts.models import (
    AlertRecord,
    AlertSettings,
    AlertState,
    AlertStateRecord,
)

from app.database.repository import sensor_belongs_to_user


def _settings_from_row(row: tuple) -> AlertSettings:
    return AlertSettings(
        sensor_id=row[0],
        threshold_db=float(row[1]),
        trigger_duration_seconds=row[2],
        recovery_duration_seconds=row[3],
        created_at=row[4],
        updated_at=row[5],
    )


def _state_from_row(row: tuple) -> AlertStateRecord:
    return AlertStateRecord(
        sensor_id=row[0],
        state=AlertState(row[1]),
        condition_started_at=row[2],
        recovery_started_at=row[3],
        current_alert_id=row[4],
        updated_at=row[5],
    )


def _alert_from_row(row: tuple) -> AlertRecord:
    return AlertRecord(
        alert_id=row[0],
        sensor_id=row[1],
        threshold_db=float(row[2]),
        started_at=row[3],
        ended_at=row[4],
        peak_noise_db=float(row[5]),
        created_at=row[6],
    )


def get_alert_settings(
    connection: psycopg.Connection,
    sensor_id: int,
) -> AlertSettings | None:
    """Busca a configuração de alerta do sensor."""

    row = connection.execute(
        """
        SELECT
            sensor_id,
            threshold_db,
            trigger_duration_seconds,
            recovery_duration_seconds,
            created_at,
            updated_at
        FROM sensor_alert_settings
        WHERE sensor_id = %s;
        """,
        (sensor_id,),
    ).fetchone()

    if row is None:
        return None

    return _settings_from_row(row)


def create_default_alert_settings(
    connection: psycopg.Connection,
    sensor_id: int,
) -> None:
    """Cria a configuração padrão de um sensor."""

    connection.execute(
        """
        INSERT INTO sensor_alert_settings (
            sensor_id,
            threshold_db,
            trigger_duration_seconds,
            recovery_duration_seconds
        )
        VALUES (%s, 70.00, 30, 15)
        ON CONFLICT (sensor_id) DO NOTHING;
        """,
        (sensor_id,),
    )


def get_or_create_alert_settings(
    connection: psycopg.Connection,
    sensor_id: int,
) -> AlertSettings:
    """Retorna a configuração, criando a padrão quando necessário."""

    settings = get_alert_settings(
        connection,
        sensor_id,
    )

    if settings is not None:
        return settings

    create_default_alert_settings(
        connection,
        sensor_id,
    )

    settings = get_alert_settings(
        connection,
        sensor_id,
    )

    if settings is None:
        raise RuntimeError(
            "Não foi possível criar a configuração de alerta."
        )

    return settings


def update_alert_settings(
    connection: psycopg.Connection,
    sensor_id: int,
    threshold_db: float,
    trigger_duration_seconds: int,
    recovery_duration_seconds: int,
) -> AlertSettings:
    """Atualiza a configuração de alerta do sensor."""

    row = connection.execute(
        """
        UPDATE sensor_alert_settings
        SET
            threshold_db = %s,
            trigger_duration_seconds = %s,
            recovery_duration_seconds = %s,
            updated_at = NOW()
        WHERE sensor_id = %s
        RETURNING
            sensor_id,
            threshold_db,
            trigger_duration_seconds,
            recovery_duration_seconds,
            created_at,
            updated_at;
        """,
        (
            threshold_db,
            trigger_duration_seconds,
            recovery_duration_seconds,
            sensor_id,
        ),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            "Não foi possível atualizar a configuração de alerta."
        )

    return _settings_from_row(row)


def get_alert_state(
    connection: psycopg.Connection,
    sensor_id: int,
) -> AlertStateRecord | None:
    """Busca o estado atual de alerta do sensor."""

    row = connection.execute(
        """
        SELECT
            sensor_id,
            state,
            condition_started_at,
            recovery_started_at,
            current_alert_id,
            updated_at
        FROM sensor_alert_states
        WHERE sensor_id = %s;
        """,
        (sensor_id,),
    ).fetchone()

    if row is None:
        return None

    return _state_from_row(row)


def create_default_alert_state(
    connection: psycopg.Connection,
    sensor_id: int,
) -> None:
    """Cria o estado inicial normal de um sensor."""

    connection.execute(
        """
        INSERT INTO sensor_alert_states (
            sensor_id,
            state
        )
        VALUES (%s, 'normal')
        ON CONFLICT (sensor_id) DO NOTHING;
        """,
        (sensor_id,),
    )


def get_or_create_alert_state(
    connection: psycopg.Connection,
    sensor_id: int,
) -> AlertStateRecord:
    """Retorna o estado, criando o estado normal quando necessário."""

    state = get_alert_state(
        connection,
        sensor_id,
    )

    if state is not None:
        return state

    create_default_alert_state(
        connection,
        sensor_id,
    )

    state = get_alert_state(
        connection,
        sensor_id,
    )

    if state is None:
        raise RuntimeError(
            "Não foi possível criar o estado de alerta."
        )

    return state


def update_alert_state(
    connection: psycopg.Connection,
    sensor_id: int,
    state: AlertState,
    condition_started_at: datetime | None,
    recovery_started_at: datetime | None,
    current_alert_id: int | None,
) -> AlertStateRecord:
    """Atualiza o estado persistido de um sensor."""

    row = connection.execute(
        """
        UPDATE sensor_alert_states
        SET
            state = %s,
            condition_started_at = %s,
            recovery_started_at = %s,
            current_alert_id = %s,
            updated_at = NOW()
        WHERE sensor_id = %s
        RETURNING
            sensor_id,
            state,
            condition_started_at,
            recovery_started_at,
            current_alert_id,
            updated_at;
        """,
        (
            state.value,
            condition_started_at,
            recovery_started_at,
            current_alert_id,
            sensor_id,
        ),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            "Não foi possível atualizar o estado do alerta."
        )

    return _state_from_row(row)


def create_alert(
    connection: psycopg.Connection,
    sensor_id: int,
    threshold_db: float,
    started_at: datetime,
    peak_noise_db: float,
) -> AlertRecord:
    """Cria um novo episódio de alerta."""

    row = connection.execute(
        """
        INSERT INTO alerts (
            sensor_id,
            threshold_db,
            started_at,
            peak_noise_db
        )
        VALUES (%s, %s, %s, %s)
        RETURNING
            alert_id,
            sensor_id,
            threshold_db,
            started_at,
            ended_at,
            peak_noise_db,
            created_at;
        """,
        (
            sensor_id,
            threshold_db,
            started_at,
            peak_noise_db,
        ),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            "Não foi possível criar o alerta."
        )

    return _alert_from_row(row)


def get_alert_by_id(
    connection: psycopg.Connection,
    alert_id: int,
) -> AlertRecord | None:
    """Busca um alerta pelo ID."""

    row = connection.execute(
        """
        SELECT
            alert_id,
            sensor_id,
            threshold_db,
            started_at,
            ended_at,
            peak_noise_db,
            created_at
        FROM alerts
        WHERE alert_id = %s;
        """,
        (alert_id,),
    ).fetchone()

    if row is None:
        return None

    return _alert_from_row(row)


def update_alert_peak(
    connection: psycopg.Connection,
    alert_id: int,
    noise_db: float,
) -> None:
    """Atualiza o pico do episódio quando necessário."""

    connection.execute(
        """
        UPDATE alerts
        SET peak_noise_db = GREATEST(peak_noise_db, %s)
        WHERE alert_id = %s
          AND ended_at IS NULL;
        """,
        (
            noise_db,
            alert_id,
        ),
    )


def finish_alert(
    connection: psycopg.Connection,
    alert_id: int,
    ended_at: datetime,
) -> AlertRecord:
    """Finaliza um episódio de alerta."""

    row = connection.execute(
        """
        UPDATE alerts
        SET ended_at = %s
        WHERE alert_id = %s
          AND ended_at IS NULL
        RETURNING
            alert_id,
            sensor_id,
            threshold_db,
            started_at,
            ended_at,
            peak_noise_db,
            created_at;
        """,
        (
            ended_at,
            alert_id,
        ),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            "Não foi possível finalizar o alerta."
        )

    return _alert_from_row(row)


def get_alert_history(
    connection: psycopg.Connection,
    sensor_id: int,
    limit: int = 20,
) -> list[AlertRecord]:
    """Retorna os episódios mais recentes de um sensor."""

    rows = connection.execute(
        """
        SELECT
            alert_id,
            sensor_id,
            threshold_db,
            started_at,
            ended_at,
            peak_noise_db,
            created_at
        FROM alerts
        WHERE sensor_id = %s
        ORDER BY started_at DESC
        LIMIT %s;
        """,
        (
            sensor_id,
            limit,
        ),
    ).fetchall()

    return [
        _alert_from_row(row)
        for row in rows
    ]
