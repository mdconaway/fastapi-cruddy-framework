"""Failure, cancellation and reference ownership for managed sockets."""

import asyncio
import gc
import weakref
from asyncio import TimeoutError
from contextlib import asynccontextmanager

import pytest
from fastapi import WebSocketDisconnect
from fastapi_cruddy_framework import (
    BROADCAST_EVENT,
    CLIENT_MESSAGE_EVENT,
    DISCONNECT_EVENT,
    WebsocketConnectionManager,
    get_state,
)
from tests.websockets.transport_helpers import (
    ControlledSocket,
    LocalPubSub,
    checkpoint,
    finished,
    managed,
    open_socket,
    reached,
    received,
)

pytestmark = pytest.mark.anyio


def manager_for(**kwargs):
    return WebsocketConnectionManager(pubsub_instance=LocalPubSub(), **kwargs)


@pytest.mark.parametrize(
    "settings",
    [
        {"queue_capacity": 0},
        {"queue_capacity": -1},
        {"queue_capacity": 1.5},
        {"queue_capacity": True},
        {"send_timeout": 0},
        {"send_timeout": -1},
        {"send_timeout": float("inf")},
        {"send_timeout": float("nan")},
        {"send_timeout": True},
        {"send_timeout": "1"},
        {"close_timeout": 0},
        {"close_timeout": -1},
        {"close_timeout": float("inf")},
        {"close_timeout": float("nan")},
        {"close_timeout": True},
        {"close_timeout": None},
    ],
)
async def test_invalid_limits_fail_before_registering_broker_callbacks(settings):
    pubsub = LocalPubSub()
    with pytest.raises(ValueError):
        WebsocketConnectionManager(pubsub_instance=pubsub, **settings)
    assert pubsub.emitter.listeners_all() == []


async def test_repeated_lifecycle_preserves_borrowed_listeners_and_releases_manager():
    pubsub = LocalPubSub()
    outside = []
    pubsub.on(BROADCAST_EVENT, outside.append)
    manager = WebsocketConnectionManager(pubsub_instance=pubsub)
    reference = weakref.ref(manager)
    await manager.startup()
    await manager.startup()
    assert pubsub.startups == 1
    await manager.dispose()
    await manager.dispose()
    await manager.startup()
    assert pubsub.disposals == 1
    assert pubsub.startups == 1
    assert pubsub.emitter.listeners_all() == [outside.append]
    with pytest.raises(RuntimeError):
        async with manager.connect(ControlledSocket()):
            pytest.fail("A disposed manager admitted a socket")
    del manager
    await checkpoint()
    gc.collect()
    assert reference() is None


async def test_startup_failure_can_retry_without_duplicate_subscription_hooks():
    pubsub = LocalPubSub()
    pubsub.start_error = OSError("broker unavailable")
    manager = WebsocketConnectionManager(pubsub_instance=pubsub)
    listeners = pubsub.emitter.listeners_all()
    with pytest.raises(OSError, match="broker unavailable"):
        await manager.startup()
    pubsub.start_error = None
    await manager.startup()
    assert pubsub.startups == 2
    assert pubsub.emitter.listeners_all() == listeners
    await manager.dispose()


@pytest.mark.parametrize("cancel_first", [False, True])
async def test_concurrent_startup_serializes_a_borrowed_subscription(cancel_first):
    class GatedPubSub(LocalPubSub):
        def __init__(self):
            super().__init__()
            self.entered = asyncio.Event()
            self.release = asyncio.Event()

        async def startup(self):
            self.startups += 1
            self.entered.set()
            await self.release.wait()

    pubsub = GatedPubSub()
    manager = WebsocketConnectionManager(pubsub_instance=pubsub)
    first = asyncio.create_task(manager.startup())
    await reached(pubsub.entered)
    second = asyncio.create_task(manager.startup())
    try:
        await checkpoint()
        assert pubsub.startups == 1
        assert not second.done()
        if cancel_first:
            first.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first
        pubsub.release.set()
        await second
        if not cancel_first:
            await first
        assert pubsub.startups == (2 if cancel_first else 1)
    finally:
        pubsub.release.set()
        await asyncio.gather(first, second, return_exceptions=True)
        await manager.dispose()


