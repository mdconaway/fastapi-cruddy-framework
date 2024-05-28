from sqlmodel import Field, Column, ForeignKey
from fastapi_cruddy_framework import UUID, CruddyModel


# Many to many relationships require a manually defined "link" model.
# This model will house the table that stores many<->many relation rows.
class GroupUserLink(CruddyModel, table=True):
    user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("User.id", ondelete="CASCADE"),
            default=None,
            primary_key=True,
            nullable=False,
        ),
    )
    group_id: UUID = Field(
        sa_column=Column(
            ForeignKey("Group.id", ondelete="CASCADE"),
            default=None,
            primary_key=True,
            nullable=False,
        ),
    )
