import difflib
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Config, ConfigVersion


class VersionRepository:
    def save_version(
        self, db: Session, config: Config, content: str, author: str, comment: str | None = None
    ) -> ConfigVersion:
        next_num = config.current_version + 1
        version = ConfigVersion(
            config_id=config.id,
            version_number=next_num,
            content=content,
            author=author,
            comment=comment,
        )
        config.current_version = next_num
        db.add(version)
        db.commit()
        db.refresh(version)
        db.refresh(config)
        return version

    def list_versions(self, db: Session, config_id: int) -> list[ConfigVersion]:
        return list(
            db.scalars(
                select(ConfigVersion)
                .where(ConfigVersion.config_id == config_id)
                .order_by(ConfigVersion.version_number)
            ).all()
        )

    def get_version(self, db: Session, config_id: int, version_number: int) -> ConfigVersion | None:
        return db.scalar(
            select(ConfigVersion).where(
                ConfigVersion.config_id == config_id,
                ConfigVersion.version_number == version_number,
            )
        )

    def diff(self, v1: ConfigVersion, v2: ConfigVersion) -> list[str]:
        return list(
            difflib.unified_diff(
                v1.content.splitlines(),
                v2.content.splitlines(),
                fromfile=f"v{v1.version_number}",
                tofile=f"v{v2.version_number}",
                lineterm="",
            )
        )
