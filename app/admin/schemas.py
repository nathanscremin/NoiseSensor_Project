"""Schemas da área administrativa."""

from datetime import datetime

from pydantic import BaseModel, Field


class RoleUpdateRequest(BaseModel):
    """Novo cargo de um usuário."""

    role: str = Field(pattern=r"^(user|admin)$")


class SensorAssignmentRequest(BaseModel):
    """Lista completa de sensores associados a um usuário."""

    sensor_ids: list[int] = Field(default_factory=list)


class AdminUserResponse(BaseModel):
    """Resumo administrativo de um usuário."""

    user_id: int
    name: str
    email: str
    email_verified: bool
    role: str
    sensor_count: int
    created_at: datetime


class AdminSensorAssignment(BaseModel):
    """Dados de um sensor e seus usuários associados."""

    sensor_id: int
    name: str
    region: str
    status: str
    user_ids: list[int]


class AdminOverviewResponse(BaseModel):
    """Indicadores gerais do painel administrativo."""

    user_count: int
    admin_count: int
    sensor_count: int
    unassigned_sensor_count: int


class AdminAuditResponse(BaseModel):
    """Registro de uma ação administrativa."""

    audit_id: int
    admin_user_id: int
    admin_name: str
    action: str
    target_user_id: int | None
    target_sensor_id: int | None
    details: str
    created_at: datetime
