"""Rotas HTTP relacionadas à autenticação."""

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Response,
    status,
)
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta, timezone

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.auth.schemas import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    UserResponse,
)
from app.auth.repository import create_telegram_link_token
from app.auth.security import (
    SESSION_COOKIE_NAME,
    generate_token,
    hash_token,
)
from app.auth.service import AuthService
from app.database.connection import create_connection
from app.notifications.telegram import (
    get_connection_url,
    is_configured as telegram_is_configured,
)


router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"],
)


auth_service = AuthService()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
) -> UserResponse:
    """Cria uma nova conta."""

    with create_connection() as connection:
        try:
            user = auth_service.register(
                connection=connection,
                name=data.name,
                email=data.email,
                password=data.password,
                confirm_password=data.confirm_password,
            )

        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error

    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        email_verified=user.email_verified,
        telegram_chat_id=user.telegram_chat_id,
    )


@router.get(
    "/verify",
)
def verify_email(
    token: str,
):
    """Verifica o e-mail e redireciona o usuário para o login."""

    with create_connection() as connection:
        verified = auth_service.verify_email(
            connection,
            token,
        )

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Token inválido, expirado "
                "ou já utilizado."
            ),
        )

    return RedirectResponse(
        url="/login?verified=1",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/telegram/link")
def create_telegram_link(
    current_user: User = Depends(get_current_user),
):
    """Gera um link temporário para vincular o Telegram à conta atual."""

    if not telegram_is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "O Telegram não está configurado no servidor. "
                "Configure TELEGRAM_BOT_TOKEN e TELEGRAM_BOT_USERNAME."
            ),
        )

    raw_token = generate_token()
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    with create_connection() as connection:
        create_telegram_link_token(
            connection=connection,
            user_id=current_user.user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

    try:
        telegram_url = get_connection_url(raw_token)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    return RedirectResponse(
        url=telegram_url,
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/login",
    response_model=UserResponse,
)
def login(
    data: LoginRequest,
    response: Response,
) -> UserResponse:
    """Realiza login e cria uma sessão."""

    with create_connection() as connection:
        try:
            session_token, user = auth_service.login(
                connection=connection,
                email=data.email,
                password=data.password,
            )

        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(error),
            ) from error

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=False,
        samesite="strict",
        path="/",
    )

    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        email_verified=user.email_verified,
        telegram_chat_id=user.telegram_chat_id,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
)
def logout(
    response: Response,
    session_token: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
    current_user: User = Depends(
        get_current_user
    ),
) -> MessageResponse:
    """Encerra a sessão atual."""

    if session_token is not None:
        with create_connection() as connection:
            auth_service.logout(
                connection,
                session_token,
            )

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
    )

    return MessageResponse(
        message="Logout realizado com sucesso."
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(
        get_current_user
    ),
) -> UserResponse:
    """Retorna o usuário atualmente autenticado."""

    return UserResponse(
        user_id=current_user.user_id,
        name=current_user.name,
        email=current_user.email,
        email_verified=current_user.email_verified,
        telegram_chat_id=current_user.telegram_chat_id,
    )
