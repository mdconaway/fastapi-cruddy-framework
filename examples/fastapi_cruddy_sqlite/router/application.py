import examples.fastapi_cruddy_sqlite
from fastapi import APIRouter
from fastapi_cruddy_framework import CreateRouterFromResources, CruddyResourceRegistry


# Users can override expected default object each resource module exports
# via the named parameter common_resource_name such as:
# common_resource_name="OddResource"
# The finder function expects to find a CRUDDY resource object, complete
# with a controller property, which is a sub-router.
router: APIRouter = CreateRouterFromResources(
    application_module=examples.fastapi_cruddy_sqlite, resource_path="resources"
)


# You can now bind additional routes to "router" below, as its a normal APIRouter
@router.get("/health", tags=["application"])
async def is_healthy() -> bool:
    return CruddyResourceRegistry.is_ready()
