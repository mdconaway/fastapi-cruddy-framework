"""Private, bounded output owned by one websocket connection."""

from __future__ import annotations

from asyncio import (
    CancelledError,
    Event,
    Future,
    Queue,
    QueueEmpty,
    QueueFull,
    Task,
    TimeoutError as _TimeoutError,
    get_running_loop,
    sleep,
)
from collections.abc import Callable
from async_timeout import timeout
from fastapi import WebSocket


class _LocalMessage:
    """Only local callers need an individual completion and cancellation state."""

    def __init__(self, payload: str):
        self.payload: str | None = payload
        self.completion: Future[None] = get_running_loop().create_future()
        self.started = False
        self.cancelled = False


class _Connection:
    """One FIFO and one writer; callbacks request cleanup without awaiting it."""

    def __init__(
        self,
        websocket: WebSocket,
        capacity: int,
        send_timeout: float,
        request_close: Callable[..., None],
        disconnect_message_type: str | None = None,
        disconnect_message_data: dict | None = None,
    ):
        self.websocket = websocket
        self.queue: Queue[str | _LocalMessage] = Queue(maxsize=capacity)
        self.send_timeout = send_timeout
        self.request_close = request_close
        self.closing = False
        self.close_code = 1000
        self.close_reason: str | None = None
        self.close_transport = True
        self.transport_closed: Future[None] = get_running_loop().create_future()
        self.close_waiters = 0
        self.close_waiters_done = Event()
        self.close_waiters_done.set()
        self.writer_task: Task | None = None
        self.receive_task: Task | None = None
        self.notification_task: Task | None = None
        self.cleanup_task: Task | None = None
        self.current: str | _LocalMessage | None = None
        self.disconnect_message_type = disconnect_message_type
        self.disconnect_message_data = disconnect_message_data

    def enqueue(self, message: str | _LocalMessage) -> bool:
        """Admission cannot wait on a recipient, including an overflowing one."""
        if self.closing:
            return False
        try:
            self.queue.put_nowait(message)
        except QueueFull:
            self.request_close(self, code=1013, reason="Outgoing queue is full")
            return False
        return True

    async def send_local(self, payload: str):
        message = _LocalMessage(payload)
        if not self.enqueue(message):
            message.completion.cancel()
            raise RuntimeError("Websocket is closed or its outgoing queue is full")
        try:
            # This deadline covers both admission-to-send waiting and transport I/O.
            async with timeout(self.send_timeout):
                await message.completion
        except CancelledError:
            message.cancelled = True
            if message.started and self.current is message:
                self.request_close(
                    self, code=1011, reason="Outgoing send was cancelled"
                )
            raise
        except _TimeoutError:
            message.cancelled = True
            self.request_close(self, code=1013, reason="Outgoing send timed out")
            raise
        finally:
            message.payload = None

    @staticmethod
    def _fail_local(message: str | _LocalMessage):
        if isinstance(message, _LocalMessage):
            if not message.completion.done():
                message.completion.set_exception(RuntimeError("Websocket closed"))
            message.payload = None

    def discard_pending(self):
        """Release all queued payloads and settle local callers on termination."""
        while True:
            try:
                message = self.queue.get_nowait()
            except QueueEmpty:
                break
            self._fail_local(message)
            self.queue.task_done()
        if self.current is not None:
            self._fail_local(self.current)

    async def write(self):
        message: str | _LocalMessage | None = None
        payload: str | None = None
        try:
            while not self.closing:
                message = await self.queue.get()
                self.current = message
                try:
                    if isinstance(message, _LocalMessage):
                        cancelled = message.cancelled or message.completion.cancelled()
                        if not cancelled:
                            message.started = True
                            payload = message.payload
                    else:
                        cancelled = False
                        payload = message
                    if not cancelled:
                        async with timeout(self.send_timeout):
                            await self.websocket.send_text(payload)
                        if isinstance(message, _LocalMessage):
                            if not message.completion.done():
                                message.completion.set_result(None)
                finally:
                    self.queue.task_done()
                    self.current = None
                    if isinstance(message, _LocalMessage):
                        self._fail_local(message)
                    message = None
                    payload = None
                # Ready Queue.get/send coroutines are not guaranteed to suspend.
                await sleep(0)
        except CancelledError:
            if not self.closing:
                self.request_close(self, code=1011, reason="Outgoing writer stopped")
            raise
        except Exception:  # pylint: disable=broad-exception-caught
            self.request_close(self, code=1011, reason="Outgoing send failed")
        finally:
            self.current = None
            message = None
            payload = None
            self.discard_pending()
