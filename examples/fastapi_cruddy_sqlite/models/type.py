# pylint: disable=duplicate-code
from typing import ForwardRef
from pydantic import ConfigDict
from sqlmodel import Field, Relationship
from strawberry.experimental.pydantic import type as strawberry_pydantic_type
from fastapi_cruddy_framework import (
    CruddyStringIDModel,
    CruddyCreatedUpdatedSignature,
    CruddyCreatedUpdatedGQLOverrides,
    CruddyCreatedUpdatedMixin,
)
from examples.fastapi_cruddy_sqlite.models.common.graphql import (
    SUBTYPE_LIST_TYPE,
    SUBTYPE_CLASS_LOADER,
)
from examples.fastapi_cruddy_sqlite.utils.schema_example import schema_example
from examples.fastapi_cruddy_sqlite.services.graphql_resolver import graphql_resolver

EXAMPLE_TYPE = {
    "id": "type",
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
class TypeUpdate(CruddyStringIDModel):
    id: str = Field(
        default=None,
        primary_key=True,
        unique=True,
        index=True,
        nullable=False,
        schema_extra=schema_example(EXAMPLE_TYPE["id"]),
    )


# The "Create" model variant expands on the update model, above, and adds
# any new fields that may be writeable only the first time a record is
# generated. This allows the POST action to accept update-able fields, as
# well as one-time writeable fields.
class TypeCreate(TypeUpdate):
    pass


# The "View" model describes all fields that should typcially be present
# in any JSON responses to the client. This should, at a minimum, include
# the identity field for the model, as well as any server-side fields that
# are important but tamper resistant, such as created_at or updated_at
# fields. This should be used when defining single responses and paged
# responses, as in the schemas below. To support column clipping, all
# fields need to be optional.
class TypeView(CruddyCreatedUpdatedSignature):
    id: str = Field(schema_extra=schema_example(EXAMPLE_TYPE["id"]))


# The "Base" model describes the actual table as it should be reflected in
# Postgresql, etc. It is generally unsafe to use this model in actions, or
# in JSON representations, as it may contain hidden fields like passwords
# or other server-internal state or tracking information. Keep your "Base"
# models separated from all other interactive derivations.
class Type(CruddyCreatedUpdatedMixin(), TypeCreate, table=True):  # type: ignore
    subtypes: list[ForwardRef("SubType")] = Relationship(  # type: ignore
        back_populates="type",
    )
    # NOTE: The below 'references' relationship syntax that forces a relationship into foreign() WILL NOT WORK. It is only
    # done here to hoist a bad relationship definition to test getter pruning with 'disable_relationship_getters' at
    # the resource level.
    references: list[ForwardRef("Reference")] = Relationship(  # type: ignore
        back_populates="type",
        sa_relationship_kwargs={
            "primaryjoin": "Type.id==foreign(Reference.type_id)",
        },
    )


# --------------------------------------------------------------------------------------
# BEGIN GRAPHQL MADNESS ----------------------------------------------------------------
# --------------------------------------------------------------------------------------


class TypeQLOverrides(CruddyCreatedUpdatedGQLOverrides, TypeView):
    model_config = ConfigDict(arbitrary_types_allowed=True)  # type: ignore


@strawberry_pydantic_type(model=TypeQLOverrides, name="Type", all_fields=True)
class TypeQL:
    subtypes = graphql_resolver.generate_resolver(
        type_name="subtype",
        graphql_type=SUBTYPE_LIST_TYPE,
        route_generator=lambda x: f"types/{getattr(x, 'id')}/subtypes",
        class_loader=SUBTYPE_CLASS_LOADER,
    )
