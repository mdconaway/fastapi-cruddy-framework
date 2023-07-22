from pytest import mark
from fastapi import status
from tests.helpers import BrowserTestClient

group_id = None
user_id = None
post_id = None


@mark.asyncio
@mark.dependency()
async def test_create_group(authenticated_client: BrowserTestClient):
    global group_id
    response = authenticated_client.post(
        f"/groups",
        json={"group": {"name": "Shire Lovers Anonymous"}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["group"], dict)
    group_id = result["group"]["id"]


@mark.asyncio
@mark.dependency(depends=["test_create_group"])
async def test_create_user(authenticated_client: BrowserTestClient):
    global group_id
    global user_id
    response = authenticated_client.post(
        f"/users",
        json={
            "user": {
                "first_name": "Frodo",
                "last_name": "Baggins",
                "email": "frodo.baggins@cruddy-framework.com",
                "is_active": True,
                "is_superuser": False,
                "birthdate": "2023-07-22T14:43:31.038Z",
                "phone": "888-555-5555",
                "state": "Eriador",
                "country": "Middle Earth",
                "address": "102 Shire Way",
                "password": "imissmyring",
                "groups": [group_id],
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["user"], dict)
    user_id = result["user"]["id"]


@mark.asyncio
@mark.dependency(depends=["test_create_user"])
async def test_create_post(authenticated_client: BrowserTestClient):
    global user_id
    global post_id
    response = authenticated_client.post(
        f"/posts",
        json={
            "post": {
                "user_id": user_id,
                "content": "Has anyone seen Bilbo lately?",
                "tags": {"categories": ["blog"]},
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["post"], dict)
    post_id = result["post"]["id"]


@mark.asyncio
@mark.dependency(depends=["test_create_post"])
async def test_get_groups_through_user(authenticated_client: BrowserTestClient):
    global user_id
    global group_id
    response = authenticated_client.get(f"/users/{user_id}/groups")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["groups"][0]["id"] == group_id
    assert len(result["groups"]) is 1
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is 10
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 1


@mark.asyncio
@mark.dependency(depends=["test_get_groups_through_user"])
async def test_get_posts_through_user(authenticated_client: BrowserTestClient):
    global user_id
    global post_id
    response = authenticated_client.get(f"/users/{user_id}/posts")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["posts"][0]["id"] == post_id
    assert len(result["posts"]) is 1
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is 10
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 1


@mark.asyncio
@mark.dependency(depends=["test_get_posts_through_user"])
async def test_get_user_through_post(authenticated_client: BrowserTestClient):
    global user_id
    global post_id
    response = authenticated_client.get(f"/posts/{post_id}/user")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["user"], dict)
    assert result["user"]["id"] == user_id


@mark.asyncio
@mark.dependency(depends=["test_get_user_through_post"])
async def test_get_users_through_group(authenticated_client: BrowserTestClient):
    global user_id
    global group_id
    response = authenticated_client.get(f"/groups/{group_id}/users")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["users"][0]["id"] == user_id
    assert len(result["users"]) is 1
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is 10
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 1


# The below functions are mainly cleanup based on the create functions above
@mark.asyncio
@mark.dependency(depends=["test_get_users_through_group"])
async def test_cleanup(authenticated_client: BrowserTestClient):
    global user_id
    global post_id
    global group_id

    response = authenticated_client.delete(f"/users/{user_id}")
    # This should return a 405 as delete-user is blocked using a framework feature!
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    response = authenticated_client.delete(f"/posts/{post_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["post"]["id"] == post_id

    response = authenticated_client.delete(f"/groups/{group_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["group"]["id"] == group_id
