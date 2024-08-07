from json import dumps
from pytest import mark
from fastapi import status
from fastapi_cruddy_framework import BrowserTestClient, uuid7
from examples.fastapi_cruddy_sqlite.config.general import general

group_id = None
alt_group_id = None
tertiary_group_id = None
user_id = None
alt_user_id = None
post_id = None


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

    # Let's add some comments
    await authenticated_client.post(
        "/comments",
        json={
            "comment": {
                "created_by_id": user_id,
                "entity_id": post_id,
                "text": "What a great post!",
            }
        },
    )
    await authenticated_client.post(
        "/comments",
        json={
            "comment": {
                "created_by_id": alt_user_id,
                "entity_id": post_id,
                "text": "You are wrong. I hate this post",
            }
        },
    )
    await authenticated_client.post(
        "/comments",
        json={
            "comment": {
                "created_by_id": alt_user_id,
                "entity_id": group_id,
                "text": "Is anyone still managing this group?? Let. Me. Leave!",
            }
        },
    )


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


@mark.dependency(depends=["test_get_groups_through_user"])
async def test_inspect_artificial_relationship(authenticated_client: BrowserTestClient):
    global user_id
    response = await authenticated_client.get(f"/users/{user_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["user"]["id"] == user_id
    assert len(result["user"]["links"]) > 1
    assert result["user"]["links"]["others"] == f"/users/{user_id}/others"


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


@mark.dependency(depends=["test_get_posts_through_user"])
async def test_get_user_through_post(authenticated_client: BrowserTestClient):
    global user_id
    global post_id
    response = await authenticated_client.get(f"/posts/{post_id}/user")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["user"], dict)
    assert result["user"]["id"] == user_id


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


