"""Readiness, cooperative draining and lifetime of the shared broker reader."""

import asyncio
from asyncio import TimeoutError
import gc
import pickle
import weakref
from types import SimpleNamespace

import pytest
from fakeredis import FakeServer
from fakeredis.aioredis import FakeRedis

import fastapi_cruddy_framework.pubsub as pubsub_module
from fastapi_cruddy_framework import PubSub, SocketMessage, WebsocketConnectionManager

pytestmark = pytest.mark.anyio


class Subscription:
    def __init__(self):
        self.messages = asyncio.Queue()
        self.subscribed = asyncio.Event()
        self.subscribe_gate = None
        self.subscribe_error = None
        self.read_error = None
        self.unsubscribe_error = None
        self.reads = []
        self.unsubscribed = []
        self.exited = False
        self.ack_pending = False
        self.before_ack = []
        self.exit_gate = None
        self.exiting = asyncio.Event()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        self.exiting.set()
        if self.exit_gate is not None:
            await self.exit_gate.wait()
        self.exited = True

    async def subscribe(self, channel):
        if self.subscribe_gate is not None:
            await self.subscribe_gate.wait()
        if self.subscribe_error is not None:
            raise self.subscribe_error
        self.subscribed.set()
        self.ack_pending = True

    async def unsubscribe(self, channel):
        self.unsubscribed.append(channel)
        if self.unsubscribe_error is not None:
            raise self.unsubscribe_error

    async def get_message(self, **kwargs):
        self.reads.append(kwargs)
        if self.before_ack:
            return self.before_ack.pop(0)
        if self.ack_pending:
            self.ack_pending = False
            return {"type": "subscribe", "channel": b"test", "data": 1}
        if self.read_error is not None:
            error, self.read_error = self.read_error, None
            raise error
        return await self.messages.get()


class Client:
    def __init__(self, subscription):
        self.subscription = subscription
        self.published = []

    def pubsub(self):
        return self.subscription

    async def publish(self, channel, message):
        self.published.append((channel, message))
        self.subscription.messages.put_nowait({"data": message})


def make_pubsub():
    subscription = Subscription()
    client = Client(subscription)
    pubsub = PubSub("test", SimpleNamespace(get_client=lambda: client))
    return pubsub, subscription, client


async def drain_loop():
    # Scheduling turns, not a wall-clock throughput threshold.
    for _ in range(5):
        await asyncio.sleep(0)


async def test_startup_waits_for_subscription_and_is_idempotent():
    pubsub, subscription, _ = make_pubsub()
    subscription.subscribe_gate = asyncio.Event()
    first = asyncio.create_task(pubsub.startup())
    second = asyncio.create_task(pubsub.startup())
    await drain_loop()
    assert not first.done() and not second.done()
    reader = pubsub.task
    subscription.subscribe_gate.set()
    await asyncio.gather(first, second)
    assert pubsub.task is reader
    assert pubsub.p is subscription
    assert subscription.reads == [
        {"ignore_subscribe_messages": False, "timeout": 1.0},
        {"ignore_subscribe_messages": True, "timeout": 1.0},
    ]
    await pubsub.dispose()
    await pubsub.dispose()
    await pubsub.startup()
    assert pubsub.task is None and pubsub.p is None and pubsub._ready is None
    assert subscription.exited and subscription.unsubscribed == ["test"]


async def test_backlog_drains_in_order_without_timed_sleep(monkeypatch):
    pubsub, subscription, client = make_pubsub()
    seen = []
    finished = asyncio.Event()
    delays = []
    real_sleep = asyncio.sleep

    async def yield_only(delay):
        delays.append(delay)
        assert delay == 0
        await real_sleep(0)

    async def received(message):
        seen.append(message.data["seq"])
        if len(seen) == 501:
            finished.set()

    monkeypatch.setattr(pubsub_module, "sleep", yield_only)
    pubsub.on("broadcast", received)
    await pubsub.startup()
    for seq in range(501):
        await pubsub.publish(SocketMessage(data={"seq": seq}))
    await asyncio.wait_for(finished.wait(), 5)
    assert seen == list(range(501))
    assert len(client.published) == 501
    assert isinstance(pickle.loads(client.published[0][1]), SocketMessage)
    await pubsub.dispose()
    assert len(delays) >= 500
    assert subscription.exited


async def test_ready_reads_without_handlers_still_yield_to_other_tasks():
    pubsub, subscription, _ = make_pubsub()
    for _ in range(100):
        subscription.messages.put_nowait(
            {"data": pickle.dumps(SocketMessage(data={"seq": 1}))}
        )
    turns = []
    running = True

    async def tick():
        while running:
            turns.append(len(subscription.reads))
            await asyncio.sleep(0)

    ticker = asyncio.create_task(tick())
    await pubsub.startup()
    while len(subscription.reads) < 102:
        await asyncio.sleep(0)
    running = False
    await ticker
    await pubsub.dispose()
    assert any(0 < count < 100 for count in turns)


