from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Config, ConfigVersion, Environment, Notification, Service, Subscriber
from app.notifier import NotificationService
from app.repository import VersionRepository
from app.schemas import ConfigCreate, ConfigUpdate, EnvironmentCreate, RollbackRequest, ServiceCreate, SubscriberCreate
from app.validator import ConfigValidator


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class ValidationFailed(Exception):
    def __init__(self, errors: list[str]):
        super().__init__("Config validation failed")
        self.errors = errors


class ConfigService:
    def __init__(self):
        self.repository = VersionRepository()
        self.validator = ConfigValidator()
        self.notifier = NotificationService()

    def _validate(self, content: str, fmt: str, schema_ref: str | None) -> None:
        report = self.validator.validate(content, fmt, schema_ref)
        if not report.valid:
            raise ValidationFailed(report.errors)

    # Services
    def create_service(self, db: Session, data: ServiceCreate) -> Service:
        if db.scalar(select(Service).where(Service.name == data.name)):
            raise ConflictError(f"Service '{data.name}' already exists")
        svc = Service(name=data.name, owner=data.owner)
        db.add(svc)
        db.commit()
        db.refresh(svc)
        return svc

    def list_services(self, db: Session) -> list[Service]:
        return list(db.scalars(select(Service).order_by(Service.id)).all())

    def get_service(self, db: Session, service_id: int) -> Service:
        svc = db.get(Service, service_id)
        if not svc:
            raise NotFoundError(f"Service {service_id} not found")
        return svc

    def delete_service(self, db: Session, service_id: int) -> None:
        svc = self.get_service(db, service_id)
        db.delete(svc)
        db.commit()

    # Environments
    def create_environment(self, db: Session, data: EnvironmentCreate) -> Environment:
        if db.scalar(select(Environment).where(Environment.name == data.name)):
            raise ConflictError(f"Environment '{data.name}' already exists")
        env = Environment(name=data.name, namespace=data.namespace)
        db.add(env)
        db.commit()
        db.refresh(env)
        return env

    def list_environments(self, db: Session) -> list[Environment]:
        return list(db.scalars(select(Environment).order_by(Environment.id)).all())

    def delete_environment(self, db: Session, env_id: int) -> None:
        env = db.get(Environment, env_id)
        if not env:
            raise NotFoundError(f"Environment {env_id} not found")
        db.delete(env)
        db.commit()

    # Configs
    def create_config(self, db: Session, data: ConfigCreate) -> Config:
        self.get_service(db, data.service_id)
        if not db.get(Environment, data.environment_id):
            raise NotFoundError(f"Environment {data.environment_id} not found")
        existing = db.scalar(
            select(Config).where(
                Config.service_id == data.service_id,
                Config.environment_id == data.environment_id,
            )
        )
        if existing:
            raise ConflictError("Config for this service and environment already exists")

        self._validate(data.content, data.format, data.schema_ref)
        config = Config(
            service_id=data.service_id,
            environment_id=data.environment_id,
            format=data.format,
            schema_ref=data.schema_ref,
            current_version=0,
        )
        db.add(config)
        db.commit()
        db.refresh(config)

        version = self.repository.save_version(db, config, data.content, data.author, data.comment)
        self.notifier.notify_subscribers(db, config, version)
        return config

    def get_config(self, db: Session, config_id: int) -> Config:
        cfg = db.get(Config, config_id)
        if not cfg:
            raise NotFoundError(f"Config {config_id} not found")
        return cfg

    def update_config(self, db: Session, config_id: int, data: ConfigUpdate) -> Config:
        config = self.get_config(db, config_id)
        self._validate(data.content, config.format, config.schema_ref)
        version = self.repository.save_version(db, config, data.content, data.author, data.comment)
        self.notifier.notify_subscribers(db, config, version)
        return config

    def delete_config(self, db: Session, config_id: int) -> None:
        cfg = self.get_config(db, config_id)
        db.delete(cfg)
        db.commit()

    def list_versions(self, db: Session, config_id: int) -> list[ConfigVersion]:
        self.get_config(db, config_id)
        return self.repository.list_versions(db, config_id)

    def get_version(self, db: Session, config_id: int, version_number: int) -> ConfigVersion:
        self.get_config(db, config_id)
        ver = self.repository.get_version(db, config_id, version_number)
        if not ver:
            raise NotFoundError(f"Version {version_number} for config {config_id} not found")
        return ver

    def rollback_config(self, db: Session, config_id: int, data: RollbackRequest) -> Config:
        config = self.get_config(db, config_id)
        target = self.get_version(db, config_id, data.version_number)
        comment = data.comment or f"Rollback to v{data.version_number}"
        version = self.repository.save_version(db, config, target.content, data.author, comment)
        self.notifier.notify_subscribers(db, config, version)
        return config

    def diff_versions(self, db: Session, config_id: int, from_v: int, to_v: int) -> dict:
        v1 = self.get_version(db, config_id, from_v)
        v2 = self.get_version(db, config_id, to_v)
        return {
            "config_id": config_id,
            "from_version": from_v,
            "to_version": to_v,
            "diff": self.repository.diff(v1, v2),
        }

    def fetch_actual(self, db: Session, service_name: str, env_name: str, version: int | None = None) -> dict:
        svc = db.scalar(select(Service).where(Service.name == service_name))
        env = db.scalar(select(Environment).where(Environment.name == env_name))
        if not svc or not env:
            raise NotFoundError(f"Config for {service_name}/{env_name} not found")
        cfg = db.scalar(
            select(Config).where(Config.service_id == svc.id, Config.environment_id == env.id)
        )
        if not cfg:
            raise NotFoundError(f"Config for {service_name}/{env_name} not found")
        ver_num = version if version is not None else cfg.current_version
        ver = self.repository.get_version(db, cfg.id, ver_num)
        if not ver:
            raise NotFoundError(f"Version {ver_num} for {service_name}/{env_name} not found")
        return {
            "service": svc.name,
            "environment": env.name,
            "format": cfg.format,
            "version": ver.version_number,
            "content": ver.content,
        }

    # Subscribers & Notifications
    def create_subscriber(self, db: Session, data: SubscriberCreate) -> Subscriber:
        if data.service_id is not None:
            self.get_service(db, data.service_id)
        sub = Subscriber(**data.model_dump())
        db.add(sub)
        db.commit()
        db.refresh(sub)
        return sub

    def list_subscribers(self, db: Session) -> list[Subscriber]:
        return list(db.scalars(select(Subscriber).order_by(Subscriber.id)).all())

    def delete_subscriber(self, db: Session, sub_id: int) -> None:
        sub = db.get(Subscriber, sub_id)
        if not sub:
            raise NotFoundError(f"Subscriber {sub_id} not found")
        db.delete(sub)
        db.commit()

    def list_notifications(self, db: Session) -> list[Notification]:
        return list(db.scalars(select(Notification).order_by(Notification.id)).all())


config_service = ConfigService()
