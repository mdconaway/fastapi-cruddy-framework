from contextlib import asynccontextmanager

from fastapi import FastAPI

from fastapi_cruddy_demo.router import application as application_router


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
