from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import EnvironmentCreate, EnvironmentRead, ServiceCreate, ServiceRead
from app.service import config_service

router = APIRouter(tags=["catalog"])


@router.get("/services", response_model=list[ServiceRead])
def list_services(db: Session = Depends(get_db)):
    return config_service.list_services(db)


@router.post("/services", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def create_service(data: ServiceCreate, db: Session = Depends(get_db)):
    return config_service.create_service(db, data)


@router.get("/services/{service_id}", response_model=ServiceRead)
def get_service(service_id: int, db: Session = Depends(get_db)):
    return config_service.get_service(db, service_id)


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(service_id: int, db: Session = Depends(get_db)):
    config_service.delete_service(db, service_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/environments", response_model=list[EnvironmentRead])
def list_environments(db: Session = Depends(get_db)):
    return config_service.list_environments(db)


@router.post("/environments", response_model=EnvironmentRead, status_code=status.HTTP_201_CREATED)
def create_environment(data: EnvironmentCreate, db: Session = Depends(get_db)):
    return config_service.create_environment(db, data)


@router.delete("/environments/{env_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_environment(env_id: int, db: Session = Depends(get_db)):
    config_service.delete_environment(db, env_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
