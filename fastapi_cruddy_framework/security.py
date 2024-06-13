from fastapi import Request, WebSocket
from fastapi.security import HTTPBearer


# This class exists to solve this issue with websockets: https://github.com/tiangolo/fastapi/discussions/9132
class CruddyHTTPBearer(HTTPBearer):
    async def __call__(self, request: Request = None, websocket: WebSocket = None):  # type: ignore
        return await super().__call__(request or websocket)  # type: ignore
