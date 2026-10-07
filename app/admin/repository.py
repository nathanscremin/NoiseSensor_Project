"""Persistência da área administrativa."""

import psycopg


ALLOWED_ROLES = {"user", "admin"}


def get_overview(connection: psycopg.Connection) -> tuple:
    """Retorna os indicadores gerais do sistema."""

    row = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM users),
            (SELECT COUNT(*) FROM users WHERE role = 'admin'),
            (SELECT COUNT(*) FROM sensors),
            (
                SELECT COUNT(*)
                FROM sensors AS s
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM sensor_users AS su
                    WHERE su.sensor_id = s.sensor_id
                )
            );
        """
    ).fetchone()

    if row is None:
        raise RuntimeError("Não foi possível obter o resumo administrativo.")

    return row


def list_users(connection: psycopg.Connection) -> list[tuple]:
    """Lista usuários com a quantidade de sensores associados."""

    return connection.execute(
        """
        SELECT
            u.user_id,
            u.name,
            u.email,
            u.email_verified,
            u.role,
            COUNT(su.sensor_id) AS sensor_count,
            u.created_at
        FROM users AS u
        LEFT JOIN sensor_users AS su
            ON su.user_id = u.user_id
        GROUP BY
            u.user_id,
            u.name,
            u.email,
            u.email_verified,
            u.role,
            u.created_at
        ORDER BY u.name, u.user_id;
        """
    ).fetchall()


def list_sensors(connection: psycopg.Connection) -> list[tuple]:
    """Lista todos os sensores e os IDs dos usuários associados."""

    return connection.execute(
        """
        SELECT
            s.sensor_id,
            s.name,
            s.region,
            s.status,
            COALESCE(
                ARRAY_AGG(su.user_id ORDER BY su.user_id)
                FILTER (WHERE su.user_id IS NOT NULL),
                ARRAY[]::BIGINT[]
            ) AS user_ids
        FROM sensors AS s
        LEFT JOIN sensor_users AS su
            ON su.sensor_id = s.sensor_id
        GROUP BY
            s.sensor_id,
            s.name,
            s.region,
            s.status
        ORDER BY s.sensor_id;
        """
    ).fetchall()


def get_user_for_update(
    connection: psycopg.Connection,
    user_id: int,
) -> tuple | None:
    """Busca um usuário bloqueando sua linha durante uma alteração."""

    return connection.execute(
        """
        SELECT user_id, name, email, role
        FROM users
        WHERE user_id = %s
        FOR UPDATE;
        """,
        (user_id,),
    ).fetchone()


def count_admins(connection: psycopg.Connection) -> int:
    """Retorna a quantidade de administradores."""

    row = connection.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE role = 'admin';
        """
    ).fetchone()

    return int(row[0]) if row else 0


def update_user_role(
    connection: psycopg.Connection,
    user_id: int,
    role: str,
) -> tuple | None:
    """Altera o cargo e retorna o usuário atualizado."""

    if role not in ALLOWED_ROLES:
        raise ValueError("Cargo inválido.")

    row = connection.execute(
        """
        UPDATE users
        SET role = %s
        WHERE user_id = %s
        RETURNING user_id, name, email, email_verified, role, created_at;
        """,
        (role, user_id),
    ).fetchone()

    return row


def get_assigned_sensor_ids(
    connection: psycopg.Connection,
    user_id: int,
) -> list[int]:
    """Retorna os sensores atualmente associados a um usuário."""

    rows = connection.execute(
        """
        SELECT sensor_id
        FROM sensor_users
        WHERE user_id = %s
        ORDER BY sensor_id;
        """,
        (user_id,),
    ).fetchall()

    return [int(row[0]) for row in rows]


def get_existing_sensor_ids(
    connection: psycopg.Connection,
    sensor_ids: list[int],
) -> set[int]:
    """Retorna quais IDs de sensores realmente existem."""

    if not sensor_ids:
        return set()

    placeholders = ", ".join(["%s"] * len(sensor_ids))

    rows = connection.execute(
        f"""
        SELECT sensor_id
        FROM sensors
        WHERE sensor_id IN ({placeholders});
        """,
        tuple(sensor_ids),
    ).fetchall()

    return {int(row[0]) for row in rows}


def get_sensor_names(
    connection: psycopg.Connection,
    sensor_ids: list[int],
) -> dict[int, str]:
    """Retorna os nomes dos sensores informados."""

    if not sensor_ids:
        return {}

    placeholders = ", ".join(["%s"] * len(sensor_ids))

    rows = connection.execute(
        f"""
        SELECT sensor_id, name
        FROM sensors
        WHERE sensor_id IN ({placeholders});
        """,
        tuple(sensor_ids),
    ).fetchall()

    return {int(row[0]): row[1] for row in rows}


def replace_sensor_assignments(
    connection: psycopg.Connection,
    user_id: int,
    sensor_ids: list[int],
) -> tuple[list[int], list[int]]:
    """Substitui todas as associações do usuário e retorna mudanças."""

    old_ids = set(get_assigned_sensor_ids(connection, user_id))
    new_ids = set(sensor_ids)

    connection.execute(
        """
        DELETE FROM sensor_users
        WHERE user_id = %s;
        """,
        (user_id,),
    )

    for sensor_id in sorted(new_ids):
        connection.execute(
            """
            INSERT INTO sensor_users (sensor_id, user_id)
            VALUES (%s, %s);
            """,
            (sensor_id, user_id),
        )

    added = sorted(new_ids - old_ids)
    removed = sorted(old_ids - new_ids)

    return added, removed


def create_audit_log(
    connection: psycopg.Connection,
    admin_user_id: int,
    action: str,
    details: str,
    target_user_id: int | None = None,
    target_sensor_id: int | None = None,
) -> None:
    """Registra uma ação administrativa."""

    connection.execute(
        """
        INSERT INTO admin_audit_log (
            admin_user_id,
            action,
            target_user_id,
            target_sensor_id,
            details
        )
        VALUES (%s, %s, %s, %s, %s);
        """,
        (
            admin_user_id,
            action,
            target_user_id,
            target_sensor_id,
            details,
        ),
    )


def list_audit_logs(
    connection: psycopg.Connection,
    limit: int,
) -> list[tuple]:
    """Retorna o histórico administrativo mais recente."""

    return connection.execute(
        """
        SELECT
            a.audit_id,
            a.admin_user_id,
            admin.name,
            a.action,
            a.target_user_id,
            a.target_sensor_id,
            a.details,
            a.created_at
        FROM admin_audit_log AS a
        INNER JOIN users AS admin
            ON admin.user_id = a.admin_user_id
        ORDER BY a.created_at DESC, a.audit_id DESC
        LIMIT %s;
        """,
        (limit,),
    ).fetchall()
