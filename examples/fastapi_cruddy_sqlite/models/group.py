from typing import TYPE_CHECKING, ForwardRef
from fastapi_cruddy_framework import (
    CruddyModel,
    CruddyUUIDModel,
    CruddyCreatedUpdatedSignature,
    CruddyCreatedUpdatedGQLOverrides,
    CruddyCreatedUpdatedMixin,
)
from pydantic import ConfigDict
from sqlmodel import Field, Relationship
from strawberry.experimental.pydantic import type as strawberry_pydantic_type
from examples.fastapi_cruddy_sqlite.services.graphql_resolver import graphql_resolver
from examples.fastapi_cruddy_sqlite.models.common.relationships import GroupUserLink
from examples.fastapi_cruddy_sqlite.models.common.graphql import (
    COMMENT_CLASS_LOADER,
    COMMENT_LIST_TYPE,
    USER_LIST_TYPE,
    USER_CLASS_LOADER,
)
from examples.fastapi_cruddy_sqlite.utils.schema_example import schema_example

if TYPE_CHECKING:
    from examples.fastapi_cruddy_sqlite.models.user import User


EXAMPLE_GROUP = {"name": "Cruddy Fans"}

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
class GroupUpdate(CruddyModel):
    name: str = Field(schema_extra=schema_example(EXAMPLE_GROUP["name"]))


# The "Create" model variant expands on the update model, above, and adds
# any new fields that may be writeable only the first time a record is
# generated. This allows the POST action to accept update-able fields, as
# well as one-time writeable fields.
class GroupCreate(GroupUpdate):
    pass


# The "View" model describes all fields that should typcially be present
# in any JSON responses to the client. This should, at a minimum, include
# the identity field for the model, as well as any server-side fields that
# are important but tamper resistant, such as created_at or updated_at
# fields. This should be used when defining single responses and paged
# responses, as in the schemas below. To support column clipping, all
# fields need to be optional.
class GroupView(CruddyCreatedUpdatedSignature, CruddyUUIDModel):
    name: str | None = Field(
        default=None, schema_extra=schema_example(EXAMPLE_GROUP["name"])
    )


# The "Base" model describes the actual table as it should be reflected in
# Postgresql, etc. It is generally unsafe to use this model in actions, or
# in JSON representations, as it may contain hidden fields like passwords
# or other server-internal state or tracking information. Keep your "Base"
# models separated from all other interactive derivations.
class Group(CruddyCreatedUpdatedMixin(), CruddyUUIDModel, GroupCreate, table=True):
    comments: list[ForwardRef("Comment")] = Relationship(  # type: ignore
        sa_relationship_kwargs={
            "primaryjoin": "Comment.entity_id==Group.id",
            "foreign_keys": "[Comment.entity_id]",
            "cascade": "all, delete",
            "viewonly": True,
        },
    )
    # is the below needed??
    users: list["User"] = Relationship(
        back_populates="groups", link_model=GroupUserLink
    )


# --------------------------------------------------------------------------------------
# BEGIN GRAPHQL DEFINITIONS ------------------------------------------------------------
# --------------------------------------------------------------------------------------


class GroupQLOverrides(CruddyCreatedUpdatedGQLOverrides, GroupView):
    model_config = ConfigDict(arbitrary_types_allowed=True)  # type: ignore


@strawberry_pydantic_type(model=GroupQLOverrides, name="Group", all_fields=True)
class GroupQL:
    comments = graphql_resolver.generate_resolver(
        type_name="comment",
        graphql_type=COMMENT_LIST_TYPE,
        # You must define your prefererd internal API path to find the relation
        # Your route generator will be passed an instance of a group record
        route_generator=lambda x: f"groups/{getattr(x, 'id')}/comments",
        class_loader=COMMENT_CLASS_LOADER,
    )

    users = graphql_resolver.generate_resolver(
        type_name="user",
        graphql_type=USER_LIST_TYPE,
        # You must define your prefererd internal API path to find the relation
        # Your route generator will be passed an instance of a group record
        route_generator=lambda x: f"groups/{getattr(x, 'id')}/users",
        class_loader=USER_CLASS_LOADER,
    )
