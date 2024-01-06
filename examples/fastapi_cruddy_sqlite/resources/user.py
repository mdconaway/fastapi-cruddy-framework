from fastapi_cruddy_framework import Resource, UUID
from examples.fastapi_cruddy_sqlite.adapters import sqlite
from examples.fastapi_cruddy_sqlite.models.user import (
    User,
    UserCreate,
    UserUpdate,
    UserView,
)
from examples.fastapi_cruddy_sqlite.controllers.user import UserController
from examples.fastapi_cruddy_sqlite.policies.verify_session import verify_session
from examples.fastapi_cruddy_sqlite.policies.naive_auth import naive_auth
from examples.fastapi_cruddy_sqlite.policies.hash_user_password import (
    hash_user_password,
)
from examples.fastapi_cruddy_sqlite.config.general import general


resource = Resource(
    adapter=sqlite,
    id_type=UUID,
    response_schema=UserView,
    resource_update_model=UserUpdate,
    resource_create_model=UserCreate,
    resource_model=User,
    protected_relationships=["posts"],
    policies_universal=[verify_session],
    policies_create=[naive_auth, hash_user_password],
    disable_delete=True,
    controller_extension=UserController,
    artificial_relationship_paths=["others"],
    default_limit=general.DEFAULT_LIMIT,
)
