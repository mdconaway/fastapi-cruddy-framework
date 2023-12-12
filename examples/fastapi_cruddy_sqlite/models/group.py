from typing import TYPE_CHECKING
from sqlmodel import Field, Relationship
from fastapi_cruddy_framework import (
    CruddyModel,
    CruddyUUIDModel,
    CruddyCreatedUpdatedSignature,
    CruddyCreatedUpdatedMixin,
)
from examples.fastapi_cruddy_sqlite.models.common.relationships import GroupUserLink

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
    name: str = Field(schema_extra={"examples": [EXAMPLE_GROUP["name"]]})


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
        default=None, schema_extra={"examples": [EXAMPLE_GROUP["name"]]}
    )


# The "Base" model describes the actual table as it should be reflected in
# Postgresql, etc. It is generally unsafe to use this model in actions, or
# in JSON representations, as it may contain hidden fields like passwords
# or other server-internal state or tracking information. Keep your "Base"
# models separated from all other interactive derivations.
class Group(CruddyCreatedUpdatedMixin(), CruddyUUIDModel, GroupCreate, table=True):  # type: ignore
    # is the below needed??
    users: list["User"] = Relationship(
        back_populates="groups", link_model=GroupUserLink
    )
