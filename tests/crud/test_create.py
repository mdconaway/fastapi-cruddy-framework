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
        json={"group": {"name": "Hobbits Anonymous"}},
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
                "first_name": "Bilbo",
                "last_name": "Baggins",
                "email": "bilbo.baggins@cruddy-framework.com",
                "is_active": True,
                "is_superuser": False,
                "birthdate": "2023-07-22T14:43:31.038Z",
                "phone": "888-555-5555",
                "state": "Eriador",
                "country": "Middle Earth",
                "address": "101 Shire Way",
                "password": "myprecious",
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
                "content": "Whatup shire homies? I'm gonna be out for a while. I have to take some stupid ring to a lava pit or something",
                "tags": {"categories": ["blog"]},
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["post"], dict)
    post_id = result["post"]["id"]


# The below functions are mainly cleanup based on the create functions above


@mark.dependency(depends=["test_create_post"])
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
