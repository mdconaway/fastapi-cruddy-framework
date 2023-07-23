from pytest import mark
from fastapi import status
from tests.helpers import BrowserTestClient


@mark.asyncio
@mark.dependency()
async def test_policy_rejects(unauthenticated_client: BrowserTestClient):
    response = unauthenticated_client.get("/users/authorization")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@mark.asyncio
@mark.dependency(depends=["test_policy_rejects"])
async def test_policy_succeeds(authenticated_client: BrowserTestClient):
    response = authenticated_client.get("/users/authorization")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert "token" in result


@mark.asyncio
@mark.dependency(depends=["test_policy_succeeds"])
async def test_delete_authorization(authenticated_client: BrowserTestClient):
    # Kill session
    response = authenticated_client.delete("/users/authorization")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert "token" not in result
    # Regenerate session
    response = authenticated_client.get("/users/authorization")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert "token" in result
