from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import Field, Relationship, Column, DateTime
from fastapi_cruddy_framework import (
    UUID,
    CruddyModel,
    CruddyUUIDModel,
)
from examples.fastapi_cruddy_sqlite.models.common.relationships import GroupUserLink

if TYPE_CHECKING:
    from examples.fastapi_cruddy_sqlite.models.post import Post
    from examples.fastapi_cruddy_sqlite.models.group import Group

# The way the CRUD Router works, it needs an update, create, and base model.
# If you always structure model files in this order, you can extend from the
# minimal number of attrs that can be updated, all the way up to the maximal
# attrs in the base model. CRUD JSON serialization schemas are also exposed
# for modification, and it makes sense to keep your response schemas defined
# in the same location as the view model used to represent records to the
# client.


EXAMPLE_USER = {
    "first_name": "John",
    "last_name": "Smith",
    "email": "john.smith@cruddy-framework.com",
    "phone": "888-555-5555",
    "state": "FL",
    "country": "USA",
    "address": "101 Sunshine Way",
}


# The "Update" model variant describes all fields that can be affected by a
# client's PATCH action. Generally, the update model should have the fewest
# number of available fields for a client to manipulate.
class UserUpdate(CruddyModel):
    first_name: str = Field(schema_extra={"example": EXAMPLE_USER["first_name"]})
    last_name: str = Field(schema_extra={"example": EXAMPLE_USER["last_name"]})
    email: str = Field(
        nullable=True,
        index=True,
        sa_column_kwargs={"unique": True},
        schema_extra={"example": EXAMPLE_USER["email"]},
    )
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    birthdate: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )  # birthday with timezone
    phone: Optional[str] = Field(schema_extra={"example": EXAMPLE_USER["phone"]})
    state: Optional[str] = Field(schema_extra={"example": EXAMPLE_USER["state"]})
    country: Optional[str] = Field(schema_extra={"example": EXAMPLE_USER["country"]})
    address: Optional[str] = Field(schema_extra={"example": EXAMPLE_USER["address"]})


# The "Create" model variant expands on the update model, above, and adds
# any new fields that may be writeable only the first time a record is
# generated. This allows the POST action to accept update-able fields, as
# well as one-time writeable fields.
class UserCreate(UserUpdate):
    password: str


# The "View" model describes all fields that should typcially be present
# in any JSON responses to the client. This should, at a minimum, include
# the identity field for the model, as well as any server-side fields that
# are important but tamper resistant, such as created_at or updated_at
# fields. This should be used when defining single responses and paged
# responses, as in the schemas below. To support column clipping, all
# fields need to be optional.
class UserView(CruddyUUIDModel):
    id: Optional[UUID]
    first_name: Optional[str] = Field(
        schema_extra={"example": EXAMPLE_USER["first_name"]}
    )
    last_name: Optional[str] = Field(
        schema_extra={"example": EXAMPLE_USER["last_name"]}
    )
    email: Optional[str] = Field(schema_extra={"example": EXAMPLE_USER["email"]})
    is_active: Optional[bool]
    is_superuser: Optional[bool]
    birthdate: Optional[datetime]
    phone: Optional[str] = Field(schema_extra={"example": EXAMPLE_USER["phone"]})
    state: Optional[str] = Field(schema_extra={"example": EXAMPLE_USER["state"]})
    country: Optional[str] = Field(schema_extra={"example": EXAMPLE_USER["country"]})
    address: Optional[str] = Field(schema_extra={"example": EXAMPLE_USER["address"]})
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


# The "Base" model describes the actual table as it should be reflected in
# Postgresql, etc. It is generally unsafe to use this model in actions, or
# in JSON representations, as it may contain hidden fields like passwords
# or other server-internal state or tracking information. Keep your "Base"
# models separated from all other interactive derivations.
class User(CruddyUUIDModel, UserCreate, table=True):  # type: ignore
    password: str = Field(nullable=False, index=True)
    posts: List["Post"] = Relationship(back_populates="user")
    groups: List["Group"] = Relationship(
        back_populates="users", link_model=GroupUserLink
    )
