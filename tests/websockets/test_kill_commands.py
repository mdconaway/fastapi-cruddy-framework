from pytest import mark
from fastapi_cruddy_framework import WebSocketSession, CONTROL_EVENT
from logging import getLogger

logger = getLogger(__name__)


@mark.asyncio
@mark.dependency()
async def test_kill_socket_id(authenticated_websocket_by_id: WebSocketSession):
    await authenticated_websocket_by_id.send_json(
        data={"route": CONTROL_EVENT, "type": "client_get_id", "target": "self"}
    )
    message = await authenticated_websocket_by_id.receive_json()
    assert isinstance(message["data"], dict)
    socket_id = message["data"]["id"]

    await authenticated_websocket_by_id.send_json(
        data={
            "route": CONTROL_EVENT,
            "type": "client_kill_socket_id",
            "target": socket_id,
        }
    )
    try:
        await authenticated_websocket_by_id.receive_json()
    except Exception as e:
        assert isinstance(e, Exception)
        assert e.args[0]["type"] == "websocket.close"


@mark.asyncio
@mark.dependency()
async def test_kill_client_id(authenticated_websocket_by_client: WebSocketSession):
    await authenticated_websocket_by_client.send_json(
        data={"route": CONTROL_EVENT, "type": "client_get_id", "target": "self"}
    )
    message = await authenticated_websocket_by_client.receive_json()
    assert isinstance(message["data"], dict)
    client_id = message["data"]["id"]

    await authenticated_websocket_by_client.send_json(
        data={
            "route": CONTROL_EVENT,
            "type": "client_kill_socket_id",
            "target": client_id,
        }
    )
    try:
        await authenticated_websocket_by_client.receive_json()
    except Exception as e:
        assert isinstance(e, Exception)
        assert e.args[0]["type"] == "websocket.close"


@mark.asyncio
@mark.dependency()
async def test_kill_room_socket_id(authenticated_websocket_by_id: WebSocketSession):
    room_name = "Casa Bonita"
    await authenticated_websocket_by_id.send_json(
        data={"route": CONTROL_EVENT, "type": "client_join_room", "target": room_name}
    )

    await authenticated_websocket_by_id.send_json(
        data={"route": CONTROL_EVENT, "type": "client_kill_room", "target": room_name}
    )
    try:
        await authenticated_websocket_by_id.receive_json()
    except Exception as e:
        assert isinstance(e, Exception)
        assert e.args[0]["type"] == "websocket.close"


@mark.asyncio
@mark.dependency()
async def test_kill_room_client_id(authenticated_websocket_by_client: WebSocketSession):
    room_name = "Casa Bonita"
    await authenticated_websocket_by_client.send_json(
        data={"route": CONTROL_EVENT, "type": "client_join_room", "target": room_name}
    )

    await authenticated_websocket_by_client.send_json(
        data={"route": CONTROL_EVENT, "type": "client_kill_room", "target": room_name}
    )
    try:
        await authenticated_websocket_by_client.receive_json()
    except Exception as e:
        assert isinstance(e, Exception)
        assert e.args[0]["type"] == "websocket.close"
