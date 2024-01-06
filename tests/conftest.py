from logging import getLogger
from asyncio import get_event_loop_policy, sleep
from pytest import fixture, mark
from fastapi import FastAPI
from fastapi_cruddy_framework import TestClient, BrowserTestClient

logger = getLogger(__name__)

FAKE_AUTH_TOKEN = "somefaketokenvalue"
FAKE_AUTH_QP = f"?auth_token={FAKE_AUTH_TOKEN}"
FAKE_AUTH_HEADERS = {"Authorization": f"Bearer {FAKE_AUTH_TOKEN}"}

FAKE_AUTH_TOKEN2 = "anotherfaketokenvalue"
FAKE_AUTH_QP2 = f"?auth_token={FAKE_AUTH_TOKEN2}"
FAKE_AUTH_HEADERS2 = {"Authorization": f"Bearer {FAKE_AUTH_TOKEN2}"}


@fixture(scope="session", autouse=True)
def event_loop():
    loop = get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@fixture(scope="session", autouse=True)
@mark.asyncio
async def app():
    # Don't move this import!
    from examples.fastapi_cruddy_sqlite.main import app

    yield app


@fixture(scope="session", autouse=True)
@mark.asyncio
async def client(app: FastAPI):
    # By using "with" the FastAPI app launch hook is run, connecting the application router
    async with TestClient(app, use_cookies=False) as client:
        while (await client.get("/health")).json() != True:
            await sleep(0.5)
        yield client


@fixture(scope="session", autouse=True)
@mark.asyncio
async def unauthenticated_client(client: TestClient):
    blank_client = BrowserTestClient(client=client, cookies=None, headers=None)
    yield blank_client


@fixture(scope="session", autouse=True)
@mark.asyncio
async def authenticated_client(client: TestClient):
    sessioned_client = BrowserTestClient(
        client=client, cookies=None, headers=FAKE_AUTH_HEADERS
    )
    await sessioned_client.get(f"/users/authorization{FAKE_AUTH_QP}")
    yield sessioned_client


@fixture(scope="session", autouse=True)
@mark.asyncio
async def authenticated_client2(client: TestClient):
    sessioned_client = BrowserTestClient(
        client=client, cookies=None, headers=FAKE_AUTH_HEADERS2
    )
    await sessioned_client.get(f"/users/authorization{FAKE_AUTH_QP2}")
    yield sessioned_client


@fixture(scope="function")
@mark.asyncio
async def authenticated_websocket_by_id(authenticated_client: BrowserTestClient):
    async with authenticated_client.websocket_connect("/ws1") as websocket:
        # For example: data = await websocket.receive_json()
        # Or await websocket.send_json(data)
        # If your server sends any kind of "welcome" messages, make
        # sure you purge them here BEFORE yielding the socket back
        # to whatever function needs to run tests
        # Like so:
        message = await websocket.receive_json()
        while message["type"] != "socket_connect":
            message = await websocket.receive_json()
        # This will ensure the socket is fully drained before handing it
        # back to the test function.
        yield websocket


@fixture(scope="function")
@mark.asyncio
async def authenticated_websocket_by_client(authenticated_client2: BrowserTestClient):
    async with authenticated_client2.websocket_connect("/ws2") as websocket:
        message = await websocket.receive_json()
        while message["type"] != "socket_connect":
            message = await websocket.receive_json()
        yield websocket
