from json import dumps
from pytest import mark
from fastapi import status
from fastapi_cruddy_framework import BrowserTestClient

group_id = None
user_id = None
post_id = None


@mark.dependency()
async def test_create_group(authenticated_client: BrowserTestClient):
    global group_id
    response = await authenticated_client.post(
        f"/groups",
        json={"group": {"name": "Followers Anonymous"}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["group"], dict)
    group_id = result["group"]["id"]


@mark.dependency(depends=["test_create_group"])
async def test_create_user(authenticated_client: BrowserTestClient):
    global group_id
    global user_id
    response = await authenticated_client.post(
        f"/users",
        json={
            "user": {
                "first_name": "Samwise",
                "last_name": "Gamgee",
                "email": "samwise.gamgee@cruddy-framework.com",
                "is_active": True,
                "is_superuser": False,
                "birthdate": "2023-07-22T14:43:31.038Z",
                "phone": "888-555-5555",
                "state": "Eriador",
                "country": "Middle Earth",
                "address": "103 Shire Way",
                "password": "frodosentourage",
                "groups": [group_id],
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["user"], dict)
    user_id = result["user"]["id"]


@mark.dependency(depends=["test_create_user"])
async def test_create_post(authenticated_client: BrowserTestClient):
    global user_id
    global post_id
    response = await authenticated_client.post(
        f"/posts",
        json={
            "post": {
                "user_id": user_id,
                "content": "Has anyone seen Frodo lately?",
                "tags": {"categories": ["blog"]},
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["post"], dict)
    post_id = result["post"]["id"]


@mark.dependency(depends=["test_create_post"])
async def test_get_user_by_id(authenticated_client: BrowserTestClient):
    global user_id
    response = await authenticated_client.get(f"/users/{user_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["user"]["id"] == user_id
    assert result["user"]["first_name"] == "Samwise"


@mark.dependency(depends=["test_get_user_by_id"])
async def test_get_user_by_id_restricted(authenticated_client: BrowserTestClient):
    global user_id
    where = dumps({"first_name": "Sauron"})
    response = await authenticated_client.get(f"/users/{user_id}?where={where}")
    # This should probably be a 404 instead of 200
    assert response.status_code == status.HTTP_404_NOT_FOUND
    result = response.json()
    assert isinstance(result, dict)
    assert len(result.keys()) is 1
    assert "detail" in result.keys()


@mark.dependency(depends=["test_get_user_by_id_restricted"])
async def test_get_group_by_id(authenticated_client: BrowserTestClient):
    global group_id
    response = await authenticated_client.get(f"/groups/{group_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["group"]["id"] == group_id
    assert result["group"]["name"] == "Followers Anonymous"


@mark.dependency(depends=["test_get_group_by_id"])
async def test_get_post_by_id(authenticated_client: BrowserTestClient):
    global post_id
    response = await authenticated_client.get(f"/posts/{post_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["post"]["id"] == post_id
    assert result["post"]["content"] == "Has anyone seen Frodo lately?"


# The below functions are mainly cleanup based on the create functions above


@mark.dependency(depends=["test_get_post_by_id"])
async def test_cleanup(authenticated_client: BrowserTestClient):
    global user_id
    global post_id
    global group_id

    response = await authenticated_client.delete(f"/users/{user_id}")
    # This should return a 405 as delete-user is blocked using a framework feature!
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    response = await authenticated_client.delete(f"/users/purge/{user_id}?confirm=Y")
    # This should return a 200 as this is an overriden action!
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["user"]["id"] == user_id

    response = await authenticated_client.delete(f"/posts/{post_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["post"]["id"] == post_id

    response = await authenticated_client.delete(f"/groups/{group_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["group"]["id"] == group_id
