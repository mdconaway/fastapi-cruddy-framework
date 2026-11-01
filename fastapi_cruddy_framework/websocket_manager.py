from __future__ import annotations
from typing import Any, Literal
from collections.abc import Callable
from contextlib import asynccontextmanager
from logging import getLogger
from uuid import uuid4
from asyncio import CancelledError, Lock, Task, create_task, gather, shield
from contextvars import ContextVar
from json import dumps
from math import isfinite
from async_timeout import timeout
from pymitter import EventEmitter
from fastapi import WebSocket, WebSocketDisconnect
from .adapters import RedisAdapter
from .pubsub import PubSub
from ._websocket_connection import _Connection
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
_callback_manager: ContextVar[WebsocketConnectionManager | None] = ContextVar(
    "cruddy_websocket_callback_manager", default=None
)


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
        *,
        queue_capacity: int = 1024,
        send_timeout: float = 5.0,
        close_timeout: float = 1.0,
    ):
        if (
            isinstance(queue_capacity, bool)
            or not isinstance(queue_capacity, int)
            or queue_capacity <= 0
        ):
            raise ValueError("queue_capacity must be a positive integer")
        for name, value in (
            ("send_timeout", send_timeout),
            ("close_timeout", close_timeout),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value <= 0
            ):
                raise ValueError(f"{name} must be a finite positive number")
        self.accept_new = True
        self.emitter = EventEmitter()
        self.active_connections: list[WebSocket] = []
        self.custom_json_serializer = custom_json_serializer
        self.custom_client_identifier = custom_client_identifier
        self.room_configuration_object_key = room_configuration_object_key
        self.socket_id_attr = socket_id_attr
        self.connected_state_attr = connected_state_attr
        self.queue_capacity = queue_capacity
        self.send_timeout = send_timeout
        self.close_timeout = close_timeout
        self._connections: dict[WebSocket, _Connection] = {}
        self._closing_connections: dict[WebSocket, _Connection] = {}
        self._cleanup_tasks: set[Task] = set()
        self._startup_lock = Lock()
        self._started = False
        self._disposed = False
        self._dispose_task: Task | None = None
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
        self._pubsub_handlers = (
            (CONTROL_EVENT, self._handle_control_plane),
            (BROADCAST_EVENT, self._transmit),
            (ROOM_EVENT, self._route_to_room),
            (
                CLIENT_EVENT,
                (
                    self._route_to_client_id
                    if custom_client_identifier is not None
                    else self._route_to_socket_id
                ),
            ),
        )
        for event, handler in self._pubsub_handlers:
            self.pubsub_instance.on(event, handler)

    def on(self, *args, **kwargs):
        return self.emitter.on(*args, **kwargs)

    def off(self, *args, **kwargs):
        return self.emitter.off(*args, **kwargs)

    async def emit(self, *args, **kwargs):
        return await self.emitter.emit_async(*args, **kwargs)

    async def startup(self):
        async with self._startup_lock:
            if not self.accept_new or self._started:
                return
            await self.pubsub_instance.startup()
            self._started = True

    async def dispose(self):
        self.accept_new = False
        if self._disposed:
            return
        if self._dispose_task is None:
            self._dispose_task = create_task(self._dispose())
            self._dispose_task.add_done_callback(self._disposal_finished)
        if _callback_manager.get() is self:
            # Cleanup collects callbacks, so a callback cannot await full disposal.
            return
        await shield(self._dispose_task)

    def _disposal_finished(self, task: Task):
        self._dispose_task = None
        if not task.cancelled():
            task.exception()

    async def _dispose(self):
        try:
            for event, handler in self._pubsub_handlers:
                self.pubsub_instance.off(event, handler)
            self._pubsub_handlers = ()
            for connection in tuple(self._connections.values()):
                self._request_close(connection)
            try:
                await self.pubsub_instance.dispose()
            finally:
                while self._cleanup_tasks:
                    await gather(*tuple(self._cleanup_tasks), return_exceptions=True)
        finally:
            self.active_connections.clear()
            self._connections.clear()
            self._closing_connections.clear()
            self._disposed = True

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
        set_state(websocket, self.connected_state_attr, False)
        connection = _Connection(
            websocket,
            self.queue_capacity,
            self.send_timeout,
            self._request_close,
            disconnect_message_type,
            disconnect_message_data,
        )
        try:
            await websocket.accept()
        except (Exception, CancelledError):
            # ASGI may have accepted the transport before this await is cancelled.
            self._request_close(connection, notify=False)
            await shield(connection.cleanup_task)
            raise
        if not self.accept_new:
            self._request_close(connection, notify=False)
            await shield(connection.cleanup_task)
            raise RuntimeError("The websocket manager is shutting down")
        self._connections[websocket] = connection
        connection.writer_task = create_task(connection.write())
        set_state(websocket, self.connected_state_attr, True)
        self.active_connections.append(websocket)
        try:
            yield socket_id
            if not connection.closing:
                connection.receive_task = create_task(self._receive(connection))
                try:
                    await shield(connection.receive_task)
                except CancelledError:
                    if not connection.closing:
                        raise
        finally:
            self._request_close(connection)
            # The cleanup task never awaits this endpoint/context-manager task.
            if connection.cleanup_task is not None:
                await shield(connection.cleanup_task)

    async def _receive(self, connection: _Connection):
        websocket = connection.websocket
        token = _callback_manager.set(self)
        try:
            while not connection.closing and get_state(
                websocket, self.connected_state_attr, default=False
            ):
                data = await websocket.receive_json()
                if isinstance(data, dict):
                    await self.emit(CLIENT_MESSAGE_EVENT, websocket, data)
        except WebSocketDisconnect as e:
            logger.info("Websocket client disconnected %s", str(e))
            self._request_close(connection, close_transport=False)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.info(
                "Killing websocket client for sending malformed JSON or generally misbehaving"
            )
        finally:
            self._request_close(connection)
            _callback_manager.reset(token)

    async def send_json_to_socket(self, websocket: WebSocket, data: Any):
        """Send raw JSON through this socket's FIFO and await its local completion."""
        connection = self._connections.get(websocket)
        if connection is None:
            raise RuntimeError("Websocket is not connected to this manager")
        # Match WebSocket.send_json's default text encoding, without an envelope.
        await connection.send_local(
            dumps(data, separators=(",", ":"), ensure_ascii=False)
        )

    async def close_socket(
        self, websocket: WebSocket, code: int = 1000, reason: str | None = None
    ):
        """Await transport closure independently of receiving/disconnect callbacks."""
        connection = self._connections.get(websocket) or self._closing_connections.get(
            websocket
        )
        if connection is not None:
            self._request_close(connection, code=code, reason=reason)
            connection.close_waiters += 1
            connection.close_waiters_done.clear()
            try:
                await shield(connection.transport_closed)
            finally:
                connection.close_waiters -= 1
                if connection.close_waiters == 0:
                    connection.close_waiters_done.set()

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
        connection = self._connections.get(websocket)
        if connection is not None:
            self._request_close(connection)

    def _request_close(
        self,
        connection: _Connection,
        *,
        code: int = 1000,
        reason: str | None = None,
        close_transport: bool = True,
        notify: bool = True,
    ):
        """Unlink synchronously; transport and application callbacks run separately."""
        if connection.closing:
            return
        connection.closing = True
        connection.close_code = code
        connection.close_reason = reason
        connection.close_transport = close_transport
        websocket = connection.websocket
        self._connections.pop(websocket, None)
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        set_state(websocket, self.connected_state_attr, False)
        connection.discard_pending()
        self._closing_connections[websocket] = connection
        if notify:
            connection.notification_task = create_task(
                self._notify_disconnect(connection)
            )
        connection.cleanup_task = create_task(self._finish_connection(connection))
        self._cleanup_tasks.add(connection.cleanup_task)
        connection.cleanup_task.add_done_callback(self._cleanup_finished)

    def _cleanup_finished(self, task: Task):
        self._cleanup_tasks.discard(task)
        if not task.cancelled():
            error = task.exception()
            if error is not None:
                logger.warning("Websocket cleanup failed: %s", str(error))

    async def _notify_disconnect(self, connection: _Connection):
        token = _callback_manager.set(self)
        try:
            try:
                await self.emit(DISCONNECT_EVENT, connection.websocket)
            except Exception as error:  # pylint: disable=broad-exception-caught
                logger.warning("Websocket disconnect callback failed: %s", str(error))
            try:
                await self._eval_disconnect_settings(
                    connection.disconnect_message_type,
                    connection.disconnect_message_data,
                )
            except Exception as error:  # pylint: disable=broad-exception-caught
                logger.warning("Websocket disconnect broadcast failed: %s", str(error))
        finally:
            connection.disconnect_message_type = None
            connection.disconnect_message_data = None
            _callback_manager.reset(token)

    async def _finish_connection(self, connection: _Connection):
        try:
            if connection.writer_task is not None:
                connection.writer_task.cancel()
                await gather(connection.writer_task, return_exceptions=True)
            try:
                if connection.close_transport:
                    async with timeout(self.close_timeout):
                        await connection.websocket.close(
                            code=connection.close_code, reason=connection.close_reason
                        )
            except Exception as error:  # pylint: disable=broad-exception-caught
                logger.info("Websocket transport close failed: %s", str(error))
            finally:
                if not connection.transport_closed.done():
                    connection.transport_closed.set_result(None)
            # A close helper inside a handler must finish before we cancel the
            # surrounding receiving operation. Coordinate explicitly rather
            # than relying on a particular number of event-loop checkpoints.
            await connection.close_waiters_done.wait()
            if connection.receive_task is not None:
                connection.receive_task.cancel()
                await gather(connection.receive_task, return_exceptions=True)
            if connection.notification_task is not None:
                await connection.notification_task
        finally:
            connection.discard_pending()
            connection.writer_task = None
            connection.receive_task = None
            connection.notification_task = None
            connection.cleanup_task = None
            self._closing_connections.pop(connection.websocket, None)

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
        for socket in tuple(sockets):
            connection = self._connections.get(socket)
            if connection is not None:
                self._request_close(connection)

    def _join_sockets(self, sockets: list[WebSocket], room_id: str):
        for socket in sockets:
            room_config = self.get_room_config(socket)
            room_config.room_list.add(room_id)

    def _leave_sockets(self, sockets: list[WebSocket], room_id: str):
        for socket in sockets:
            room_config = self.get_room_config(socket)
            room_config.room_list.remove(room_id)

    async def _send_to_sockets(self, sockets: list[WebSocket], message: str):
        for socket in tuple(sockets):
            connection = self._connections.get(socket)
            if connection is not None:
                connection.enqueue(message)

    async def _transmit(self, message: SocketMessage):
        await self._send_to_sockets(
            sockets=self.active_connections,
            message=self.generate_client_message(
                BROADCAST_EVENT,
                None,
                message.sender,
                message.type,
                self.custom_json_serializer(message.data),
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
                self.custom_json_serializer(message.data),
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
                self.custom_json_serializer(message.data),
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
                self.custom_json_serializer(message.data),
            ),
        )
