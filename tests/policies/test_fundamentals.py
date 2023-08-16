from pytest import mark
from fastapi import status
from fastapi_cruddy_framework import BrowserTestClient


@mark.asyncio
@mark.dependency()
async def test_policy_rejects(unauthenticated_client: BrowserTestClient):
    response = await unauthenticated_client.get("/users/authorization")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@mark.asyncio
@mark.dependency(depends=["test_policy_rejects"])
async def test_policy_succeeds(authenticated_client: BrowserTestClient):
    response = await authenticated_client.get("/users/authorization")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert "token" in result


@mark.asyncio
@mark.dependency(depends=["test_policy_succeeds"])
async def test_delete_authorization(authenticated_client: BrowserTestClient):
    # Kill session
    response = await authenticated_client.delete("/users/authorization")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert "token" not in result
    # Regenerate session
    response = await authenticated_client.get("/users/authorization")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert "token" in result
