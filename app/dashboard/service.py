"""Serviço responsável pelo servidor web do dashboard."""

from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth.dependencies import get_optional_current_user
from app.auth.models import User
from app.auth.routes import router as auth_router
from app.dashboard.routes import router


class DashboardService:
    """Gerencia a aplicação web do dashboard."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
    ):
        self.host = host
        self.port = port

        base_dir = Path(__file__).resolve().parent

        self.app = FastAPI(
            title="NoiseSensor Dashboard",
        )

        self.templates = Jinja2Templates(
            directory=base_dir / "templates",
        )

        self.app.mount(
            "/static",
            StaticFiles(
                directory=base_dir / "static"
            ),
            name="static",
        )

        self.app.include_router(router)
        self.app.include_router(auth_router)

        self._configure_pages()

    def _configure_pages(self) -> None:
        """Configura as páginas HTML do dashboard."""

        @self.app.get("/")
        def dashboard(
            request: Request,
            current_user: User | None = Depends(
                get_optional_current_user
            ),
        ):
            """Entrega o dashboard somente para usuários autenticados."""

            if current_user is None:
                return RedirectResponse(
                    url="/login",
                    status_code=303,
                )

            return self.templates.TemplateResponse(
                request=request,
                name="dashboard.html",
            )

        @self.app.get("/login")
        def login_page(
            request: Request,
            current_user: User | None = Depends(
                get_optional_current_user
            ),
        ):
            """Exibe a página de login para usuários não autenticados."""

            if current_user is not None:
                return RedirectResponse(
                    url="/",
                    status_code=303,
                )

            return self.templates.TemplateResponse(
                request=request,
                name="login.html",
            )

        @self.app.get("/cadastro")
        def cadastro_page(
            request: Request,
            current_user: User | None = Depends(
                get_optional_current_user
            ),
        ):
            """Exibe a página de cadastro para usuários não autenticados."""

            if current_user is not None:
                return RedirectResponse(
                    url="/",
                    status_code=303,
                )

            return self.templates.TemplateResponse(
                request=request,
                name="cadastro.html",
            )

    def run(self) -> None:
        """Inicia o servidor do dashboard."""

        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
        )
