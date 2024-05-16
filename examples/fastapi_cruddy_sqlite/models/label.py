from typing import TYPE_CHECKING
from fastapi import status
from fastapi_cruddy_framework import (
    CruddyStringIDModel,
    CruddyCreatedUpdatedSignature,
    CruddyCreatedUpdatedGQLOverrides,
    CruddyCreatedUpdatedMixin,
)
from pydantic import ConfigDict
from sqlmodel import Field, Relationship
from strawberry.experimental.pydantic import type as strawberry_pydantic_type
from examples.fastapi_cruddy_sqlite.services.graphql_resolver import graphql_resolver
from examples.fastapi_cruddy_sqlite.models.common.graphql import (
    POST_LIST_TYPE,
    POST_CLASS_LOADER,
)
from examples.fastapi_cruddy_sqlite.utils.schema_example import schema_example

if TYPE_CHECKING:
    from examples.fastapi_cruddy_sqlite.models.post import Post

HTTP_422_UNPROCESSABLE_ENTITY = status.HTTP_422_UNPROCESSABLE_ENTITY
EXAMPLE_LABEL = {"id": "Fan Fiction"}

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
class LabelUpdate(CruddyStringIDModel):
    id: str = Field(
        default=None,
        primary_key=True,
        index=True,
        nullable=False,
        schema_extra=schema_example(EXAMPLE_LABEL["id"]),
    )


# The "Create" model variant expands on the update model, above, and adds
# any new fields that may be writeable only the first time a record is
# generated. This allows the POST action to accept update-able fields, as
# well as one-time writeable fields.
class LabelCreate(LabelUpdate):
    pass


# The "View" model describes all fields that should typcially be present
# in any JSON responses to the client. This should, at a minimum, include
# the identity field for the model, as well as any server-side fields that
# are important but tamper resistant, such as created_at or updated_at
# fields. This should be used when defining single responses and paged
# responses, as in the schemas below. To support column clipping, all
# fields need to be optional.
class LabelView(CruddyCreatedUpdatedSignature):
    id: str | None = Field(
        default=None, schema_extra=schema_example(EXAMPLE_LABEL["id"])
    )


# The "Base" model describes the actual table as it should be reflected in
# Postgresql, etc. It is generally unsafe to use this model in actions, or
# in JSON representations, as it may contain hidden fields like passwords
# or other server-internal state or tracking information. Keep your "Base"
# models separated from all other interactive derivations.
class Label(CruddyCreatedUpdatedMixin(), LabelCreate, table=True):
    # is the below needed??
    posts: list["Post"] = Relationship(back_populates="label")


# --------------------------------------------------------------------------------------
# BEGIN GRAPHQL DEFINITIONS ------------------------------------------------------------
# --------------------------------------------------------------------------------------


class LabelQLOverrides(CruddyCreatedUpdatedGQLOverrides, LabelView):
    model_config = ConfigDict(arbitrary_types_allowed=True)  # type: ignore


@strawberry_pydantic_type(model=LabelQLOverrides, name="Label", all_fields=True)
class LabelQL:
    posts = graphql_resolver.generate_resolver(
        type_name="post",
        graphql_type=POST_LIST_TYPE,
        # You must define your prefererd internal API path to find the relation
        # Your route generator will be passed an instance of a group record
        route_generator=lambda x: f"labels/{getattr(x, 'id')}/posts",
        class_loader=POST_CLASS_LOADER,
    )
