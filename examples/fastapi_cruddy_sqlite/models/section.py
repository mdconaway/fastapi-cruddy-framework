from typing import TYPE_CHECKING
from fastapi_cruddy_framework import (
    UUID,
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
from examples.fastapi_cruddy_sqlite.models.common.graphql import (
    POST_LIST_TYPE,
    POST_CLASS_LOADER,
)
from examples.fastapi_cruddy_sqlite.utils.schema_example import schema_example

if TYPE_CHECKING:
    from examples.fastapi_cruddy_sqlite.models.post import Post


EXAMPLE_SECTION = {"name": "Opinions"}

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
class SectionUpdate(CruddyModel):
    name: str = Field(schema_extra=schema_example(EXAMPLE_SECTION["name"]))


# The "Create" model variant expands on the update model, above, and adds
# any new fields that may be writeable only the first time a record is
# generated. This allows the POST action to accept update-able fields, as
# well as one-time writeable fields.
class SectionCreate(SectionUpdate):
    uuid: UUID


# The "View" model describes all fields that should typcially be present
# in any JSON responses to the client. This should, at a minimum, include
# the identity field for the model, as well as any server-side fields that
# are important but tamper resistant, such as created_at or updated_at
# fields. This should be used when defining single responses and paged
# responses, as in the schemas below. To support column clipping, all
# fields need to be optional.
class SectionView(CruddyCreatedUpdatedSignature, CruddyUUIDModel):
    name: str | None = Field(
        default=None, schema_extra=schema_example(EXAMPLE_SECTION["name"])
    )


# The "Base" model describes the actual table as it should be reflected in
# Postgresql, etc. It is generally unsafe to use this model in actions, or
# in JSON representations, as it may contain hidden fields like passwords
# or other server-internal state or tracking information. Keep your "Base"
# models separated from all other interactive derivations.
class Section(CruddyCreatedUpdatedMixin(), CruddyUUIDModel, SectionCreate, table=True):
    # is the below needed??
    posts: list["Post"] = Relationship(back_populates="section")


# --------------------------------------------------------------------------------------
# BEGIN GRAPHQL DEFINITIONS ------------------------------------------------------------
# --------------------------------------------------------------------------------------


class SectionQLOverrides(CruddyCreatedUpdatedGQLOverrides, SectionView):
    model_config = ConfigDict(arbitrary_types_allowed=True)  # type: ignore


@strawberry_pydantic_type(model=SectionQLOverrides, name="Section", all_fields=True)
class SectionQL:
    posts = graphql_resolver.generate_resolver(
        type_name="post",
        graphql_type=POST_LIST_TYPE,
        # You must define your prefererd internal API path to find the relation
        # Your route generator will be passed an instance of a section record
        route_generator=lambda x: f"sections/{getattr(x, 'id')}/posts",
        class_loader=POST_CLASS_LOADER,
    )
