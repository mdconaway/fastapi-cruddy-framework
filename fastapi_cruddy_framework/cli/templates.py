"""
Templates for FastAPI Cruddy Framework CLI
"""

# Model template
MODEL_TEMPLATE = '''"""
{model_name} model for FastAPI Cruddy Framework
"""{any_import}
from fastapi_cruddy_framework import (
    CruddyModel,
    {base_class},
    CruddyCreatedUpdatedMixin,
    CruddyCreatedUpdatedSignature,
)
from sqlmodel import Field


class {model_name}Update(CruddyModel):
    """Update model for {model_name} - contains fields that can be updated."""
{fields}


class {model_name}Create({model_name}Update):
    """Create model for {model_name} - extends update model with creation-only fields."""
    pass


class {model_name}View(CruddyCreatedUpdatedSignature, {base_class}):
    """View model for {model_name} - defines fields returned in API responses."""
{view_fields}


class {model_name}(CruddyCreatedUpdatedMixin(), {base_class}, {model_name}Create, table=True):
    """Base {model_name} model with database table definition."""
    pass
'''

# Resource template
RESOURCE_TEMPLATE = '''"""
{resource_name} resource for FastAPI Cruddy Framework
"""
from fastapi_cruddy_framework import Resource{id_type_import_line}
from {project_name_lower}.adapters.application import adapter  # Import your configured adapter
from {project_name_lower}.models.{resource_name_lower} import (
    {resource_name},
    {resource_name}Create,
    {resource_name}Update,
    {resource_name}View,
)
from {project_name_lower}.controllers.{resource_name_lower} import {resource_name}Controller


resource = Resource(
    adapter=adapter,
    id_type={id_type_name},
    resource_model={resource_name},
    resource_create_model={resource_name}Create,
    resource_update_model={resource_name}Update,
    response_schema={resource_name}View,
    controller_extension={resource_name}Controller,
    # Add your policies, lifecycle hooks, and other configurations here
    # policies_universal=[example_policy],
    # protected_relationships=["example_relation"],
)
'''

# Controller template
CONTROLLER_TEMPLATE = '''"""
{controller_name} controller extensions for FastAPI Cruddy Framework
"""
from fastapi_cruddy_framework import CruddyController, dependency_list


class {controller_name}Controller(CruddyController):
    """Extended controller for {controller_name} resource."""

    def setup(self):
        """Setup custom routes and extend default CRUD functionality."""
        # Access available properties:
        # - self.actions (CRUD actions)
        # - self.resource (Resource instance)
        # - self.repository (Repository instance)
        # - self.adapter (Database adapter)
        # - self.controller (FastAPI router)

        # Example custom route:
        @self.controller.get(
            "/example",
            summary="Example custom endpoint",
            description="This is an example of how to add custom endpoints",
        )
        async def custom_example():
            return {{"message": "Hello from {controller_name}!"}}

        # Example of extending default actions:
        # original_create = self.actions.create
        #
        # async def enhanced_create(request, data):
        #     # Add custom logic before creation
        #     result = await original_create(request, data)
        #     # Add custom logic after creation
        #     return result
        #
        # self.actions.create = enhanced_create
'''

