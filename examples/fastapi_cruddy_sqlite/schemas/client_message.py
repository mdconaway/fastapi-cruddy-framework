from typing import Literal
from fastapi_cruddy_framework import CruddyGenericModel


class ClientMessage(CruddyGenericModel):
    route: (
        Literal["broadcast"] | Literal["room"] | Literal["client"] | Literal["control"]
    )
    type: str
    source: str | None = None
    target: str | None = None
    data: dict | None = None


class ClientControlWithTarget(ClientMessage):
    target: str
    type: (
        Literal["client_join_room"]
        | Literal["client_leave_room"]
        | Literal["client_kill_socket_id"]
        | Literal["client_kill_room"]
        | Literal["client_get_id"]
    )
