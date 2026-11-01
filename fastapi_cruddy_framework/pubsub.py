from __future__ import annotations
from logging import getLogger
from pickle import dumps, loads, HIGHEST_PROTOCOL
from contextvars import ContextVar
from asyncio import (
    sleep,
    TimeoutError as _TimeoutError,
    create_task,
    current_task,
    gather,
    get_running_loop,
    shield,
    CancelledError,
    Future,
    Task,
)
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
_dispatching = ContextVar("cruddy_pubsub_dispatch", default=None)


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
        self._ready: Future | None = None
        self._dispose_task: Task | None = None

    async def startup(self):
        if not self.keep_reading:
            return
        if self._dispose_task is not None:
            # A cancelled startup may still be collecting its previous reader.
            await shield(self._dispose_task)
            if not self.keep_reading:
                return
        if self.task is None:
            self._ready = get_running_loop().create_future()
            self.task = create_task(self.read())
            self.task.add_done_callback(self._reader_finished)
        try:
            await shield(self._ready)
        except CancelledError:
            # Cancellation abandons this startup, not the reusable subscriber.
            # Concurrent starters share and collect the same stopping reader.
            if self._dispose_task is None:
                self._dispose_task = create_task(self._stop_reader())
            await shield(self._dispose_task)
            raise

    @staticmethod
    def _reader_finished(task: Task):
        if not task.cancelled() and task.exception() is not None:
            logger.warning("PubSub reader exited abnormally: %s", task.exception())

    async def read(self):
        try:
            async with self.psub as p:
                # Redis subscribe() writes the command; the matching response
                # proves the subscription is active before startup returns.
                async with timeout(2):
                    await p.subscribe(self.channel)
                    while True:
                        acknowledgement = await p.get_message(
                            ignore_subscribe_messages=False, timeout=1.0
                        )
                        if (
                            acknowledgement is not None
                            and acknowledgement.get("type") == "subscribe"
                            and acknowledgement.get("channel")
                            in (self.channel, self.channel.encode("utf-8"))
                        ):
                            break
                        await sleep(0)
                self.p = p
                if self._ready is not None and not self._ready.done():
                    self._ready.set_result(None)
                try:
                    while self.keep_reading:
                        try:
                            # Bound only the idle read. Never cancel routing
                            # halfway through selecting a message's recipients.
                            async with timeout(2):
                                message: dict | None = await p.get_message(
                                    ignore_subscribe_messages=True, timeout=1.0
                                )
                        except _TimeoutError:
                            continue
                        if message is not None:
                            token = _dispatching.set(self)
                            try:
                                await self.route_message(loads(message.get("data", "")))
                            except Exception as error:  # pylint: disable=W0718
                                logger.info(msg=str(error))
                            finally:
                                _dispatching.reset(token)
                                # An idle subscriber must not retain the last
                                # message or its application payload.
                                message = None
                        # Buffered reads and synchronous callbacks can complete
                        # immediately. Yield without throttling ready messages.
                        await sleep(0)
                finally:
                    async with timeout(2):
                        await p.unsubscribe(self.channel)
        except BaseException as error:
            if self._ready is not None and not self._ready.done():
                self._ready.set_exception(error)
            raise
        finally:
            self.p = None
            if self.task is current_task():
                self.task = None
                self._ready = None

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

    async def dispose(self):
        self.keep_reading = False
        if self._dispose_task is None:
            self._dispose_task = create_task(self._stop_reader())
        # Handlers (including their background work) can request cleanup, but
        # cannot await a reader that is waiting for that handler to finish.
        if _dispatching.get() is self:
            return
        await shield(self._dispose_task)

    async def _stop_reader(self):
        if self._ready is not None and not self._ready.done():
            self._ready.cancel()
        task = self.task
        if task is not None:
            task.cancel()
            await gather(task, return_exceptions=True)
        self.task = None
        self._ready = None
        self._dispose_task = None
