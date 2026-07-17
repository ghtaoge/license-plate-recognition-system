from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import PROJECT_ROOT, Settings
from app.core.errors import AppError
from app.services.history_repository import HistoryRepository


def create_app() -> FastAPI:
    settings = Settings.from_env()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    repository = HistoryRepository(settings.database_path)
    repository.initialize()

    app = FastAPI(title="车牌号识别系统")
    app.state.settings = settings
    app.state.repository = repository

    app.include_router(router, prefix="/api")
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

    static_dir = PROJECT_ROOT / "app" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "message" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": "HTTP_ERROR", "message": str(exc.detail), "detail": ""},
        )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"code": exc.code, "message": exc.message, "detail": exc.detail},
        )

    @app.get("/")
    def index():
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse(
            status_code=404,
            content={"code": "FRONTEND_NOT_READY", "message": "前端页面尚未生成", "detail": ""},
        )

    return app


app = create_app()
