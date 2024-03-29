from json import dumps
from pytest import mark
from fastapi import status
from fastapi_cruddy_framework import BrowserTestClient

user_id = None


@mark.dependency()
async def test_cast_json_as_text(authenticated_client: BrowserTestClient):
    global user_id
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
                "groups": [],
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
                "content": "Has anyone seen Bilbo lately?",
                "tags": {"some_key": 123456789},
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["post"], dict)
    post_id = result["post"]["id"]

    where = {"tags:Text": {"*icontains": "456"}}
    response = await authenticated_client.get(f"/posts?where={dumps(where)}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["posts"]) is 1
    assert result["posts"][0]["id"] == post_id

    not_where = {"*not": where}
    response = await authenticated_client.get(f"/posts?where={dumps(not_where)}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert len(result["posts"]) is 0

    response = await authenticated_client.delete(f"/users/purge/{user_id}?confirm=Y")
    assert response.status_code == status.HTTP_200_OK

    response = await authenticated_client.delete(f"/posts/{post_id}")
    assert response.status_code == status.HTTP_200_OK