async def test_endpoint_body_exception_still_closes_and_unlinks_once():
    manager = manager_for()
    socket = ControlledSocket()
    notifications = []
    manager.on(DISCONNECT_EVENT, notifications.append)
    async with managed(manager):
        with pytest.raises(ValueError, match="setup failed"):
            async with manager.connect(socket, override_socket_id="setup"):
                raise ValueError("setup failed")
        await reached(socket.close_started)
        await manager.close_socket(socket)
        assert notifications == [socket]
        assert socket not in manager.active_connections
        assert get_state(socket, "is_connected") is False


async def test_accept_failure_leaves_no_connection_and_shutdown_race_closes_accepted_peer():
    manager = manager_for()
    failed = ControlledSocket()
    failed.accept_error = OSError("accept failed")
    await manager.startup()
    with pytest.raises(OSError, match="accept failed"):
        async with manager.connect(failed):
            pytest.fail("Failed accept yielded")
    assert manager.active_connections == []
    delayed = ControlledSocket()
    delayed.accept_gate.clear()

    async def endpoint():
        async with manager.connect(delayed):
            pytest.fail("Shutdown race yielded an active connection")

    task = asyncio.create_task(endpoint())
    await reached(delayed.accepted)
    await manager.dispose()
    delayed.accept_gate.set()
    with pytest.raises(RuntimeError):
        await finished(task)
    await reached(delayed.close_started)
    assert manager.active_connections == []


async def test_accept_cancellation_closes_partial_transport_without_registering_peer():
    manager = manager_for()
    socket = ControlledSocket()
    socket.accept_gate.clear()
    notifications = []
    manager.on(DISCONNECT_EVENT, notifications.append)
    async with managed(manager):

        async def endpoint():
            async with manager.connect(socket):
                pytest.fail("Cancelled acceptance yielded")

        task = asyncio.create_task(endpoint())
        await reached(socket.accepted)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await finished(task)
        assert socket.close_calls == [(1000, None)]
        assert notifications == []
        assert get_state(socket, "is_connected") is False
        assert manager.active_connections == []
        assert manager._connections == manager._closing_connections == {}
        assert manager._cleanup_tasks == set()


async def test_local_close_in_connect_body_skips_receiving_and_preserves_context_contract():
    manager = manager_for()
    socket = ControlledSocket()
    async with managed(manager):
        async with manager.connect(
            socket, override_socket_id="setup-close"
        ) as assigned:
            assert assigned == "setup-close"
            assert socket in manager.active_connections
            await manager.send_json_to_socket(socket, {"setup": True})
            assert await received(socket) == [{"setup": True}]
            await manager.close_socket(socket)
        assert manager.active_connections == []


async def test_live_connected_state_can_stop_receive_loop_without_an_incoming_message():
    manager = manager_for()
    socket = ControlledSocket()
    async with managed(manager):
        async with manager.connect(socket):
            socket.state.is_connected = False
        assert socket not in manager.active_connections
        assert len(socket.close_calls) == 1


async def test_endpoint_cancellation_stops_writer_receive_and_disconnects_once():
    manager = manager_for()
    socket = ControlledSocket(send_blocked=True)
    notifications = []
    manager.on(DISCONNECT_EVENT, notifications.append)
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        await manager.broadcast(type="blocked")
        await reached(socket.send_started)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await finished(task)
        await manager.close_socket(socket)
        assert notifications == [socket]
        assert socket.send_cancelled.is_set()
        assert manager.active_connections == []


async def test_local_cancellation_before_coroutine_runs_does_not_affect_connection():
    manager = manager_for()
    socket = ControlledSocket()
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        cancelled = asyncio.create_task(
            manager.send_json_to_socket(socket, {"expired": True})
        )
        cancelled.cancel()
        with pytest.raises(asyncio.CancelledError):
            await cancelled
        await manager.send_json_to_socket(socket, {"still": "alive"})
        assert await received(socket) == [{"still": "alive"}]
        assert socket in manager.active_connections
        await manager.close_socket(socket)
        await finished(task)


async def test_queued_local_cancellation_skips_expired_payload_and_releases_waiter():
    manager = manager_for()
    socket = ControlledSocket(send_blocked=True)
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        await manager.broadcast(type="in-flight", data={})
        await reached(socket.send_started)
        cancelled = asyncio.create_task(
            manager.send_json_to_socket(socket, {"expired": True})
        )
        await checkpoint()
        reference = weakref.ref(cancelled)
        cancelled.cancel()
        with pytest.raises(asyncio.CancelledError):
            await cancelled
        await manager.broadcast(type="after", data={})
        socket.send_gate.set()
        values = await received(socket, 2)
        assert [item["type"] for item in values] == ["in-flight", "after"]
        assert socket in manager.active_connections
        del cancelled
        await checkpoint()
        gc.collect()
        assert reference() is None
        await manager.close_socket(socket)
        await finished(task)


