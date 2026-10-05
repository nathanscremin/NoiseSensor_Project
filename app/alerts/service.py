"""Regras de negócio e máquina de estados dos alertas."""

from datetime import timedelta

import psycopg

from app.alerts.models import (
    AlertEvent,
    AlertEventType,
    AlertState,
)
from app.alerts.repository import (
    create_alert,
    finish_alert,
    get_or_create_alert_settings,
    get_or_create_alert_state,
    update_alert_peak,
    update_alert_state,
)
from app.simulator.reading import SensorReading


class AlertService:
    """Processa cada leitura e controla o estado do sensor."""

    def process_reading(
        self,
        connection: psycopg.Connection,
        reading: SensorReading,
    ) -> AlertEvent | None:
        """
        Processa uma leitura e pode gerar um evento de início ou fim.

        O tempo é calculado usando o timestamp da leitura. Dessa forma,
        o comportamento não depende da velocidade do loop do Python.
        """

        with connection.transaction():
            settings = get_or_create_alert_settings(
                connection,
                reading.sensor_id,
            )

            state = get_or_create_alert_state(
                connection,
                reading.sensor_id,
            )

            if state.state == AlertState.NORMAL:
                return self._handle_normal(
                    connection,
                    reading,
                    settings,
                )

            if state.state == AlertState.PENDING_ALERT:
                return self._handle_pending_alert(
                    connection,
                    reading,
                    settings,
                    state,
                )

            if state.state == AlertState.ALERT:
                return self._handle_alert(
                    connection,
                    reading,
                    settings,
                    state,
                )

            if state.state == AlertState.PENDING_RECOVERY:
                return self._handle_pending_recovery(
                    connection,
                    reading,
                    settings,
                    state,
                )

            raise RuntimeError(
                f"Estado de alerta desconhecido: {state.state}"
            )

    @staticmethod
    def _handle_normal(
        connection: psycopg.Connection,
        reading: SensorReading,
        settings,
    ) -> None:
        """Normal -> começa a contagem para possível alerta."""

        if reading.noise_db < settings.threshold_db:
            return None

        update_alert_state(
            connection,
            sensor_id=reading.sensor_id,
            state=AlertState.PENDING_ALERT,
            condition_started_at=reading.timestamp,
            recovery_started_at=None,
            current_alert_id=None,
        )

        return None

    @staticmethod
    def _handle_pending_alert(
        connection: psycopg.Connection,
        reading: SensorReading,
        settings,
        state,
    ) -> AlertEvent | None:
        """Verifica se a leitura alta já durou o suficiente."""

        if reading.noise_db < settings.threshold_db:
            update_alert_state(
                connection,
                sensor_id=reading.sensor_id,
                state=AlertState.NORMAL,
                condition_started_at=None,
                recovery_started_at=None,
                current_alert_id=None,
            )
            return None

        if state.condition_started_at is None:
            update_alert_state(
                connection,
                sensor_id=reading.sensor_id,
                state=AlertState.PENDING_ALERT,
                condition_started_at=reading.timestamp,
                recovery_started_at=None,
                current_alert_id=None,
            )
            return None

        elapsed = reading.timestamp - state.condition_started_at

        if elapsed < timedelta(
            seconds=settings.trigger_duration_seconds
        ):
            return None

        alert = create_alert(
            connection,
            sensor_id=reading.sensor_id,
            threshold_db=settings.threshold_db,
            started_at=reading.timestamp,
            peak_noise_db=reading.noise_db,
        )

        update_alert_state(
            connection,
            sensor_id=reading.sensor_id,
            state=AlertState.ALERT,
            condition_started_at=None,
            recovery_started_at=None,
            current_alert_id=alert.alert_id,
        )

        return AlertEvent(
            event_type=AlertEventType.STARTED,
            alert=alert,
        )

    @staticmethod
    def _handle_alert(
        connection: psycopg.Connection,
        reading: SensorReading,
        settings,
        state,
    ) -> AlertEvent | None:
        """Mantém o alerta ou começa a contagem de recuperação."""

        if state.current_alert_id is None:
            raise RuntimeError(
                "Sensor em ALERT sem current_alert_id."
            )

        if reading.noise_db >= settings.threshold_db:
            update_alert_peak(
                connection,
                alert_id=state.current_alert_id,
                noise_db=reading.noise_db,
            )
            return None

        update_alert_state(
            connection,
            sensor_id=reading.sensor_id,
            state=AlertState.PENDING_RECOVERY,
            condition_started_at=None,
            recovery_started_at=reading.timestamp,
            current_alert_id=state.current_alert_id,
        )

        return None

    @staticmethod
    def _handle_pending_recovery(
        connection: psycopg.Connection,
        reading: SensorReading,
        settings,
        state,
    ) -> AlertEvent | None:
        """Confirma a recuperação ou cancela a contagem."""

        if state.current_alert_id is None:
            raise RuntimeError(
                "Sensor em PENDING_RECOVERY sem current_alert_id."
            )

        if reading.noise_db >= settings.threshold_db:
            update_alert_peak(
                connection,
                alert_id=state.current_alert_id,
                noise_db=reading.noise_db,
            )

            update_alert_state(
                connection,
                sensor_id=reading.sensor_id,
                state=AlertState.ALERT,
                condition_started_at=None,
                recovery_started_at=None,
                current_alert_id=state.current_alert_id,
            )
            return None

        if state.recovery_started_at is None:
            update_alert_state(
                connection,
                sensor_id=reading.sensor_id,
                state=AlertState.PENDING_RECOVERY,
                condition_started_at=None,
                recovery_started_at=reading.timestamp,
                current_alert_id=state.current_alert_id,
            )
            return None

        elapsed = reading.timestamp - state.recovery_started_at

        if elapsed < timedelta(
            seconds=settings.recovery_duration_seconds
        ):
            return None

        alert = finish_alert(
            connection,
            alert_id=state.current_alert_id,
            ended_at=reading.timestamp,
        )

        update_alert_state(
            connection,
            sensor_id=reading.sensor_id,
            state=AlertState.NORMAL,
            condition_started_at=None,
            recovery_started_at=None,
            current_alert_id=None,
        )

        return AlertEvent(
            event_type=AlertEventType.ENDED,
            alert=alert,
        )
