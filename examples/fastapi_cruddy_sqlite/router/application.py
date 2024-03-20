from typing_extensions import Annotated
from logging import getLogger
import examples.fastapi_cruddy_sqlite
from fastapi import APIRouter, WebSocket, Query
from fastapi_cruddy_framework import (
    uuid7,
    CreateRouterFromResources,
    CruddyResourceRegistry,
)
from examples.fastapi_cruddy_sqlite.controllers.graphql import graphql_controller
from examples.fastapi_cruddy_sqlite.services.websocket_1 import websocket_manager_1
from examples.fastapi_cruddy_sqlite.services.websocket_2 import websocket_manager_2
from examples.fastapi_cruddy_sqlite.utils.session import get_client_identity
from examples.fastapi_cruddy_sqlite.policies.verify_session import verify_session
from examples.fastapi_cruddy_sqlite.policies.naive_auth import naive_auth

logger = getLogger(__name__)

# Users can override expected default object each resource module exports
# via the named parameter common_resource_name such as:
# common_resource_name="OddResource"
# The finder function expects to find a CRUDDY resource object, complete
# with a controller property, which is a sub-router.
router: APIRouter = CreateRouterFromResources(
    application_module=examples.fastapi_cruddy_sqlite, resource_path="resources"
)

router.include_router(graphql_controller.router)


# You can now bind additional routes to "router" below, as its a normal APIRouter
@router.get("/health", tags=["application"])
async def is_healthy() -> bool:
    # This function will start returning True when the async sqlalchemy relationsip mapping is complete!
    return CruddyResourceRegistry.is_ready()


# Here, as an example, you can add a websocket route off of your base router!
# Cruddy ships with a fairly robust websocket manager for JSON communications.
# Similar to socket.io, it supports the concepts of "broadcast", "room", and direct "client" messaging.
# It also has powerful "kill" functions to terminate sockets based on any necessary server logic.
# The Cruddy websocket manager reflects all traffic through a Redis control-plane, meaning every
# websocket manager function will automatically scale horizontally as your servers scale!


@router.websocket("/ws1")
async def websocket_connector1(
    websocket: WebSocket, auth_token: Annotated[str | None, Query()] = None
):
    # If you write flexible policies, you can execute your normal auth chain on sockets too!
    # BEGIN POLICY CHAIN -------------------------------------------------------------------
    await verify_session(websocket=websocket)
    await naive_auth(
        websocket=websocket,
        credentials=None,
        auth_token=auth_token
        if auth_token
        else websocket.headers.get("authorization", "Bearer ").split(" ").pop(),
    )
    # END POLICY CHAIN ---------------------------------------------------------------------
    # You can generate your own socket ID if you want!
    # The manager will default to a uuid4
    override_socket_id = str(uuid7())
    # You can pass in a default message to auto-broadcast when the socket disconnects
    async with websocket_manager_1.connect(
        websocket,
        override_socket_id=override_socket_id,
        disconnect_message_type="socket_disconnect",
        disconnect_message_data={
            "socket_id": f"{override_socket_id}",
            "message": f"Websocket client {override_socket_id} disconnected",
        },
    ) as socket_id:
        logger.info("Socket %s connected", socket_id)
        await websocket_manager_1.broadcast(
            type="socket_connect", data={"socket_id": socket_id}
        )
        # The context manager will return the id of the socket, which could have been auto-generated
        # or overriden when .connect() was called. If code steps into this async context, it means
        # your socket is now fully connected, and has been added to the connected_sockets tracker.
        #
        # Any code written here will execute immediately AFTER accepting the socket connection, but
        # BEFORE the socket manager starts listening indefinitely for messages from the new client.
        # You can use this space to do additional setup, log information, or mutate the socket state.
    # Any code after the async context WILL NOT EXECUTE until the socket disconnects, whether that is
    # a voluntary disconnect, or a force disconnect. The websocket_manager has several methods to
    # force-kill sockets by id, room, or a custom identity function. You can do this in controller
    # functions, etc.


# The ws2 endpoint exists to test out the "custom" identity function of the websocket manager
@router.websocket("/ws2")
async def websocket_connector2(
    websocket: WebSocket, auth_token: Annotated[str | None, Query()] = None
):
    # BEGIN POLICY CHAIN -------------------------------------------------------------------
    await verify_session(websocket=websocket)
    await naive_auth(
        websocket=websocket,
        credentials=None,
        auth_token=auth_token
        if auth_token
        else websocket.headers.get("authorization", "Bearer ").split(" ").pop(),
    )
    # END POLICY CHAIN ---------------------------------------------------------------------
    # There is still a socket id associated with all sockets, even in custom mode
    override_socket_id = str(uuid7())
    client_id = get_client_identity(websocket)
    async with websocket_manager_2.connect(
        websocket,
        override_socket_id=override_socket_id,
        disconnect_message_type="socket_disconnect",
        disconnect_message_data={
            "socket_id": f"{override_socket_id}",
            "client_id": f"{client_id}",
            "message": f"Websocket client {override_socket_id} disconnected",
        },
    ) as socket_id:
        logger.info("Socket %s connected", socket_id)
        await websocket_manager_2.broadcast(
            type="socket_connect",
            data={"socket_id": socket_id, "client_id": f"{client_id}"},
        )
