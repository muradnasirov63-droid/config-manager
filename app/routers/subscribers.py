from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import NotificationRead, SubscriberCreate, SubscriberRead
from app.service import config_service

router = APIRouter(tags=["notifications"])


@router.get("/subscribers", response_model=list[SubscriberRead])
def list_subscribers(db: Session = Depends(get_db)):
    return config_service.list_subscribers(db)


@router.post("/subscribers", response_model=SubscriberRead, status_code=status.HTTP_201_CREATED)
def create_subscriber(data: SubscriberCreate, db: Session = Depends(get_db)):
    return config_service.create_subscriber(db, data)


@router.delete("/subscribers/{subscriber_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscriber(subscriber_id: int, db: Session = Depends(get_db)):
    config_service.delete_subscriber(db, subscriber_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/notifications", response_model=list[NotificationRead])
def list_notifications(db: Session = Depends(get_db)):
    return config_service.list_notifications(db)
