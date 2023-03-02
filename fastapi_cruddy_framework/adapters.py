from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from contextlib import asynccontextmanager
from sqlmodel import text
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Union, AsyncIterator, Literal
from .schemas import CruddyModel


# -------------------------------------------------------------------------------------------
# BASE ADAPTER
# -------------------------------------------------------------------------------------------
class BaseAdapter:
    engine: None

    def __init__(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///file:temp.db?mode=memory&cache=shared&uri=true",
            echo=True,
            future=True,
        )

    async def __call__(self) -> AsyncIterator[AsyncSession]:
        # Used by FastAPI Depends
        async with self.getSession() as session:
            yield session

    def asyncSessionGenerator(self):
        return sessionmaker(
            autocommit=False,
            autoflush=False,
            future=True,
            bind=self.engine,
            class_=AsyncSession,
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
    async def getSession(self):
        try:
            asyncSession = self.asyncSessionGenerator()
            async with asyncSession() as session:
                yield session
                await session.commit()
        except:
            await session.rollback()
            raise
        finally:
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
    connection_uri: str = None
    engine: Union[AsyncEngine, None] = None

    def __init__(self, connection_uri="", pool_size=4, max_overflow=64):
        self.connection_uri = connection_uri
        self.engine = create_async_engine(
            self.connection_uri,
            echo=True,
            future=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )


# -------------------------------------------------------------------------------------------
# POSTGRESQL ADAPTER
# -------------------------------------------------------------------------------------------


class PostgresqlAdapter(MysqlAdapter):
    async def addPostgresqlExtension(self) -> None:
        query = text("CREATE EXTENSION IF NOT EXISTS pg_trgm")
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
    connection_uri: str = None
    engine: Union[AsyncEngine, None] = None

    def __init__(self, db_path="temp.db", mode: Literal["memory", "file"] = "memory"):
        if mode == "memory":
            self.connection_uri = f"{self.SQLITE_ASYNC_URL_PREFIX}{self.MEMORY_LOCATION_START}{db_path}{self.MEMORY_LOCATION_END}"
        else:
            self.connection_uri = f"{self.SQLITE_ASYNC_URL_PREFIX}{db_path}"
        self.engine = create_async_engine(self.connection_uri, echo=True, future=True)
