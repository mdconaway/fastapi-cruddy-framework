from fastapi_cruddy_framework import Resource, UUID
from examples.fastapi_cruddy_sqlite.adapters import sqlite
from examples.fastapi_cruddy_sqlite.models.post import (
    Post,
    PostCreate,
    PostUpdate,
    PostView,
)
from examples.fastapi_cruddy_sqlite.policies.verify_session import verify_session
from examples.fastapi_cruddy_sqlite.config.general import general


resource = Resource(
    adapter=sqlite,
    id_type=UUID,
    response_schema=PostView,
    resource_update_model=PostUpdate,
    resource_create_model=PostCreate,
    resource_model=Post,
    policies_universal=[verify_session],
    protected_relationships=["user"],
    default_limit=general.DEFAULT_LIMIT,
)
