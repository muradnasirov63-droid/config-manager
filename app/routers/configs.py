from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    ConfigCreate,
    ConfigRead,
    ConfigUpdate,
    ConfigVersionRead,
    RollbackRequest,
    ValidateRequest,
    ValidationReport,
)
from app.service import config_service

router = APIRouter(tags=["configs"])


@router.post("/configs/validate", response_model=ValidationReport)
def validate_config(data: ValidateRequest):
    return config_service.validator.validate(data.content, data.format, data.schema_ref)


@router.post("/configs", response_model=ConfigRead, status_code=status.HTTP_201_CREATED)
def create_config(data: ConfigCreate, db: Session = Depends(get_db)):
    return config_service.create_config(db, data)


@router.get("/configs/{config_id}", response_model=ConfigRead)
def get_config(config_id: int, db: Session = Depends(get_db)):
    return config_service.get_config(db, config_id)


@router.put("/configs/{config_id}", response_model=ConfigRead)
def update_config(config_id: int, data: ConfigUpdate, db: Session = Depends(get_db)):
    return config_service.update_config(db, config_id, data)


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_config(config_id: int, db: Session = Depends(get_db)):
    config_service.delete_config(db, config_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/configs/{config_id}/versions", response_model=list[ConfigVersionRead])
def list_versions(config_id: int, db: Session = Depends(get_db)):
    return config_service.list_versions(db, config_id)


@router.get("/configs/{config_id}/versions/{version_number}", response_model=ConfigVersionRead)
def get_version(config_id: int, version_number: int, db: Session = Depends(get_db)):
    return config_service.get_version(db, config_id, version_number)


@router.post("/configs/{config_id}/rollback", response_model=ConfigRead)
def rollback_config(config_id: int, data: RollbackRequest, db: Session = Depends(get_db)):
    return config_service.rollback_config(db, config_id, data)


@router.get("/configs/{config_id}/diff")
def diff_versions(
    config_id: int,
    from_version: int = Query(gt=0),
    to_version: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    return config_service.diff_versions(db, config_id, from_version, to_version)


@router.get("/configs/{config_id}/export", response_class=PlainTextResponse)
def export_config(config_id: int, db: Session = Depends(get_db)):
    cfg = config_service.get_config(db, config_id)
    ver = config_service.get_version(db, config_id, cfg.current_version)
    return ver.content


@router.get("/fetch/{service_name}/{env_name}")
def fetch_actual_config(
    service_name: str,
    env_name: str,
    version: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    return config_service.fetch_actual(db, service_name, env_name, version)
