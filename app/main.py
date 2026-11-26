"""Точка входа: Система управления конфигурациями (вариант 15), ЛР№3–ЛР№5."""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import models, predict_api  # noqa: F401
from app.database import Base, SessionLocal, engine
from app.metrics import HTTP_LATENCY, HTTP_REQUESTS, VALIDATION_ERRORS_TOTAL, render_metrics
from app.routers import catalog, configs, subscribers
from app.service import ConflictError, NotFoundError, ValidationFailed


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Config Manager",
    description="Централизованное хранение конфигураций микросервисов: REST API, версионирование, "
    "валидация YAML/JSON, уведомления об изменениях, мониторинг и цифровой двойник.",
    version="0.5.0",
    lifespan=lifespan,
)

app.include_router(catalog.router)
app.include_router(configs.router)
app.include_router(subscribers.router)
app.include_router(predict_api.router)


@app.middleware("http")
async def collect_metrics(request: Request, call_next):
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        path = route.path if route is not None else "unmatched"
        if path != "/metrics":
            HTTP_REQUESTS.labels(request.method, path, str(status_code)).inc()
            HTTP_LATENCY.labels(request.method, path).observe(time.perf_counter() - start)


@app.exception_handler(NotFoundError)
async def not_found_handler(_: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict_handler(_: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ValidationFailed)
async def validation_failed_handler(_: Request, exc: ValidationFailed):
    VALIDATION_ERRORS_TOTAL.inc()
    return JSONResponse(
        status_code=422, content={"detail": "Config validation failed", "errors": exc.errors}
    )


@app.get("/health", tags=["system"])
def health():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "error", "db": "unavailable"})
    return {"status": "ok", "db": "up"}


@app.get("/metrics", tags=["system"])
def metrics():
    with SessionLocal() as db:
        body, content_type = render_metrics(db)
    return Response(content=body, media_type=content_type)