# Project templates
MINIMAL_SQLITE_TEMPLATE = {
    "main.py": '''"""
FastAPI Cruddy Framework Application
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi_cruddy_framework import CruddyNoMatchingRowException
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from starlette_session import SessionMiddleware
from datetime import timedelta
from {{PROJECT_NAME_LOWER}}.adapters.application import adapter
from {{PROJECT_NAME_LOWER}}.config.general import general
from {{PROJECT_NAME_LOWER}}.config.http import http
from {{PROJECT_NAME_LOWER}}.config.sessions import sessions
from {{PROJECT_NAME_LOWER}}.router.application import router as application_router

logger = logging.getLogger(__name__)
HTTP_400_BAD_REQUEST = status.HTTP_400_BAD_REQUEST
HTTP_404_NOT_FOUND = status.HTTP_404_NOT_FOUND


async def bootstrap(application: FastAPI):
    """Bootstrap the application."""
    # Because of how fastapi and sqlalchemy populate the relationship mappers, the CRUD router
    # can't be fully loaded until after the fastapi server starts. Make sure you only mount
    # the application_router in the bootstrapper. Fortunately, routers can be added lazily, which
    # forces fastapi to re-index the routes and update the openapi.json.
    await adapter.destroy_then_create_all_tables_unsafe()
    application.include_router(application_router)
    logger.info(f"{general.PROJECT_NAME}, {general.API_VERSION}: Bootstrap complete")


async def shutdown():
    """Application shutdown handler."""
    logger.info(f"{general.PROJECT_NAME}: Shutdown complete")


@asynccontextmanager
async def lifespan(application: FastAPI):
    await bootstrap(application)
    yield
    await shutdown()


app = FastAPI(
    title=general.PROJECT_NAME,
    version=general.API_VERSION,
    lifespan=lifespan
)

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("{{PROJECT_NAME_LOWER}}.main:app", host="0.0.0.0", port=http.HTTP_PORT, reload=True)
''',
    "router/__init__.py": '''"""
Router modules for {{PROJECT_NAME}}
"""
''',
    "router/application.py": '''"""
Main application router for {{PROJECT_NAME}}
"""
from logging import getLogger
from fastapi import APIRouter
from fastapi_cruddy_framework import CreateRouterFromResources, CruddyResourceRegistry
import {{PROJECT_NAME_LOWER}}

logger = getLogger(__name__)

# Create the main application router from resources
router: APIRouter = CreateRouterFromResources(
    application_module={{PROJECT_NAME_LOWER}},
    resource_path="resources"
)


@router.get("/health", tags=["application"])
async def health_check() -> bool:
    """Health check endpoint - returns True when the application is ready."""
    return CruddyResourceRegistry.is_ready()


# You can add additional routes to this router below
# For example:
# @router.get("/custom", tags=["custom"])
# async def custom_endpoint():
#     return {"message": "Custom endpoint"}
''',
    "bootloader.py": """import uvicorn
from {{PROJECT_NAME_LOWER}}.config.http import http


def start():
    uvicorn.run(
        "{{PROJECT_NAME_LOWER}}.main:app",
        host="0.0.0.0",
        port=http.HTTP_PORT,
        reload=True,
    )
""",
    "adapters/__init__.py": '''"""
Database adapters for {{PROJECT_NAME}}
"""
''',
    "adapters/application.py": '''"""
Application database adapter for {{PROJECT_NAME}}
"""
from fastapi import Request
from fastapi_cruddy_framework import SqliteAdapter
from sqlmodel.ext.asyncio.session import AsyncSession


async def session_setup(session: AsyncSession, request: Request):
    """
    Setup database session for each request.

    Here you can set roles and session values on the database layer session.
    This allows you to propagate user identity information all the way into
    the database to perform row-level data security.

    Since you can access a request object here, you can scope a database
    role to the specific user launching the HTTP request!

    NOTE: Calling AbstractRepository functions WITHOUT sending the request value
    WILL bypass this session setup function. This allows an app to still perform
    root level queries when needed. All auto-generated routes WILL enforce
    role-scope via this hook as the HTTP endpoint will always pass the request.

    Args:
        session: The database session
        request: The HTTP request object
    """
    assert isinstance(request, Request)
    assert isinstance(session, AsyncSession)
    # Add your session setup logic here


async def session_teardown(session: AsyncSession, request: Request):
    """
    Cleanup database session after each request.

    Here you can tear-down any roles/settings you setup on a per-session basis.

    Args:
        session: The database session
        request: The HTTP request object
    """
    assert isinstance(request, Request)
    assert isinstance(session, AsyncSession)
    # Add your session teardown logic here


# Initialize the application database adapter
adapter = SqliteAdapter(
    mode="memory",  # Change to "file" and set db_path for persistent storage
    # db_path="./{{PROJECT_NAME_LOWER}}.db",
    session_setup=session_setup,
    session_teardown=session_teardown,
)
''',
    "config/__init__.py": '''"""
Configuration settings for {{PROJECT_NAME}}
"""
''',
    "config/_base.py": """import os
from pydantic_settings import BaseSettings


class Base(BaseSettings):
    class Config:
        case_sensitive = True
        env_file = os.path.expanduser("~/.env")
        env_file_encoding = "utf-8"
""",
    "config/general.py": """from {{PROJECT_NAME_LOWER}}.config._base import Base


class General(Base):
    PROJECT_NAME: str = "{{PROJECT_NAME}}"
    API_VERSION: str = "1.0.0"
    DEFAULT_LIMIT: int = 20


general = General()
""",
    "config/http.py": """from {{PROJECT_NAME_LOWER}}.config._base import Base
from pydantic import model_validator, AnyHttpUrl


class Http(Base):
    HTTP_PORT: int = 8000
    HTTP_CORS_ORIGINS: str | list[str] | list[AnyHttpUrl] = ["*"]

    @model_validator(mode="after")
    def assemble_cors_origins(self):
        if isinstance(
            self.HTTP_CORS_ORIGINS, str
        ) and not self.HTTP_CORS_ORIGINS.startswith("["):
            self.HTTP_CORS_ORIGINS = [
                i.strip() for i in self.HTTP_CORS_ORIGINS.split(",")
            ]
        elif isinstance(self.HTTP_CORS_ORIGINS, list):
            self.HTTP_CORS_ORIGINS = self.HTTP_CORS_ORIGINS
        else:
            raise ValueError(self.HTTP_CORS_ORIGINS)
        return self


http = Http()
""",
    "config/sessions.py": """from {{PROJECT_NAME_LOWER}}.config._base import Base
from pydantic import model_validator
from secrets import token_urlsafe


class Sessions(Base):
    SESSION_COOKIE_NAME: str = "{{PROJECT_NAME_LOWER}}"
    SESSION_SECRET_KEY: str | None = None
    SESSION_MAX_AGE: int = 1

    @model_validator(mode="after")
    def validate_session_secret(self):
        self.SESSION_SECRET_KEY = (
            self.SESSION_SECRET_KEY
            if isinstance(self.SESSION_SECRET_KEY, str)
            else token_urlsafe(32)
        )
        return self


sessions = Sessions()
""",
    "pyproject.toml": """[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "{{PROJECT_NAME_LOWER}}"
version = "0.1.0"
description = "A FastAPI Cruddy Framework application"
authors = ["Your Name <you@example.com>"]
readme = "README.md"
packages = [{include = "{{PROJECT_NAME_LOWER}}"}]

[tool.poetry.dependencies]
python = ">=3.10,<4.0"
fastapi = {extras = ["all"], version = "^0.128.0"}
fastapi-cruddy-framework = "^1.12.1"
uvicorn = {extras = ["standard"], version = "^0.40.0"}
pydantic-settings = "^2.0.0"
aiosqlite = "^0.21.0"
starlette-session = "^0.4.3"

[tool.poetry.group.dev.dependencies]
pytest = "^9.0.2"
pytest-dependency = "^0.6.0"
black = "^26.1.0"
pylint = "^4.0.4"
coverage = "^7.13.2"

[tool.poetry.scripts]
start = "{{PROJECT_NAME_LOWER}}.bootloader:start"

[tool.black]
line-length = 88
target-version = ['py310']

[tool.ruff]
target-version = "py310"
line-length = 88
select = ["E", "W", "F", "I"]
ignore = ["E501"]
""",
    ".env": """# Environment variables for {{PROJECT_NAME}}
DEBUG=true
DATABASE_URL=sqlite:///./{{PROJECT_NAME_LOWER}}.db
""",
    "README.md": """# {{PROJECT_NAME}}

A FastAPI Cruddy Framework application.

## Setup

1. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

2. Run the application:
   ```bash
   poetry run python main.py
   # OR
   poetry shell
   python main.py
   # OR use the poetry script
   poetry run start
   ```

3. Access the API documentation at http://localhost:8000/docs

## Usage

### Generate a new resource:
```bash
cruddy generate resource User --fields "name:str,email:str,age:int"
```

### Generate just a model:
```bash
cruddy generate model Product --fields "name:str,price:float,description:str"
```

### Generate a controller:
```bash
cruddy generate controller CustomEndpoints
```

## Development

### Code formatting:
```bash
poetry run black .
```

### Linting:
```bash
poetry run ruff check .
```

### Tests:
```bash
poetry run pytest
```

## Project Structure

- `models/` - Database models
- `resources/` - Resource definitions (combines models, controllers, repositories)
- `controllers/` - Custom controller extensions
- `config/` - Configuration settings
- `adapters/` - Database adapter configuration
- `policies/` - Business logic policies
- `schemas/` - Response and validation schemas
""",
}

