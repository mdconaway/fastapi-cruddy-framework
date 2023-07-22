from json import dumps
from pytest import mark
from tests.helpers import BrowserTestClient


group_id = None


@mark.asyncio
@mark.dependency()
async def test_get_groups(authenticated_client: BrowserTestClient):
    response = authenticated_client.get("/groups")
    assert response.status_code == 200
    response_obj = response.json()
    assert isinstance(response_obj["groups"], list)
    assert isinstance(response_obj["meta"], dict)
    assert isinstance(response_obj["meta"]["page"], int)
    assert isinstance(response_obj["meta"]["limit"], int)
    assert isinstance(response_obj["meta"]["pages"], int)
    assert isinstance(response_obj["meta"]["records"], int)


@mark.asyncio
@mark.dependency(depends=["test_get_groups"])
async def test_get_groups_where_list(authenticated_client: BrowserTestClient):
    response = authenticated_client.get("/groups?where=[]")
    assert response.status_code == 200


@mark.asyncio
@mark.dependency(depends=["test_get_groups_where_list"])
async def test_create_group(authenticated_client: BrowserTestClient):
    global group_id
    response = authenticated_client.post(
        f"/groups",
        json={"group": {"name": "Elves Anonymous"}},
    )
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result["group"], dict)
    group_id = result["group"]["id"]


@mark.asyncio
@mark.dependency(depends=["test_create_group"])
async def test_get_group_where_dict(authenticated_client: BrowserTestClient):
    global group_id
    where = dumps({"name": "Elves Anonymous"})
    response = authenticated_client.get(f"/groups?where={where}")
    assert response.status_code == 200
    result = response.json()
    assert result["groups"][0]["id"] == group_id


# Cleanup the objects made for this test suite
@mark.asyncio
@mark.dependency(depends=["test_get_group_where_dict"])
async def test_delete_group(authenticated_client: BrowserTestClient):
    global group_id
    response = authenticated_client.delete(f"/groups/{group_id}")
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, dict)
    assert result["group"]["id"] == group_id
