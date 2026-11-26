import logging
from abc import ABC, abstractmethod
from typing import Any
import httpx
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from app.models import Config, ConfigVersion, Notification, Subscriber, utcnow

log = logging.getLogger(__name__)


class NotificationChannel(ABC):
    @abstractmethod
    def send(self, endpoint: str, payload: dict[str, Any]) -> None:
        ...


class WebhookChannel(NotificationChannel):
    def send(self, endpoint: str, payload: dict[str, Any]) -> None:
        resp = httpx.post(endpoint, json=payload, timeout=3.0)
        resp.raise_for_status()


class EmailChannel(NotificationChannel):
    def send(self, endpoint: str, payload: dict[str, Any]) -> None:
        log.info("Email notification to %s: %s", endpoint, payload)


class SseChannel(NotificationChannel):
    def send(self, endpoint: str, payload: dict[str, Any]) -> None:
        log.info("SSE notification to %s: %s", endpoint, payload)


CHANNELS: dict[str, NotificationChannel] = {
    "webhook": WebhookChannel(),
    "email": EmailChannel(),
    "sse": SseChannel(),
}


class NotificationService:
    def __init__(self, channels: dict[str, NotificationChannel] | None = None):
        self.channels = channels or CHANNELS

    def notify_subscribers(
        self, db: Session, config: Config, version: ConfigVersion
    ) -> list[Notification]:
        subscribers = db.scalars(
            select(Subscriber).where(
                or_(Subscriber.service_id.is_(None), Subscriber.service_id == config.service_id)
            )
        ).all()
        payload = {
            "event": "config.updated",
            "service": config.service.name,
            "environment": config.environment.name,
            "config_id": config.id,
            "version": version.version_number,
            "author": version.author,
        }
        results: list[Notification] = []
        for sub in subscribers:
            note = Notification(version_id=version.id, subscriber_id=sub.id, attempts=1)
            try:
                self.channels[sub.channel].send(sub.endpoint, payload)
                note.status, note.sent_at = "sent", utcnow()
            except Exception as exc:
                note.status, note.error = "failed", str(exc)[:255]
                log.warning("Notification to %s failed: %s", sub.name, exc)
            db.add(note)
            results.append(note)
        db.commit()
        return results
