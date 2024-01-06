from __future__ import annotations
from logging import getLogger
from pickle import dumps, loads, HIGHEST_PROTOCOL
from asyncio import sleep, TimeoutError as _TimeoutError, create_task, Task
from async_timeout import timeout
from pymitter import EventEmitter
from redis.asyncio.client import PubSub as _PubSub
from .adapters import RedisAdapter
from .schemas import (
    SocketMessage,
    BROADCAST_EVENT,
    CONTROL_EVENT,
    ROOM_EVENT,
    CLIENT_EVENT,
)

logger = getLogger(__name__)


class PubSub:
    psub: _PubSub
    redis_client: RedisAdapter
    channel: str
    task: Task | None
    emitter: EventEmitter
    keep_reading: bool
    p: _PubSub | None

    def __init__(self, channel: str, redis_client: RedisAdapter):
        self.p = None
        self.emitter = EventEmitter()
        self.redis_client = redis_client
        self.psub = redis_client.get_client().pubsub()
        self.channel = channel
        self.keep_reading = True
        self.task = None

    async def startup(self):
        try:
            self.task = create_task(self.read())
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Unable to spawn pubsub read loop |%s|", e)

    async def read(self):
        async with self.psub as p:
            await p.subscribe(self.channel)
            self.p = p
            while self.keep_reading:
                try:
                    async with timeout(2):
                        message: dict | None = await p.get_message(
                            ignore_subscribe_messages=True
                        )
                        if message is not None:
                            try:
                                socket_message: SocketMessage = loads(
                                    message.get("data", "")
                                )
                                await self.route_message(socket_message)
                            except (
                                Exception  # pylint: disable=broad-exception-caught
                            ) as e:
                                logger.info(msg=str(e))
                        await sleep(0.01)
                except _TimeoutError:
                    pass
            await self.p.unsubscribe(self.channel)
            self.p = None

    async def publish(self, message: SocketMessage):
        publisher = self.redis_client.get_client()
        await publisher.publish(
            channel=self.channel, message=dumps(obj=message, protocol=HIGHEST_PROTOCOL)
        )

    async def route_message(self, socket_message: SocketMessage):
        if socket_message.route in [
            BROADCAST_EVENT,
            CONTROL_EVENT,
            ROOM_EVENT,
            CLIENT_EVENT,
        ]:
            return await self.emit(socket_message.route, socket_message)
        raise ValueError(
            f"Socket message contained route: {socket_message.route}, which is not a valid routing value"
        )

    async def emit(self, *args, **kwargs):
        return await self.emitter.emit_async(*args, **kwargs)

    def on(self, *args, **kwargs):
        return self.emitter.on(*args, **kwargs)

    def off(self, *args, **kwargs):
        return self.emitter.off(*args, **kwargs)

    # During tests, the task could enter its own run loop, catch the error
    async def dispose(self):
        self.keep_reading = False
        if self.task is not None:
            try:
                await self.task
            except RuntimeError:
                logger.warning("PubSub exited abnormally")
