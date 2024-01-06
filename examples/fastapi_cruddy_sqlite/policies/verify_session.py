from fastapi import HTTPException, Request, WebSocket


async def verify_session(
    request: Request = None,  # type: ignore
    websocket: WebSocket = None,  # type: ignore
):
    connection = request if request else websocket
    if not isinstance(connection.session, dict):
        raise HTTPException(status_code=400, detail="session does not exist!")
