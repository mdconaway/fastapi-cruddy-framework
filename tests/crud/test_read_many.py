from json import dumps
from pytest import mark
from fastapi import status
from fastapi_cruddy_framework import BrowserTestClient

elves_group_id = None
orcs_group_id = None
user_id = None
post_id = None


@mark.asyncio
@mark.dependency()
async def test_get_groups(authenticated_client: BrowserTestClient):
    response = authenticated_client.get("/groups")
    assert response.status_code == status.HTTP_200_OK
    response_obj = response.json()
    assert isinstance(response_obj["groups"], list)
    assert isinstance(response_obj["meta"], dict)
    assert isinstance(response_obj["meta"]["page"], int)
    assert isinstance(response_obj["meta"]["limit"], int)
    assert isinstance(response_obj["meta"]["pages"], int)
    assert isinstance(response_obj["meta"]["records"], int)


@mark.asyncio
@mark.dependency(depends=["test_get_groups"])
async def test_get_groups_where_list_simple(authenticated_client: BrowserTestClient):
    response = authenticated_client.get("/groups?where=[]")
    assert response.status_code == status.HTTP_200_OK


@mark.asyncio
@mark.dependency(depends=["test_get_groups_where_list_simple"])
async def test_setup(authenticated_client: BrowserTestClient):
    global elves_group_id
    global orcs_group_id
    global user_id
    global post_id

    response = authenticated_client.post(
        f"/groups",
        json={"group": {"name": "Elves Anonymous"}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["group"], dict)
    elves_group_id = result["group"]["id"]

    response = authenticated_client.post(
        f"/groups",
        json={"group": {"name": "Orcs Anonymous"}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["group"], dict)
    orcs_group_id = result["group"]["id"]

    response = authenticated_client.post(
        f"/users",
        json={
            "user": {
                "first_name": "Orc",
                "last_name": "Peasant",
                "email": "orc.peasant@cruddy-framework.com",
                "is_active": True,
                "is_superuser": False,
                "birthdate": "2023-07-22T14:43:31.038Z",
                "phone": "888-555-5555",
                "state": "Mordor",
                "country": "Middle Earth",
                "address": "1 Volcano Way",
                "password": "itoilallday",
                "groups": [orcs_group_id],
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
                "content": "I'm so tired of working for lord Sauron. We keep getting sent into battle and charging at walls full of knights. It's like he doesn't care about us.",
                "tags": {"categories": ["rant"]},
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["post"], dict)
    post_id = result["post"]["id"]


@mark.asyncio
@mark.dependency(depends=["test_setup"])
async def test_get_posts_json_notation(authenticated_client: BrowserTestClient):
    global post_id

    response = authenticated_client.get(f"/posts")
    result = response.json()

    where = dumps({"tags.categories": {"*eq": ["rant"]}})
    response = authenticated_client.get(f"/posts?where={where}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["posts"]) is 1
    assert result["posts"][0]["id"] == post_id
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is 10
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 1

    where = dumps({"tags.categories": {"*eq": ["blog"]}})
    response = authenticated_client.get(f"/posts?where={where}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["posts"], list)
    assert len(result["posts"]) is 0


@mark.asyncio
@mark.dependency(depends=["test_get_posts_json_notation"])
async def test_get_groups_no_results(authenticated_client: BrowserTestClient):
    global elves_group_id
    global orcs_group_id

    where = dumps({"name": "I'm not real"})
    response = authenticated_client.get(f"/groups?where={where}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["groups"]) is 0
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is 10
    assert result["meta"]["pages"] is 0
    assert result["meta"]["records"] is 0


@mark.asyncio
@mark.dependency(depends=["test_get_groups_no_results"])
async def test_get_groups_where_list_complex(authenticated_client: BrowserTestClient):
    where = dumps(
        [{"name": {"*contains": "Elves"}}, {"name": {"*contains": "Anonymous"}}]
    )
    response = authenticated_client.get(f"/groups?where={where}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["groups"]) is 1
    assert result["groups"][0]["id"] == elves_group_id
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is 10
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 1


@mark.asyncio
@mark.dependency(depends=["test_get_groups_where_list_complex"])
async def test_get_group_where_dict_simple(authenticated_client: BrowserTestClient):
    global elves_group_id
    global orcs_group_id

    where = dumps({"name": "Elves Anonymous"})
    response = authenticated_client.get(f"/groups?where={where}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["groups"]) is 1
    assert result["groups"][0]["id"] == elves_group_id
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is 10
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 1

    where = dumps({"name": "Orcs Anonymous"})
    response = authenticated_client.get(f"/groups?where={where}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["groups"]) is 1
    assert result["groups"][0]["id"] == orcs_group_id
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is 10
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 1


@mark.asyncio
@mark.dependency(depends=["test_get_group_where_dict_simple"])
async def test_get_group_where_dict_complex(authenticated_client: BrowserTestClient):
    global elves_group_id
    global orcs_group_id

    where = dumps({"*or": [{"name": "Orcs Anonymous"}, {"name": "Elves Anonymous"}]})
    response = authenticated_client.get(f"/groups?where={where}&sort=name asc")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["groups"]) is 2
    assert result["groups"][0]["id"] == elves_group_id
    assert result["groups"][1]["id"] == orcs_group_id
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is 10
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 2

    where = dumps(
        {"*or": [{"name": {"*contains": "Orcs"}}, {"name": {"*contains": "Elves"}}]}
    )
    response = authenticated_client.get(f"/groups?where={where}&sort=name desc")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["groups"]) is 2
    assert result["groups"][0]["id"] == orcs_group_id
    assert result["groups"][1]["id"] == elves_group_id
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is 10
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 2


@mark.asyncio
@mark.dependency(depends=["test_get_group_where_dict_complex"])
async def test_get_group_where_dict_complex_limit(
    authenticated_client: BrowserTestClient,
):
    global elves_group_id
    global orcs_group_id
    where = dumps(
        {"*or": [{"name": {"*contains": "Orcs"}}, {"name": {"*contains": "Elves"}}]}
    )
    response = authenticated_client.get(f"/groups?where={where}&sort=name desc&limit=1")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["groups"]) is 1
    assert result["groups"][0]["id"] == orcs_group_id
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is 1
    assert result["meta"]["pages"] is 2
    assert result["meta"]["records"] is 2


@mark.asyncio
@mark.dependency(depends=["test_get_group_where_dict_complex_limit"])
async def test_get_group_where_dict_complex_column_clip(
    authenticated_client: BrowserTestClient,
):
    global elves_group_id
    global orcs_group_id
    where = dumps(
        {"*or": [{"name": {"*contains": "Orcs"}}, {"name": {"*contains": "Elves"}}]}
    )
    response = authenticated_client.get(
        f"/groups?where={where}&sort=name desc&columns=name"
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["groups"]) is 2
    assert isinstance(result["groups"][0], dict)
    assert isinstance(result["groups"][1], dict)
    assert result["groups"][0]["id"] == orcs_group_id
    assert result["groups"][1]["id"] == elves_group_id
    assert len(result["groups"][0].keys()) is 3
    assert len(result["groups"][1].keys()) is 3
    assert "id" in result["groups"][0].keys()
    assert "name" in result["groups"][0].keys()
    assert "links" in result["groups"][0].keys()
    assert "id" in result["groups"][1].keys()
    assert "name" in result["groups"][1].keys()
    assert "links" in result["groups"][1].keys()
    assert result["meta"]["page"] is 1
    assert result["meta"]["limit"] is 10
    assert result["meta"]["pages"] is 1
    assert result["meta"]["records"] is 2


@mark.asyncio
@mark.dependency(depends=["test_get_group_where_dict_complex_column_clip"])
async def test_get_group_where_dict_validate_links(
    authenticated_client: BrowserTestClient,
):
    global orcs_group_id
    where = dumps(
        {"*or": [{"name": {"*contains": "Orcs"}}, {"name": {"*contains": "Elves"}}]}
    )
    response = authenticated_client.get(f"/groups?where={where}&sort=name desc&limit=1")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["groups"]) is 1
    assert result["groups"][0]["id"] == orcs_group_id
    assert isinstance(result["groups"][0]["links"], dict)
    assert "users" in result["groups"][0]["links"]
    assert isinstance(result["groups"][0]["links"]["users"], str)
    assert result["groups"][0]["links"]["users"] == f"/groups/{orcs_group_id}/users"


# Cleanup the objects made for this test suite
@mark.asyncio
@mark.dependency(depends=["test_get_group_where_dict_complex_column_clip"])
async def test_cleanup(authenticated_client: BrowserTestClient):
    global elves_group_id
    global orcs_group_id
    global user_id
    global post_id

    response = authenticated_client.delete(f"/groups/{elves_group_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["group"]["id"] == elves_group_id

    response = authenticated_client.delete(f"/groups/{orcs_group_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["group"]["id"] == orcs_group_id

    response = authenticated_client.delete(f"/users/{user_id}")
    # This should return a 405 as delete-user is blocked using a framework feature!
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    response = authenticated_client.delete(f"/users/purge/{user_id}?confirm=Y")
    # This should return a 200 as this is an overriden action!
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["user"]["id"] == user_id

    response = authenticated_client.delete(f"/posts/{post_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["post"]["id"] == post_id
