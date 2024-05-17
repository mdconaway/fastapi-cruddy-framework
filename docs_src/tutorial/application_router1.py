from fastapi import APIRouter
from fastapi_cruddy_framework import CreateRouterFromResources, CruddyResourceRegistry

import fastapi_cruddy_demo

router: APIRouter = CreateRouterFromResources(application_module=fastapi_cruddy_demo)


# You can now bind additional routes to "router" below, as its a normal APIRouter
@router.get("/health", tags=["application"])
async def is_healthy() -> bool:
    # This function will start returning True when the async sqlalchemy relationsip mapping is complete!
    return CruddyResourceRegistry.is_ready()
