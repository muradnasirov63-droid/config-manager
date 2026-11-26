from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    owner: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    configs: Mapped[list["Config"]] = relationship(
        back_populates="service", cascade="all, delete-orphan"
    )


class Environment(Base):
    __tablename__ = "environments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    namespace: Mapped[str] = mapped_column(String(100))

    configs: Mapped[list["Config"]] = relationship(
        back_populates="environment", cascade="all, delete-orphan"
    )


class Config(Base):
    __tablename__ = "configs"
    __table_args__ = (
        UniqueConstraint("service_id", "environment_id", name="uq_config_service_env"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), index=True)
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"), index=True)
    format: Mapped[str] = mapped_column(String(10), default="yaml")
    schema_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    current_version: Mapped[int] = mapped_column(Integer, default=0)

    service: Mapped[Service] = relationship(back_populates="configs")
    environment: Mapped[Environment] = relationship(back_populates="configs")
    versions: Mapped[list["ConfigVersion"]] = relationship(
        back_populates="config",
        cascade="all, delete-orphan",
        order_by="ConfigVersion.version_number",
    )


class ConfigVersion(Base):
    __tablename__ = "config_versions"
    __table_args__ = (
        UniqueConstraint("config_id", "version_number", name="uq_version_per_config"),
        Index("ix_versions_config_number", "config_id", "version_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    config_id: Mapped[int] = mapped_column(ForeignKey("configs.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    author: Mapped[str] = mapped_column(String(100))
    comment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    config: Mapped[Config] = relationship(back_populates="versions")


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    channel: Mapped[str] = mapped_column(String(20))
    endpoint: Mapped[str] = mapped_column(String(255))
    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id"), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("config_versions.id"), index=True)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="sent")
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