async def test_bad_payload_route_and_callback_do_not_stop_reader():
    pubsub, subscription, _ = make_pubsub()
    received = asyncio.Event()

    async def handler(message):
        if message.type == "bad_callback":
            raise ValueError("callback failed")
        received.set()

    pubsub.on("broadcast", handler)
    for payload in [
        b"not-pickle",
        pickle.dumps(SocketMessage(route="invalid")),
        pickle.dumps(SocketMessage(type="bad_callback")),
        pickle.dumps(SocketMessage(type="good")),
    ]:
        subscription.messages.put_nowait({"data": payload})
    subscription.read_error = TimeoutError()
    await pubsub.startup()
    await asyncio.wait_for(received.wait(), 5)
    assert not pubsub.task.done()
    await pubsub.dispose()
    with pytest.raises(ValueError, match="not a valid routing"):
        await pubsub.route_message(SocketMessage(route="wrong"))


async def test_event_delegates_preserve_routes_and_arguments():
    pubsub, _, _ = make_pubsub()
    seen = []

    async def handler(*args, **kwargs):
        seen.append((args, kwargs))

    for route in ["broadcast", "control", "room", "client"]:
        pubsub.on(route, handler)
        message = SocketMessage(route=route)
        await pubsub.route_message(message)
        assert seen[-1] == ((message,), {})
        pubsub.off(route, handler)
        before = len(seen)
        await pubsub.route_message(message)
        assert len(seen) == before
    pubsub.on("custom", handler)
    await pubsub.emit("custom", 1, value=2)
    assert seen[-1] == ((1,), {"value": 2})
    await pubsub.dispose()


async def test_subscription_failure_reaches_startup_and_can_be_disposed():
    pubsub, subscription, _ = make_pubsub()
    subscription.subscribe_error = RuntimeError("cannot subscribe")
    with pytest.raises(RuntimeError, match="cannot subscribe"):
        await pubsub.startup()
    await drain_loop()
    assert pubsub.task is None and pubsub._ready is None
    assert pubsub.p is None and subscription.exited
    subscription.subscribe_error = None
    await pubsub.startup()
    assert pubsub.task is not None and not pubsub.task.done()
    await pubsub.dispose()
    assert pubsub.task is None and pubsub._ready is None


async def test_cancelling_startup_releases_reader_and_ready_future():
    pubsub, subscription, _ = make_pubsub()
    subscription.subscribe_gate = asyncio.Event()
    start = asyncio.create_task(pubsub.startup())
    await drain_loop()
    reader = pubsub.task
    start.cancel()
    with pytest.raises(asyncio.CancelledError):
        await start
    assert reader.done() and pubsub.task is None and pubsub._ready is None
    assert subscription.exited


async def test_read_without_startup_unsubscribes_on_exit_and_failure():
    pubsub, subscription, _ = make_pubsub()
    pubsub.keep_reading = False
    await pubsub.read()
    assert pubsub.p is None and subscription.unsubscribed == ["test"]
    pubsub, subscription, _ = make_pubsub()
    subscription.subscribe_error = ValueError("direct failure")
    with pytest.raises(ValueError, match="direct failure"):
        await pubsub.read()
    assert pubsub.p is None and subscription.exited


async def test_unsubscribe_failure_does_not_retain_subscription_or_task():
    pubsub, subscription, _ = make_pubsub()
    subscription.unsubscribe_error = RuntimeError("unsubscribe failed")
    await pubsub.startup()
    reader = pubsub.task
    await pubsub.dispose()
    assert reader.done() and pubsub.p is None and pubsub.task is None
    assert subscription.exited


async def test_callback_can_request_disposal_without_waiting_on_itself():
    pubsub, subscription, _ = make_pubsub()
    called = asyncio.Event()

    async def stop(_):
        await pubsub.dispose()
        called.set()

    pubsub.on("control", stop)
    await pubsub.startup()
    reader = pubsub.task
    await pubsub.publish(SocketMessage(route="control"))
    await asyncio.wait_for(called.wait(), 5)
    await asyncio.gather(reader, return_exceptions=True)
    await pubsub.dispose()
    assert pubsub.task is None and pubsub._ready is None
    assert subscription.exited and pubsub.p is None


async def test_idle_reader_releases_its_last_application_message():
    pubsub, subscription, _ = make_pubsub()
    observed = []

    async def handler(message):
        observed.append(weakref.ref(message))

    pubsub.on("broadcast", handler)
    await pubsub.startup()
    await pubsub.publish(SocketMessage(data={"large": "x" * 10000}))
    while not observed or len(subscription.reads) < 2:
        await asyncio.sleep(0)
    await drain_loop()
    gc.collect()
    assert observed[0]() is None
    await pubsub.dispose()
    pubsub.off("broadcast", handler)
    ref = weakref.ref(pubsub)
    del pubsub
    gc.collect()
    assert ref() is None