@pytest.mark.parametrize("cancel_before_completion", [False, True])
async def test_cancellation_after_send_completes_does_not_close_a_healthy_connection(
    cancel_before_completion,
):
    manager = manager_for()
    socket = ControlledSocket()
    original_send = socket.send_text
    cancel_after_send = True
    local = None

    async def send_then_cancel_waiter(text):
        await original_send(text)
        if cancel_after_send:
            if cancel_before_completion:
                local.cancel()
            else:
                asyncio.get_running_loop().call_soon(local.cancel)

    socket.send_text = send_then_cancel_waiter
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        local = asyncio.create_task(manager.send_json_to_socket(socket, {"sent": True}))
        with pytest.raises(asyncio.CancelledError):
            await local
        assert await received(socket) == [{"sent": True}]
        assert socket in manager.active_connections
        cancel_after_send = False
        await manager.send_json_to_socket(socket, {"still": "healthy"})
        assert await received(socket) == [{"still": "healthy"}]
        await manager.close_socket(socket)
        await finished(task)


async def test_inflight_local_cancellation_stops_only_its_socket_before_blocked_close():
    manager = manager_for()
    socket = ControlledSocket(send_blocked=True, close_blocked=True)
    healthy = ControlledSocket()
    notifications = []
    manager.on(DISCONNECT_EVENT, notifications.append)
    async with managed(manager):
        _, task = await open_socket(manager, socket, "slow")
        _, healthy_task = await open_socket(manager, healthy, "healthy")
        local = asyncio.create_task(
            manager.send_json_to_socket(socket, {"expired": True})
        )
        await reached(socket.send_started)
        local.cancel()
        with pytest.raises(asyncio.CancelledError):
            await local
        await reached(socket.close_started)
        assert socket.send_cancelled.is_set()
        assert socket not in manager.active_connections
        assert notifications == [socket]
        assert not socket.close_gate.is_set()
        await manager.send_json_to_socket(healthy, {"healthy": True})
        assert await received(healthy) == [{"healthy": True}]
        socket.send_gate.set()
        socket.close_gate.set()
        await finished(task)
        assert socket.sent == []
        await manager.close_socket(healthy)
        await finished(healthy_task)


async def test_pending_local_waiter_fails_on_kill_and_unmanaged_helpers_are_explicit():
    manager = manager_for()
    socket = ControlledSocket(send_blocked=True)
    async with managed(manager):
        with pytest.raises(RuntimeError):
            await manager.send_json_to_socket(socket, {})
        await manager.close_socket(socket)
        _, task = await open_socket(manager, socket, "pending")
        await manager.broadcast(type="blocking")
        await reached(socket.send_started)
        local = asyncio.create_task(
            manager.send_json_to_socket(socket, {"pending": True})
        )
        await checkpoint()
        await manager.kill_sockets_by_socket_id("pending")
        with pytest.raises(RuntimeError):
            await local
        await finished(task)
        with pytest.raises(RuntimeError):
            await manager.send_json_to_socket(socket, {})


@pytest.mark.parametrize(
    "send_error",
    [OSError("send failed"), RuntimeError("closed"), WebSocketDisconnect(1006)],
)
async def test_send_failure_closes_connection_and_settles_local_completion(send_error):
    manager = manager_for()
    socket = ControlledSocket()
    socket.send_error = send_error
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        with pytest.raises((OSError, RuntimeError, WebSocketDisconnect)):
            await manager.send_json_to_socket(socket, {"fails": True})
        await reached(socket.close_started)
        await finished(task)
        assert manager.active_connections == []


async def test_disconnect_hook_can_await_close_without_awaiting_itself():
    manager = manager_for()
    socket = ControlledSocket(close_blocked=True)
    entered, exited = asyncio.Event(), asyncio.Event()

    async def disconnected(original):
        assert original is socket
        assert original not in manager.active_connections
        entered.set()
        await manager.close_socket(original)
        exited.set()

    manager.on(DISCONNECT_EVENT, disconnected)
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        closing = asyncio.create_task(
            manager.close_socket(socket, code=1013, reason="stalled")
        )
        await reached(entered)
        await reached(socket.close_started)
        assert not closing.done()
        socket.close_gate.set()
        await closing
        await reached(exited)
        await finished(task)
        assert socket.close_calls == [(1013, "stalled")]


