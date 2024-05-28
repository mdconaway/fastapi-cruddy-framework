from fastapi_cruddy_framework import Resource
from examples.fastapi_cruddy_sqlite.adapters import sqlite
from examples.fastapi_cruddy_sqlite.models.type import (
    Type,
    TypeCreate,
    TypeUpdate,
    TypeView,
)
from examples.fastapi_cruddy_sqlite.policies.verify_session import verify_session
from examples.fastapi_cruddy_sqlite.config.general import general


resource = Resource(
    adapter=sqlite,
    id_type=str,
    response_schema=TypeView,
    resource_update_model=TypeUpdate,
    resource_create_model=TypeCreate,
    resource_model=Type,
    policies_universal=[verify_session],
    protected_relationships=["subtypes"],
    default_limit=general.DEFAULT_LIMIT,
)
