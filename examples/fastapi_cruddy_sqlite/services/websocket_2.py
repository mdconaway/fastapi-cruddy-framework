from typing import Any
from logging import getLogger
from fastapi import WebSocket
from fastapi_cruddy_framework import WebsocketConnectionManager, CLIENT_MESSAGE_EVENT
from examples.fastapi_cruddy_sqlite.schemas.client_message import (
    ClientMessage,
    ClientControlWithTarget,
)
from examples.fastapi_cruddy_sqlite.utils.session import get_client_identity
from examples.fastapi_cruddy_sqlite.config import adapters

logger = getLogger(__name__)
websocket_manager_2 = WebsocketConnectionManager(
    redis_mode=adapters.REDIS_MODE,
    redis_channel="websockets_custom",
    custom_client_identifier=get_client_identity,
)


# This is just an example of how to let sockets "control" things.
# Obviously you should have security in a real-world scenario.
async def client_controls(websocket: WebSocket, message: ClientMessage):
    try:
        control_message = ClientControlWithTarget.model_validate(message.model_dump())
    except Exception as e:
        logger.info(
            "Discarding message %s, due to missing params: %s", message.model_dump(), e
        )
        return
    client_id = get_client_identity(websocket)
    if control_message.type == "client_join_room":
        await websocket_manager_2.join_room_by_client_id(
            id=str(client_id), room_id=control_message.target
        )
    elif control_message.type == "client_leave_room":
        await websocket_manager_2.leave_room_by_client_id(
            id=str(client_id), room_id=control_message.target
        )
    elif control_message.type == "client_kill_socket_id":
        await websocket_manager_2.kill_sockets_by_client_id(id=control_message.target)
    elif control_message.type == "client_kill_room":
        await websocket_manager_2.kill_room_by_id(room_id=control_message.target)
    elif control_message.type == "client_get_id":
        await websocket_manager_2.direct_message(
            target=client_id,
            sender=client_id,
            type=control_message.type,
            data={"id": client_id},
        )


# This is just an example of how to let sockets send messages.
# Obviously you should have security in a real-world scenario.
async def client_message_router(websocket: WebSocket, raw_message: Any):
    try:
        message = ClientMessage.model_validate(raw_message)
    except:
        return
    client_id = get_client_identity(websocket)
    logger.info("Socket %s sent message %s", client_id, message.model_dump())
    if message.route == "broadcast":
        return await websocket_manager_2.broadcast(
            sender=client_id, type=message.type, data=message.data
        )
    elif message.route == "room":
        return await websocket_manager_2.room_message(
            target=message.target,
            sender=client_id,
            type=message.type,
            data=message.data,
        )
    elif message.route == "client":
        return await websocket_manager_2.direct_message(
            target=message.target,
            sender=client_id,
            type=message.type,
            data=message.data,
        )
    elif message.route == "control":
        return await client_controls(websocket=websocket, message=message)


websocket_manager_2.on(CLIENT_MESSAGE_EVENT, client_message_router)