async def test_receive_handler_can_send_then_close_and_hooks_are_not_transport_barriers():
    manager = manager_for()
    socket = ControlledSocket()
    hook_entered, hook_release, handler_exited = (
        asyncio.Event(),
        asyncio.Event(),
        asyncio.Event(),
    )

    async def disconnected(_socket):
        hook_entered.set()
        await hook_release.wait()

    async def handler(original, data):
        await manager.send_json_to_socket(original, {"reply": data})
        await manager.close_socket(original)
        handler_exited.set()

    manager.on(DISCONNECT_EVENT, disconnected)
    manager.on(CLIENT_MESSAGE_EVENT, handler)
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        try:
            socket.incoming.put_nowait({"command": 1})
            assert await received(socket) == [{"reply": {"command": 1}}]
            await reached(hook_entered)
            await reached(socket.close_started)
            await reached(handler_exited)
            assert not hook_release.is_set()
        finally:
            # An assertion failure must not strand the deliberately waiting hook.
            hook_release.set()
        await finished(task)


async def test_disconnect_callback_failure_does_not_leave_connection_or_transport_alive():
    manager = manager_for()
    socket = ControlledSocket()

    async def broken(_socket):
        raise ValueError("disconnect hook failed")

    manager.on(DISCONNECT_EVENT, broken)
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        await manager.close_socket(socket)
        await finished(task)
        assert socket not in manager.active_connections
        assert len(socket.close_calls) == 1


async def test_disconnect_broadcast_failure_does_not_leave_transport_or_bindings_alive():
    class FailedDisconnectBroadcast(LocalPubSub):
        async def publish(self, message):
            if message.type == "left":
                raise OSError("broker publication failed")
            await super().publish(message)

    manager = WebsocketConnectionManager(pubsub_instance=FailedDisconnectBroadcast())
    socket = ControlledSocket()
    async with managed(manager):
        _, task = await open_socket(
            manager,
            socket,
            disconnect_message_type="left",
            disconnect_message_data={},
        )
        await manager.close_socket(socket)
        await finished(task)
        assert socket not in manager.active_connections
        assert len(socket.close_calls) == 1


async def test_cancelled_close_caller_does_not_cancel_another_close_waiter():
    manager = manager_for()
    socket = ControlledSocket(close_blocked=True)
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        connection = manager._connections[socket]
        first = asyncio.create_task(manager.close_socket(socket))
        await reached(socket.close_started)
        second = asyncio.create_task(manager.close_socket(socket))
        await checkpoint()
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert not connection.transport_closed.cancelled()
        assert not second.done()
        socket.close_gate.set()
        await second
        await finished(task)
        assert connection.close_waiters == 0
        assert connection.close_waiters_done.is_set()
        assert len(socket.close_calls) == 1


@pytest.mark.parametrize(
    "close_error", [RuntimeError("already closed"), OSError("transport failed")]
)
async def test_close_failure_and_repeated_close_do_not_repeat_notifications(
    close_error,
):
    manager = manager_for()
    socket = ControlledSocket()
    socket.close_error = close_error
    notifications = []
    manager.on(DISCONNECT_EVENT, notifications.append)
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        await asyncio.gather(manager.close_socket(socket), manager.close_socket(socket))
        await finished(task)
        assert notifications == [socket]
        assert len(socket.close_calls) == 1


async def test_manager_disposal_settles_pending_local_helpers_and_clears_owned_registries():
    manager = manager_for()
    socket = ControlledSocket(send_blocked=True)
    await manager.startup()
    _, task = await open_socket(manager, socket)
    local = asyncio.create_task(manager.send_json_to_socket(socket, {"pending": True}))
    await reached(socket.send_started)
    await manager.dispose()
    with pytest.raises(RuntimeError):
        await local
    await finished(task)
    assert manager.active_connections == []
    assert manager._connections == {}
    assert manager._closing_connections == {}
    assert manager._cleanup_tasks == set()


async def test_local_queue_overflow_settles_every_waiter_without_waiting_for_capacity():
    manager = manager_for(queue_capacity=1)
    socket = ControlledSocket(send_blocked=True)
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        await manager.broadcast(type="in-flight")
        await reached(socket.send_started)
        pending = asyncio.create_task(
            manager.send_json_to_socket(socket, {"queued": True})
        )
        await checkpoint()
        with pytest.raises(RuntimeError, match="closed|full"):
            await manager.send_json_to_socket(socket, {"overflow": True})
        with pytest.raises(RuntimeError):
            await pending
        await finished(task)
        assert socket.sent == []
        assert len(socket.close_calls) == 1


