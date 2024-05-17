from typing import Any
from datetime import datetime
from fastapi_cruddy_framework import (
    CruddyModel,
    CruddyUUIDModel,
    CruddyCreatedUpdatedSignature,
    CruddyCreatedUpdatedMixin,
    validate_utc_datetime,
)
from pydantic import field_validator
from sqlmodel import Column, DateTime, Field, JSON


EXAMPLE_POST = {
    "content": "Today I felt like blogging. Fin.",
    "tags": {"categories": ["blog"]},
    "event_date": "2023-12-11T15:27:39.984Z",
}


def schema_example(value: Any):
    return {"json_schema_extra": {"example": value}}


class PostUpdate(CruddyModel):
    content: str = Field(schema_extra=schema_example(EXAMPLE_POST["content"]))
    event_date: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=True,
            index=True,
            default=None,
        ),
        schema_extra=schema_example(EXAMPLE_POST["event_date"]),
    )
    tags: dict = Field(
        sa_column=Column(JSON),
        default={},
        schema_extra=schema_example(EXAMPLE_POST["tags"]),
    )

    @field_validator("event_date", mode="before")
    @classmethod
    def validate_event_date(cls, v: Any) -> datetime | None:
        return validate_utc_datetime(v, allow_none=True)


class PostCreate(PostUpdate):
    pass


class PostView(CruddyCreatedUpdatedSignature, CruddyUUIDModel):
    content: str | None = Field(
        default=None, schema_extra=schema_example(EXAMPLE_POST["content"])
    )
    tags: dict[str, Any] | None = Field(
        sa_column=Column(JSON, index=True),
        default=None,
        schema_extra=schema_example(EXAMPLE_POST["tags"]),
    )
    event_date: datetime | None = None


class Post(CruddyCreatedUpdatedMixin(), CruddyUUIDModel, PostCreate, table=True):
    pass
