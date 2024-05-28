# This software is provided to the United States Government (USG) with SBIR Data Rights as defined at Federal Acquisition Regulation 52.227-14, "Rights in Data-SBIR Program" (May 2014) SBIR Rights Notice (Dec 2023-2024) These SBIR data are furnished with SBIR rights under Contract No. H9241522D0001. For a period of 19 years, unless extended in accordance with FAR 27.409(h), after acceptance of all items to be delivered under this contract, the Government will use these data for Government purposes only, and they shall not be disclosed outside the Government (including disclosure for procurement purposes) during such period without permission of the Contractor, except that, subject to the foregoing use and disclosure prohibitions, these data may be disclosed for use by support Contractors. After the protection period, the Government has a paid-up license to use, and to authorize others to use on its behalf, these data for Government purposes, but is relieved of all disclosure prohibitions and assumes no liability for unauthorized use of these data by third parties. This notice shall be affixed to any reproductions of these data, in whole or in part.
# pylint: disable=duplicate-code
from typing import ForwardRef
from pydantic import ConfigDict
from sqlmodel import ForeignKeyConstraint, Field, Relationship
from strawberry.experimental.pydantic import type as strawberry_pydantic_type
from fastapi_cruddy_framework import (
    UUID,
    CruddyModel,
    CruddyUUIDModel,
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

EXAMPLE_REFERENCE = {
    "type_id": "type",
    "subtype_id": "subtype",
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
class ReferenceUpdate(CruddyModel):
    type_id: str = Field(
        default=None,
        index=True,
        nullable=False,
        unique=False,
        schema_extra=schema_example(EXAMPLE_REFERENCE["type_id"]),
    )
    subtype_id: str = Field(
        default=None,
        index=True,
        nullable=False,
        unique=False,
        schema_extra=schema_example(EXAMPLE_REFERENCE["subtype_id"]),
    )


# The "Create" model variant expands on the update model, above, and adds
# any new fields that may be writeable only the first time a record is
# generated. This allows the POST action to accept update-able fields, as
# well as one-time writeable fields.
class ReferenceCreate(ReferenceUpdate):
    pass


# The "View" model describes all fields that should typcially be present
# in any JSON responses to the client. This should, at a minimum, include
# the identity field for the model, as well as any server-side fields that
# are important but tamper resistant, such as created_at or updated_at
# fields. This should be used when defining single responses and paged
# responses, as in the schemas below. To support column clipping, all
# fields need to be optional.
class ReferenceView(CruddyCreatedUpdatedSignature):
    id: UUID
    type_id: str | None = Field(
        default=None, schema_extra=schema_example(EXAMPLE_REFERENCE["type_id"])
    )
    subtype_id: str | None = Field(
        default=None, schema_extra=schema_example(EXAMPLE_REFERENCE["subtype_id"])
    )


# The "Base" model describes the actual table as it should be reflected in
# Postgresql, etc. It is generally unsafe to use this model in actions, or
# in JSON representations, as it may contain hidden fields like passwords
# or other server-internal state or tracking information. Keep your "Base"
# models separated from all other interactive derivations.
class Reference(CruddyCreatedUpdatedMixin(), CruddyUUIDModel, ReferenceCreate, table=True):  # type: ignore
    subtype: ForwardRef("SubType") = Relationship(  # type: ignore
        back_populates="references",
    )
    # NOTE: The below 'type' relationship syntax that forces a relationship into foreign() WILL NOT WORK. It is only
    # done here to hoist a bad relationship definition to test getter pruning with 'disable_relationship_getters' at
    # the resource level.
    type: ForwardRef("Type") = Relationship(  # type: ignore
        back_populates="references",
        sa_relationship_kwargs={
            "primaryjoin": "Type.id==foreign(Reference.type_id)",
        },
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["type_id", "subtype_id"],
            ["SubType.type_id", "SubType.id"],
            ondelete="CASCADE",
        ),
    )


# --------------------------------------------------------------------------------------
# BEGIN GRAPHQL MADNESS ----------------------------------------------------------------
# --------------------------------------------------------------------------------------


class ReferenceQLOverrides(CruddyCreatedUpdatedGQLOverrides, ReferenceView):
    model_config = ConfigDict(arbitrary_types_allowed=True)  # type: ignore


@strawberry_pydantic_type(model=ReferenceQLOverrides, name="Reference", all_fields=True)
class ReferenceQL:
    subtype = graphql_resolver.generate_resolver(
        type_name="subtype",
        is_singular=True,
        graphql_type=SUBTYPE_LIST_TYPE,
        route_generator=lambda x: f"references/{getattr(x, 'id')}/subtype",
        class_loader=SUBTYPE_CLASS_LOADER,
    )