def controlled_deadline(boundary, task_name=None):
    """Expire at a known await boundary, independent of host scheduling speed."""

    @asynccontextmanager
    async def deadline(_seconds):
        task = asyncio.current_task()
        if task_name is not None and task.get_name() != task_name:
            yield
            return

        async def expire():
            await boundary.wait()
            task.cancel()

        controller = asyncio.create_task(expire())
        try:
            try:
                yield
            except asyncio.CancelledError as exc:
                if hasattr(task, "uncancel"):
                    task.uncancel()
                raise TimeoutError("controlled deadline") from exc
        finally:
            controller.cancel()
            await asyncio.gather(controller, return_exceptions=True)

    return deadline


async def test_local_deadline_includes_wait_behind_another_send(monkeypatch):
    import fastapi_cruddy_framework._websocket_connection as connection_module

    manager = manager_for()
    socket = ControlledSocket(send_blocked=True)
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        await manager.broadcast(type="in-flight")
        await reached(socket.send_started)
        monkeypatch.setattr(
            connection_module,
            "timeout",
            controlled_deadline(socket.send_started, "local-deadline"),
        )
        expired = asyncio.create_task(
            manager.send_json_to_socket(socket, {"expired": True}),
            name="local-deadline",
        )
        with pytest.raises(TimeoutError, match="controlled deadline"):
            await expired
        await reached(socket.close_started)
        await finished(task)
        assert socket.sent == []
        assert socket not in manager.active_connections


async def test_writer_deadline_retires_connection_even_without_a_local_waiter(
    monkeypatch,
):
    import fastapi_cruddy_framework._websocket_connection as connection_module

    manager = manager_for()
    socket = ControlledSocket(send_blocked=True)
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        writer = manager._connections[socket].writer_task
        writer.set_name("writer-deadline")
        monkeypatch.setattr(
            connection_module,
            "timeout",
            controlled_deadline(socket.send_started, "writer-deadline"),
        )
        await manager.broadcast(type="expires")
        await reached(socket.close_started)
        await finished(task)
        assert socket.send_cancelled.is_set()
        assert socket not in manager.active_connections


async def test_unexpected_writer_cancellation_and_already_closing_admission():
    manager = manager_for()
    socket = ControlledSocket()
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        connection = manager._connections[socket]
        await checkpoint()
        connection.writer_task.cancel()
        await reached(socket.close_started)
        await finished(task)
        assert connection.closing
        assert not connection.enqueue("late")
        assert connection.queue.empty()
        await connection.write()
        assert connection.current is None


async def test_transport_close_deadline_is_bounded_without_suppressing_disconnect(
    monkeypatch,
):
    import fastapi_cruddy_framework.websocket_manager as manager_module

    manager = manager_for()
    socket = ControlledSocket(close_blocked=True)
    disconnected = asyncio.Event()
    manager.on(DISCONNECT_EVENT, lambda _socket: disconnected.set())
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        monkeypatch.setattr(
            manager_module, "timeout", controlled_deadline(socket.close_started)
        )
        await manager.close_socket(socket)
        await reached(disconnected)
        await finished(task)
        assert not socket.close_gate.is_set()
        assert socket not in manager.active_connections


async def test_disposal_caller_cancellation_does_not_cancel_shared_teardown():
    manager = manager_for()
    socket = ControlledSocket(close_blocked=True)
    await manager.startup()
    _, task = await open_socket(manager, socket)
    caller = asyncio.create_task(manager.dispose())
    await reached(socket.close_started)
    caller.cancel()
    with pytest.raises(asyncio.CancelledError):
        await caller
    assert manager.accept_new is False
    socket.close_gate.set()
    await manager.dispose()
    await finished(task)
    assert manager._connections == manager._closing_connections == {}
    assert manager._cleanup_tasks == set()


async def test_broker_disposal_error_still_collects_active_connection_work():
    manager = manager_for()
    socket = ControlledSocket()
    await manager.startup()
    _, task = await open_socket(manager, socket)
    manager.pubsub_instance.dispose_error = OSError("broker shutdown failed")
    with pytest.raises(OSError, match="broker shutdown failed"):
        await manager.dispose()
    await finished(task)
    await manager.dispose()
    assert manager.active_connections == []
    assert manager._connections == manager._closing_connections == {}
    assert manager._cleanup_tasks == set()


