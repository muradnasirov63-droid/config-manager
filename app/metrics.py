from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models import Config, ConfigVersion, Notification, Service

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Общее количество HTTP-запросов",
    ["method", "path", "status"],
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Время обработки HTTP-запроса, с",
    ["method", "path"],
)
VALIDATION_ERRORS_TOTAL = Counter(
    "config_validation_errors_total",
    "Количество ошибок валидации конфигураций (Т2)",
)
SERVICES_TOTAL = Gauge("config_services_total", "Количество зарегистрированных микросервисов")
CONFIGS_TOTAL = Gauge("config_configs_total", "Количество конфигураций в базе")
VERSIONS_TOTAL = Gauge("config_versions_total", "Количество сохранённых версий конфигураций")
NOTIFICATIONS_TOTAL = Gauge(
    "config_notifications_total",
    "Количество записей в журнале уведомлений по статусу (Т3)",
    ["status"],
)


def render_metrics(db: Session) -> tuple[bytes, str]:
    try:
        SERVICES_TOTAL.set(db.scalar(select(func.count(Service.id))) or 0)
        CONFIGS_TOTAL.set(db.scalar(select(func.count(Config.id))) or 0)
        VERSIONS_TOTAL.set(db.scalar(select(func.count(ConfigVersion.id))) or 0)
        for st in ("sent", "failed"):
            cnt = db.scalar(
                select(func.count(Notification.id)).where(Notification.status == st)
            ) or 0
            NOTIFICATIONS_TOTAL.labels(status=st).set(cnt)
    except Exception:
        pass
    return generate_latest(), CONTENT_TYPE_LATEST
