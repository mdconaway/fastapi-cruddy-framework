from sqlalchemy import Column
from sqlalchemy.orm import declared_attr, RelationshipProperty
from sqlalchemy.engine.row import Row
from typing import Any, Type, TypeVar, Optional, Generic, Union, List, TYPE_CHECKING
from pydantic.generics import GenericModel
from pydantic.datetime_parse import parse_datetime
from sqlmodel import Field, SQLModel, DateTime
from datetime import datetime
from .uuid import UUID, uuid7
from .util import build_tz_aware_date, coerce_to_utc_datetime

if TYPE_CHECKING:
    from .resource import Resource


# -------------------------------------------------------------------------------------------
# SCHEMAS / MODELS
# -------------------------------------------------------------------------------------------

T = TypeVar("T")


class UTCDateTime(datetime):
    @classmethod
    def __get_validators__(cls):
        yield parse_datetime
        yield cls.validate

    @classmethod
    def validate(cls, v):
        return coerce_to_utc_datetime(v)


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


class CruddyGenericModel(GenericModel, Generic[T]):
    def __init__(self, *args, **kwargs):
        return super().__init__(*args, **kwargs)


class BulkDTO(CruddyGenericModel):
    total_pages: int
    total_records: int
    limit: int
    page: int
    data: List[Row]

    class Config:
        arbitrary_types_allowed = True


class ResponseSchema(CruddyGenericModel):
    # The response for a single object return
    data: Optional[Any] = None


class CruddyModel(SQLModel):
    @declared_attr  # type: ignore
    def __tablename__(cls) -> str:
        return cls.__name__


class MetaObject(CruddyModel):
    page: int = Field(schema_extra={"example": 1})
    limit: int = Field(schema_extra={"example": 10})
    pages: int = Field(schema_extra={"example": 1})
    records: int = Field(schema_extra={"example": 1})


class PageResponse(CruddyGenericModel):
    # The response for a pagination query.
    meta: Union[Type[CruddyModel], Type[CruddyGenericModel]]
    data: List[Any]


class CruddyIntIDModel(CruddyModel):
    id: Optional[int] = Field(
        default=None,
        primary_key=True,
        index=True,
        nullable=False,
    )
    created_at: Optional[UTCDateTime] = Field(
        default_factory=build_tz_aware_date,
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
    updated_at: Optional[UTCDateTime] = Field(
        default_factory=build_tz_aware_date,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            index=True,
            onupdate=build_tz_aware_date,
        ),
    )


class CruddyUUIDModel(CruddyModel):
    id: UUID = Field(
        default_factory=uuid7,
        primary_key=True,
        index=True,
        nullable=False,
    )
    created_at: Optional[UTCDateTime] = Field(
        default_factory=build_tz_aware_date,
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
    updated_at: Optional[UTCDateTime] = Field(
        default_factory=build_tz_aware_date,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            index=True,
            onupdate=build_tz_aware_date,
        ),
    )


class ExampleUpdate(CruddyModel):
    updateable_field: str


class ExampleCreate(ExampleUpdate):
    create_only_field: str


class ExampleView(CruddyIntIDModel, ExampleCreate):
    pass


class Example(ExampleView, table=False):  # Set table=True on your app's core models
    db_only_field: str
