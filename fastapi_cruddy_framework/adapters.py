from __future__ import annotations
from typing import Any, AsyncIterator, Literal
from typing_extensions import Callable, Awaitable
from contextlib import asynccontextmanager
from redis.asyncio import Redis, from_url
from fastapi import Request
from fakeredis.aioredis import FakeRedis
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker
from sqlmodel import text
from sqlmodel.ext.asyncio.session import AsyncSession
from .schemas import CruddyModel

AsyncFunctionType = Callable[[AsyncSession, Request], Awaitable[Any]]


# -------------------------------------------------------------------------------------------
# BASE ADAPTER
# -------------------------------------------------------------------------------------------
class BaseAdapter:
    engine: AsyncEngine
    session_setup: AsyncFunctionType | None
    session_teardown: AsyncFunctionType | None

    def __init__(
        self,
        echo=True,
        session_setup: AsyncFunctionType | None = None,
        session_teardown: AsyncFunctionType | None = None,
        **kwargs,
    ):
        self.session_setup = session_setup
        self.session_teardown = session_teardown
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///file:temp.db?mode=memory&cache=shared&uri=true",
            echo=echo,
            future=True,
            **kwargs,
        )

    async def __call__(self, request: Request) -> AsyncIterator[AsyncSession]:
        # Used by FastAPI Depends
        async with self.getSession(request) as session:
            yield session

    def asyncSessionGenerator(self):
        return async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    # Since this returns an async generator, to use it elsewhere, it
    # should be invoked using the following syntax.
    #
    # async with adapter.getSession() as session:
    #
    # which will iterate through the generator context and yield the
    # product into a local variable named session.
    # Coding this method in this way also means classes interacting
    # with the adapter dont have to handle commiting thier
    # transactions, or rolling them back. It will happen here after
    # the yielded context cedes control of the event loop back to
    # the adapter. If the database explodes, the rollback happens.
    @asynccontextmanager
    async def getSession(self, request: Request | None = None):
        asyncSession = self.asyncSessionGenerator()
        async with asyncSession() as session:
            try:
                if self.session_setup is not None and request is not None:
                    await self.session_setup(session, request)
                yield session
                if self.session_teardown is not None and request is not None:
                    await self.session_teardown(session, request)
                await session.commit()
                await session.close()
            # If there are errors, we don't need to re-run session_teardown, there is a deeper issue.
            except:
                try:
                    await session.rollback()
                except:
                    pass
                await session.close()
                raise
            else:
                await session.close()

    # Don't call this until the app "startup" hook is invoked. Or ever.
    async def destroy_then_create_all_tables_unsafe(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(CruddyModel.metadata.drop_all)
            await conn.run_sync(CruddyModel.metadata.create_all)


# -------------------------------------------------------------------------------------------
# MYSQL ADAPTER
# -------------------------------------------------------------------------------------------
class MysqlAdapter(BaseAdapter):
    connection_uri: str

    def __init__(
        self,
        connection_uri="",
        pool_size=4,
        max_overflow=64,
        echo=True,
        session_setup: AsyncFunctionType | None = None,
        session_teardown: AsyncFunctionType | None = None,
        **kwargs,
    ):
        self.session_setup = session_setup
        self.session_teardown = session_teardown
        self.connection_uri = connection_uri
        self.engine = create_async_engine(
            self.connection_uri,
            echo=echo,
            future=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
            **kwargs,
        )


# -------------------------------------------------------------------------------------------
# POSTGRESQL ADAPTER
# -------------------------------------------------------------------------------------------
class PostgresqlAdapter(MysqlAdapter):
    async def addPostgresqlExtension(self, extension_name: str = "pg_trgm") -> None:
        query = text(f"CREATE EXTENSION IF NOT EXISTS {extension_name}")
        # Use root user session (no request context)
        async with self.getSession() as session:
            await session.execute(query)


# -------------------------------------------------------------------------------------------
# SQLITE ADAPTER
# -------------------------------------------------------------------------------------------
# The default adapter for CruddyResource
class SqliteAdapter(BaseAdapter):
    SQLITE_ASYNC_URL_PREFIX = "sqlite+aiosqlite:///"
    MEMORY_LOCATION_START = "file:"
    MEMORY_LOCATION_END = "?mode=memory&cache=shared&uri=true"
    connection_uri: str
    engine: AsyncEngine

    def __init__(
        self,
        db_path="temp.db",
        mode: Literal["memory", "file"] = "memory",
        echo=True,
        session_setup: AsyncFunctionType | None = None,
        session_teardown: AsyncFunctionType | None = None,
        **kwargs,
    ):
        self.session_setup = session_setup
        self.session_teardown = session_teardown
        if mode == "memory":
            self.connection_uri = f"{self.SQLITE_ASYNC_URL_PREFIX}{self.MEMORY_LOCATION_START}{db_path}{self.MEMORY_LOCATION_END}"
        else:
            self.connection_uri = f"{self.SQLITE_ASYNC_URL_PREFIX}{db_path}"
        self.engine = create_async_engine(
            self.connection_uri,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=echo,
            future=True,
            **kwargs,
        )

    async def enable_foreignkey_constraints(self):
        # Use root user session (no request context)
        async with self.getSession() as session:
            await session.execute(text("PRAGMA foreign_keys=ON"))


# -------------------------------------------------------------------------------------------
# REDIS ADAPTER
# -------------------------------------------------------------------------------------------
# The adapter for all things websocket
class RedisAdapter:
    client: Redis | None = None
    ADAPTER_MODE: Literal["redis"] | Literal["memory"]
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_MAX_CONNECTIONS: int
    ADDITIONAL_ADAPTER_ARGS: dict

    def __init__(
        self,
        mode: Literal["redis"] | Literal["memory"] = "redis",
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_max_connections: int = 10000,
        **kwargs,
    ):
        self.ADAPTER_MODE = mode
        self.REDIS_HOST = redis_host
        self.REDIS_PORT = redis_port
        self.REDIS_MAX_CONNECTIONS = redis_max_connections
        self.ADDITIONAL_ADAPTER_ARGS = kwargs

    def get_client(self):
        if not self.client:
            # Other client options:
            # encoding="utf8",
            # decode_responses=True,
            # These have not been set so that starlette sessions can
            # determine encoding of the items it saves.
            if self.ADAPTER_MODE == "redis":
                self.client = from_url(
                    url=f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}",
                    max_connections=self.REDIS_MAX_CONNECTIONS,
                    **self.ADDITIONAL_ADAPTER_ARGS,
                )
            else:
                self.client = FakeRedis(
                    host=self.REDIS_HOST,
                    port=self.REDIS_PORT,
                    max_connections=self.REDIS_MAX_CONNECTIONS,
                    **self.ADDITIONAL_ADAPTER_ARGS,
                )
        return self.client
