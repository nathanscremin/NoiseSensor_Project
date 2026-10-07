"""Regras de negócio do painel administrativo."""

import psycopg

from app.admin.repository import (
    ALLOWED_ROLES,
    count_admins,
    create_audit_log,
    get_assigned_sensor_ids,
    get_existing_sensor_ids,
    get_overview,
    get_sensor_names,
    get_user_for_update,
    list_audit_logs,
    list_sensors,
    list_users,
    replace_sensor_assignments,
    update_user_role,
)


class AdminService:
    """Coordena as operações administrativas."""

    def get_overview(self, connection: psycopg.Connection):
        return get_overview(connection)

    def get_users(self, connection: psycopg.Connection):
        return list_users(connection)

    def get_sensors(self, connection: psycopg.Connection):
        return list_sensors(connection)

    def get_audit_logs(self, connection: psycopg.Connection, limit: int):
        return list_audit_logs(connection, limit)

    def change_user_role(
        self,
        connection: psycopg.Connection,
        admin_user_id: int,
        target_user_id: int,
        role: str,
    ) -> tuple:
        if role not in ALLOWED_ROLES:
            raise ValueError("Cargo inválido.")

        if admin_user_id == target_user_id:
            raise ValueError(
                "Um administrador não pode alterar o próprio cargo."
            )

        with connection.transaction():
            target = get_user_for_update(
                connection,
                target_user_id,
            )

            if target is None:
                raise ValueError("Usuário não encontrado.")

            current_role = target[3]

            if current_role == role:
                return target

            if current_role == "admin" and role == "user":
                if count_admins(connection) <= 1:
                    raise ValueError(
                        "O sistema precisa manter pelo menos um administrador."
                    )

            updated = update_user_role(
                connection,
                target_user_id,
                role,
            )

            if updated is None:
                raise RuntimeError(
                    "Não foi possível atualizar o cargo do usuário."
                )

            create_audit_log(
                connection=connection,
                admin_user_id=admin_user_id,
                action="role_changed",
                target_user_id=target_user_id,
                details=(
                    f"Cargo alterado de '{current_role}' para '{role}'."
                ),
            )

        return updated

    def update_sensor_assignments(
        self,
        connection: psycopg.Connection,
        admin_user_id: int,
        target_user_id: int,
        sensor_ids: list[int],
    ) -> tuple[list[int], list[int], list[int]]:
        """Atualiza associações e retorna atuais, adicionados e removidos."""

        normalized_ids = sorted(set(sensor_ids))

        with connection.transaction():
            target = get_user_for_update(
                connection,
                target_user_id,
            )

            if target is None:
                raise ValueError("Usuário não encontrado.")

            existing_sensor_ids = get_existing_sensor_ids(
                connection,
                normalized_ids,
            )

            if existing_sensor_ids != set(normalized_ids):
                missing = sorted(
                    set(normalized_ids) - existing_sensor_ids
                )
                raise ValueError(
                    "Um ou mais sensores não existem: "
                    + ", ".join(str(sensor_id) for sensor_id in missing)
                    + "."
                )

            added, removed = replace_sensor_assignments(
                connection,
                target_user_id,
                normalized_ids,
            )

            sensor_names = get_sensor_names(
                connection,
                sorted(set(added + removed)),
            )

            target_name = target[1]

            for sensor_id in added:
                create_audit_log(
                    connection=connection,
                    admin_user_id=admin_user_id,
                    action="sensor_assigned",
                    target_user_id=target_user_id,
                    target_sensor_id=sensor_id,
                    details=(
                        f"Sensor '{sensor_names.get(sensor_id, sensor_id)}' "
                        f"associado ao usuário '{target_name}'."
                    ),
                )

            for sensor_id in removed:
                create_audit_log(
                    connection=connection,
                    admin_user_id=admin_user_id,
                    action="sensor_unassigned",
                    target_user_id=target_user_id,
                    target_sensor_id=sensor_id,
                    details=(
                        f"Sensor '{sensor_names.get(sensor_id, sensor_id)}' "
                        f"desassociado do usuário '{target_name}'."
                    ),
                )

        return normalized_ids, added, removed

    def get_user_sensor_ids(
        self,
        connection: psycopg.Connection,
        user_id: int,
    ) -> list[int]:
        """Retorna as associações de um usuário."""

        return get_assigned_sensor_ids(connection, user_id)
