"""Public websocket contracts and independent managed output."""

import asyncio
import gc
import inspect
import json
import weakref
from uuid import UUID

import pytest
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from async_asgi_testclient import TestClient as OriginalTestClient
from async_asgi_testclient.websocket import WebSocketSession as OriginalSession
from fastapi_cruddy_framework import (
    BROADCAST_EVENT,
    CLIENT_EVENT,
    CLIENT_MESSAGE_EVENT,
    CONTROL_EVENT,
    DISCONNECT_EVENT,
    ROOM_EVENT,
    BrowserTestClient,
    SocketMessage,
    TestClient,
    WebSocketSession,
    WebsocketConnectionManager,
    get_state,
    set_state,
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


async def test_public_publication_envelopes_and_event_registration():
    manager = manager_for()
    pubsub = manager.pubsub_instance
    observed = []

    async def listener(*args, **kwargs):
        await checkpoint()
        observed.append((args, kwargs))

    assert manager.on("custom", listener) is listener
    assert await manager.emit("custom", 7, named="value") is None
    assert observed == [((7,), {"named": "value"})]
    assert manager.off("custom", listener) is listener
    await manager.emit("custom", "unobserved")
    assert len(observed) == 1
    assert manager.on("decorator")(listener) is listener
    assert manager.off("decorator") is None

    async with managed(manager):
        await manager.broadcast("ignored-target", "sender", "b", {"n": 1})
        await manager.direct_message("socket", "sender", "d", {"n": 2})
        await manager.room_message("room", "sender", "r", {"n": 3})
        raw = SocketMessage(route=BROADCAST_EVENT, type="raw", data={})
        assert await manager.send_message_raw(raw) is None
        control = SocketMessage(route=ROOM_EVENT, type="application_control", data={})
        controls = []
        manager.on(CONTROL_EVENT, controls.append)
        assert await manager.send_control_message(control) is None
        assert control.route == CONTROL_EVENT
        assert controls == [control]
        assert pubsub.messages[-2] is raw
        assert pubsub.messages[-1] is control
        assert [item.route for item in pubsub.messages] == [
            BROADCAST_EVENT,
            CLIENT_EVENT,
            ROOM_EVENT,
            BROADCAST_EVENT,
            CONTROL_EVENT,
        ]
        assert pubsub.messages[0].model_dump() == {
            "route": BROADCAST_EVENT,
            "target": "ignored-target",
            "sender": "sender",
            "type": "b",
            "data": {"n": 1},
        }
        encoded = manager.generate_client_message("route", "target", "sender", None, {})
        assert isinstance(encoded, str)
        assert json.loads(encoded) == {
            "route": "route",
            "target": "target",
            "sender": "sender",
            "type": None,
            "data": {},
        }


async def test_constructor_precedence_and_existing_positional_arguments(monkeypatch):
    import fastapi_cruddy_framework.websocket_manager as module

    adapters = []
    subscriptions = []

    class Adapter:
        def __init__(self, **kwargs):
            adapters.append(kwargs)

    class Subscription(LocalPubSub):
        def __init__(self, channel, redis_client):
            super().__init__()
            subscriptions.append((channel, redis_client))

    monkeypatch.setattr(module, "RedisAdapter", Adapter)
    monkeypatch.setattr(module, "PubSub", Subscription)
    default = module.WebsocketConnectionManager()
    assert adapters == [
        {
            "mode": "redis",
            "redis_host": "redis",
            "redis_port": 6379,
            "redis_max_connections": 10000,
        }
    ]
    assert subscriptions[0][0] == "websockets"
    supplied_adapter = object()
    with_adapter = module.WebsocketConnectionManager(
        redis_adapter=supplied_adapter, redis_channel="explicit"
    )
    assert subscriptions[-1] == ("explicit", supplied_adapter)
    supplied_pubsub = LocalPubSub()
    normalizer = lambda data: data
    getter = lambda socket: getattr(socket.state, "identity", "")
    with_pubsub = module.WebsocketConnectionManager(
        supplied_pubsub,
        "memory",
        supplied_adapter,
        "unused",
        "host",
        123,
        9,
        normalizer,
        "connected",
        "sid",
        getter,
        "membership",
    )
    assert len(adapters) == 1
    assert len(subscriptions) == 2
    assert with_pubsub.pubsub_instance is supplied_pubsub
    assert with_pubsub.custom_json_serializer is normalizer
    assert with_pubsub.custom_client_identifier is getter
    assert with_pubsub.connected_state_attr == "connected"
    assert with_pubsub.socket_id_attr == "sid"
    assert with_pubsub.room_configuration_object_key == "membership"
    for name in ("queue_capacity", "send_timeout", "close_timeout"):
        parameter = inspect.signature(module.WebsocketConnectionManager).parameters[
            name
        ]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    for item in (default, with_adapter, with_pubsub):
        await item.dispose()


async def test_live_original_sockets_duplicate_ids_and_mutable_routing():
    manager = manager_for(
        socket_id_attr="sid",
        connected_state_attr="connected",
        room_configuration_object_key="membership",
        custom_client_identifier=lambda socket: getattr(socket.state, "identity", ""),
    )
    sockets = [ControlledSocket() for _ in range(3)]
    async with managed(manager):
        tasks = []
        for index, socket in enumerate(sockets):
            assigned, task = await open_socket(
                manager,
                socket,
                "same" if index < 2 else "other",
                setup=lambda peer: set_state(peer, "identity", "operator"),
            )
            tasks.append(task)
            assert assigned == ("same" if index < 2 else "other")
            assert get_state(socket, "connected") is True
            assert manager.get_room_config(socket) is socket.state.membership
        assert manager.get_sockets_by_id("same") == sockets[:2]
        assert manager.get_sockets_by_client_id("operator") == sockets
        await manager.join_room_by_socket_id("same", "one")
        await manager.join_room_by_client_id("operator", "two")
        assert manager.get_sockets_by_room("one") == sockets[:2]
        assert manager.get_room_list() == {"one", "two"}
        await manager.leave_room_by_socket_id("same", "one")
        await manager.leave_room_by_client_id("operator", "two")
        assert manager.get_room_list() == set()
        manager.get_room_config(sockets[0]).room_list.add("live")
        set_state(sockets[1], "sid", "changed")
        set_state(sockets[1], "identity", "new-operator")
        assert manager.get_sockets_by_room("live") == [sockets[0]]
        assert manager.get_sockets_by_id("same") == [sockets[0]]
        assert manager.get_sockets_by_client_id("new-operator") == [sockets[1]]
        await manager.direct_message("new-operator", "source", "direct", {})
        assert (await received(sockets[1]))[0]["target"] == "new-operator"
        assert sockets[0].sent == sockets[2].sent == []
        await manager.direct_message("absent", type="none")
        await manager.room_message("absent", type="none")
        await manager.kill_sockets_by_client_id("new-operator")
        await reached(sockets[1].close_started)
        await finished(tasks[1])
        await manager.kill_room_by_id("live")
        await reached(sockets[0].close_started)
        await finished(tasks[0])
        await manager.kill_sockets_by_socket_id("other")
        await reached(sockets[2].close_started)
        await finished(tasks[2])
        assert manager.active_connections == []
        assert manager.get_room_list() == set()
        assert manager.get_sockets_by_id("absent") == []
        assert manager.get_sockets_by_client_id("operator") == []


async def test_default_ids_missing_state_and_absent_recipients():
    manager = manager_for()
    blank = ControlledSocket()
    assert manager.get_room_config(blank).room_list == set()
    async with managed(manager):
        socket = ControlledSocket()
        assigned, task = await open_socket(manager, socket)
        assert str(UUID(assigned)) == assigned
        assert manager.get_sockets_by_client_id("") == [socket]
        assert manager.get_sockets_by_id("missing") == []
        await manager.direct_message("missing")
        await manager.room_message("missing")
        await manager.kill_sockets_by_socket_id("missing")
        await manager.kill_sockets_by_client_id("missing")
        await manager.kill_room_by_id("missing")
        await manager.join_room_by_socket_id("missing", "none")
        await manager.leave_room_by_socket_id("missing", "none")
        await manager.close_socket(socket)
        await finished(task)


@pytest.mark.parametrize("target_kind", ["socket", "client", "room"])
async def test_targeted_kill_includes_all_matching_original_connections(target_kind):
    manager = manager_for(custom_client_identifier=lambda socket: socket.state.identity)
    sockets = [ControlledSocket() for _ in range(3)]
    async with managed(manager):
        tasks = []
        for index, socket in enumerate(sockets):
            _, task = await open_socket(
                manager,
                socket,
                "duplicate" if index < 2 else "other",
                setup=lambda peer, index=index: set_state(
                    peer, "identity", "shared" if index < 2 else "other"
                ),
            )
            tasks.append(task)
            if index < 2:
                manager.get_room_config(socket).room_list.add("shared-room")
        if target_kind == "socket":
            await manager.kill_sockets_by_socket_id("duplicate")
        elif target_kind == "client":
            await manager.kill_sockets_by_client_id("shared")
        else:
            await manager.kill_room_by_id("shared-room")
        await asyncio.gather(*(reached(socket.close_started) for socket in sockets[:2]))
        await asyncio.gather(*(finished(task) for task in tasks[:2]))
        assert manager.active_connections == [sockets[2]]
        await manager.send_json_to_socket(sockets[2], {"still": "connected"})
        assert await received(sockets[2]) == [{"still": "connected"}]
        await manager.close_socket(sockets[2])
        await finished(tasks[2])


async def test_mixed_messages_share_fifo_and_one_serialization_per_fanout():
    normalized = []

    def normalize(data):
        normalized.append(data)
        return {"normalized": data}

    manager = manager_for(custom_json_serializer=normalize)
    first, second = ControlledSocket(send_blocked=True), ControlledSocket()
    async with managed(manager):
        _, task1 = await open_socket(manager, first, "first")
        _, task2 = await open_socket(manager, second, "second")
        await manager.join_room_by_socket_id("first", "room")
        await manager.broadcast("ignored", "sender", "broadcast", {"n": 1})
        await reached(first.send_started)
        await manager.room_message("room", "sender", "room", {"n": 2})
        await manager.direct_message("first", "sender", "direct", {"n": 3})
        raw = {"type": "assisted_manual.status", "data": {"unicode": "é", "nil": None}}
        local = asyncio.create_task(manager.send_json_to_socket(first, raw))
        await checkpoint()
        assert not local.done()
        await manager.leave_room_by_socket_id("first", "room")
        await manager.room_message("room", type="excluded", data={"n": 4})
        first.send_gate.set()
        values = await received(first, 4)
        assert [item.get("type") for item in values] == [
            "broadcast",
            "room",
            "direct",
            "assisted_manual.status",
        ]
        assert values[-1] == raw
        assert values[0] == {
            "route": BROADCAST_EVENT,
            "target": None,
            "sender": "sender",
            "type": "broadcast",
            "data": {"normalized": {"n": 1}},
        }
        assert values[1]["route"] == ROOM_EVENT
        assert values[2]["route"] == CLIENT_EVENT
        assert normalized == [{"n": 1}, {"n": 2}, {"n": 3}]
        assert await local is None
        assert await received(second) == [values[0]]
        assert first.sent[0] is second.sent[0]
        assert first.max_sending == second.max_sending == 1
        await manager.close_socket(first)
        await manager.close_socket(second)
        await finished(task1)
        await finished(task2)


async def test_blocked_send_and_close_do_not_stop_healthy_delivery_or_receive():
    manager = manager_for(queue_capacity=2)
    slow = ControlledSocket(send_blocked=True, close_blocked=True)
    healthy = ControlledSocket()
    disconnects = []
    commands = asyncio.Event()

    async def handle(socket, data):
        if socket is healthy:
            await manager.send_json_to_socket(socket, {"reply": data})
            commands.set()

    manager.on(DISCONNECT_EVENT, disconnects.append)
    manager.on(CLIENT_MESSAGE_EVENT, handle)
    async with managed(manager):
        _, slow_task = await open_socket(manager, slow, "slow")
        _, healthy_task = await open_socket(manager, healthy, "healthy")
        await manager.broadcast(type="0", data={})
        await reached(slow.send_started)
        assert (await received(healthy))[0]["type"] == "0"
        for number in range(1, 4):
            await manager.broadcast(type=str(number), data={})
            assert (await received(healthy))[0]["type"] == str(number)
        await reached(slow.close_started)
        assert slow in disconnects
        assert slow not in manager.active_connections
        assert slow.sent == []
        assert not slow.close_gate.is_set()
        healthy.incoming.put_nowait({"command": 1})
        await reached(commands)
        assert await received(healthy) == [{"reply": {"command": 1}}]
        await manager.direct_message("healthy", type="after-close")
        assert (await received(healthy))[0]["type"] == "after-close"
        slow.close_gate.set()
        await finished(slow_task)
        await manager.close_socket(healthy)
        await finished(healthy_task)
        assert disconnects.count(slow) == disconnects.count(healthy) == 1


async def test_waiting_incoming_handler_is_per_socket_and_keeps_original_arguments():
    manager = manager_for()
    first, second = ControlledSocket(), ControlledSocket()
    entered, release, other_handled = asyncio.Event(), asyncio.Event(), asyncio.Event()
    calls = []

    async def handler(socket, data):
        calls.append((socket, data))
        if socket is first and data == {"n": 1}:
            entered.set()
            await release.wait()
        if socket is second:
            other_handled.set()

    manager.on(CLIENT_MESSAGE_EVENT, handler)
    async with managed(manager):
        _, task1 = await open_socket(manager, first, "one")
        _, task2 = await open_socket(manager, second, "two")
        first.incoming.put_nowait(["ignored"])
        first.incoming.put_nowait({"n": 1})
        first.incoming.put_nowait({"n": 2})
        await reached(entered)
        second.incoming.put_nowait({"n": 3})
        await reached(other_handled)
        assert calls == [(first, {"n": 1}), (second, {"n": 3})]
        release.set()
        await manager.close_socket(second)
        first.incoming.put_nowait(WebSocketDisconnect())
        await finished(task1)
        await finished(task2)
        assert calls[-1] == (first, {"n": 2})


@pytest.mark.parametrize(
    "receive_error", [ValueError("bad json"), WebSocketDisconnect(1001)]
)
async def test_receive_failure_and_disconnect_publish_once_with_empty_data(
    receive_error,
):
    manager = manager_for()
    socket = ControlledSocket()
    notifications = []

    def disconnected(original):
        assert original not in manager.active_connections
        notifications.append(original)

    manager.on(DISCONNECT_EVENT, disconnected)
    async with managed(manager):
        _, task = await open_socket(
            manager,
            socket,
            "id",
            disconnect_message_type="left",
            disconnect_message_data={},
        )
        socket.incoming.put_nowait(receive_error)
        await finished(task)
        await manager.close_socket(socket)
        assert notifications == [socket]
        assert (
            len(
                [
                    item
                    for item in manager.pubsub_instance.messages
                    if item.type == "left"
                ]
            )
            == 1
        )
        assert get_state(socket, "is_connected") is False


async def test_client_handler_error_cleans_up_and_custom_control_is_awaited():
    manager = manager_for()
    socket = ControlledSocket()
    controls = []

    async def control(message):
        await checkpoint()
        controls.append(message)

    async def broken_handler(_socket, _data):
        raise ValueError("application failed")

    manager.on(CONTROL_EVENT, control)
    manager.on(CLIENT_MESSAGE_EVENT, broken_handler)
    async with managed(manager):
        message = SocketMessage(type="custom", route=CONTROL_EVENT)
        await manager.send_control_message(message)
        assert controls == [message]
        _, task = await open_socket(manager, socket, "id")
        socket.incoming.put_nowait({"fail": True})
        await finished(task)
        assert socket not in manager.active_connections


async def test_original_test_client_exports_and_browser_header_contract():
    assert TestClient is OriginalTestClient
    assert WebSocketSession is OriginalSession
    app = FastAPI()
    application_sockets = []

    @app.websocket("/raw")
    async def raw(socket: WebSocket):
        application_sockets.append(socket)
        await socket.accept()
        try:
            while True:
                message = await socket.receive()
                if message["type"] == "websocket.disconnect":
                    break
                if "text" in message:
                    await socket.send_text(message["text"])
                else:
                    await socket.send_bytes(message["bytes"])
        except WebSocketDisconnect:
            pass

    async with TestClient(app) as client:
        browser = BrowserTestClient(client=client, headers={"X-Identity": "default"})
        async with browser.websocket_connect("/raw") as session:
            endpoint = session._app_task
            assert type(session) is WebSocketSession
            assert application_sockets[-1].headers["x-identity"] == "default"
            await session.send_json({"one": 1})
            assert await session.receive_json() == {"one": 1}
            await session.send_json({"two": 2}, mode="binary")
            assert await session.receive_json() == {"two": 2}
            await session.send_text("text")
            assert await session.receive_text() == "text"
            await session.send_str("alias")
            assert await session.receive_text() == "alias"
            await session.send_bytes(b"bytes")
            assert await session.receive_bytes() == b"bytes"
        await finished(endpoint)
        async with browser.websocket_connect(
            "/raw", headers={"X-Identity": "override"}
        ) as session:
            endpoint = session._app_task
            assert application_sockets[-1].headers["x-identity"] == "override"
            await session.close(1001)
        await finished(endpoint)


async def test_connection_payloads_and_finished_tasks_are_collectible_after_churn():
    manager = manager_for()
    references = []
    async with managed(manager):
        for index in range(12):
            socket = ControlledSocket()
            _, task = await open_socket(manager, socket, f"id-{index}")
            send = asyncio.create_task(
                manager.send_json_to_socket(socket, {"n": index})
            )
            assert await received(socket) == [{"n": index}]
            await send
            references.extend(
                (weakref.ref(socket), weakref.ref(task), weakref.ref(send))
            )
            await manager.close_socket(socket)
            await finished(task)
        assert manager.active_connections == []
        assert manager.get_room_list() == set()
        del socket, task, send
        await checkpoint()
        gc.collect()
        assert all(reference() is None for reference in references)


async def test_ready_writer_work_yields_to_an_independent_event_loop_task():
    manager = manager_for(queue_capacity=512)
    socket = ControlledSocket()
    async with managed(manager):
        _, task = await open_socket(manager, socket)
        connection = manager._connections[socket]
        for number in range(500):
            assert connection.enqueue(json.dumps({"n": number}))

        async def observer():
            await reached(socket.send_started)
            return len(socket.sent)

        observed = await observer()
        assert observed < 500
        values = await received(socket, 500)
        assert values == [{"n": number} for number in range(500)]
        assert socket.max_sending == 1
        await manager.close_socket(socket)
        await finished(task)
