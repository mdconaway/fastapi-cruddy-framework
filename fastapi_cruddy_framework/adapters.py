from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from contextlib import asynccontextmanager
from sqlmodel import text
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Union


# -------------------------------------------------------------------------------------------
# POSTGRESQL ADAPTER
# -------------------------------------------------------------------------------------------
# The default adapter for CruddyResource
class PostgresqlAdapter:
    engine: Union[AsyncEngine, None] = None

    def __init__(self, connection_uri="", pool_size=4, max_overflow=64):
        self.engine = create_async_engine(
            connection_uri,
            echo=True,
            future=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )

    # Since this returns an async generator, to use it elsewhere, it
    # should be invoked using the following syntax.
    #
    # async with postgresql.getSession() as session:
    #
    # which will iterate through the generator context and yield the
    # product into a local variable named session.
    # Coding this method in this way also means classes interacting
    # with the adapter dont have to handle commiting thier
    # transactions, or rolling them back. It will happen here after
    # the yielded context cedes control of the event loop back to
    # the adapter. If the database explodes, the rollback happens.

    def asyncSessionGenerator(self):
        return sessionmaker(
            autocommit=False,
            autoflush=False,
            future=True,
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

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

    async def addPostgresqlExtension(self) -> None:
        query = text("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        async with self.getSession() as session:
            await session.execute(query)