MINIMAL_POSTGRESQL_TEMPLATE = {
    "main.py": MINIMAL_SQLITE_TEMPLATE["main.py"],
    "bootloader.py": MINIMAL_SQLITE_TEMPLATE["bootloader.py"],
    "adapters/__init__.py": '''"""
Database adapters for {{PROJECT_NAME}}
"""
''',
    "adapters/application.py": '''"""
Application database adapter for {{PROJECT_NAME}}
"""
from fastapi import Request
from fastapi_cruddy_framework import PostgresqlAdapter
from sqlmodel.ext.asyncio.session import AsyncSession


async def session_setup(session: AsyncSession, request: Request):
    """
    Setup database session for each request.

    Here you can set roles and session values on the database layer session.
    This allows you to propagate user identity information all the way into
    the database to perform row-level data security.

    Since you can access a request object here, you can scope a database
    role to the specific user launching the HTTP request!

    NOTE: Calling AbstractRepository functions WITHOUT sending the request value
    WILL bypass this session setup function. This allows an app to still perform
    root level queries when needed. All auto-generated routes WILL enforce
    role-scope via this hook as the HTTP endpoint will always pass the request.

    Args:
        session: The database session
        request: The HTTP request object
    """
    assert isinstance(request, Request)
    assert isinstance(session, AsyncSession)
    # Add your session setup logic here


async def session_teardown(session: AsyncSession, request: Request):
    """
    Cleanup database session after each request.

    Here you can tear-down any roles/settings you setup on a per-session basis.

    Args:
        session: The database session
        request: The HTTP request object
    """
    assert isinstance(request, Request)
    assert isinstance(session, AsyncSession)
    # Add your session teardown logic here


# Initialize the application database adapter
adapter = PostgresqlAdapter(
    connection_uri="postgresql://user:password@localhost/{{PROJECT_NAME_LOWER}}",
    pool_size=5,
    max_overflow=10,
    session_setup=session_setup,
    session_teardown=session_teardown,
)
''',
    "config/__init__.py": MINIMAL_SQLITE_TEMPLATE["config/__init__.py"],
    "config/_base.py": MINIMAL_SQLITE_TEMPLATE["config/_base.py"],
    "config/general.py": MINIMAL_SQLITE_TEMPLATE["config/general.py"],
    "config/http.py": MINIMAL_SQLITE_TEMPLATE["config/http.py"],
    "config/sessions.py": MINIMAL_SQLITE_TEMPLATE["config/sessions.py"],
    "router/__init__.py": MINIMAL_SQLITE_TEMPLATE["router/__init__.py"],
    "router/application.py": MINIMAL_SQLITE_TEMPLATE["router/application.py"],
    "pyproject.toml": """[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "{{PROJECT_NAME_LOWER}}"
version = "0.1.0"
description = "A FastAPI Cruddy Framework application"
authors = ["Your Name <you@example.com>"]
readme = "README.md"
packages = [{include = "{{PROJECT_NAME_LOWER}}"}]

[tool.poetry.dependencies]
python = ">=3.10,<4.0"
fastapi = {extras = ["all"], version = "^0.128.0"}
fastapi-cruddy-framework = "^1.12.1"
uvicorn = {extras = ["standard"], version = "^0.40.0"}
pydantic-settings = "^2.0.0"
asyncpg = "^0.30.0"
starlette-session = "^0.4.3"

[tool.poetry.group.dev.dependencies]
pytest = "^9.0.2"
pytest-dependency = "^0.6.0"
black = "^26.1.0"
pylint = "^4.0.4"
coverage = "^7.13.2"

[tool.poetry.scripts]
start = "{{PROJECT_NAME_LOWER}}.bootloader:start"

[tool.black]
line-length = 88
target-version = ['py310']

[tool.ruff]
target-version = "py310"
line-length = 88
select = ["E", "W", "F", "I"]
ignore = ["E501"]
""",
    ".env": """# Environment variables for {{PROJECT_NAME}}
DEBUG=true
DATABASE_URL=postgresql://user:password@localhost/{{PROJECT_NAME_LOWER}}
""",
    "README.md": MINIMAL_SQLITE_TEMPLATE["README.md"],
}

