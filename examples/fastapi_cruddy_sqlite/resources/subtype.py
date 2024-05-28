from sqlalchemy import and_
from fastapi import HTTPException, status
from fastapi_cruddy_framework import Resource
from examples.fastapi_cruddy_sqlite.adapters import sqlite
from examples.fastapi_cruddy_sqlite.models.subtype import (
    SubType,
    SubTypeCreate,
    SubTypeUpdate,
    SubTypeView,
)
from examples.fastapi_cruddy_sqlite.policies.verify_session import verify_session
from examples.fastapi_cruddy_sqlite.config.general import general

HTTP_400_BAD_REQUEST = status.HTTP_400_BAD_REQUEST
primary_key = getattr(SubType, "id")
type_key = getattr(SubType, "type_id")


def db_identity(id: str):
    parts = id.split(".")
    if len(parts) != 2:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"'id' must be of format <type>.<subtype> | Example: 'type.subtype'",
        )
    type_id = parts[0]
    subtype_id = parts[1]
    return and_(type_key == type_id, primary_key == subtype_id)


resource = Resource(
    adapter=sqlite,
    id_type=str,
    response_schema=SubTypeView,
    resource_update_model=SubTypeUpdate,
    resource_create_model=SubTypeCreate,
    resource_model=SubType,
    policies_universal=[verify_session],
    custom_link_identity=lambda record: f"{record['type_id']}.{record['id']}",
    custom_sql_identity_function=db_identity,
    protected_relationships=["type", "references"],
    default_limit=general.DEFAULT_LIMIT,
)
