## BrowserTestClient

The `BrowserTestClient` is a useful helper class to enable test suites to "boot" a Cruddy based app, and then use different virtual "browsers" to execute API tests against the app at the same time, against the same app instance. For usage examples, see `tests/conftest.py` and `tests/crud/*.py`. `BrowserTestClient` is designed to use the async ASGI server runner `TestClient`, which is re-exported from [async-asgi-testclient](https://github.com/vinissimus/async-asgi-testclient). Assuming your app has some level of authentication present you could setup your own conftest.py to look like:

```python
from logging import getLogger
from asyncio import get_event_loop_policy, sleep
from pytest import fixture, mark
from fastapi import FastAPI
from fastapi_cruddy_framework import TestClient, BrowserTestClient

logger = getLogger(__name__)

FAKE_AUTH_TOKEN = "somefaketokenvalue"
FAKE_AUTH_QP = f"?auth_token={FAKE_AUTH_TOKEN}"
FAKE_AUTH_HEADERS = {"Authorization": f"Bearer {FAKE_AUTH_TOKEN}"}


@fixture(scope="session", autouse=True)
def event_loop():
    loop = get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@fixture(scope="session", autouse=True)
@mark.asyncio
async def app():
    # Don't move this import!
    from your_app.main import app

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


@fixture(scope="function")
@mark.asyncio
async def authenticated_websocket(authenticated_client: BrowserTestClient):
    async with authenticated_client.websocket_connect("/ws") as websocket:
        # For example: data = await websocket.receive_json()
        # Or await websocket.send_json(data)
        # If your server sends any kind of "welcome" messages, make
        # sure you purge them here BEFORE yielding the socket back
        # to whatever function needs to run tests
        yield websocket

```

<p align="right">(<a href="#readme-top">back to top</a>)</p>