MINIMAL_MYSQL_TEMPLATE = {
    "main.py": MINIMAL_SQLITE_TEMPLATE["main.py"],
    "bootloader.py": MINIMAL_SQLITE_TEMPLATE["bootloader.py"],
    "adapters/__init__.py": '''"""
Database adapters for {{PROJECT_NAME}}
"""
''',
    "adapters/application.py": '''"""
Application database adapter for {{PROJECT_NAME}}
"""
from fastapi import Request
from fastapi_cruddy_framework import MysqlAdapter
from sqlmodel.ext.asyncio.session import AsyncSession


async def session_setup(session: AsyncSession, request: Request):
    """
    Setup database session for each request.

    Here you can set roles and session values on the database layer session.
    This allows you to propagate user identity information all the way into
    the database to perform row-level data security.

    Since you can access a request object here, you can scope a database
    role to the specific user launching the HTTP request!

    NOTE: Calling AbstractRepository functions WITHOUT sending the request value
    WILL bypass this session setup function. This allows an app to still perform
    root level queries when needed. All auto-generated routes WILL enforce
    role-scope via this hook as the HTTP endpoint will always pass the request.

    Args:
        session: The database session
        request: The HTTP request object
    """
    assert isinstance(request, Request)
    assert isinstance(session, AsyncSession)
    # Add your session setup logic here


async def session_teardown(session: AsyncSession, request: Request):
    """
    Cleanup database session after each request.

    Here you can tear-down any roles/settings you setup on a per-session basis.

    Args:
        session: The database session
        request: The HTTP request object
    """
    assert isinstance(request, Request)
    assert isinstance(session, AsyncSession)
    # Add your session teardown logic here


# Initialize the application database adapter
adapter = MysqlAdapter(
    connection_uri="mysql://user:password@localhost/{{PROJECT_NAME_LOWER}}",
    pool_size=5,
    max_overflow=10,
    session_setup=session_setup,
    session_teardown=session_teardown,
)
''',
    "config/__init__.py": MINIMAL_SQLITE_TEMPLATE["config/__init__.py"],
    "config/_base.py": MINIMAL_SQLITE_TEMPLATE["config/_base.py"],
    "config/general.py": MINIMAL_SQLITE_TEMPLATE["config/general.py"],
    "config/http.py": MINIMAL_SQLITE_TEMPLATE["config/http.py"],
    "config/sessions.py": MINIMAL_SQLITE_TEMPLATE["config/sessions.py"],
    "router/__init__.py": MINIMAL_SQLITE_TEMPLATE["router/__init__.py"],
    "router/application.py": MINIMAL_SQLITE_TEMPLATE["router/application.py"],
    "pyproject.toml": """[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "{{PROJECT_NAME_LOWER}}"
version = "0.1.0"
description = "A FastAPI Cruddy Framework application"
authors = ["Your Name <you@example.com>"]
readme = "README.md"
packages = [{include = "{{PROJECT_NAME_LOWER}}"}]

[tool.poetry.dependencies]
python = ">=3.10,<4.0"
fastapi = {extras = ["all"], version = "^0.128.0"}
fastapi-cruddy-framework = "^1.12.1"
uvicorn = {extras = ["standard"], version = "^0.40.0"}
pydantic-settings = "^2.0.0"
PyMySQL = "^1.1.2"
starlette-session = "^0.4.3"

[tool.poetry.group.dev.dependencies]
pytest = "^9.0.2"
pytest-dependency = "^0.6.0"
black = "^26.1.0"
pylint = "^4.0.4"
coverage = "^7.13.2"

[tool.poetry.scripts]
start = "{{PROJECT_NAME_LOWER}}.bootloader:start"

[tool.black]
line-length = 88
target-version = ['py310']

[tool.ruff]
target-version = "py310"
line-length = 88
select = ["E", "W", "F", "I"]
ignore = ["E501"]
""",
    ".env": """# Environment variables for {{PROJECT_NAME}}
DEBUG=true
DATABASE_URL=mysql://user:password@localhost/{{PROJECT_NAME_LOWER}}
""",
    "README.md": MINIMAL_SQLITE_TEMPLATE["README.md"],
}

