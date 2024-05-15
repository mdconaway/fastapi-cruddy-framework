from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi_cruddy_framework import CreateRouterFromResources

import fastapi_cruddy_demo

application_router: APIRouter = CreateRouterFromResources(
    application_module=fastapi_cruddy_demo
)


# You can now bind additional routes to "router" below, as its a normal APIRouter
@application_router.get("/")
async def root():
    return {"message": "Hello World"}


async def bootstrap(application: FastAPI):
    application.include_router(application_router)
    # You can do any init hooks below


async def shutdown():
    pass


@asynccontextmanager
async def lifespan(application: FastAPI):
    await bootstrap(application)
    yield
    await shutdown()


app = FastAPI(title="Smallest App Ever", version="0.0.1", lifespan=lifespan)
