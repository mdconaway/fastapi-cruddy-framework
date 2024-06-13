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
            detail="You shall not pass",
        )

    connection.session["token"] = token