# Full templates with auth, websockets, GraphQL, and middleware
FULL_SQLITE_TEMPLATE = {
    **MINIMAL_SQLITE_TEMPLATE,
    # Enhanced main.py with websocket managers
    "main.py": '''"""
FastAPI Cruddy Framework Application with Auth, Websockets, and GraphQL
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi_cruddy_framework import CruddyNoMatchingRowException
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from starlette_session import SessionMiddleware
from datetime import timedelta
from {{PROJECT_NAME_LOWER}}.adapters.application import adapter
from {{PROJECT_NAME_LOWER}}.config.general import general
from {{PROJECT_NAME_LOWER}}.config.http import http
from {{PROJECT_NAME_LOWER}}.config.sessions import sessions
from {{PROJECT_NAME_LOWER}}.router.application import router as application_router
from {{PROJECT_NAME_LOWER}}.services.websocket_manager import websocket_manager
from {{PROJECT_NAME_LOWER}}.middleware.request_logger import RequestLogger

logger = logging.getLogger(__name__)
HTTP_400_BAD_REQUEST = status.HTTP_400_BAD_REQUEST
HTTP_404_NOT_FOUND = status.HTTP_404_NOT_FOUND


async def bootstrap(application: FastAPI):
    """Bootstrap the application."""
    # Because of how fastapi and sqlalchemy populate the relationship mappers, the CRUD router
    # can't be fully loaded until after the fastapi server starts. Make sure you only mount
    # the application_router in the bootstrapper. Fortunately, routers can be added lazily, which
    # forces fastapi to re-index the routes and update the openapi.json.
    await adapter.destroy_then_create_all_tables_unsafe()

    # Start websocket manager
    await websocket_manager.startup()

    application.include_router(application_router)
    logger.info(f"{general.PROJECT_NAME}, {general.API_VERSION}: Bootstrap complete")


async def shutdown():
    """Application shutdown handler."""
    await websocket_manager.dispose()
    logger.info(f"{general.PROJECT_NAME}: Shutdown complete")


@asynccontextmanager
async def lifespan(application: FastAPI):
    await bootstrap(application)
    yield
    await shutdown()


app = FastAPI(
    title=general.PROJECT_NAME,
    version=general.API_VERSION,
    lifespan=lifespan
)

# Add request logging middleware
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("{{PROJECT_NAME_LOWER}}.main:app", host="0.0.0.0", port=http.HTTP_PORT, reload=True)
''',
    # Enhanced router with websocket endpoints
    "router/application.py": '''"""
Main application router for {{PROJECT_NAME}} with Websockets
"""
from logging import getLogger
from fastapi import APIRouter, WebSocket
from fastapi_cruddy_framework import (
    CreateRouterFromResources,
    CruddyResourceRegistry,
    uuid7,
    dependency_list
)
from {{PROJECT_NAME_LOWER}}.policies.verify_session import verify_session
from {{PROJECT_NAME_LOWER}}.policies.naive_auth import naive_auth
from {{PROJECT_NAME_LOWER}}.services.websocket_manager import websocket_manager
import {{PROJECT_NAME_LOWER}}

logger = getLogger(__name__)

# Create the main application router from resources
router: APIRouter = CreateRouterFromResources(
    application_module={{PROJECT_NAME_LOWER}},
    resource_path="resources"
)


@router.get("/health", tags=["application"])
async def health_check() -> bool:
    """Health check endpoint - returns True when the application is ready."""
    return CruddyResourceRegistry.is_ready()


# Websocket endpoint with authentication
@router.websocket("/ws", dependencies=dependency_list(verify_session, naive_auth))
async def websocket_endpoint(websocket: WebSocket):
    """Main websocket endpoint with authentication and session management."""
    override_socket_id = str(uuid7())

    async with websocket_manager.connect(
        websocket,
        override_socket_id=override_socket_id,
        disconnect_message_type="socket_disconnect",
        disconnect_message_data={
            "socket_id": f"{override_socket_id}",
            "message": f"Websocket client {override_socket_id} disconnected",
        },
    ) as socket_id:
        logger.info("Socket %s connected", socket_id)
        await websocket_manager.broadcast(
            type="socket_connect",
            data={"socket_id": socket_id}
        )


# You can add additional routes to this router below
# For example:
# @router.get("/custom", tags=["custom"])
# async def custom_endpoint():
#     return {"message": "Custom endpoint"}
''',
    # Auth policies
    "policies/verify_session.py": '''"""
Session verification policy for {{PROJECT_NAME}}
"""
from fastapi import HTTPException
from fastapi.requests import HTTPConnection


async def verify_session(connection: HTTPConnection):
    """Verify that a valid session exists."""
    if not isinstance(connection.session, dict):
        raise HTTPException(status_code=400, detail="session does not exist!")
''',
    "policies/naive_auth.py": '''"""
Authentication policy for {{PROJECT_NAME}}
"""
from __future__ import annotations
from typing_extensions import Annotated
from fastapi import Security, Query, HTTPException, status
from fastapi_cruddy_framework import CruddyHTTPBearer
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.requests import HTTPConnection


HTTP_403_FORBIDDEN = status.HTTP_403_FORBIDDEN


async def naive_auth(
    connection: HTTPConnection,
    credentials: HTTPAuthorizationCredentials | None = Security(
        CruddyHTTPBearer(auto_error=False)
    ),
    auth_token: Annotated[str | None, Query()] = None,
):
    """Authenticate users via Bearer token or query parameter."""
    if connection.session.get("token") is not None:
        return

    if (
        not credentials
        or not hasattr(credentials, "scheme")
        or credentials.scheme != "Bearer"
    ):
        if isinstance(auth_token, str):
            token = auth_token
        else:
            token = None
    else:
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Authentication required - provide Bearer token or auth_token query parameter",
        )

    connection.session["token"] = token
''',
    # Websocket services
    "services/__init__.py": '''"""
Service modules for {{PROJECT_NAME}}
"""
''',
    "services/websocket_manager.py": '''"""
Websocket connection manager for {{PROJECT_NAME}}
"""
from typing import Any
from logging import getLogger
from fastapi import WebSocket
from fastapi_cruddy_framework import (
    WebsocketConnectionManager,
    CLIENT_MESSAGE_EVENT,
    get_state,
)
from {{PROJECT_NAME_LOWER}}.schemas.client_message import ClientMessage, ClientControlWithTarget

logger = getLogger(__name__)

# Initialize websocket manager (uses in-memory Redis for development)
websocket_manager = WebsocketConnectionManager(
    redis_mode="memory",  # Change to "connection" for production Redis
    redis_channel="{{PROJECT_NAME_LOWER}}_websockets"
)


async def client_controls(websocket: WebSocket, message: ClientMessage):
    """Handle websocket control messages like join/leave room, kill socket, etc."""
    try:
        control_message = ClientControlWithTarget.model_validate(message.model_dump())
    except Exception as e:
        logger.info(
            "Discarding message %s, due to missing params: %s", message.model_dump(), e
        )
        return

    socket_id = str(get_state(websocket, "socket_id", ""))

    if control_message.type == "client_join_room":
        await websocket_manager.join_room_by_socket_id(
            id=socket_id, room_id=control_message.target
        )
    elif control_message.type == "client_leave_room":
        await websocket_manager.leave_room_by_socket_id(
            id=socket_id, room_id=control_message.target
        )
    elif control_message.type == "client_kill_socket_id":
        await websocket_manager.kill_sockets_by_socket_id(id=control_message.target)
    elif control_message.type == "client_kill_room":
        await websocket_manager.kill_room_by_id(room_id=control_message.target)
    elif control_message.type == "client_get_id":
        await websocket_manager.direct_message(
            target=socket_id,
            sender=socket_id,
            type=control_message.type,
            data={"id": socket_id},
        )


async def client_message_router(websocket: WebSocket, raw_message: Any):
    """Route incoming websocket messages to appropriate handlers."""
    try:
        message = ClientMessage.model_validate(raw_message)
    except Exception:
        logger.warning("Invalid websocket message received: %s", raw_message)
        return

    socket_id = get_state(websocket, "socket_id", "")
    logger.info("Socket %s sent message %s", socket_id, message.model_dump())

    if message.route == "broadcast":
        return await websocket_manager.broadcast(
            sender=socket_id, type=message.type, data=message.data
        )
    elif message.route == "room":
        return await websocket_manager.room_message(
            target=message.target,
            sender=socket_id,
            type=message.type,
            data=message.data,
        )
    elif message.route == "client":
        return await websocket_manager.direct_message(
            target=message.target,
            sender=socket_id,
            type=message.type,
            data=message.data,
        )
    elif message.route == "control":
        return await client_controls(websocket=websocket, message=message)


# Register the message router
websocket_manager.on(CLIENT_MESSAGE_EVENT, client_message_router)
''',
    # Client message schemas
    "schemas/client_message.py": '''"""
Websocket client message schemas for {{PROJECT_NAME}}
"""
from typing import Any
from fastapi_cruddy_framework import CruddyGenericModel


class ClientMessage(CruddyGenericModel):
    """Base websocket message from client."""
    route: str  # "broadcast", "room", "client", "control"
    type: str   # Message type identifier
    target: str | None = None  # Target room/client (if applicable)
    data: Any = None  # Message payload


class ClientControlWithTarget(CruddyGenericModel):
    """Control message with required target field."""
    type: str   # Control command type
    target: str # Target ID for control operation
    data: Any = None
''',
    # Middleware
    "middleware/__init__.py": '''"""
Middleware modules for {{PROJECT_NAME}}
"""
''',
    "middleware/request_logger.py": '''"""
Request logging middleware for {{PROJECT_NAME}}
"""
import logging
from random import choices
from time import time
from string import ascii_uppercase, digits
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLogger(BaseHTTPMiddleware):
    """Middleware to log HTTP requests with timing and unique identifiers."""

    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        req_id = "".join(choices(ascii_uppercase + digits, k=6))
        logger.info(f"rid={req_id} start request path={request.url.path}")

        start_time = time()
        response = await call_next(request)
        process_time = (time() - start_time) * 1000
        formatted_process_time = "{0:.2f}".format(process_time)

        logger.info(
            f"rid={req_id} completed_in={formatted_process_time}ms status_code={response.status_code}"
        )

        return response
''',
    # Enhanced pyproject.toml with additional dependencies
    "pyproject.toml": """[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "{{PROJECT_NAME_LOWER}}"
version = "0.1.0"
description = "A FastAPI Cruddy Framework application with Auth, Websockets, and GraphQL"
authors = ["Your Name <you@example.com>"]
readme = "README.md"
packages = [{include = "{{PROJECT_NAME_LOWER}}"}]

[tool.poetry.dependencies]
python = ">=3.10,<4.0"
fastapi = {extras = ["all"], version = "^0.128.0"}
fastapi-cruddy-framework = "^1.12.1"
uvicorn = {extras = ["standard"], version = "^0.40.0"}
pydantic-settings = "^2.0.0"
aiosqlite = "^0.21.0"
starlette-session = "^0.4.3"

[tool.poetry.group.dev.dependencies]
pytest = "^9.0.2"
pytest-dependency = "^0.6.0"
black = "^26.1.0"
pylint = "^4.0.4"
coverage = "^7.13.2"

[tool.poetry.scripts]
start = "{{PROJECT_NAME_LOWER}}.bootloader:start"

[tool.black]
line-length = 88
target-version = ['py310']

[tool.ruff]
target-version = "py310"
line-length = 88
select = ["E", "W", "F", "I"]
ignore = ["E501"]
""",
    # Enhanced README with full features
    "README.md": """# {{PROJECT_NAME}}

A full-featured FastAPI Cruddy Framework application with authentication, websockets, GraphQL, and more.

## Features

- 🔐 **Authentication**: Bearer token and session-based auth
- 🔌 **WebSockets**: Real-time messaging with rooms and broadcasting
- 📊 **GraphQL**: GraphQL endpoint for flexible data queries
- 🛡️ **Middleware**: Request logging and error handling
- 📝 **CRUD Operations**: Auto-generated REST endpoints
- 🔄 **Modern Stack**: Poetry, async/await, type hints

## Setup

1. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

2. Run the application:
   ```bash
   poetry run start
   # OR
   poetry run python main.py
   ```

3. Access the services:
   - **API Documentation**: http://localhost:8000/docs
   - **Health Check**: http://localhost:8000/health
   - **WebSocket**: ws://localhost:8000/ws (requires auth)

## Authentication

The application uses bearer token authentication:

```bash
# Via Authorization header
curl -H "Authorization: Bearer your-token" http://localhost:8000/health

# Via query parameter
curl http://localhost:8000/health?auth_token=your-token
```

## WebSocket Usage

Connect to the WebSocket endpoint with authentication:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?auth_token=your-token');

// Send a broadcast message
ws.send(JSON.stringify({
    route: "broadcast",
    type: "chat_message",
    data: { message: "Hello everyone!" }
}));

// Join a room
ws.send(JSON.stringify({
    route: "control",
    type: "client_join_room",
    target: "room_1"
}));

// Send message to room
ws.send(JSON.stringify({
    route: "room",
    type: "room_message",
    target: "room_1",
    data: { message: "Hello room!" }
}));
```

## Resource Generation

### Generate a new resource:
```bash
cruddy generate resource User --fields "name:str,email:str,age:int"
```

### Generate individual components:
```bash
cruddy generate model Product --fields "name:str,price:float,description:str"
cruddy generate controller CustomEndpoints
```

## Development

### Code formatting:
```bash
poetry run black .
```

### Linting:
```bash
poetry run ruff check .
```

### Tests:
```bash
poetry run pytest
```

## Project Structure

- `main.py` - FastAPI application with full middleware stack
- `router/application.py` - Main router with websocket endpoints
- `policies/` - Authentication and authorization policies
- `services/` - WebSocket managers and business logic
- `middleware/` - Request logging and custom middleware
- `schemas/` - Pydantic models for validation
- `models/` - Database models
- `resources/` - Resource definitions (CRUD endpoints)
- `controllers/` - Custom controller extensions
- `config/` - Configuration settings

## Production Notes

For production deployment:
- Change `redis_mode` from "memory" to "connection" in websocket manager
- Set up proper Redis server
- Configure environment variables in `.env`
- Use proper authentication tokens
- Enable HTTPS for websocket connections
""",
}

