from json import dumps
from pytest import mark
from fastapi import status
from fastapi_cruddy_framework import BrowserTestClient
from examples.fastapi_cruddy_sqlite.config.general import general

group_id = None
alt_group_id = None
tertiary_group_id = None
user_id = None
alt_user_id = None
post_id = None


@mark.asyncio
@mark.dependency()
async def test_setup(authenticated_client: BrowserTestClient):
    global group_id
    global alt_group_id
    global tertiary_group_id
    global user_id
    global alt_user_id
    global post_id

    response = await authenticated_client.post(
        f"/groups",
        json={"group": {"name": "Shire Lovers Anonymous"}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["group"], dict)
    group_id = result["group"]["id"]

    response = await authenticated_client.post(
        f"/groups",
        json={"group": {"name": "Shire Haters Anonymous"}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["group"], dict)
    alt_group_id = result["group"]["id"]

    response = await authenticated_client.post(
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

    response = await authenticated_client.post(
        f"/users",
        json={
            "user": {
                "first_name": "Sauron",
                "last_name": "The Artist Formerly Known As",
                "email": "theartistformerlyknownassauon@cruddy-framework.com",
                "is_active": True,
                "is_superuser": True,
                "birthdate": "2023-07-22T14:43:31.038Z",
                "phone": "888-555-5555",
                "state": "Mordor",
                "country": "Middle Earth",
                "address": "1 Volcano Way",
                "password": "peskyhobbits",
                "groups": [alt_group_id],
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["user"], dict)
    alt_user_id = result["user"]["id"]

    response = await authenticated_client.post(
        f"/groups",
        json={
            "group": {
                "name": "Good and Evil Anonymous",
                "users": [user_id, alt_user_id],
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["group"], dict)
    tertiary_group_id = result["group"]["id"]

    response = await authenticated_client.post(
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
@mark.dependency(depends=["test_setup"])
async def test_get_groups_through_user(authenticated_client: BrowserTestClient):
    global user_id
    global group_id
    response = await authenticated_client.get(f"/users/{user_id}/groups")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["groups"]) is 2
    assert result["groups"][0]["id"] in [tertiary_group_id, group_id]
    assert result["groups"][1]["id"] in [tertiary_group_id, group_id]
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is general.DEFAULT_LIMIT
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 2


@mark.asyncio
@mark.dependency(depends=["test_get_groups_through_user"])
async def test_inspect_artificial_relationship(authenticated_client: BrowserTestClient):
    global user_id
    response = await authenticated_client.get(f"/users/{user_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["user"]["id"] == user_id
    assert len(result["user"]["links"]) > 1
    assert result["user"]["links"]["others"] == f"/users/{user_id}/others"


@mark.asyncio
@mark.dependency(depends=["test_inspect_artificial_relationship"])
async def test_get_posts_through_user(authenticated_client: BrowserTestClient):
    global user_id
    global post_id
    response = await authenticated_client.get(f"/users/{user_id}/posts")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["posts"][0]["id"] == post_id
    assert len(result["posts"]) is 1
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is general.DEFAULT_LIMIT
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 1


@mark.asyncio
@mark.dependency(depends=["test_get_posts_through_user"])
async def test_get_user_through_post(authenticated_client: BrowserTestClient):
    global user_id
    global post_id
    response = await authenticated_client.get(f"/posts/{post_id}/user")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["user"], dict)
    assert result["user"]["id"] == user_id


@mark.asyncio
@mark.dependency(depends=["test_get_user_through_post"])
async def test_get_users_through_group(authenticated_client: BrowserTestClient):
    global user_id
    global group_id
    response = await authenticated_client.get(f"/groups/{group_id}/users")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["users"]) is 1
    assert result["users"][0]["id"] == user_id
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is general.DEFAULT_LIMIT
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 1


@mark.asyncio
@mark.dependency(depends=["test_get_users_through_group"])
async def test_alter_users_in_group(authenticated_client: BrowserTestClient):
    global group_id
    global user_id
    global alt_user_id
    response = await authenticated_client.patch(
        f"/groups/{group_id}",
        json={
            "group": {
                "id": "woopsie",
                "users": [user_id, alt_user_id],
                "name": "Shire Watchers Anonymous",
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK

    response = await authenticated_client.get(
        f"/groups/{group_id}/users?sort=first_name asc"
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["users"]) is 2
    assert result["users"][0]["id"] == user_id
    assert result["users"][1]["id"] == alt_user_id
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is general.DEFAULT_LIMIT
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 2

    response = await authenticated_client.get(
        f"/groups/{group_id}/users?where={dumps([{'email': {'*contains': 'cruddy-framework'}}, {'email': {'*contains': 'com'}}])}&sort=first_name asc"
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["users"]) is 2
    assert result["users"][0]["id"] == user_id
    assert result["users"][1]["id"] == alt_user_id
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is general.DEFAULT_LIMIT
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 2

    response = await authenticated_client.get(
        f"/groups/{group_id}/users?where={dumps([{'email': {'*contains': 'cruddy-framework'}}, {'email': {'*contains': 'frodo.baggins'}}])}&sort=first_name asc"
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["users"]) is 1
    assert result["users"][0]["id"] == user_id
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is general.DEFAULT_LIMIT
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 1

    response = await authenticated_client.get(
        f"/groups/{group_id}/users?where={dumps({'email': {'*contains': 'frodo.baggins'}})}&sort=first_name asc"
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["users"]) is 1
    assert result["users"][0]["id"] == user_id
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is general.DEFAULT_LIMIT
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 1


@mark.asyncio
@mark.dependency(depends=["test_alter_users_in_group"])
async def test_filter_users_in_group(authenticated_client: BrowserTestClient):
    global user_id
    global alt_user_id
    global tertiary_group_id

    response = await authenticated_client.get(f"/groups/{tertiary_group_id}/users")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["users"]) is 2

    where = dumps({"id": alt_user_id})
    response = await authenticated_client.get(
        f"/groups/{tertiary_group_id}/users?where={where}"
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["users"]) is 1
    assert result["users"][0]["id"] == alt_user_id

    where = dumps({"id": user_id})
    response = await authenticated_client.get(
        f"/groups/{tertiary_group_id}/users?where={where}"
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["users"]) is 1
    assert result["users"][0]["id"] == user_id

    where = dumps({"*or": [{"id": user_id}, {"id": alt_user_id}]})
    response = await authenticated_client.get(
        f"/groups/{tertiary_group_id}/users?where={where}&sort=first_name asc"
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["users"]) is 2
    assert result["users"][0]["id"] == user_id
    assert result["users"][1]["id"] == alt_user_id

    where = dumps(
        {
            "*or": [
                {"first_name": {"*contains": "rodo"}},
                {"first_name": {"*contains": "auron"}},
            ]
        }
    )
    response = await authenticated_client.get(
        f"/groups/{tertiary_group_id}/users?where={where}&sort=first_name desc"
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["users"]) is 2
    assert result["users"][0]["id"] == alt_user_id
    assert result["users"][1]["id"] == user_id

    where = dumps(
        {
            "*or": [
                {"first_name": {"*contains": "rodo"}},
                {"first_name": {"*contains": "auron"}},
            ]
        }
    )
    response = await authenticated_client.get(
        f"/groups/{tertiary_group_id}/users?where={where}&columns=first_name"
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["users"]) is 2
    assert len(result["users"][0].keys()) is 3
    assert len(result["users"][1].keys()) is 3
    assert "id" in result["users"][0].keys()
    assert "first_name" in result["users"][0].keys()
    assert "links" in result["users"][0].keys()
    assert "id" in result["users"][1].keys()
    assert "first_name" in result["users"][1].keys()
    assert "links" in result["users"][1].keys()

    where = dumps(
        {
            "*or": [
                {"first_name": {"*contains": "rodo"}},
                {"first_name": {"*contains": "auron"}},
            ]
        }
    )
    response = await authenticated_client.get(
        f"/groups/{tertiary_group_id}/users?where={where}&sort=first_name asc&limit=1"
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["users"]) is 1
    assert result["users"][0]["id"] == user_id
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is 1
    assert result["meta"]["pages"] is 2
    assert result["meta"]["records"] is 2


@mark.asyncio
@mark.dependency(depends=["test_filter_users_in_group"])
async def test_remove_from_all_groups(authenticated_client: BrowserTestClient):
    global alt_user_id
    global alt_group_id

    response = await authenticated_client.get(f"/users/{alt_user_id}/groups")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["groups"]) is 3

    response = await authenticated_client.patch(
        f"/users/{alt_user_id}",
        json={
            "user": {
                "id": "woopsie",
                "first_name": "Sauron",
                "last_name": "The Artist Formerly Known As",
                "email": "theartistformerlyknownassauon@cruddy-framework.com",
                "is_active": True,
                "is_superuser": True,
                "birthdate": "2023-07-22T14:43:31.038Z",
                "phone": "888-555-5555",
                "state": "Mordor",
                "country": "Middle Earth",
                "address": "1 Volcano Way",
                "password": "peskyhobbits",
                "groups": [],
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK

    response = await authenticated_client.get(f"/users/{alt_user_id}/groups")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["groups"]) is 0

    response = await authenticated_client.get(f"/groups/{alt_group_id}/users")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["users"]) is 0


@mark.asyncio
@mark.dependency(depends=["test_remove_from_all_groups"])
async def test_guarded_relationship(authenticated_client: BrowserTestClient):
    global post_id
    global user_id
    global alt_user_id

    response = await authenticated_client.patch(
        f"/posts/{post_id}",
        json={
            "post": {
                "user_id": alt_user_id,
                "content": "Sauron sees Bilbo.",
                "tags": {"categories": ["blog"]},
            }
        },
    )

    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["post"]["user_id"] == user_id

    response = await authenticated_client.patch(
        f"/users/{alt_user_id}",
        json={
            "user": {
                "id": "woopsie",
                "first_name": "Sauron",
                "last_name": "The Artist Formerly Known As",
                "email": "theartistformerlyknownassauon@cruddy-framework.com",
                "is_active": True,
                "is_superuser": True,
                "birthdate": "2023-07-22T14:43:31.038Z",
                "phone": "888-555-5555",
                "state": "Mordor",
                "country": "Middle Earth",
                "address": "1 Volcano Way",
                "password": "peskyhobbits",
                "posts": [post_id],
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK

    response = await authenticated_client.get(f"/posts/{post_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["post"]["user_id"] == user_id


# The below functions are mainly cleanup based on the create functions above
@mark.asyncio
@mark.dependency(depends=["test_guarded_relationship"])
async def test_cleanup(authenticated_client: BrowserTestClient):
    global user_id
    global alt_user_id
    global post_id
    global group_id
    global alt_group_id
    global tertiary_group_id

    response = await authenticated_client.delete(f"/users/{user_id}")
    # This should return a 405 as delete-user is blocked using a framework feature!
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    response = await authenticated_client.delete(f"/users/{alt_user_id}")
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

    response = await authenticated_client.delete(f"/groups/{alt_group_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["group"]["id"] == alt_group_id

    response = await authenticated_client.delete(f"/groups/{tertiary_group_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["group"]["id"] == tertiary_group_id
