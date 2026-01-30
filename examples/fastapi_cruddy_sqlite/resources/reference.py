from fastapi_cruddy_framework import Resource, UUID
from examples.fastapi_cruddy_sqlite.adapters import sqlite
from examples.fastapi_cruddy_sqlite.models.reference import (
    Reference,
    ReferenceCreate,
    ReferenceUpdate,
    ReferenceView,
)
from examples.fastapi_cruddy_sqlite.policies.verify_session import verify_session
from examples.fastapi_cruddy_sqlite.config.general import general

resource = Resource(
    adapter=sqlite,
    id_type=UUID,
    response_schema=ReferenceView,
    resource_update_model=ReferenceUpdate,
    resource_create_model=ReferenceCreate,
    resource_model=Reference,
    policies_universal=[verify_session],
    protected_relationships=["subtype", "type"],
    disable_relationship_getters=["type"],
    default_limit=general.DEFAULT_LIMIT,
)
