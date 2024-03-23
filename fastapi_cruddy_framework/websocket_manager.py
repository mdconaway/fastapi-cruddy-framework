from __future__ import annotations
from typing import Any, Literal
from collections.abc import Callable
from contextlib import asynccontextmanager
from logging import getLogger
from uuid import uuid4
from asyncio import gather
from json import dumps
from pymitter import EventEmitter
from fastapi import WebSocket, WebSocketDisconnect
from .adapters import RedisAdapter
from .pubsub import PubSub
from .schemas import (
    SocketMessage,
    SocketRoomConfiguration,
    BROADCAST_EVENT,
    CLIENT_EVENT,
    ROOM_EVENT,
    CONTROL_EVENT,
    KILL_SOCKET_BY_ID,
    KILL_SOCKET_BY_CLIENT,
    KILL_ROOM_BY_ID,
    JOIN_SOCKET_BY_ID,
    JOIN_SOCKET_BY_CLIENT,
    LEAVE_SOCKET_BY_ID,
    LEAVE_SOCKET_BY_CLIENT,
    CLIENT_MESSAGE_EVENT,
    DISCONNECT_EVENT,
)
from .util import to_json_object, get_state, set_state

logger = getLogger(__name__)


class WebsocketConnectionManager:
    pubsub_instance: PubSub
    active_connections: list[WebSocket]
    emitter: EventEmitter
    accept_new: bool
    custom_client_identifier: Callable | None
    custom_json_serializer: Callable
    room_configuration_object_key: str
    socket_id_attr: str
    connected_state_attr: str

    def __init__(
        self,
        pubsub_instance: PubSub | None = None,
        redis_mode: Literal["redis"] | Literal["memory"] = "redis",
        redis_adapter: RedisAdapter | None = None,
        redis_channel: str = "websockets",
        redis_host: str = "redis",
        redis_port: int = 6379,
        redis_max_connections: int = 10000,
        custom_json_serializer: Callable = to_json_object,
        connected_state_attr: str = "is_connected",
        socket_id_attr: str = "socket_id",
        custom_client_identifier: Callable | None = None,
        room_configuration_object_key: str = "rooms",
    ):
        self.accept_new = True
        self.emitter = EventEmitter()
        self.active_connections: list[WebSocket] = []
        self.custom_json_serializer = custom_json_serializer
        self.custom_client_identifier = custom_client_identifier
        self.room_configuration_object_key = room_configuration_object_key
        self.socket_id_attr = socket_id_attr
        self.connected_state_attr = connected_state_attr
        if pubsub_instance is None:
            if redis_adapter is None:
                redis_adapter = RedisAdapter(
                    mode=redis_mode,
                    redis_host=redis_host,
                    redis_port=redis_port,
                    redis_max_connections=redis_max_connections,
                )
            self.pubsub_instance = PubSub(
                channel=redis_channel, redis_client=redis_adapter
            )
        else:
            self.pubsub_instance = pubsub_instance
        self.pubsub_instance.on(CONTROL_EVENT, self._handle_control_plane)
        self.pubsub_instance.on(BROADCAST_EVENT, self._transmit)
        self.pubsub_instance.on(ROOM_EVENT, self._route_to_room)
        if custom_client_identifier is not None:
            self.pubsub_instance.on(CLIENT_EVENT, self._route_to_client_id)
        else:
            self.pubsub_instance.on(CLIENT_EVENT, self._route_to_socket_id)

    def on(self, *args, **kwargs):
        return self.emitter.on(*args, **kwargs)

    def off(self, *args, **kwargs):
        return self.emitter.off(*args, **kwargs)

    async def emit(self, *args, **kwargs):
        return await self.emitter.emit_async(*args, **kwargs)

    async def startup(self):
        if self.accept_new:
            await self.pubsub_instance.startup()

    async def dispose(self):
        self.accept_new = False
        await self.pubsub_instance.dispose()
        await self._kill_sockets(sockets=self.active_connections)
        self.active_connections = []

    @asynccontextmanager
    async def connect(
        self,
        websocket: WebSocket,
        override_socket_id: str | None = None,
        disconnect_message_type: str | None = None,
        disconnect_message_data: dict | None = None,
    ):
        if not self.accept_new:
            raise RuntimeError(
                "The WebsocketConnectionManager instance is shutting down and not accepting new connections"
            )
        socket_id = str(uuid4()) if override_socket_id is None else override_socket_id
        set_state(websocket, self.socket_id_attr, socket_id)
        set_state(
            websocket,
            self.room_configuration_object_key,
            SocketRoomConfiguration(room_list=set()),
        )
        set_state(websocket, self.connected_state_attr, True)
        await websocket.accept()
        self.active_connections.append(websocket)
        yield socket_id
        try:
            while get_state(websocket, self.connected_state_attr, default=False):
                data = await websocket.receive_json()
                if isinstance(data, dict):
                    await self.emit(CLIENT_MESSAGE_EVENT, websocket, data)
        except WebSocketDisconnect as e:
            await self._unlink_socket(websocket)
            logger.info("Websocket client %s disconnected %s", socket_id, str(e))
            await self._eval_disconnect_settings(
                disconnect_message_type, disconnect_message_data
            )
            return
        except Exception:
            logger.info(
                "Killing websocket client %s for sending malformed JSON or generally misbehaving",
                socket_id,
            )
        await self._unlink_socket(websocket)
        logger.info("Websocket client %s force closed", socket_id)
        await websocket.close()
        await self._eval_disconnect_settings(
            disconnect_message_type, disconnect_message_data
        )

    async def broadcast(  # pylint: disable=redefined-builtin
        self,
        target: str | None = None,
        sender: str | None = None,
        type: str = "",
        data: dict | None = {},
    ):
        await self.send_message_raw(
            message=SocketMessage(
                route=BROADCAST_EVENT,
                target=target,
                sender=sender,
                type=type,
                data=data,
            )
        )

    async def direct_message(
        self,
        target: str | None = None,
        sender: str | None = None,
        type: str = "",
        data: dict | None = {},
    ):
        await self.send_message_raw(
            message=SocketMessage(
                route=CLIENT_EVENT,
                target=target,
                sender=sender,
                type=type,
                data=data,
            )
        )

    async def room_message(
        self,
        target: str | None = None,
        sender: str | None = None,
        type: str = "",
        data: dict | None = {},
    ):
        await self.send_message_raw(
            message=SocketMessage(
                route=ROOM_EVENT,
                target=target,
                sender=sender,
                type=type,
                data=data,
            )
        )

    def get_room_config(self, socket: WebSocket):
        room_config: SocketRoomConfiguration = get_state(
            socket,
            self.room_configuration_object_key,
            default=SocketRoomConfiguration(room_list=set()),
        )
        return room_config

    def get_sockets_by_id(self, id: str):
        sockets: list[WebSocket] = []
        for socket in self.active_connections:
            if get_state(socket, self.socket_id_attr, default="") == id:
                sockets.append(socket)
        return sockets

    def get_sockets_by_client_id(self, id: str):
        sockets: list[WebSocket] = []
        for socket in self.active_connections:
            if self._exec_custom_getter(socket) == id:
                sockets.append(socket)
        return sockets

    def get_sockets_by_room(self, room_id: str):
        sockets: list[WebSocket] = []
        for socket in self.active_connections:
            room_config = self.get_room_config(socket)
            if room_id in room_config.room_list:
                sockets.append(socket)
        return sockets

    def get_room_list(self) -> set[str]:
        rooms = set()
        for socket in self.active_connections:
            room_config = self.get_room_config(socket)
            rooms.update(room_config.room_list)
        return rooms

    async def join_room_by_socket_id(self, id: str, room_id: str):
        await self.send_control_message(
            message=SocketMessage(
                route=CONTROL_EVENT,
                type=JOIN_SOCKET_BY_ID,
                target=id,
                sender=room_id,
                data=None,
            )
        )

    async def join_room_by_client_id(self, id: str, room_id: str):
        await self.send_control_message(
            message=SocketMessage(
                route=CONTROL_EVENT,
                type=JOIN_SOCKET_BY_CLIENT,
                target=id,
                sender=room_id,
                data=None,
            )
        )

    async def leave_room_by_socket_id(self, id: str, room_id: str):
        await self.send_control_message(
            message=SocketMessage(
                route=CONTROL_EVENT,
                type=LEAVE_SOCKET_BY_ID,
                target=id,
                sender=room_id,
                data=None,
            )
        )

    async def leave_room_by_client_id(self, id: str, room_id: str):
        await self.send_control_message(
            message=SocketMessage(
                route=CONTROL_EVENT,
                type=LEAVE_SOCKET_BY_CLIENT,
                target=id,
                sender=room_id,
                data=None,
            )
        )

    async def kill_sockets_by_socket_id(self, id: str):
        await self.send_control_message(
            message=SocketMessage(
                route=CONTROL_EVENT, type=KILL_SOCKET_BY_ID, target=id, data=None
            )
        )

    async def kill_sockets_by_client_id(self, id: str):
        await self.send_control_message(
            message=SocketMessage(
                route=CONTROL_EVENT,
                type=KILL_SOCKET_BY_CLIENT,
                target=id,
                data=None,
            )
        )

    async def kill_room_by_id(self, room_id: str):
        await self.send_control_message(
            message=SocketMessage(
                route=CONTROL_EVENT,
                type=KILL_ROOM_BY_ID,
                target=room_id,
                data=None,
            )
        )

    async def send_control_message(self, message: SocketMessage):
        message.route = CONTROL_EVENT
        await self.send_message_raw(message=message)

    async def send_message_raw(self, message: SocketMessage):
        await self.pubsub_instance.publish(message=message)

    def generate_client_message(
        self,
        route: str,
        target: str | None,
        sender: str | None,
        type: str | None,
        data: Any,
    ):
        return dumps(
            {
                "route": route,
                "target": target,
                "sender": sender,
                "type": type,
                "data": data,
            }
        )

    async def _eval_disconnect_settings(
        self,
        disconnect_message_type: str | None = None,
        disconnect_message_data: dict | None = None,
    ):
        if disconnect_message_type is not None and disconnect_message_data is not None:
            await self.broadcast(
                type=disconnect_message_type, data=disconnect_message_data
            )

    async def _unlink_socket(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        await self.emit(DISCONNECT_EVENT, websocket)

    def _exec_custom_getter(self, socket: WebSocket):
        if self.custom_client_identifier is not None:
            return self.custom_client_identifier(socket)
        return ""

    async def _handle_control_plane(self, message: SocketMessage):
        if KILL_SOCKET_BY_ID == message.type:
            return await self._kill_sockets(
                self.get_sockets_by_id(id=str(message.target))
            )
        elif KILL_SOCKET_BY_CLIENT == message.type:
            return await self._kill_sockets(
                self.get_sockets_by_client_id(id=str(message.target))
            )
        elif KILL_ROOM_BY_ID == message.type:
            return await self._kill_sockets(
                self.get_sockets_by_room(room_id=str(message.target))
            )
        elif JOIN_SOCKET_BY_ID == message.type:
            return self._join_sockets(
                sockets=self.get_sockets_by_id(id=str(message.target)),
                room_id=str(message.sender),
            )
        elif JOIN_SOCKET_BY_CLIENT == message.type:
            return self._join_sockets(
                sockets=self.get_sockets_by_client_id(id=str(message.target)),
                room_id=str(message.sender),
            )
        elif LEAVE_SOCKET_BY_ID == message.type:
            return self._leave_sockets(
                sockets=self.get_sockets_by_id(id=str(message.target)),
                room_id=str(message.sender),
            )
        elif LEAVE_SOCKET_BY_CLIENT == message.type:
            return self._leave_sockets(
                sockets=self.get_sockets_by_client_id(id=str(message.target)),
                room_id=str(message.sender),
            )
        # unhandled control messages are probably custom, so emit them
        return await self.emit(CONTROL_EVENT, message)

    async def _kill_sockets(self, sockets: list[WebSocket]):
        for socket in sockets:
            set_state(socket, self.connected_state_attr, False)
            await socket.close()

    def _join_sockets(self, sockets: list[WebSocket], room_id: str):
        for socket in sockets:
            room_config = self.get_room_config(socket)
            room_config.room_list.add(room_id)

    def _leave_sockets(self, sockets: list[WebSocket], room_id: str):
        for socket in sockets:
            room_config = self.get_room_config(socket)
            room_config.room_list.remove(room_id)

    async def _send_to_sockets(self, sockets: list[WebSocket], message: str):
        awaitables = [connection.send_text(message) for connection in sockets]
        await gather(*awaitables, return_exceptions=True)

    async def _transmit(self, message: SocketMessage):
        await self._send_to_sockets(
            sockets=self.active_connections,
            message=self.generate_client_message(
                BROADCAST_EVENT,
                None,
                message.sender,
                message.type,
                to_json_object(message.data),
            ),
        )

    async def _route_to_socket_id(self, message: SocketMessage):
        sockets = self.get_sockets_by_id(id=str(message.target))
        if len(sockets) == 0:
            return
        await self._send_to_sockets(
            sockets=sockets,
            message=self.generate_client_message(
                CLIENT_EVENT,
                message.target,
                message.sender,
                message.type,
                to_json_object(message.data),
            ),
        )

    async def _route_to_client_id(self, message: SocketMessage):
        sockets = self.get_sockets_by_client_id(id=str(message.target))
        if len(sockets) == 0:
            return
        await self._send_to_sockets(
            sockets=sockets,
            message=self.generate_client_message(
                CLIENT_EVENT,
                message.target,
                message.sender,
                message.type,
                to_json_object(message.data),
            ),
        )

    async def _route_to_room(self, message: SocketMessage):
        sockets = self.get_sockets_by_room(room_id=str(message.target))
        if len(sockets) == 0:
            return
        await self._send_to_sockets(
            sockets=sockets,
            message=self.generate_client_message(
                ROOM_EVENT,
                message.target,
                message.sender,
                message.type,
                to_json_object(message.data),
            ),
        )