async def test_cancelled_broker_disposal_still_collects_active_connection_work():
    manager = manager_for()
    socket = ControlledSocket()
    await manager.startup()
    _, task = await open_socket(manager, socket)
    manager.pubsub_instance.dispose_error = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await manager.dispose()
    await finished(task)
    await checkpoint()
    assert manager._dispose_task is None
    assert manager._disposed
    assert manager._connections == manager._closing_connections == {}
    assert manager._cleanup_tasks == set()
    await manager.dispose()


@pytest.mark.parametrize("event", [CLIENT_MESSAGE_EVENT, DISCONNECT_EVENT])
async def test_disposal_requested_inside_callback_cannot_wait_on_itself(event):
    manager = manager_for()
    socket = ControlledSocket()
    requested = asyncio.Event()

    async def request_disposal(*_args):
        await manager.dispose()
        requested.set()

    manager.on(event, request_disposal)
    await manager.startup()
    _, task = await open_socket(manager, socket)
    if event == CLIENT_MESSAGE_EVENT:
        socket.incoming.put_nowait({"shutdown": True})
    else:
        socket.incoming.put_nowait(WebSocketDisconnect())
    await reached(requested)
    await manager.dispose()
    await finished(task)
    assert manager.active_connections == []


async def test_connection_closed_while_endpoint_setup_waits_exits_after_cleanup():
    manager = manager_for()
    socket = ControlledSocket(close_blocked=True)
    body_entered, release_body = asyncio.Event(), asyncio.Event()

    async def endpoint():
        async with manager.connect(socket):
            body_entered.set()
            await release_body.wait()

    async with managed(manager):
        endpoint_task = asyncio.create_task(endpoint())
        try:
            await reached(body_entered)
            connection = manager._connections[socket]
            closing = asyncio.create_task(manager.close_socket(socket))
            await reached(socket.close_started)
            cleanup = connection.cleanup_task
            socket.close_gate.set()
            await closing
            await finished(cleanup)
            assert connection.cleanup_task is None
            assert not endpoint_task.done()
        finally:
            socket.close_gate.set()
            release_body.set()
            await finished(endpoint_task)
        assert manager.active_connections == []


async def test_stale_recipient_snapshot_and_repeated_unlink_do_not_resurrect_output():
    manager = manager_for()
    socket = ControlledSocket()
    notifications = []
    manager.on(DISCONNECT_EVENT, notifications.append)
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        selected_recipients = manager.get_sockets_by_id(socket.state.socket_id)
        await manager._unlink_socket(socket)
        await manager._unlink_socket(socket)
        await manager._send_to_sockets(selected_recipients, '{"stale":true}')
        await manager._kill_sockets(selected_recipients)
        await finished(task)
        assert notifications == [socket]
        assert socket.sent == []
        assert len(socket.close_calls) == 1


@pytest.mark.parametrize("abort_kind", ["cancelled", "unexpected"])
async def test_aborted_disconnect_hook_does_not_retain_connection_work(abort_kind):
    class HookAbort(BaseException):
        pass

    manager = manager_for()
    socket = ControlledSocket()
    failure = asyncio.CancelledError if abort_kind == "cancelled" else HookAbort

    async def aborted(_socket):
        raise failure("hook interrupted")

    manager.on(DISCONNECT_EVENT, aborted)
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        await manager.close_socket(socket)
        with pytest.raises(failure):
            await finished(task)
        await checkpoint()
        assert socket not in manager.active_connections
        assert manager._closing_connections == {}
        assert manager._cleanup_tasks == set()
        assert len(socket.close_calls) == 1


@pytest.mark.parametrize("completion_state", ["completed", "cancelled"])
async def test_transport_teardown_survives_a_pre_set_internal_completion(
    completion_state,
):
    manager = manager_for()
    socket = ControlledSocket()
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        connection = manager._connections[socket]
        # Fault injection: public close callers are shielded from mutating this
        # shared future, but an already-set completion must not strand teardown.
        if completion_state == "completed":
            connection.transport_closed.set_result(None)
            await manager.close_socket(socket)
        else:
            connection.transport_closed.cancel()
            with pytest.raises(asyncio.CancelledError):
                await manager.close_socket(socket)
        await finished(task)
        assert len(socket.close_calls) == 1
        assert manager._connections == manager._closing_connections == {}
        assert manager._cleanup_tasks == set()