async def test_separate_readers_share_real_memory_broker_and_channel_isolation():
    server = FakeServer()
    client = FakeRedis(server=server)
    adapter = SimpleNamespace(get_client=lambda: client)
    first, second = PubSub("shared", adapter), PubSub("shared", adapter)
    other = PubSub("other", adapter)
    seen = [[], [], []]
    completed = [asyncio.Event(), asyncio.Event()]

    async def receive(index, message):
        seen[index].append(message.data)
        if index < 2:
            completed[index].set()

    for index, pubsub in enumerate([first, second, other]):

        async def handler(message, index=index):
            await receive(index, message)

        pubsub.on("broadcast", handler)
        await pubsub.startup()
    await first.publish(SocketMessage(data={"value": 1}))
    await asyncio.wait_for(asyncio.gather(*(event.wait() for event in completed)), 5)
    assert seen == [[{"value": 1}], [{"value": 1}], []]
    await asyncio.gather(first.dispose(), second.dispose(), other.dispose())
    assert await client.ping()  # A shared adapter client is not owned by the reader.
    await client.aclose()


async def test_startup_waits_for_matching_ack_and_failed_reader_can_restart():
    pubsub, subscription, _ = make_pubsub()
    subscription.before_ack = [None, {"type": "subscribe", "channel": b"wrong"}]
    await pubsub.startup()
    assert len(subscription.reads) >= 4
    reader = pubsub.task
    subscription.read_error = RuntimeError("read lost")
    subscription.messages.put_nowait({"data": pickle.dumps(SocketMessage())})
    await asyncio.gather(reader, return_exceptions=True)
    assert pubsub.task is None and pubsub._ready is None and pubsub.p is None
    await pubsub.startup()
    assert pubsub.task is not None and not pubsub.task.done()
    await pubsub.dispose()


async def test_external_emit_disposal_collects_unrelated_blocked_reader():
    pubsub, _, _ = make_pubsub()
    entered = asyncio.Event()
    blocked = asyncio.Event()

    async def receive(_):
        entered.set()
        await blocked.wait()

    async def stop():
        await pubsub.dispose()

    pubsub.on("broadcast", receive)
    pubsub.on("stop", stop)
    await pubsub.startup()
    reader = pubsub.task
    await pubsub.publish(SocketMessage())
    await asyncio.wait_for(entered.wait(), 5)
    await asyncio.wait_for(pubsub.emit("stop"), 5)
    assert reader.done() and pubsub.task is None and pubsub.p is None


async def test_idle_result_yields_and_concurrent_disposal_collects_one_reader():
    pubsub, subscription, _ = make_pubsub()
    await pubsub.startup()
    reader = pubsub.task
    subscription.messages.put_nowait(None)
    await drain_loop()
    assert len(subscription.reads) >= 3
    await asyncio.gather(pubsub.dispose(), pubsub.dispose())
    assert reader.done() and pubsub.task is None
    assert subscription.unsubscribed == ["test"]


async def test_manager_startup_can_retry_after_cancelled_first_caller():
    pubsub, subscription, _ = make_pubsub()
    manager = WebsocketConnectionManager(pubsub_instance=pubsub)
    subscription.subscribe_gate = asyncio.Event()
    first = asyncio.create_task(manager.startup())
    await drain_loop()
    second = asyncio.create_task(manager.startup())
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    subscription.subscribe_gate.set()
    await asyncio.wait_for(second, 5)
    assert pubsub.task is not None and not pubsub.task.done()
    assert pubsub.p is subscription
    await manager.dispose()


async def test_cancelled_shared_startup_collects_reader_and_allows_retry():
    pubsub, subscription, _ = make_pubsub()
    subscription.subscribe_gate = asyncio.Event()
    first = asyncio.create_task(pubsub.startup())
    second = asyncio.create_task(pubsub.startup())
    await drain_loop()
    first.cancel()
    results = await asyncio.gather(first, second, return_exceptions=True)
    assert all(isinstance(result, asyncio.CancelledError) for result in results)
    assert pubsub.task is None and pubsub.p is None and pubsub._ready is None
    subscription.subscribe_gate.set()
    await pubsub.startup()
    assert pubsub.task is not None and not pubsub.task.done()
    await pubsub.dispose()


@pytest.mark.parametrize("dispose_during_cleanup", [False, True])
async def test_startup_waits_for_previous_reader_cleanup(dispose_during_cleanup):
    pubsub, subscription, _ = make_pubsub()
    subscription.subscribe_gate = asyncio.Event()
    subscription.exit_gate = asyncio.Event()
    first = asyncio.create_task(pubsub.startup())
    await drain_loop()
    first.cancel()
    await asyncio.wait_for(subscription.exiting.wait(), 5)
    retry = asyncio.create_task(pubsub.startup())
    await drain_loop()
    assert not retry.done()
    disposal = None
    if dispose_during_cleanup:
        disposal = asyncio.create_task(pubsub.dispose())
        await drain_loop()
    subscription.exit_gate.set()
    subscription.subscribe_gate.set()
    with pytest.raises(asyncio.CancelledError):
        await first
    await asyncio.wait_for(retry, 5)
    if disposal is not None:
        await disposal
        assert pubsub.task is None and pubsub.p is None
    else:
        assert pubsub.task is not None and not pubsub.task.done()
        assert pubsub.p is subscription
    await pubsub.dispose()
