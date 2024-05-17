from fastapi_cruddy_framework import Resource, UUID
from fastapi_cruddy_demo.adapters import sqlite
from fastapi_cruddy_demo.models.post import (
    Post,
    PostCreate,
    PostUpdate,
    PostView,
)


resource = Resource(
    adapter=sqlite,
    id_type=UUID,
    response_schema=PostView,
    resource_update_model=PostUpdate,
    resource_create_model=PostCreate,
    resource_model=Post,
    default_limit=10,
)
