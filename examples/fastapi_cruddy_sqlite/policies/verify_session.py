from fastapi import HTTPException
from fastapi.requests import HTTPConnection


async def verify_session(connection: HTTPConnection):
    if not isinstance(connection.session, dict):
        raise HTTPException(status_code=400, detail="session does not exist!")
