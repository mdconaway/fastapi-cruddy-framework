from pytest import mark
from fastapi import status
from fastapi_cruddy_framework import BrowserTestClient

group_id = None
user_id = None
post_id = None


@mark.asyncio
@mark.dependency()
async def test_setup(authenticated_client: BrowserTestClient):
    global group_id
    global user_id
    global post_id

    response = authenticated_client.post(
        f"/groups",
        json={"group": {"name": "Ring-bearers Anonymous"}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["group"], dict)
    group_id = result["group"]["id"]

    response = authenticated_client.post(
        f"/users",
        json={
            "user": {
                "first_name": "Sméagol",
                "last_name": "Stoorish",
                "email": "smeagol.stoorish@cruddy-framework.com",
                "is_active": True,
                "is_superuser": False,
                "birthdate": "2023-07-22T14:43:31.038Z",
                "phone": "888-555-5555",
                "state": "Eriador",
                "country": "Middle Earth",
                "address": "1200 Gladden Fields",
                "password": "wewantsitback",
                "groups": [group_id],
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["user"], dict)
    user_id = result["user"]["id"]

    response = authenticated_client.post(
        f"/posts",
        json={
            "post": {
                "user_id": user_id,
                "content": "Thief, Thief, Thief! Baggins! We hates it, we hates it, we hates it forever!",
                "tags": {"categories": ["blog"]},
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["post"], dict)
    post_id = result["post"]["id"]


@mark.asyncio
@mark.dependency(depends=["test_setup"])
async def test_delete_user(authenticated_client: BrowserTestClient):
    global user_id
    response = authenticated_client.delete(f"/users/{user_id}")
    # This should return a 405 as delete-user is blocked using a framework feature!
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    response = authenticated_client.delete(f"/users/purge/{user_id}?confirm=Y")
    # This should return a 200 as this is an overriden action!
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["user"]["id"] == user_id


@mark.asyncio
@mark.dependency(depends=["test_delete_user"])
async def test_delete_post(authenticated_client: BrowserTestClient):
    global post_id
    response = authenticated_client.delete(f"/posts/{post_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["post"]["id"] == post_id


@mark.asyncio
@mark.dependency(depends=["test_delete_post"])
async def test_delete_group(authenticated_client: BrowserTestClient):
    global group_id
    response = authenticated_client.delete(f"/groups/{group_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["group"]["id"] == group_id