FULL_POSTGRESQL_TEMPLATE = {
    **FULL_SQLITE_TEMPLATE,
    "adapters/__init__.py": MINIMAL_POSTGRESQL_TEMPLATE["adapters/__init__.py"],
    "adapters/application.py": MINIMAL_POSTGRESQL_TEMPLATE["adapters/application.py"],
    "pyproject.toml": """[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "{{PROJECT_NAME_LOWER}}"
version = "0.1.0"
description = "A FastAPI Cruddy Framework application with Auth, Websockets, and GraphQL"
authors = ["Your Name <you@example.com>"]
readme = "README.md"
packages = [{include = "{{PROJECT_NAME_LOWER}}"}]

[tool.poetry.dependencies]
python = ">=3.10,<4.0"
fastapi = {extras = ["all"], version = "^0.128.0"}
fastapi-cruddy-framework = "^1.12.1"
uvicorn = {extras = ["standard"], version = "^0.40.0"}
pydantic-settings = "^2.0.0"
asyncpg = "^0.30.0"
starlette-session = "^0.4.3"

[tool.poetry.group.dev.dependencies]
pytest = "^9.0.2"
pytest-dependency = "^0.6.0"
black = "^26.1.0"
pylint = "^4.0.4"
coverage = "^7.13.2"

[tool.poetry.scripts]
start = "{{PROJECT_NAME_LOWER}}.bootloader:start"

[tool.black]
line-length = 88
target-version = ['py310']

[tool.ruff]
target-version = "py310"
line-length = 88
select = ["E", "W", "F", "I"]
ignore = ["E501"]
""",
    ".env": MINIMAL_POSTGRESQL_TEMPLATE[".env"],
}

