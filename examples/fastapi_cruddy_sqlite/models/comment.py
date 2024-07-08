# This software is provided to the United States Government (USG) with SBIR Data Rights as defined at Federal Acquisition Regulation 52.227-14, "Rights in Data-SBIR Program" (May 2014) SBIR Rights Notice (Dec 2023-2024) These SBIR data are furnished with SBIR rights under Contract No. H9241522D0001. For a period of 19 years, unless extended in accordance with FAR 27.409(h), after acceptance of all items to be delivered under this contract, the Government will use these data for Government purposes only, and they shall not be disclosed outside the Government (including disclosure for procurement purposes) during such period without permission of the Contractor, except that, subject to the foregoing use and disclosure prohibitions, these data may be disclosed for use by support Contractors. After the protection period, the Government has a paid-up license to use, and to authorize others to use on its behalf, these data for Government purposes, but is relieved of all disclosure prohibitions and assumes no liability for unauthorized use of these data by third parties. This notice shall be affixed to any reproductions of these data, in whole or in part.
from typing import TYPE_CHECKING

from fastapi_cruddy_framework import (
    CruddyCreatedUpdatedMixin,
    CruddyCreatedUpdatedSignature,
    CruddyCreatedUpdatedGQLOverrides,
    CruddyModel,
    CruddyUUIDModel,
    UUID,
)

from sqlmodel import Column, Field, ForeignKey, Relationship
from strawberry.experimental.pydantic import type as strawberry_pydantic_type

from examples.fastapi_cruddy_sqlite.utils.schema_example import schema_example

if TYPE_CHECKING:
    from examples.fastapi_cruddy_sqlite.models.user import User

EXAMPLE_COMMENT = {"text": "What a great post"}


class CommentCreate(CruddyModel):
    created_by_id: UUID
    entity_id: UUID
    text: str = Field(schema_extra=schema_example(EXAMPLE_COMMENT["text"]))


class CommentView(CruddyCreatedUpdatedSignature, CruddyUUIDModel):
    created_by_id: UUID | None = None
    entity_id: UUID | None = None
    text: str | None = None


class Comment(CruddyCreatedUpdatedMixin(), CruddyUUIDModel, CommentCreate, table=True):
    created_by_id: UUID = Field(
        sa_column=Column(
            ForeignKey("User.id", ondelete="CASCADE"),
            index=True,
            default=None,
            nullable=False,
            unique=False,
        )
    )

    created_by: "User" = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": f"User.id==foreign(Comment.created_by_id)",
        }
    )


# --------------------------------------------------------------------------------------
# BEGIN GRAPHQL DEFINITIONS ------------------------------------------------------------
# --------------------------------------------------------------------------------------


class CommentQLOverrides(CruddyCreatedUpdatedGQLOverrides, CommentView):
    pass


@strawberry_pydantic_type(model=CommentQLOverrides, name="comment", all_fields=True)
class CommentQL:
    pass
