"""Serviço responsável pelo servidor web do dashboard."""

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
            StaticFiles(directory=base_dir / "static"),
            name="static",
        )

        self.app.include_router(router)

        self._configure_pages()

    def _configure_pages(self) -> None:
        """Configura as páginas HTML do dashboard."""

        @self.app.get("/")
        def dashboard(request: Request):
            return self.templates.TemplateResponse(
                request=request,
                name="dashboard.html",
            )

    def run(self) -> None:
        """Inicia o servidor do dashboard."""

        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
        )
