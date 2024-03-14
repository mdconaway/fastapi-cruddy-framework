from fastapi_cruddy_framework import Resource, UUID
from examples.fastapi_cruddy_sqlite.adapters import sqlite
from examples.fastapi_cruddy_sqlite.models.section import (
    Section,
    SectionCreate,
    SectionUpdate,
    SectionView,
)
from examples.fastapi_cruddy_sqlite.policies.verify_session import verify_session
from examples.fastapi_cruddy_sqlite.config.general import general


resource = Resource(
    adapter=sqlite,
    id_type=UUID,
    response_schema=SectionView,
    resource_update_model=SectionUpdate,
    resource_create_model=SectionCreate,
    resource_model=Section,
    policies_universal=[verify_session],
    default_limit=general.DEFAULT_LIMIT,
)