@mark.dependency(depends=["test_guarded_relationship"])
async def test_nested_create_single_objects(authenticated_client: BrowserTestClient):
    global user_id

    response = await authenticated_client.post(
        "/posts",
        json={
            "post": {
                "content": "Today I learned I can create nested objects with my POST requests.",
                "event_date": "2023-12-11T15:27:39.984Z",
                "tags": {
                    "categories": ["blog"],
                },
                "user_id": user_id,
                "section": {"name": "Opinons", "uuid": str(uuid7())},
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["meta"], dict)
    assert isinstance(result["meta"]["relations"], dict)
    assert isinstance(result["meta"]["relations"]["records"], dict)
    assert isinstance(result["meta"]["relations"]["records"]["section"], dict)
    assert isinstance(result["meta"]["relations"]["records"]["section"]["id"], str)
    assert isinstance(result["meta"]["relations"]["total_modified"], int)
    assert isinstance(result["meta"]["relations"]["invalid"], dict)
    assert isinstance(result["meta"]["relations"]["messages"], dict)
    assert result["meta"]["relations"]["total_modified"] == 1
    section_id = result["meta"]["relations"]["records"]["section"]["id"]
    assert result["post"]["section_id"] == section_id
    post_id = result["post"]["id"]

    response = await authenticated_client.get(f"/posts/{post_id}/section")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert isinstance(result["section"], dict)
    assert result["section"]["id"] == section_id

    response = await authenticated_client.delete(f"/posts/{post_id}")
    assert response.status_code == status.HTTP_200_OK
    response = await authenticated_client.delete(f"/sections/{section_id}")
    assert response.status_code == status.HTTP_200_OK

    response = await authenticated_client.post(
        "/posts",
        json={
            "post": {
                "content": "Today I learned I can create nested objects with my POST requests.",
                "event_date": "2023-12-11T15:27:39.984Z",
                "tags": {
                    "categories": ["blog"],
                },
                "user_id": user_id,
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    create_result = response.json()
    response = await authenticated_client.patch(
        f"/posts/{create_result['post']['id']}",
        json={
            "post": {
                "content": "Today I learned I can create nested objects with my POST requests.",
                "event_date": "2023-12-11T15:27:39.984Z",
                "tags": {
                    "categories": ["blog"],
                },
                "user_id": user_id,
                "section": {
                    "name": "Opinons",
                    "uuid": str(uuid7()),
                },
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()

    assert isinstance(result["meta"], dict)
    assert isinstance(result["meta"]["relations"], dict)
    assert isinstance(result["meta"]["relations"]["records"], dict)
    assert isinstance(result["meta"]["relations"]["records"]["section"], dict)
    assert isinstance(result["meta"]["relations"]["records"]["section"]["id"], str)
    assert isinstance(result["meta"]["relations"]["total_modified"], int)
    assert isinstance(result["meta"]["relations"]["invalid"], dict)
    assert isinstance(result["meta"]["relations"]["messages"], dict)
    assert result["meta"]["relations"]["total_modified"] == 1
    section_id = result["meta"]["relations"]["records"]["section"]["id"]
    assert result["post"]["section_id"] == section_id
    post_id = result["post"]["id"]

    response = await authenticated_client.get(f"/posts/{post_id}/section")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert isinstance(result["section"], dict)
    assert result["section"]["id"] == section_id

    response = await authenticated_client.delete(f"/posts/{post_id}")
    assert response.status_code == status.HTTP_200_OK
    response = await authenticated_client.delete(f"/sections/{section_id}")
    assert response.status_code == status.HTTP_200_OK


@mark.dependency(depends=["test_nested_create_single_objects"])
async def test_nested_create_multiple_objects(authenticated_client: BrowserTestClient):
    global user_id
    response = await authenticated_client.post(
        "/sections",
        json={
            "section": {
                "name": "Opinions",
                "uuid": str(uuid7()),
                "posts": [
                    {
                        "content": "Today I learned I can create nested objects with my POST requests.",
                        "event_date": "2023-12-11T15:27:39.984Z",
                        "tags": {
                            "categories": ["blog"],
                        },
                        "user_id": user_id,
                    },
                    {
                        "content": "Seriously! I can create nested objects with my POST requests.",
                        "event_date": "2023-12-11T15:27:39.984Z",
                        "tags": {
                            "categories": ["blog"],
                        },
                        "user_id": user_id,
                    },
                ],
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["meta"], dict)
    assert isinstance(result["meta"]["relations"], dict)
    assert isinstance(result["meta"]["relations"]["records"], dict)
    assert isinstance(result["meta"]["relations"]["records"]["posts"], list)
    assert isinstance(result["meta"]["relations"]["records"]["posts"][0]["id"], str)
    assert isinstance(result["meta"]["relations"]["total_modified"], int)
    assert isinstance(result["meta"]["relations"]["invalid"], dict)
    assert isinstance(result["meta"]["relations"]["messages"], dict)
    assert result["meta"]["relations"]["total_modified"] == 2
    post_id1 = result["meta"]["relations"]["records"]["posts"][0]["id"]
    post_id2 = result["meta"]["relations"]["records"]["posts"][1]["id"]
    section_id = result["section"]["id"]

    response = await authenticated_client.get(f"/sections/{section_id}/posts")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert isinstance(result["posts"], list)
    assert len(result["posts"]) == 2
    assert post_id1 in [result["posts"][0]["id"], result["posts"][1]["id"]]
    assert post_id2 in [result["posts"][0]["id"], result["posts"][1]["id"]]

    response = await authenticated_client.delete(f"/posts/{post_id1}")
    assert response.status_code == status.HTTP_200_OK
    response = await authenticated_client.delete(f"/posts/{post_id2}")
    assert response.status_code == status.HTTP_200_OK
    response = await authenticated_client.delete(f"/sections/{section_id}")
    assert response.status_code == status.HTTP_200_OK

    response = await authenticated_client.post(
        "/sections",
        json={
            "section": {
                "name": "Opinions",
                "uuid": str(uuid7()),
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    create_result = response.json()
    response = await authenticated_client.patch(
        f"/sections/{create_result['section']['id']}",
        json={
            "section": {
                "name": "Opinions",
                "posts": [
                    {
                        "content": "Today I learned I can create nested objects with my POST requests.",
                        "event_date": "2023-12-11T15:27:39.984Z",
                        "tags": {
                            "categories": ["blog"],
                        },
                        "user_id": user_id,
                    },
                    {
                        "content": "Seriously! I can create nested objects with my POST requests.",
                        "event_date": "2023-12-11T15:27:39.984Z",
                        "tags": {
                            "categories": ["blog"],
                        },
                        "user_id": user_id,
                    },
                ],
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["meta"], dict)
    assert isinstance(result["meta"]["relations"], dict)
    assert isinstance(result["meta"]["relations"]["records"], dict)
    assert isinstance(result["meta"]["relations"]["records"]["posts"], list)
    assert isinstance(result["meta"]["relations"]["records"]["posts"][0]["id"], str)
    assert isinstance(result["meta"]["relations"]["total_modified"], int)
    assert isinstance(result["meta"]["relations"]["invalid"], dict)
    assert isinstance(result["meta"]["relations"]["messages"], dict)
    assert result["meta"]["relations"]["total_modified"] == 2
    post_id1 = result["meta"]["relations"]["records"]["posts"][0]["id"]
    post_id2 = result["meta"]["relations"]["records"]["posts"][1]["id"]
    section_id = result["section"]["id"]

    response = await authenticated_client.get(f"/sections/{section_id}/posts")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert isinstance(result["posts"], list)
    assert len(result["posts"]) == 2
    assert post_id1 in [result["posts"][0]["id"], result["posts"][1]["id"]]
    assert post_id2 in [result["posts"][0]["id"], result["posts"][1]["id"]]

    response = await authenticated_client.delete(f"/posts/{post_id1}")
    assert response.status_code == status.HTTP_200_OK
    response = await authenticated_client.delete(f"/posts/{post_id2}")
    assert response.status_code == status.HTTP_200_OK
    response = await authenticated_client.delete(f"/sections/{section_id}")
    assert response.status_code == status.HTTP_200_OK


@mark.dependency(depends=["test_nested_create_multiple_objects"])
async def test_nested_update_single_objects(authenticated_client: BrowserTestClient):
    global user_id
    response = await authenticated_client.post(
        "/sections",
        json={
            "section": {
                "name": "Opinions",
                "uuid": str(uuid7()),
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    section_result = response.json()
    response = await authenticated_client.post(
        "/posts",
        json={
            "post": {
                "content": "Today I learned I can create nested objects with my POST requests.",
                "event_date": "2023-12-11T15:27:39.984Z",
                "tags": {
                    "categories": ["blog"],
                },
                "user_id": user_id,
                "section": {
                    "id": section_result["section"]["id"],
                    "name": "Deep Thoughts",
                },
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["meta"], dict)
    assert isinstance(result["meta"]["relations"], dict)
    assert isinstance(result["meta"]["relations"]["records"], dict)
    assert isinstance(result["meta"]["relations"]["records"]["section"], dict)
    assert isinstance(result["meta"]["relations"]["records"]["section"]["id"], str)
    assert isinstance(result["meta"]["relations"]["total_modified"], int)
    assert isinstance(result["meta"]["relations"]["invalid"], dict)
    assert isinstance(result["meta"]["relations"]["messages"], dict)
    assert result["meta"]["relations"]["total_modified"] == 1
    section_id = result["meta"]["relations"]["records"]["section"]["id"]
    assert result["post"]["section_id"] == section_id
    assert section_result["section"]["id"] == section_id
    post_id = result["post"]["id"]

    response = await authenticated_client.get(f"/posts/{post_id}/section")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert isinstance(result["section"], dict)
    assert result["section"]["id"] == section_id

    response = await authenticated_client.delete(f"/posts/{post_id}")
    assert response.status_code == status.HTTP_200_OK
    response = await authenticated_client.delete(f"/sections/{section_id}")
    assert response.status_code == status.HTTP_200_OK

    response = await authenticated_client.post(
        "/sections",
        json={
            "section": {
                "name": "Opinions",
                "uuid": str(uuid7()),
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    section_result = response.json()
    response = await authenticated_client.post(
        "/posts",
        json={
            "post": {
                "content": "Today I learned I can create nested objects with my POST requests.",
                "event_date": "2023-12-11T15:27:39.984Z",
                "tags": {
                    "categories": ["blog"],
                },
                "user_id": user_id,
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    create_result = response.json()
    response = await authenticated_client.patch(
        f"/posts/{create_result['post']['id']}",
        json={
            "post": {
                "content": "Today I learned I can create nested objects with my POST requests.",
                "event_date": "2023-12-11T15:27:39.984Z",
                "tags": {
                    "categories": ["blog"],
                },
                "user_id": user_id,
                "section": {
                    "id": section_result["section"]["id"],
                    "name": "Deep Thoughts",
                },
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["meta"], dict)
    assert isinstance(result["meta"]["relations"], dict)
    assert isinstance(result["meta"]["relations"]["records"], dict)
    assert isinstance(result["meta"]["relations"]["records"]["section"], dict)
    assert isinstance(result["meta"]["relations"]["records"]["section"]["id"], str)
    assert isinstance(result["meta"]["relations"]["total_modified"], int)
    assert isinstance(result["meta"]["relations"]["invalid"], dict)
    assert isinstance(result["meta"]["relations"]["messages"], dict)
    assert result["meta"]["relations"]["total_modified"] == 1
    section_id = result["meta"]["relations"]["records"]["section"]["id"]
    assert result["post"]["section_id"] == section_id
    assert section_result["section"]["id"] == section_id
    post_id = result["post"]["id"]

    response = await authenticated_client.get(f"/posts/{post_id}/section")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert isinstance(result["section"], dict)
    assert result["section"]["id"] == section_id

    response = await authenticated_client.delete(f"/posts/{post_id}")
    assert response.status_code == status.HTTP_200_OK
    response = await authenticated_client.delete(f"/sections/{section_id}")
    assert response.status_code == status.HTTP_200_OK


@mark.dependency(depends=["test_nested_update_single_objects"])
async def test_nested_update_multiple_objects(authenticated_client: BrowserTestClient):
    global user_id
    response = await authenticated_client.post(
        "/posts",
        json={
            "post": {
                "content": "Today I learned I can create nested objects with my POST requests.",
                "event_date": "2023-12-11T15:27:39.984Z",
                "tags": {
                    "categories": ["blog"],
                },
                "user_id": user_id,
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    post_result1 = response.json()
    response = await authenticated_client.post(
        "/posts",
        json={
            "post": {
                "content": "Seriously! I can create nested objects with my POST requests.",
                "event_date": "2023-12-11T15:27:39.984Z",
                "tags": {
                    "categories": ["blog"],
                },
                "user_id": user_id,
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    post_result2 = response.json()

    update_post_1 = {**post_result1["post"]}
    update_post_1.pop("links", None)
    update_post_1["content"] = "I've updated this POST via a related POST!"

    update_post_2 = {**post_result2["post"]}
    update_post_2.pop("links", None)
    update_post_2["content"] = "I've updated this POST via a related POST TOOOO!"

    response = await authenticated_client.post(
        "/sections",
        json={
            "section": {
                "name": "Opinion",
                "uuid": str(uuid7()),
                "posts": [
                    update_post_1,
                    update_post_2,
                    {},
                ],
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["meta"], dict)
    assert isinstance(result["meta"]["relations"], dict)
    assert isinstance(result["meta"]["relations"]["records"], dict)
    assert isinstance(result["meta"]["relations"]["records"]["posts"], list)
    assert isinstance(result["meta"]["relations"]["records"]["posts"][0], dict)
    assert isinstance(result["meta"]["relations"]["records"]["posts"][0]["id"], str)
    assert isinstance(result["meta"]["relations"]["records"]["posts"][1], dict)
    assert isinstance(result["meta"]["relations"]["records"]["posts"][1]["id"], str)
    assert isinstance(result["meta"]["relations"]["total_modified"], int)
    assert isinstance(result["meta"]["relations"]["invalid"], dict)
    assert isinstance(result["meta"]["relations"]["messages"], dict)
    assert result["meta"]["relations"]["total_modified"] == 2
    assert len(result["meta"]["relations"]["invalid"]) == 1
    assert len(result["meta"]["relations"]["messages"]) == 1
    post_id1 = result["meta"]["relations"]["records"]["posts"][0]["id"]
    post_id2 = result["meta"]["relations"]["records"]["posts"][1]["id"]
    assert post_id1 in [post_result1["post"]["id"], post_result2["post"]["id"]]
    assert post_id2 in [post_result1["post"]["id"], post_result2["post"]["id"]]
    assert (
        result["meta"]["relations"]["records"]["posts"][0]["content"]
        == "I've updated this POST via a related POST!"
    )
    assert (
        result["meta"]["relations"]["records"]["posts"][1]["content"]
        == "I've updated this POST via a related POST TOOOO!"
    )
    section_id = result["section"]["id"]

    response = await authenticated_client.get(f"/posts/{post_id1}/section")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert isinstance(result["section"], dict)
    assert result["section"]["id"] == section_id

    response = await authenticated_client.get(f"/posts/{post_id2}/section")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert isinstance(result["section"], dict)
    assert result["section"]["id"] == section_id

    response = await authenticated_client.delete(f"/posts/{post_id1}")
    assert response.status_code == status.HTTP_200_OK
    response = await authenticated_client.delete(f"/posts/{post_id2}")
    assert response.status_code == status.HTTP_200_OK
    response = await authenticated_client.delete(f"/sections/{section_id}")
    assert response.status_code == status.HTTP_200_OK

    response = await authenticated_client.post(
        "/posts",
        json={
            "post": {
                "content": "Today I learned I can create nested objects with my POST requests.",
                "event_date": "2023-12-11T15:27:39.984Z",
                "tags": {
                    "categories": ["blog"],
                },
                "user_id": user_id,
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    post_result1 = response.json()
    response = await authenticated_client.post(
        "/posts",
        json={
            "post": {
                "content": "Seriously! I can create nested objects with my POST requests.",
                "event_date": "2023-12-11T15:27:39.984Z",
                "tags": {
                    "categories": ["blog"],
                },
                "user_id": user_id,
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    post_result2 = response.json()

    update_post_1 = {**post_result1["post"]}
    update_post_1.pop("links", None)
    update_post_1["content"] = "I've updated this POST via a related POST!"

    update_post_2 = {**post_result2["post"]}
    update_post_2.pop("links", None)
    update_post_2["content"] = "I've updated this POST via a related POST TOOOO!"

    response = await authenticated_client.post(
        "/sections",
        json={
            "section": {
                "name": "Opinion",
                "uuid": str(uuid7()),
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    create_result = response.json()
    response = await authenticated_client.patch(
        f"/sections/{create_result['section']['id']}",
        json={
            "section": {
                "name": "Opinion",
                "posts": [
                    update_post_1,
                    update_post_2,
                    {},
                ],
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["meta"], dict)
    assert isinstance(result["meta"]["relations"], dict)
    assert isinstance(result["meta"]["relations"]["records"], dict)
    assert isinstance(result["meta"]["relations"]["records"]["posts"], list)
    assert isinstance(result["meta"]["relations"]["records"]["posts"][0], dict)
    assert isinstance(result["meta"]["relations"]["records"]["posts"][0]["id"], str)
    assert isinstance(result["meta"]["relations"]["records"]["posts"][1], dict)
    assert isinstance(result["meta"]["relations"]["records"]["posts"][1]["id"], str)
    assert isinstance(result["meta"]["relations"]["total_modified"], int)
    assert isinstance(result["meta"]["relations"]["invalid"], dict)
    assert isinstance(result["meta"]["relations"]["messages"], dict)
    assert result["meta"]["relations"]["total_modified"] == 2
    assert len(result["meta"]["relations"]["invalid"]) == 1
    assert len(result["meta"]["relations"]["messages"]) == 1
    post_id1 = result["meta"]["relations"]["records"]["posts"][0]["id"]
    post_id2 = result["meta"]["relations"]["records"]["posts"][1]["id"]
    assert post_id1 in [post_result1["post"]["id"], post_result2["post"]["id"]]
    assert post_id2 in [post_result1["post"]["id"], post_result2["post"]["id"]]
    assert (
        result["meta"]["relations"]["records"]["posts"][0]["content"]
        == "I've updated this POST via a related POST!"
    )
    assert (
        result["meta"]["relations"]["records"]["posts"][1]["content"]
        == "I've updated this POST via a related POST TOOOO!"
    )
    section_id = result["section"]["id"]

    response = await authenticated_client.get(f"/posts/{post_id1}/section")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert isinstance(result["section"], dict)
    assert result["section"]["id"] == section_id

    response = await authenticated_client.get(f"/posts/{post_id2}/section")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert isinstance(result["section"], dict)
    assert result["section"]["id"] == section_id

    response = await authenticated_client.delete(f"/posts/{post_id1}")
    assert response.status_code == status.HTTP_200_OK
    response = await authenticated_client.delete(f"/posts/{post_id2}")
    assert response.status_code == status.HTTP_200_OK
    response = await authenticated_client.delete(f"/sections/{section_id}")
    assert response.status_code == status.HTTP_200_OK


@mark.dependency(depends=["test_nested_update_multiple_objects"])
async def test_custom_foreign_relationships(authenticated_client: BrowserTestClient):
    global group_id
    global post_id

    # First verify that a link exists on the resources supporting comments
    post = (await authenticated_client.get(f"/posts/{post_id}")).json()
    group = (await authenticated_client.get(f"/groups/{group_id}")).json()
    post_comments_link = post["post"]["links"].get("comments")
    group_comments_link = group["group"]["links"].get("comments")
    assert post_comments_link is not None
    assert group_comments_link is not None

    # Next fetch the associated comments from each resource and verify they're populated
    post_comments = (await authenticated_client.get(post_comments_link)).json()
    group_comments = (await authenticated_client.get(group_comments_link)).json()
    assert post_comments["meta"]["records"] > 0
    assert group_comments["meta"]["records"] > 0

    # Finally, double check we're working with Comment records here
    for comment in post_comments["comments"]:
        assert comment.get("text") is not None

    for comment in group_comments["comments"]:
        assert comment.get("text") is not None


# The below functions are mainly cleanup based on the create functions above


@mark.dependency(depends=["test_nested_update_single_objects"])
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
