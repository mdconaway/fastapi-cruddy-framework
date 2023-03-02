from fastapi_cruddy_framework import Resource, UUID
from examples.fastapi_cruddy_sqlite.adapters import sqlite
from examples.fastapi_cruddy_sqlite.models.post import (
    Post,
    PostCreate,
    PostUpdate,
    PostView,
)
from examples.fastapi_cruddy_sqlite.schemas.response import MetaObject
from examples.fastapi_cruddy_sqlite.policies.verify_session import verify_session


resource = Resource(
    adapter=sqlite,
    response_schema=PostView,
    response_meta_schema=MetaObject,
    resource_update_model=PostUpdate,
    resource_create_model=PostCreate,
    resource_model=Post,
    id_type=UUID,
    policies_universal=[verify_session],
)
