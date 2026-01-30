from fastapi_cruddy_framework import Resource, UUID
from examples.fastapi_cruddy_sqlite.adapters import sqlite
from examples.fastapi_cruddy_sqlite.models.label import (
    Label,
    LabelCreate,
    LabelUpdate,
    LabelView,
)
from examples.fastapi_cruddy_sqlite.policies.verify_session import verify_session
from examples.fastapi_cruddy_sqlite.config.general import general

resource = Resource(
    adapter=sqlite,
    id_type=str,
    response_schema=LabelView,
    resource_update_model=LabelUpdate,
    resource_create_model=LabelCreate,
    resource_model=Label,
    policies_universal=[verify_session],
    default_limit=general.DEFAULT_LIMIT,
    protected_relationships=["posts"],
)
