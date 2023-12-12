from typing import (
    Any,
    Type,
    TypeVar,
    Generic,
    Sequence,
    TYPE_CHECKING,
)
from datetime import datetime
from uuid import UUID
from uuid_extensions import uuid7
from sqlalchemy import Column
from sqlalchemy.orm import declared_attr, RelationshipProperty
from sqlalchemy.engine.row import Row
from pydantic import BaseModel, field_validator
from sqlmodel import Field, SQLModel, DateTime
from .util import build_tz_aware_date, parse_and_coerce_to_utc_datetime

if TYPE_CHECKING:
    from .resource import Resource


# -------------------------------------------------------------------------------------------
# SCHEMAS / MODELS
# -------------------------------------------------------------------------------------------

T = TypeVar("T")


class RelationshipConfig:
    orm_relationship: RelationshipProperty
    foreign_resource: "Resource"

    def __init__(
        self,
        orm_relationship: RelationshipProperty,
        foreign_resource: "Resource",
    ):
        self.orm_relationship = orm_relationship
        self.foreign_resource = foreign_resource


class CruddyGenericModel(BaseModel, Generic[T]):
    pass


class BulkDTO(CruddyGenericModel):
    total_pages: int
    total_records: int
    limit: int
    page: int
    data: Sequence[Row]

    class Config:
        arbitrary_types_allowed = True


class ResponseSchema(CruddyGenericModel):
    # The response for a single object return
    data: Any | None = None


class CruddyModel(SQLModel):
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__


class MetaObject(CruddyModel):
    page: int = Field(schema_extra={"examples": [1]})
    limit: int = Field(schema_extra={"examples": [10]})
    pages: int = Field(schema_extra={"examples": [1]})
    records: int = Field(schema_extra={"examples": [1]})


class PageResponse(CruddyGenericModel):
    # The response for a pagination query.
    meta: Type[CruddyModel] | Type[CruddyGenericModel]
    data: list[Any]


class CruddyIntIDModel(CruddyModel):
    id: int | None = Field(
        default=None,
        primary_key=True,
        index=True,
        nullable=False,
    )


class CruddyUUIDModel(CruddyModel):
    id: UUID = Field(
        default_factory=uuid7,
        primary_key=True,
        index=True,
        nullable=False,
    )


class CruddyCreatedUpdatedSignature(CruddyModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None


def CruddyCreatedUpdatedMixin() -> type[CruddyCreatedUpdatedSignature]:
    class CruddyCreatedUpdatedInstance(CruddyCreatedUpdatedSignature):
        created_at: datetime | None = Field(
            default_factory=build_tz_aware_date,
            sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
        )
        updated_at: datetime | None = Field(
            default_factory=build_tz_aware_date,
            sa_column=Column(
                DateTime(timezone=True),
                nullable=False,
                index=True,
                onupdate=build_tz_aware_date,
            ),
        )

        @field_validator("created_at", "updated_at", mode="before")
        @classmethod
        def _validate_cruddy_timestamps(cls, v: Any) -> datetime:
            return parse_and_coerce_to_utc_datetime(v)

    return CruddyCreatedUpdatedInstance


class ExampleUpdate(CruddyModel):
    updateable_field: str


class ExampleCreate(ExampleUpdate):
    create_only_field: str


class ExampleView(CruddyIntIDModel, ExampleCreate):
    pass


class Example(ExampleView, table=False):  # type: ignore # Set table=True on your app's core models
    db_only_field: str
