import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi_cruddy_framework import CruddyNoMatchingRowException
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from examples.fastapi_cruddy_sqlite.config import general, http, sessions
from examples.fastapi_cruddy_sqlite.router import application as application_router
from examples.fastapi_cruddy_sqlite.middleware import RequestLogger
from examples.fastapi_cruddy_sqlite.adapters import sqlite
from examples.fastapi_cruddy_sqlite.services.websocket_1 import websocket_manager_1
from examples.fastapi_cruddy_sqlite.services.websocket_2 import websocket_manager_2
from starlette_session import SessionMiddleware
from datetime import timedelta


logger = logging.getLogger(__name__)
HTTP_400_BAD_REQUEST = status.HTTP_400_BAD_REQUEST
HTTP_404_NOT_FOUND = status.HTTP_404_NOT_FOUND


async def bootstrap(application: FastAPI):
    # Because of how fastapi and sqlalchemy populate the relationship mappers, the CRUD router
    # can't be fully loaded until after the fastapi server starts. Make sure you only mount
    # the application_router in the bootstrapper. Fortunately, routers can be added lazily, which
    # forces fastapi to re-index the routes and update the openapi.json.
    await sqlite.destroy_then_create_all_tables_unsafe()
    await sqlite.enable_foreignkey_constraints()
    # You must activate the websocket manager in your application bootstrapper.
    # This .startup() function will spawn a listener loop that watches redis pub/sub channels.
    await websocket_manager_1.startup()
    await websocket_manager_2.startup()
    application.include_router(application_router)
    logger.info(f"{general.PROJECT_NAME}, {general.API_VERSION}: Bootstrap complete")
    # You can do any init hooks below


async def shutdown():
    await websocket_manager_1.dispose()
    await websocket_manager_2.dispose()


@asynccontextmanager
async def lifespan(application: FastAPI):
    await bootstrap(application)
    yield
    await shutdown()


app = FastAPI(
    title=general.PROJECT_NAME, version=general.API_VERSION, lifespan=lifespan
)

# As of fastapi 0.91.0+, all middlewares have to be defined immediately
app.add_middleware(RequestLogger)

# Set all CORS origins enabled
if http.HTTP_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in http.HTTP_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add session storage/retrieval to incoming requests
app.add_middleware(
    SessionMiddleware,
    secret_key=str(sessions.SESSION_SECRET_KEY),
    cookie_name=sessions.SESSION_COOKIE_NAME,
    https_only=False,
    same_site="lax",  # lax or strict
    max_age=int(timedelta(days=sessions.SESSION_MAX_AGE).total_seconds()),  # in seconds
)


# Add global handler to catch DB integrity errors
@app.exception_handler(IntegrityError)
async def integrity_exception_handler(_, exc: IntegrityError):
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content={"detail": [str(exc.orig)]},
    )


@app.exception_handler(CruddyNoMatchingRowException)
async def no_row_exception_handler(_, exc: CruddyNoMatchingRowException):
    return JSONResponse(
        status_code=HTTP_404_NOT_FOUND,
        content={"detail": [str(exc)]},
    )