FULL_MYSQL_TEMPLATE = {
    **FULL_SQLITE_TEMPLATE,
    "adapters/__init__.py": MINIMAL_MYSQL_TEMPLATE["adapters/__init__.py"],
    "adapters/application.py": MINIMAL_MYSQL_TEMPLATE["adapters/application.py"],
    "pyproject.toml": """[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "{{PROJECT_NAME_LOWER}}"
version = "0.1.0"
description = "A FastAPI Cruddy Framework application with Auth, Websockets, and GraphQL"
authors = ["Your Name <you@example.com>"]
readme = "README.md"
packages = [{include = "{{PROJECT_NAME_LOWER}}"}]

[tool.poetry.dependencies]
python = ">=3.10,<4.0"
fastapi = {extras = ["all"], version = "^0.128.0"}
fastapi-cruddy-framework = "^1.12.1"
uvicorn = {extras = ["standard"], version = "^0.40.0"}
pydantic-settings = "^2.0.0"
PyMySQL = "^1.1.2"
starlette-session = "^0.4.3"

[tool.poetry.group.dev.dependencies]
pytest = "^9.0.2"
pytest-dependency = "^0.6.0"
black = "^26.1.0"
pylint = "^4.0.4"
coverage = "^7.13.2"

[tool.poetry.scripts]
start = "{{PROJECT_NAME_LOWER}}.bootloader:start"

[tool.black]
line-length = 88
target-version = ['py310']

[tool.ruff]
target-version = "py310"
line-length = 88
select = ["E", "W", "F", "I"]
ignore = ["E501"]
""",
    ".env": MINIMAL_MYSQL_TEMPLATE[".env"],
}

# Organize templates by template type and database
PROJECT_TEMPLATES = {
    "minimal": {
        "sqlite": MINIMAL_SQLITE_TEMPLATE,
        "postgresql": MINIMAL_POSTGRESQL_TEMPLATE,
        "mysql": MINIMAL_MYSQL_TEMPLATE,
    },
    "full": {
        "sqlite": FULL_SQLITE_TEMPLATE,
        "postgresql": FULL_POSTGRESQL_TEMPLATE,
        "mysql": FULL_MYSQL_TEMPLATE,
    },
}
