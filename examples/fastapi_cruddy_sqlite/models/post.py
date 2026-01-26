from typing import Any, ForwardRef, TYPE_CHECKING
from datetime import datetime
from fastapi_cruddy_framework import (
    UUID,
    CruddyModel,
    CruddyUUIDModel,
    CruddyCreatedUpdatedSignature,
    CruddyCreatedUpdatedGQLOverrides,
    CruddyCreatedUpdatedMixin,
    validate_utc_datetime,
    CruddyGQLObject,
)
from pydantic import field_validator, ConfigDict
from sqlmodel import Column, ForeignKey, DateTime, Field, JSON, Relationship
from strawberry.experimental.pydantic import type as strawberry_pydantic_type
from examples.fastapi_cruddy_sqlite.services.graphql_resolver import graphql_resolver
from examples.fastapi_cruddy_sqlite.models.common.graphql import (
    COMMENT_CLASS_LOADER,
    COMMENT_LIST_TYPE,
    SECTION_LIST_TYPE,
    SECTION_CLASS_LOADER,
    USER_LIST_TYPE,
    USER_CLASS_LOADER,
    LABEL_LIST_TYPE,
    LABEL_CLASS_LOADER,
)
from examples.fastapi_cruddy_sqlite.utils.schema_example import schema_example

if TYPE_CHECKING:
    from examples.fastapi_cruddy_sqlite.models.user import User
    from examples.fastapi_cruddy_sqlite.models.section import Section
    from examples.fastapi_cruddy_sqlite.models.label import Label


EXAMPLE_POST = {
    "content": "Today I felt like blogging. Fin.",
    "tags": {"categories": ["blog"]},
    "event_date": "2023-12-11T15:27:39.984Z",
    "label_id": "Fan Fiction",
}

# The way the CRUD Router works, it needs an update, create, and base model.
# If you always structure model files in this order, you can extend from the
# minimal number of attrs that can be updated, all the way up to the maximal
# attrs in the base model. CRUD JSON serialization schemas are also exposed
# for modification, and it makes sense to keep your response schemas defined
# in the same location as the view model used to represent records to the
# client.


# The "Update" model variant describes all fields that can be affected by a
# client's PATCH action. Generally, the update model should have the fewest
# number of available fields for a client to manipulate.
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
    section_id: UUID | None = Field(
        sa_column=Column(
            ForeignKey("Section.id", ondelete="SET NULL"),
            index=True,
            default=None,
            nullable=True,
            unique=False,
        ),
        default=None,
    )
    label_id: str | None = Field(
        sa_column=Column(
            ForeignKey("Label.id", ondelete="SET NULL"),
            index=True,
            default=None,
            nullable=True,
            unique=False,
        ),
        default=None,
        schema_extra=schema_example(EXAMPLE_POST["label_id"]),
    )

    @field_validator("event_date", mode="before")
    @classmethod
    def validate_event_date(cls, v: Any) -> datetime | None:
        return validate_utc_datetime(v, allow_none=True)


# The "Create" model variant expands on the update model, above, and adds
# any new fields that may be writeable only the first time a record is
# generated. This allows the POST action to accept update-able fields, as
# well as one-time writeable fields.
class PostCreate(PostUpdate):
    user_id: UUID | None = Field(
        sa_column=Column(
            ForeignKey("User.id", ondelete="SET NULL"),
            index=True,
            default=None,
            nullable=True,
            unique=False,
        ),
    )


# The "View" model describes all fields that should typcially be present
# in any JSON responses to the client. This should, at a minimum, include
# the identity field for the model, as well as any server-side fields that
# are important but tamper resistant, such as created_at or updated_at
# fields. This should be used when defining single responses and paged
# responses, as in the schemas below. To support column clipping, all
# fields need to be optional.
class PostView(CruddyCreatedUpdatedSignature, CruddyUUIDModel):
    user_id: UUID | None = None
    section_id: UUID | None = None
    label_id: str | None = Field(
        default=None, schema_extra=schema_example(EXAMPLE_POST["label_id"])
    )
    content: str | None = Field(
        default=None, schema_extra=schema_example(EXAMPLE_POST["content"])
    )
    tags: dict[str, Any] | None = Field(
        sa_column=Column(JSON, index=True),
        default=None,
        schema_extra=schema_example(EXAMPLE_POST["tags"]),
    )
    event_date: datetime | None = None


# The "Base" model describes the actual table as it should be reflected in
# Postgresql, etc. It is generally unsafe to use this model in actions, or
# in JSON representations, as it may contain hidden fields like passwords
# or other server-internal state or tracking information. Keep your "Base"
# models separated from all other interactive derivations.
class Post(CruddyCreatedUpdatedMixin(), CruddyUUIDModel, PostCreate, table=True):
    user: "User" = Relationship(back_populates="posts")
    section: "Section" = Relationship(back_populates="posts")
    label: "Label" = Relationship(back_populates="posts")
    comments: list[ForwardRef("Comment")] = Relationship(  # type: ignore
        sa_relationship_kwargs={
            "primaryjoin": "Comment.entity_id==Post.id",
            "foreign_keys": "[Comment.entity_id]",
            "cascade": "all, delete",
            "viewonly": True,
        },
    )


# --------------------------------------------------------------------------------------
# BEGIN GRAPHQL DEFINITIONS ------------------------------------------------------------
# --------------------------------------------------------------------------------------


class PostQLOverrides(CruddyCreatedUpdatedGQLOverrides, PostView):
    model_config = ConfigDict(arbitrary_types_allowed=True)  # type: ignore
    event_date: str | None = None
    tags: CruddyGQLObject | None = None  # type: ignore


@strawberry_pydantic_type(model=PostQLOverrides, name="Post", all_fields=True)
class PostQL:
    user = graphql_resolver.generate_resolver(
        type_name="user",
        graphql_type=USER_LIST_TYPE,
        # You must define your prefererd internal API path to find the relation
        # Your route generator will be passed an instance of a post record
        route_generator=lambda x: f"users/{getattr(x, 'user_id')}",
        class_loader=USER_CLASS_LOADER,
        is_singular=True,
    )
    section = graphql_resolver.generate_resolver(
        type_name="section",
        graphql_type=SECTION_LIST_TYPE,
        # You must define your prefererd internal API path to find the relation
        # Your route generator will be passed an instance of a post record
        route_generator=lambda x: f"sections/{getattr(x, 'section_id')}",
        class_loader=SECTION_CLASS_LOADER,
        is_singular=True,
    )
    label = graphql_resolver.generate_resolver(
        type_name="label",
        graphql_type=LABEL_LIST_TYPE,
        # You must define your prefererd internal API path to find the relation
        # Your route generator will be passed an instance of a post record
        route_generator=lambda x: f"labels/{getattr(x, 'label_id')}",
        class_loader=LABEL_CLASS_LOADER,
        is_singular=True,
    )
    comments = graphql_resolver.generate_resolver(
        type_name="comment",
        graphql_type=COMMENT_LIST_TYPE,
        # You must define your prefererd internal API path to find the relation
        # Your route generator will be passed an instance of a group record
        route_generator=lambda x: f"posts/{getattr(x, 'id')}/comments",
        class_loader=COMMENT_CLASS_LOADER,
    )
