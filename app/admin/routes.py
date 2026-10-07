"""Rotas HTTP da área administrativa."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.admin.schemas import (
    AdminAuditResponse,
    AdminOverviewResponse,
    AdminSensorAssignment,
    AdminUserResponse,
    RoleUpdateRequest,
    SensorAssignmentRequest,
)
from app.admin.service import AdminService
from app.auth.dependencies import get_current_admin
from app.auth.models import User
from app.database.connection import create_connection


router = APIRouter(
    prefix="/api/admin",
    tags=["administration"],
)

admin_service = AdminService()


@router.get(
    "/overview",
    response_model=AdminOverviewResponse,
)
def get_admin_overview(
    _: User = Depends(get_current_admin),
) -> AdminOverviewResponse:
    """Retorna os indicadores do painel administrativo."""

    with create_connection() as connection:
        row = admin_service.get_overview(connection)

    return AdminOverviewResponse(
        user_count=row[0],
        admin_count=row[1],
        sensor_count=row[2],
        unassigned_sensor_count=row[3],
    )


@router.get(
    "/users",
    response_model=list[AdminUserResponse],
)
def get_admin_users(
    _: User = Depends(get_current_admin),
) -> list[AdminUserResponse]:
    """Lista os usuários para administração."""

    with create_connection() as connection:
        rows = admin_service.get_users(connection)

    return [
        AdminUserResponse(
            user_id=row[0],
            name=row[1],
            email=row[2],
            email_verified=row[3],
            role=row[4],
            sensor_count=row[5],
            created_at=row[6],
        )
        for row in rows
    ]


@router.get(
    "/sensors",
    response_model=list[AdminSensorAssignment],
)
def get_admin_sensors(
    _: User = Depends(get_current_admin),
) -> list[AdminSensorAssignment]:
    """Lista os sensores e seus usuários associados."""

    with create_connection() as connection:
        rows = admin_service.get_sensors(connection)

    return [
        AdminSensorAssignment(
            sensor_id=row[0],
            name=row[1],
            region=row[2],
            status=row[3],
            user_ids=[int(user_id) for user_id in row[4]],
        )
        for row in rows
    ]


@router.get(
    "/users/{user_id}/sensors",
)
def get_user_sensors(
    user_id: int,
    _: User = Depends(get_current_admin),
) -> dict[str, list[int]]:
    """Retorna os sensores associados a um usuário específico."""

    with create_connection() as connection:
        sensor_ids = admin_service.get_user_sensor_ids(
            connection,
            user_id,
        )

    return {"sensor_ids": sensor_ids}


@router.patch(
    "/users/{user_id}/role",
    response_model=AdminUserResponse,
)
def change_user_role(
    user_id: int,
    data: RoleUpdateRequest,
    current_admin: User = Depends(get_current_admin),
) -> AdminUserResponse:
    """Altera o cargo de outro usuário."""

    with create_connection() as connection:
        try:
            updated = admin_service.change_user_role(
                connection=connection,
                admin_user_id=current_admin.user_id,
                target_user_id=user_id,
                role=data.role,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error

        users = admin_service.get_users(connection)

    user_row = next(
        (row for row in users if row[0] == user_id),
        None,
    )

    if user_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    return AdminUserResponse(
        user_id=user_row[0],
        name=user_row[1],
        email=user_row[2],
        email_verified=user_row[3],
        role=user_row[4],
        sensor_count=user_row[5],
        created_at=user_row[6],
    )


@router.put(
    "/users/{user_id}/sensors",
)
def update_user_sensors(
    user_id: int,
    data: SensorAssignmentRequest,
    current_admin: User = Depends(get_current_admin),
) -> dict[str, list[int]]:
    """Substitui as associações de sensores de um usuário."""

    with create_connection() as connection:
        try:
            sensor_ids, _, _ = admin_service.update_sensor_assignments(
                connection=connection,
                admin_user_id=current_admin.user_id,
                target_user_id=user_id,
                sensor_ids=data.sensor_ids,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error

    return {"sensor_ids": sensor_ids}


@router.get(
    "/audit",
    response_model=list[AdminAuditResponse],
)
def get_admin_audit(
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(get_current_admin),
) -> list[AdminAuditResponse]:
    """Retorna o histórico recente de ações administrativas."""

    with create_connection() as connection:
        rows = admin_service.get_audit_logs(
            connection,
            limit,
        )

    return [
        AdminAuditResponse(
            audit_id=row[0],
            admin_user_id=row[1],
            admin_name=row[2],
            action=row[3],
            target_user_id=row[4],
            target_sensor_id=row[5],
            details=row[6],
            created_at=row[7],
        )
        for row in rows
    ]
