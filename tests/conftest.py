from logging import getLogger
from asyncio import get_event_loop_policy, sleep
from pytest import fixture, mark
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx._models import Cookies
from fastapi_cruddy_framework import BrowserTestClient

logger = getLogger(__name__)

FAKE_AUTH_TOKEN = "somefaketokenvalue"
FAKE_AUTH_QP = f"?auth_token={FAKE_AUTH_TOKEN}"
FAKE_WEBSOCKET_HEADERS = {"Authorization": f"Bearer {FAKE_AUTH_TOKEN}"}


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
    with TestClient(app) as client:
        while client.get("/health").json() != True:
            await sleep(0.5)
        yield client


@fixture(scope="session", autouse=True)
@mark.asyncio
async def unauthenticated_client(client: TestClient):
    blank_client = BrowserTestClient(
        client=client, cookies=None, headers=None, ws_headers=None
    )
    yield blank_client


@fixture(scope="session", autouse=True)
@mark.asyncio
async def authenticated_client(client: TestClient):
    response = client.get(f"/users/authorization{FAKE_AUTH_QP}")
    client.cookies = Cookies()
    sessioned_client = BrowserTestClient(
        client=client,
        cookies=response.cookies,
        headers=FAKE_WEBSOCKET_HEADERS,
        ws_headers=FAKE_WEBSOCKET_HEADERS,
    )
    yield sessioned_client


@fixture(scope="module")
@mark.asyncio
async def authenticated_websocket(authenticated_client: BrowserTestClient):
    with authenticated_client.websocket_connect("/ws") as websocket:
        # For example: data = websocket.receive_json(mode="text")
        # Or websocket.send_json(data, mode="text")
        yield websocket
        websocket.close(code=1000)
