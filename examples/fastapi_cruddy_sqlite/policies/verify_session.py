from fastapi import HTTPException, Request


async def verify_session(request: Request):
    if not isinstance(request.session, dict):
        raise HTTPException(status_code=400, detail="session does not exist!")
