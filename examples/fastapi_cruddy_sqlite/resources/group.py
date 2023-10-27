from fastapi_cruddy_framework import Resource, UUID
from examples.fastapi_cruddy_sqlite.adapters import sqlite
from examples.fastapi_cruddy_sqlite.models.group import (
    Group,
    GroupCreate,
    GroupUpdate,
    GroupView,
)
from examples.fastapi_cruddy_sqlite.policies.verify_session import verify_session
from examples.fastapi_cruddy_sqlite.config.general import general


resource = Resource(
    adapter=sqlite,
    id_type=UUID,
    response_schema=GroupView,
    resource_update_model=GroupUpdate,
    resource_create_model=GroupCreate,
    resource_model=Group,
    policies_universal=[verify_session],
    default_limit=general.DEFAULT_LIMIT,
)
