from typing import (
    Any,
    Type,
    TypeVar,
    Generic,
    Sequence,
    NewType,
    TYPE_CHECKING,
)
from re import match
from datetime import datetime
from uuid import UUID
from uuid_extensions import uuid7
from fastapi import HTTPException, status
from sqlalchemy import Column
from sqlalchemy.orm import declared_attr, RelationshipProperty
from sqlalchemy.engine.row import Row
from pydantic import BaseModel, ConfigDict, field_validator
from strawberry import scalar
from sqlmodel import Field, SQLModel, DateTime
from .util import build_tz_aware_date, parse_and_coerce_to_utc_datetime

if TYPE_CHECKING:
    from .resource import Resource

HTTP_422_UNPROCESSABLE_ENTITY = status.HTTP_422_UNPROCESSABLE_ENTITY

# -------------------------------------------------------------------------------------------
# SCHEMAS / MODELS
# -------------------------------------------------------------------------------------------
BROADCAST_EVENT = "broadcast"
CONTROL_EVENT = "control"
DISCONNECT_EVENT = "disconnect"
ROOM_EVENT = "room"
CLIENT_EVENT = "client"
KILL_SOCKET_BY_ID = "killsocket_id"
KILL_SOCKET_BY_CLIENT = "killsocket_client"
KILL_ROOM_BY_ID = "killroom_id"
JOIN_SOCKET_BY_ID = "joinsocket_id"
JOIN_SOCKET_BY_CLIENT = "joinsocket_client"
LEAVE_SOCKET_BY_ID = "leavesocket_id"
LEAVE_SOCKET_BY_CLIENT = "leavesocket_client"
CLIENT_MESSAGE_EVENT = "client_message"
T = TypeVar("T")

# The below graphQL types are basically pass-through types to improve performance
# The base resource responders will have already formatted these elements properly
CruddyGQLDateTime = scalar(
    NewType("CruddyGQLDateTime", str),
    serialize=lambda v: v,
    parse_value=lambda v: v,
)

CruddyGQLObject = scalar(
    NewType("CruddyGQLObject", dict),
    serialize=lambda v: v,
    parse_value=lambda v: v,
)

CruddyGQLArray = scalar(
    NewType("CruddyGQLArray", list),
    serialize=lambda v: v,
    parse_value=lambda v: v,
)


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


class SocketMessage(CruddyGenericModel):
    route: str = (
        BROADCAST_EVENT  # How to route this between the pubsub/connection_manager module (default to a broadcast)
    )
    target: str | None = None  # A target for the message (if route is "room" or "user")
    type: str | None = None  # Message type
    sender: str | None = None  # Sender (if any)
    data: dict | None = None  # Message payload


class SocketRoomConfiguration(CruddyGenericModel):
    room_list: set


class ResponseSchema(CruddyGenericModel):
    # The response for a single object return
    data: Any | None = None


class CruddyModel(SQLModel):
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__


class MetaObject(CruddyModel):
    page: int = Field(schema_extra={"json_schema_extra": {"example": 1}})
    limit: int = Field(schema_extra={"json_schema_extra": {"example": 10}})
    pages: int = Field(schema_extra={"json_schema_extra": {"example": 1}})
    records: int = Field(schema_extra={"json_schema_extra": {"example": 1}})


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


class CruddyStringIDModel(CruddyModel):
    id: str = Field(
        default=None,
        primary_key=True,
        index=True,
        nullable=False,
    )

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{v} is not a string"
            )
        if not match(r"^[a-zA-Z0-9_-]+( [a-zA-Z0-9_-]+)*$", v):
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{v} must be alphanumeric, with dashes or underscores and only one space max between words",
            )
        return v


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


class CruddyGQLOverrides(CruddyModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)  # type: ignore
    links: CruddyGQLObject | None = None


class CruddyCreatedUpdatedGQLOverrides(CruddyModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)  # type: ignore
    links: CruddyGQLObject | None = None
    created_at: CruddyGQLDateTime | None = None
    updated_at: CruddyGQLDateTime | None = None


class ExampleUpdate(CruddyModel):
    updateable_field: str


class ExampleCreate(ExampleUpdate):
    create_only_field: str


class ExampleView(CruddyIntIDModel, ExampleCreate):
    pass


class Example(ExampleView, table=False):  # type: ignore # Set table=True on your app's core models
    db_only_field: str
