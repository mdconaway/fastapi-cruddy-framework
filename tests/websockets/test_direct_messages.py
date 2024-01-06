from pytest import mark
from fastapi_cruddy_framework import WebSocketSession, CONTROL_EVENT, CLIENT_EVENT


@mark.asyncio
@mark.dependency()
async def test_send_dms(
    authenticated_websocket_by_id: WebSocketSession,
    authenticated_websocket_by_client: WebSocketSession,
):
    datagram = {"message": "I am king of the sea people"}
    await authenticated_websocket_by_id.send_json(
        data={"route": CONTROL_EVENT, "type": "client_get_id", "target": "self"}
    )
    message = await authenticated_websocket_by_id.receive_json()
    assert isinstance(message["data"], dict)
    socket_id = message["data"]["id"]

    await authenticated_websocket_by_client.send_json(
        data={"route": CONTROL_EVENT, "type": "client_get_id", "target": "self"}
    )
    message = await authenticated_websocket_by_client.receive_json()
    assert isinstance(message["data"], dict)
    client_id = message["data"]["id"]

    # Test sending a DM by default socket_id
    await authenticated_websocket_by_id.send_json(
        data={
            "route": CLIENT_EVENT,
            "type": "direct_message",
            "target": socket_id,
            "data": datagram,
        }
    )
    message = await authenticated_websocket_by_id.receive_json()
    assert message["route"] == CLIENT_EVENT
    assert message["target"] == socket_id
    assert message["sender"] == socket_id
    assert message["type"] == "direct_message"
    assert message["data"] == datagram

    # Test sending a DM by custom client id
    await authenticated_websocket_by_client.send_json(
        data={
            "route": CLIENT_EVENT,
            "type": "direct_message",
            "target": client_id,
            "data": datagram,
        }
    )
    message = await authenticated_websocket_by_client.receive_json()
    assert message["route"] == CLIENT_EVENT
    assert message["target"] == client_id
    assert message["sender"] == client_id
    assert message["type"] == "direct_message"
    assert message["data"] == datagram
