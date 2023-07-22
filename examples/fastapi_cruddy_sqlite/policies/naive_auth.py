from __future__ import annotations
from typing_extensions import Annotated
from fastapi import Security, Request, Query, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


HTTP_403_FORBIDDEN = status.HTTP_403_FORBIDDEN


async def auth_user_session(
    request: Request,
    credentials: HTTPAuthorizationCredentials
    | None = Security(HTTPBearer(auto_error=False)),
    auth_token: Annotated[str | None, Query()] = None,
):
    if request.session.get("token") is not None:
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
            detail="You shall not pass",
        )

    request.session["token"] = token
