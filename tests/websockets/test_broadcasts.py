from pytest import mark
from fastapi_cruddy_framework import WebSocketSession, BROADCAST_EVENT


@mark.dependency()
async def test_send_broadcast(authenticated_websocket_by_id: WebSocketSession):
    datagram = {"message": "I am king of the sea people"}
    await authenticated_websocket_by_id.send_json(
        data={"route": BROADCAST_EVENT, "type": "peer_broadcast", "data": datagram}
    )
    message = await authenticated_websocket_by_id.receive_json()
    assert message["route"] == BROADCAST_EVENT
    assert message["type"] == "peer_broadcast"
    assert message["data"] == datagram
