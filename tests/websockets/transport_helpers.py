"""Controllable transport boundaries, without a test client's unbounded buffers."""

import asyncio
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import WebSocketDisconnect
from pymitter import EventEmitter


class LocalPubSub:
    """Dispatch publication sequentially; keep socket I/O separately controllable."""

    def __init__(self):
        self.emitter = EventEmitter()
        self.messages = []
        self.startups = 0
        self.disposals = 0
        self.start_error = None
        self.dispose_error = None

    def on(self, *args, **kwargs):
        return self.emitter.on(*args, **kwargs)

    def off(self, *args, **kwargs):
        return self.emitter.off(*args, **kwargs)

    async def startup(self):
        self.startups += 1
        if self.start_error:
            raise self.start_error

    async def dispose(self):
        self.disposals += 1
        if self.dispose_error:
            raise self.dispose_error

    async def publish(self, message):
        self.messages.append(message)
        await self.emitter.emit_async(message.route, message)


class ControlledSocket:
    """A socket whose send, close, accept and receive boundaries can be gated."""

    def __init__(self, *, send_blocked=False, close_blocked=False):
        self.state = SimpleNamespace()
        self.incoming = asyncio.Queue()
        self.delivered = asyncio.Queue()
        self.sent = []
        self.close_calls = []
        self.accepted = asyncio.Event()
        self.accept_gate = asyncio.Event()
        self.accept_gate.set()
        self.send_started = asyncio.Event()
        self.close_started = asyncio.Event()
        self.send_cancelled = asyncio.Event()
        self.receive_cancelled = asyncio.Event()
        self.send_gate = asyncio.Event()
        self.close_gate = asyncio.Event()
        if not send_blocked:
            self.send_gate.set()
        if not close_blocked:
            self.close_gate.set()
        self.send_error = None
        self.close_error = None
        self.accept_error = None
        self.sending = 0
        self.max_sending = 0

    async def accept(self):
        self.accepted.set()
        await self.accept_gate.wait()
        if self.accept_error:
            raise self.accept_error

    async def receive_json(self):
        try:
            item = await self.incoming.get()
        except asyncio.CancelledError:
            self.receive_cancelled.set()
            raise
        if isinstance(item, BaseException):
            raise item
        return item

    async def send_text(self, text):
        self.sending += 1
        self.max_sending = max(self.max_sending, self.sending)
        self.send_started.set()
        try:
            await self.send_gate.wait()
            if self.send_error:
                raise self.send_error
            self.sent.append(text)
            self.delivered.put_nowait(json.loads(text))
        except asyncio.CancelledError:
            self.send_cancelled.set()
            raise
        finally:
            self.sending -= 1

    async def close(self, code=1000, reason=None):
        self.close_calls.append((code, reason))
        self.close_started.set()
        await self.close_gate.wait()
        if self.close_error:
            raise self.close_error
        self.incoming.put_nowait(WebSocketDisconnect(code))


async def checkpoint():
    """Let already runnable work execute without imposing a throughput delay."""
    await asyncio.sleep(0)


async def reached(event):
    """A test deadlock guard, not a performance acceptance threshold."""
    await asyncio.wait_for(event.wait(), timeout=3)


async def received(socket, count=1):
    return [
        await asyncio.wait_for(socket.delivered.get(), timeout=3) for _ in range(count)
    ]


async def open_socket(manager, socket, socket_id=None, setup=None, **kwargs):
    ready = asyncio.get_running_loop().create_future()

    async def endpoint():
        try:
            async with manager.connect(
                socket, override_socket_id=socket_id, **kwargs
            ) as assigned:
                if setup:
                    setup(socket)
                ready.set_result(assigned)
        except BaseException as exc:
            if not ready.done():
                ready.set_exception(exc)
            raise

    task = asyncio.create_task(endpoint())
    assigned = await asyncio.wait_for(ready, timeout=3)
    return assigned, task


@asynccontextmanager
async def managed(manager):
    """Always collect the manager's work, including when an assertion fails."""
    await manager.startup()
    try:
        yield manager
    finally:
        await manager.dispose()


async def finished(task):
    await asyncio.wait_for(task, timeout=3)
