from fastapi import Request
from fastapi_cruddy_framework import SqliteAdapter
from sqlmodel.ext.asyncio.session import AsyncSession
from examples.fastapi_cruddy_sqlite.config import adapters


async def session_setup(session: AsyncSession, request: Request):
    # Here you can do anything you desire to set roles and session values
    # on the database layer session. This would allow you to propagate
    # user identity information all the way into a DB like postgres
    # to perform row-level data security.
    # Since you can access a request object here, you can scope a database
    # role to the specific user launching the HTTP request!
    #
    # NOTE: Calling AbstractRepository functions WITHOUT sending the request value
    # WILL bypass this session setup function. This is what can allow an app to
    # still perform root level queries when needed. All auto-generated routes
    # WILL enforce role-scope via this hook as the HTTP endpoint will always pass
    # the request.
    assert isinstance(request, Request)
    assert isinstance(session, AsyncSession)


async def session_teardown(session: AsyncSession, request: Request):
    # Here you can tear-down and roles / settings you setup on a per-session basis.
    assert isinstance(request, Request)
    assert isinstance(session, AsyncSession)


sqlite = SqliteAdapter(
    db_path=adapters.DATABASE_PATH,
    mode=adapters.DATABASE_MODE,
    session_setup=session_setup,
    session_teardown=session_teardown,
)
