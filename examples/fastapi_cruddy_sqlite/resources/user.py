from fastapi_cruddy_framework import Resource, UUID
from examples.fastapi_cruddy_sqlite.adapters import sqlite
from examples.fastapi_cruddy_sqlite.models.user import (
    User,
    UserCreate,
    UserUpdate,
    UserView,
)
from examples.fastapi_cruddy_sqlite.schemas.response import MetaObject
from examples.fastapi_cruddy_sqlite.policies.verify_session import verify_session
from examples.fastapi_cruddy_sqlite.policies.hash_user_password import (
    hash_user_password,
)


resource = Resource(
    adapter=sqlite,
    response_schema=UserView,
    response_meta_schema=MetaObject,
    resource_update_model=UserUpdate,
    resource_create_model=UserCreate,
    resource_model=User,
    protected_relationships=["posts"],
    id_type=UUID,
    policies_universal=[verify_session],
    policies_create=[hash_user_password],
)
