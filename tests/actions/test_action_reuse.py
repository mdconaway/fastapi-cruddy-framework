from json import dumps
from pytest import mark
from fastapi import status
from fastapi_cruddy_framework import BrowserTestClient

user_id = None


@mark.asyncio
@mark.dependency()
async def test_setup(authenticated_client: BrowserTestClient):
    global user_id

    response = await authenticated_client.post(
        f"/users",
        json={
            "user": {
                "first_name": "Meriadoc",
                "last_name": "Brandybuck",
                "email": "merry.brandybuck@cruddy-framework.com",
                "is_active": True,
                "is_superuser": False,
                "birthdate": "2023-07-22T14:43:31.038Z",
                "phone": "888-555-5555",
                "state": "Buckland",
                "country": "Middle Earth",
                "address": "1 Buckland Circle",
                "password": "frodoscousin",
                "groups": [],
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["user"], dict)
    user_id = result["user"]["id"]


@mark.asyncio
@mark.dependency(depends=["test_setup"])
async def test_get_users_remapped_actions(authenticated_client: BrowserTestClient):
    global user_id

    where = dumps({"first_name": {"*eq": "Meriadoc"}})
    response1 = await authenticated_client.get(f"/users?where={where}")
    assert response1.status_code == status.HTTP_200_OK
    result1 = response1.json()
    assert len(result1["users"]) is 1
    assert result1["users"][0]["id"] == user_id
    assert result1["meta"]["page"] is 1
    assert result1["meta"]["limit"] is 10
    assert result1["meta"]["pages"] is 1
    assert result1["meta"]["records"] is 1

    response2 = await authenticated_client.get(f"/users/all?where={where}")
    assert response2.status_code == status.HTTP_200_OK
    result2 = response2.json()
    assert len(result2["users"]) is 1
    assert result2["users"][0]["id"] == user_id
    assert result2["meta"]["page"] is 1
    assert result2["meta"]["limit"] is 10
    assert result2["meta"]["pages"] is 1
    assert result2["meta"]["records"] is 1

    response3 = await authenticated_client.get(f"/users/everything?where={where}")
    assert response3.status_code == status.HTTP_200_OK
    result3 = response3.json()
    assert len(result2["users"]) is 1
    assert result3["users"][0]["id"] == user_id
    assert result3["meta"]["page"] is 1
    assert result3["meta"]["limit"] is 10
    assert result3["meta"]["pages"] is 1
    assert result3["meta"]["records"] is 1

    assert result1 == result2
    assert result2 == result3
    assert result3 == result1


# Cleanup the objects made for this test suite
@mark.asyncio
@mark.dependency(depends=["test_get_users_remapped_actions"])
async def test_cleanup(authenticated_client: BrowserTestClient):
    global user_id

    response = await authenticated_client.delete(f"/users/{user_id}")
    # This should return a 405 as delete-user is blocked using a framework feature!
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    response = await authenticated_client.delete(f"/users/purge/{user_id}?confirm=Y")
    # This should return a 200 as this is an overriden action!
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["user"]["id"] == user_id
