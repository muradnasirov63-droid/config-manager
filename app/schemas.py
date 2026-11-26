from datetime import datetime
from typing import Annotated, Literal
from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _non_blank(v: str) -> str:
    if not v or not v.strip():
        raise ValueError("Content must not be blank")
    return v


NonBlankText = Annotated[str, AfterValidator(_non_blank)]


class ServiceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    owner: str = Field(min_length=1, max_length=100)


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    owner: str
    created_at: datetime


class EnvironmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$")
    namespace: str = Field(min_length=1, max_length=100)


class EnvironmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    namespace: str


class ConfigCreate(BaseModel):
    service_id: int = Field(gt=0)
    environment_id: int = Field(gt=0)
    format: Literal["yaml", "json"] = "yaml"
    schema_ref: str | None = Field(default=None, max_length=100)
    content: NonBlankText
    author: str = Field(min_length=1, max_length=100)
    comment: str | None = Field(default=None, max_length=255)


class ConfigUpdate(BaseModel):
    content: NonBlankText
    author: str = Field(min_length=1, max_length=100)
    comment: str | None = Field(default=None, max_length=255)


class ConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    service_id: int
    environment_id: int
    format: str
    schema_ref: str | None
    current_version: int


class ConfigVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    config_id: int
    version_number: int
    content: str
    author: str
    comment: str | None
    created_at: datetime


class RollbackRequest(BaseModel):
    version_number: int = Field(gt=0)
    author: str = Field(min_length=1, max_length=100)
    comment: str | None = Field(default=None, max_length=255)


class ValidateRequest(BaseModel):
    content: NonBlankText
    format: Literal["yaml", "json"] = "yaml"
    schema_ref: str | None = Field(default=None, max_length=100)


class ValidationReport(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class SubscriberCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    channel: Literal["webhook", "email", "sse"]
    endpoint: str = Field(min_length=1, max_length=255)
    service_id: int | None = Field(default=None, gt=0)


class SubscriberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    channel: str
    endpoint: str
    service_id: int | None


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    version_id: int
    subscriber_id: int
    status: str
    attempts: int
    error: str | None
    sent_at: datetime | None
