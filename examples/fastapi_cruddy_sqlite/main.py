import uvicorn
import logging
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from examples.fastapi_cruddy_sqlite.config import general, http, sessions
from examples.fastapi_cruddy_sqlite.router import application as ApplicationRouter
from examples.fastapi_cruddy_sqlite.middleware import RequestLogger
from examples.fastapi_cruddy_sqlite.adapters import sqlite
from starlette_session import SessionMiddleware
from datetime import timedelta


logger = logging.getLogger(__name__)

app = FastAPI(title=general.PROJECT_NAME, version=general.API_VERSION)

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
    secret_key=sessions.SESSION_SECRET_KEY,
    cookie_name=sessions.SESSION_COOKIE_NAME,
    https_only=False,
    same_site="lax",  # lax or strict
    max_age=timedelta(days=int(sessions.SESSION_MAX_AGE)),  # in seconds
)


@app.on_event("startup")
async def bootstrap():
    # Because of how fastapi and sqlalchemy populate the relationship mappers, the CRUD router
    # can't be fully loaded until after the fastapi server starts. Make sure you only mount
    # the ApplicationRouter in the bootstrapper. Fortunately, routers can be added lazily, which
    # forces fastapi to re-index the routes and update the openapi.json.
    await sqlite.destroy_then_create_all_tables_unsafe()
    app.include_router(ApplicationRouter)
    logger.info(f"{general.PROJECT_NAME}, {general.API_VERSION}: Bootstrap complete")
    # You can do any init hooks below


def local_start():
    uvicorn.run(
        "examples.fastapi_cruddy_sqlite.main:app",
        host="0.0.0.0",
        port=http.HTTP_PORT,
        reload=True,
    )
