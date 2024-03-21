from pytest import mark
from fastapi import status
from fastapi_cruddy_framework import BrowserTestClient

elves_group_id = None
orcs_group_id = None
user_id = None
post_id = None
section_id = None


@mark.asyncio
@mark.dependency()
async def test_setup(authenticated_client: BrowserTestClient):
    global elves_group_id
    global orcs_group_id
    global user_id
    global post_id
    global section_id

    response = await authenticated_client.post(
        f"/groups",
        json={"group": {"name": "Elves Anonymous"}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["group"], dict)
    elves_group_id = result["group"]["id"]

    response = await authenticated_client.post(
        f"/groups",
        json={"group": {"name": "Orcs Anonymous"}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["group"], dict)
    orcs_group_id = result["group"]["id"]

    response = await authenticated_client.post(
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

    response = await authenticated_client.post(
        f"/sections",
        json={"section": {"name": "Opinions"}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["section"], dict)
    section_id = result["section"]["id"]

    response = await authenticated_client.post(
        f"/posts",
        json={
            "post": {
                "user_id": user_id,
                "content": "I'm so tired of working for lord Sauron. We keep getting sent into battle and charging at walls full of knights. It's like he doesn't care about us.",
                "tags": {"categories": ["rant"]},
                "section_id": section_id,
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["post"], dict)
    post_id = result["post"]["id"]


@mark.asyncio
@mark.dependency(depends=["test_setup"])
async def test_graphql_read(authenticated_client: BrowserTestClient):
    global elves_group_id
    global orcs_group_id
    global user_id
    global post_id
    global section_id

    response = await authenticated_client.post(
        f"/graphql",
        json={
            "query": """query TestQuery {
                groups {
                    id
                    links
                    created_at
                    updated_at
                    users(where: { email: { __contains: "orc.peasant" } }, limit: 1, page: 1, sort: ["email asc"]) {
                        id
                        email
                        first_name
                        last_name
                        created_at
                        updated_at
                    }
                    name
                }
                sections {
                    id
                    posts {
                        id
                        content
                        created_at
                        updated_at
                        sections {
                            name
                        }
                    }
                    name
                    created_at
                    updated_at
                }
                users {
                    id
                    email
                    first_name
                    last_name
                }
            }
        """
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert isinstance(result["data"], dict)
    assert isinstance(result["data"]["groups"], list)
    assert isinstance(result["data"]["sections"], list)
    assert isinstance(result["data"]["users"], list)
    assert len(result["data"]["groups"]) == 2
    assert len(result["data"]["sections"]) == 1
    assert len(result["data"]["users"]) == 1
    assert isinstance(result["data"]["groups"][0]["created_at"], str)
    assert isinstance(result["data"]["groups"][0]["updated_at"], str)
    assert isinstance(result["data"]["groups"][0]["links"], dict)
    assert len(result["data"]["sections"][0]["posts"]) == 1
    assert isinstance(result["data"]["sections"][0]["posts"][0]["created_at"], str)
    assert isinstance(result["data"]["sections"][0]["posts"][0]["updated_at"], str)
    assert isinstance(result["data"]["sections"][0]["posts"][0]["sections"], list)
    assert len(result["data"]["sections"][0]["posts"][0]["sections"]) == 1
    assert isinstance(
        result["data"]["sections"][0]["posts"][0]["sections"][0]["name"], str
    )


@mark.asyncio
@mark.dependency(depends=["test_graphql_read"])
async def test_cleanup(authenticated_client: BrowserTestClient):
    global elves_group_id
    global orcs_group_id
    global user_id
    global post_id
    global section_id

    response = await authenticated_client.delete(f"/groups/{elves_group_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["group"]["id"] == elves_group_id

    response = await authenticated_client.delete(f"/groups/{orcs_group_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["group"]["id"] == orcs_group_id

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

    response = await authenticated_client.delete(f"/sections/{section_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["section"]["id"] == section_id
