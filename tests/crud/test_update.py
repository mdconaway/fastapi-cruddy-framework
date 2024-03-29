from pytest import mark
from fastapi import status
from fastapi_cruddy_framework import BrowserTestClient

group_id = None
user_id = None
post_id = None


@mark.dependency()
async def test_setup(authenticated_client: BrowserTestClient):
    global group_id
    global user_id
    global post_id

    response = await authenticated_client.post(
        f"/groups",
        json={"group": {"name": "Supporting Characters Anonymous"}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["group"], dict)
    group_id = result["group"]["id"]

    response = await authenticated_client.post(
        f"/users",
        json={
            "user": {
                "first_name": "Tom",
                "last_name": "Bombadil",
                "email": "tom.bombadil@cruddy-framework.com",
                "is_active": True,
                "is_superuser": False,
                "birthdate": "2023-07-22T14:43:31.038Z",
                "phone": "888-555-5555",
                "state": "Withywindle River Valley",
                "country": "Middle Earth",
                "address": "1 Withywindle Way",
                "password": "nevergonnaletyoudown",
                "groups": [group_id],
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["user"], dict)
    user_id = result["user"]["id"]

    response = await authenticated_client.post(
        f"/posts",
        json={
            "post": {
                "user_id": user_id,
                "content": "Old Tom Bombadil is a merry fellow, Bright blue his jacket is, and his boots are yellow. None has ever caught him yet, for Tom, he is the Master: His songs are stronger songs, and his feet are faster.",
                "tags": {"categories": ["blog"]},
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["post"], dict)
    post_id = result["post"]["id"]


@mark.dependency(depends=["test_setup"])
async def test_update_group(authenticated_client: BrowserTestClient):
    global group_id
    response = await authenticated_client.patch(
        f"/groups/{group_id}",
        json={"group": {"id": "woopsie", "name": "Forgotten Characters Anonymous"}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["group"]["name"] == "Forgotten Characters Anonymous"
    assert result["group"]["id"] == group_id


@mark.dependency(depends=["test_update_group"])
async def test_update_user(authenticated_client: BrowserTestClient):
    global user_id
    response = await authenticated_client.patch(
        f"/users/{user_id}",
        json={
            "user": {
                "id": "woopsie",
                "first_name": "Tim",
                "last_name": "Benzedrino",
                "email": "tim.benzedrino@cruddy-framework.com",
                "is_active": True,
                "is_superuser": False,
                "birthdate": "2023-07-22T14:43:31.038Z",
                "phone": "888-555-5555",
                "state": "Withywindle River Valley",
                "country": "Middle Earth",
                "address": "1 Withywindle Way",
                "password": "nevergonnagiveyouup",
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["user"]["first_name"] == "Tim"
    assert result["user"]["id"] == user_id


@mark.dependency(depends=["test_update_user"])
async def test_update_post(authenticated_client: BrowserTestClient):
    global user_id
    global post_id
    response = await authenticated_client.patch(
        f"/posts/{post_id}",
        json={
            "post": {
                "id": "woopsie",
                "user_id": user_id,
                "content": "Toke a lid, smoke a lid, pop the mescalino! ...Hop a hill! Pop a pill! For old Tim Benzedrino!",
                "tags": {"categories": ["blog"]},
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert (
        result["post"]["content"]
        == "Toke a lid, smoke a lid, pop the mescalino! ...Hop a hill! Pop a pill! For old Tim Benzedrino!"
    )
    assert result["post"]["id"] == post_id


# The below functions are mainly cleanup based on the create functions above


@mark.dependency(depends=["test_update_post"])
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
