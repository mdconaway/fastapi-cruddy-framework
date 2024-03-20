from typing import Any, TYPE_CHECKING
from datetime import datetime
from fastapi_cruddy_framework import (
    CruddyModel,
    CruddyUUIDModel,
    CruddyCreatedUpdatedSignature,
    CruddyCreatedUpdatedQLOverrides,
    CruddyCreatedUpdatedMixin,
    validate_utc_datetime,
)
from pydantic import field_validator, ConfigDict
from strawberry.experimental.pydantic import type as strawberry_pydantic_type
from sqlmodel import Field, Relationship, Column, DateTime
from examples.fastapi_cruddy_sqlite.services.graphql_resolver import graphql_resolver
from examples.fastapi_cruddy_sqlite.models.common.relationships import GroupUserLink
from examples.fastapi_cruddy_sqlite.models.common.graphql import (
    GROUP_LIST_TYPE,
    GROUP_CLASS_LOADER,
    POST_LIST_TYPE,
    POST_CLASS_LOADER,
)

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
    "password": "at-least-6-characters",
    "birthdate": "2012-12-11T15:27:39.984Z",
}


# The "Update" model variant describes all fields that can be affected by a
# client's PATCH action. Generally, the update model should have the fewest
# number of available fields for a client to manipulate.
class UserUpdate(CruddyModel):
    first_name: str = Field(schema_extra={"examples": [EXAMPLE_USER["first_name"]]})
    last_name: str = Field(schema_extra={"examples": [EXAMPLE_USER["last_name"]]})
    email: str = Field(
        nullable=True,
        index=True,
        sa_column_kwargs={"unique": True},
        schema_extra={"examples": [EXAMPLE_USER["email"]]},
    )
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    birthdate: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=True,
            index=True,
            default=None,
        ),
        schema_extra={"examples": [EXAMPLE_USER["birthdate"]]},
    )  # birthday with timezone
    phone: str | None = Field(schema_extra={"examples": [EXAMPLE_USER["phone"]]})
    state: str | None = Field(schema_extra={"examples": [EXAMPLE_USER["state"]]})
    country: str | None = Field(schema_extra={"examples": [EXAMPLE_USER["country"]]})
    address: str | None = Field(schema_extra={"examples": [EXAMPLE_USER["address"]]})

    @field_validator("birthdate", mode="before")
    @classmethod
    def validate_birthdate(cls, v: Any) -> datetime | None:
        return validate_utc_datetime(v, allow_none=True)


# The "Create" model variant expands on the update model, above, and adds
# any new fields that may be writeable only the first time a record is
# generated. This allows the POST action to accept update-able fields, as
# well as one-time writeable fields.
class UserCreate(UserUpdate):
    password: str = Field(schema_extra={"examples": [EXAMPLE_USER["password"]]})


# The "View" model describes all fields that should typcially be present
# in any JSON responses to the client. This should, at a minimum, include
# the identity field for the model, as well as any server-side fields that
# are important but tamper resistant, such as created_at or updated_at
# fields. This should be used when defining single responses and paged
# responses, as in the schemas below. To support column clipping, all
# fields need to be optional.
class UserView(CruddyCreatedUpdatedSignature, CruddyUUIDModel):
    first_name: str | None = Field(
        default=None, schema_extra={"examples": [EXAMPLE_USER["first_name"]]}
    )
    last_name: str | None = Field(
        default=None, schema_extra={"examples": [EXAMPLE_USER["last_name"]]}
    )
    email: str | None = Field(
        default=None, schema_extra={"examples": [EXAMPLE_USER["email"]]}
    )
    is_active: bool | None = None
    is_superuser: bool | None = None
    birthdate: datetime | None = None
    phone: str | None = Field(
        default=None, schema_extra={"examples": [EXAMPLE_USER["phone"]]}
    )
    state: str | None = Field(
        default=None, schema_extra={"examples": [EXAMPLE_USER["state"]]}
    )
    country: str | None = Field(
        default=None, schema_extra={"examples": [EXAMPLE_USER["country"]]}
    )
    address: str | None = Field(
        default=None, schema_extra={"examples": [EXAMPLE_USER["address"]]}
    )


# The "Base" model describes the actual table as it should be reflected in
# Postgresql, etc. It is generally unsafe to use this model in actions, or
# in JSON representations, as it may contain hidden fields like passwords
# or other server-internal state or tracking information. Keep your "Base"
# models separated from all other interactive derivations.
class User(CruddyCreatedUpdatedMixin(), CruddyUUIDModel, UserCreate, table=True):
    password: str = Field(nullable=False, index=True)
    posts: list["Post"] = Relationship(back_populates="user")
    groups: list["Group"] = Relationship(
        back_populates="users", link_model=GroupUserLink
    )


# --------------------------------------------------------------------------------------
# BEGIN GRAPHQL DEFINITIONS ------------------------------------------------------------
# --------------------------------------------------------------------------------------


class UserQLOverrides(CruddyCreatedUpdatedQLOverrides, UserView):
    model_config = ConfigDict(arbitrary_types_allowed=True)  # type: ignore
    birthdate: str | None = None


@strawberry_pydantic_type(model=UserQLOverrides, name="User", all_fields=True)
class UserQL:
    posts = graphql_resolver.generate_resolver(
        type_name="post",
        graphql_type=POST_LIST_TYPE,
        # You must define your prefererd internal API path to find the relation
        # Your route generator will be passed an instance of a user record
        route_generator=lambda x: f"users/{getattr(x, 'id')}/posts",
        class_loader=POST_CLASS_LOADER,
    )
    groups = graphql_resolver.generate_resolver(
        type_name="group",
        graphql_type=GROUP_LIST_TYPE,
        # You must define your prefererd internal API path to find the relation
        # Your route generator will be passed an instance of a user record
        route_generator=lambda x: f"users/{getattr(x, 'id')}/groups",
        class_loader=GROUP_CLASS_LOADER,
    )
