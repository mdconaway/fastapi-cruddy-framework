from typing import (
    Any,
    Type,
    TypeVar,
    Optional,
    Generic,
    Union,
    Sequence,
    List,
    TYPE_CHECKING,
)
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column
from sqlalchemy.orm import declared_attr, RelationshipProperty  # , mapped_column
from sqlalchemy.engine.row import Row
from pydantic import BaseModel  # , GetCoreSchemaHandler
from sqlmodel import Field, SQLModel, DateTime
from .util import build_tz_aware_date

# from pydantic.types import _check_annotated_type
# from pydantic_core.core_schema import CoreSchema, datetime_schema

if TYPE_CHECKING:
    from .resource import Resource


# -------------------------------------------------------------------------------------------
# SCHEMAS / MODELS
# -------------------------------------------------------------------------------------------

T = TypeVar("T")


# class UTCDateTime:
#    """A datetime that needs UTC as the timezone."""
#
#    @classmethod
#    def __get_pydantic_core_schema__(
#        cls, source: type[Any], handler: GetCoreSchemaHandler
#    ) -> CoreSchema:
#        if cls is source:
#            # used directly as a type
#            return datetime_schema(tz_constraint=0)
#        else:
#            schema = handler(source)
#            _check_annotated_type(schema["type"], "datetime", cls.__name__)
#            schema["tz_constraint"] = 0  # type: ignore
#            return schema
#
#    def __repr__(self) -> str:
#        return "UTCDateTime"

# UTCDateTime = Annotated[datetime, FieldAfterValidator(parse_and_coerce_to_utc_datetime)]

# class UTCDateTime(datetime):
#    @classmethod
#    def __get_validators__(cls):
#        yield parse_datetime
#        yield cls.validate
#
#    @classmethod
#    def validate(cls, v):
#        return coerce_to_utc_datetime(v)


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
    data: Optional[Any] = None


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
    meta: Union[Type[CruddyModel], Type[CruddyGenericModel]]
    data: List[Any]


class CruddyIntIDModel(CruddyModel):
    id: Optional[int] = Field(
        default=None,
        primary_key=True,
        index=True,
        nullable=False,
    )
    created_at: Optional[datetime] = Field(
        default_factory=build_tz_aware_date,
        sa_column=lambda: Column(DateTime(timezone=True), nullable=False, index=True),
    )
    updated_at: Optional[datetime] = Field(
        default_factory=build_tz_aware_date,
        sa_column=lambda: Column(
            DateTime(timezone=True),
            nullable=False,
            index=True,
            onupdate=build_tz_aware_date,
        ),
    )


class CruddyUUIDModel(CruddyModel):
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    created_at: Optional[datetime] = Field(
        default_factory=build_tz_aware_date,
        sa_column=lambda: Column(DateTime(timezone=True), nullable=False, index=True),
    )
    updated_at: Optional[datetime] = Field(
        default_factory=build_tz_aware_date,
        sa_column=lambda: Column(
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


class Example(ExampleView, table=False):  # type: ignore # Set table=True on your app's core models
    db_only_field: str
