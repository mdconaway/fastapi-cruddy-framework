from pytest import mark
from fastapi_cruddy_framework import (
    WebSocketSession,
    CONTROL_EVENT,
    ROOM_EVENT,
    CLIENT_EVENT,
)


@mark.asyncio
@mark.dependency()
async def test_room_join_leave_message_id(
    authenticated_websocket_by_id: WebSocketSession,
):
    datagram = {"message": "I am king of the sea people"}
    room_name = "Casa Bonita"

    await authenticated_websocket_by_id.send_json(
        data={"route": CONTROL_EVENT, "type": "client_get_id", "target": "self"}
    )
    message = await authenticated_websocket_by_id.receive_json()
    assert isinstance(message["data"], dict)
    socket_id = message["data"]["id"]

    await authenticated_websocket_by_id.send_json(
        data={"route": CONTROL_EVENT, "type": "client_join_room", "target": room_name}
    )

    # Test sending a DM by default socket_id
    await authenticated_websocket_by_id.send_json(
        data={
            "route": ROOM_EVENT,
            "type": "room_message",
            "target": room_name,
            "data": datagram,
        }
    )
    message = await authenticated_websocket_by_id.receive_json()
    assert message["route"] == ROOM_EVENT
    assert message["target"] == room_name
    assert message["sender"] == socket_id
    assert message["type"] == "room_message"
    assert message["data"] == datagram

    await authenticated_websocket_by_id.send_json(
        data={"route": CONTROL_EVENT, "type": "client_leave_room", "target": room_name}
    )

    await authenticated_websocket_by_id.send_json(
        data={
            "route": ROOM_EVENT,
            "type": "room_message",
            "target": room_name,
            "data": datagram,
        }
    )
    await authenticated_websocket_by_id.send_json(
        data={
            "route": CLIENT_EVENT,
            "type": "direct_message",
            "target": socket_id,
            "data": datagram,
        }
    )

    # Reading the messages after leaving the room, the first message in the queue should be the direct message
    message = await authenticated_websocket_by_id.receive_json()
    assert message["route"] == CLIENT_EVENT
    assert message["target"] == socket_id
    assert message["sender"] == socket_id
    assert message["type"] == "direct_message"
    assert message["data"] == datagram


@mark.asyncio
@mark.dependency()
async def test_room_join_leave_message_client(
    authenticated_websocket_by_client: WebSocketSession,
):
    datagram = {"message": "I am king of the sea people"}
    room_name = "Casa Bonita"

    await authenticated_websocket_by_client.send_json(
        data={"route": CONTROL_EVENT, "type": "client_get_id", "target": "self"}
    )
    message = await authenticated_websocket_by_client.receive_json()
    assert isinstance(message["data"], dict)
    client_id = message["data"]["id"]

    await authenticated_websocket_by_client.send_json(
        data={"route": CONTROL_EVENT, "type": "client_join_room", "target": room_name}
    )

    # Test sending a DM by default socket_id
    await authenticated_websocket_by_client.send_json(
        data={
            "route": ROOM_EVENT,
            "type": "room_message",
            "target": room_name,
            "data": datagram,
        }
    )
    message = await authenticated_websocket_by_client.receive_json()
    assert message["route"] == ROOM_EVENT
    assert message["target"] == room_name
    assert message["sender"] == client_id
    assert message["type"] == "room_message"
    assert message["data"] == datagram

    await authenticated_websocket_by_client.send_json(
        data={"route": CONTROL_EVENT, "type": "client_leave_room", "target": room_name}
    )

    await authenticated_websocket_by_client.send_json(
        data={
            "route": ROOM_EVENT,
            "type": "room_message",
            "target": room_name,
            "data": datagram,
        }
    )
    await authenticated_websocket_by_client.send_json(
        data={
            "route": CLIENT_EVENT,
            "type": "direct_message",
            "target": client_id,
            "data": datagram,
        }
    )

    # Reading the messages after leaving the room, the first message in the queue should be the direct message
    message = await authenticated_websocket_by_client.receive_json()
    assert message["route"] == CLIENT_EVENT
    assert message["target"] == client_id
    assert message["sender"] == client_id
    assert message["type"] == "direct_message"
    assert message["data"] == datagram
