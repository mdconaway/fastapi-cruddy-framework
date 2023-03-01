from sqlalchemy.orm import declared_attr, RelationshipProperty
from typing import TypeVar, Optional, Generic, List, TYPE_CHECKING
from pydantic.generics import GenericModel
from sqlmodel import Field, SQLModel
from datetime import datetime
from .uuid import UUID, uuid7

if TYPE_CHECKING:
    from .resource import Resource


# -------------------------------------------------------------------------------------------
# SCHEMAS / MODELS
# -------------------------------------------------------------------------------------------

T = TypeVar("T")


class RelationshipConfig:
    orm_relationship: RelationshipProperty = None
    foreign_resource: "Resource" = None

    def __init__(self, orm_relationship=None, foreign_resource=None):
        self.orm_relationship = orm_relationship
        self.foreign_resource = foreign_resource


class CruddyGenericModel(GenericModel, Generic[T]):
    def __init__(self, *args, **kwargs):
        return super().__init__(*args, **kwargs)


class BulkDTO(CruddyGenericModel):
    total_pages: int
    total_records: int
    data: List


class MetaObject(CruddyGenericModel):
    page: int
    limit: int
    pages: int
    records: int


class PageResponse(CruddyGenericModel):
    # The response for a pagination query.
    meta: MetaObject
    data: List[T]


class ResponseSchema(SQLModel):
    # The response for a single object return
    data: Optional[T] = None


class CruddyModel(SQLModel):
    @declared_attr  # type: ignore
    def __tablename__(cls) -> str:
        return cls.__name__


class CruddyIntIDModel(CruddyModel):
    id: Optional[int] = Field(
        default=None,
        primary_key=True,
        index=True,
        nullable=False,
    )
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow}
    )
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class CruddyUUIDModel(CruddyModel):
    id: UUID = Field(
        default_factory=uuid7,
        primary_key=True,
        index=True,
        nullable=False,
    )
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow}
    )
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class ExampleUpdate(CruddyModel):
    updateable_field: str


class ExampleCreate(ExampleUpdate):
    create_only_field: str


class ExampleView(CruddyIntIDModel, ExampleCreate):
    pass


class Example(ExampleView, table=False):  # Set table=True on your app's core models
    db_only_field: str
