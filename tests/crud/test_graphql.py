from pytest import mark
from fastapi import status
from fastapi_cruddy_framework import BrowserTestClient, uuid7

elves_group_id = None
orcs_group_id = None
user_id = None
post_id = None
section_id = None
type1_id = None
type2_id = None
subtype1_id = None
subtype2_id = None
reference1_id = None
reference2_id = None
comment_id = None


@mark.dependency()
async def test_setup(authenticated_client: BrowserTestClient):
    global elves_group_id
    global orcs_group_id
    global user_id
    global post_id
    global section_id
    global type1_id
    global type2_id
    global subtype1_id
    global subtype2_id
    global reference1_id
    global reference2_id
    global comment_id

    response = await authenticated_client.post(
        f"/types",
        json={"type": {"id": "Master-Type-1"}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["type"], dict)
    assert result["type"]["id"] == "Master-Type-1"
    type1_id = result["type"]["id"]

    response = await authenticated_client.post(
        f"/types",
        json={"type": {"id": "Master-Type-2"}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["type"], dict)
    assert result["type"]["id"] == "Master-Type-2"
    type2_id = result["type"]["id"]

    response = await authenticated_client.post(
        f"/subtypes",
        json={"subtype": {"id": "Sub-Type", "type_id": type1_id}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["subtype"], dict)
    assert result["subtype"]["id"] == "Sub-Type"
    subtype1_id = result["subtype"]["id"]

    response = await authenticated_client.post(
        f"/subtypes",
        json={"subtype": {"id": "Sub-Type", "type_id": type2_id}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["subtype"], dict)
    assert result["subtype"]["id"] == "Sub-Type"
    subtype2_id = result["subtype"]["id"]

    response = await authenticated_client.post(
        f"/references",
        json={"reference": {"type_id": type1_id, "subtype_id": subtype1_id}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["reference"], dict)
    assert result["reference"]["type_id"] == type1_id
    assert result["reference"]["subtype_id"] == subtype1_id
    reference1_id = result["reference"]["id"]

    response = await authenticated_client.post(
        f"/references",
        json={"reference": {"type_id": type2_id, "subtype_id": subtype2_id}},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["reference"], dict)
    assert result["reference"]["type_id"] == type2_id
    assert result["reference"]["subtype_id"] == subtype2_id
    reference2_id = result["reference"]["id"]

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
        json={"section": {"name": "Opinions", "uuid": str(uuid7())}},
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

    response = await authenticated_client.post(
        "/comments",
        json={
            "comment": {
                "created_by_id": user_id,
                "entity_id": post_id,
                "text": "My greatest work EVER.",
            }
        },
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["comment"], dict)
    comment_id = result["comment"]["id"]


@mark.dependency(depends=["test_setup"])
async def test_graphql_read(authenticated_client: BrowserTestClient):
    global elves_group_id
    global orcs_group_id
    global user_id
    global post_id
    global section_id
    global type1_id
    global type2_id
    global subtype1_id
    global subtype2_id
    global reference1_id
    global reference2_id
    global comment_id

    response = await authenticated_client.post(
        f"/graphql",
        json={"query": """query TestQuery {
                types (sort: "id asc") {
                    id
                    links
                    subtypes (sort: "id asc") {
                        id
                        type_id
                        links
                        references {
                            id
                            type_id
                            subtype_id
                            links
                        }
                    }
                }
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
                        comments {
                            text
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
            """},
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert isinstance(result["data"], dict)
    assert isinstance(result["data"]["types"], list)
    assert isinstance(result["data"]["groups"], list)
    assert isinstance(result["data"]["sections"], list)
    assert isinstance(result["data"]["users"], list)
    assert len(result["data"]["types"]) == 2
    assert len(result["data"]["groups"]) == 2
    assert len(result["data"]["sections"]) == 1
    assert len(result["data"]["users"]) == 1
    assert isinstance(result["data"]["types"][0]["subtypes"], list)
    assert isinstance(result["data"]["types"][1]["subtypes"], list)
    assert len(result["data"]["types"][0]["subtypes"]) == 1
    assert len(result["data"]["types"][1]["subtypes"]) == 1
    assert isinstance(result["data"]["types"][0]["subtypes"][0]["references"], list)
    assert isinstance(result["data"]["types"][1]["subtypes"][0]["references"], list)
    assert len(result["data"]["types"][0]["subtypes"][0]["references"]) == 1
    assert len(result["data"]["types"][1]["subtypes"][0]["references"]) == 1
    assert (
        result["data"]["types"][0]["subtypes"][0]["references"][0]["id"]
        == reference1_id
    )
    assert (
        result["data"]["types"][1]["subtypes"][0]["references"][0]["id"]
        == reference2_id
    )
    assert isinstance(result["data"]["groups"][0]["created_at"], str)
    assert isinstance(result["data"]["groups"][0]["updated_at"], str)
    assert isinstance(result["data"]["groups"][0]["links"], dict)
    assert len(result["data"]["sections"][0]["posts"]) == 1
    assert isinstance(result["data"]["sections"][0]["posts"][0]["created_at"], str)
    assert isinstance(result["data"]["sections"][0]["posts"][0]["updated_at"], str)
    assert isinstance(result["data"]["sections"][0]["posts"][0]["comments"], list)
    assert isinstance(result["data"]["sections"][0]["posts"][0]["sections"], list)
    assert len(result["data"]["sections"][0]["posts"][0]["comments"]) == 1
    assert isinstance(
        result["data"]["sections"][0]["posts"][0]["comments"][0]["text"], str
    )
    assert len(result["data"]["sections"][0]["posts"][0]["sections"]) == 1
    assert isinstance(
        result["data"]["sections"][0]["posts"][0]["sections"][0]["name"], str
    )


@mark.dependency(depends=["test_graphql_read"])
async def test_cleanup(authenticated_client: BrowserTestClient):
    global elves_group_id
    global orcs_group_id
    global user_id
    global post_id
    global section_id
    global type1_id
    global type2_id
    global subtype1_id
    global subtype2_id
    global reference1_id
    global reference2_id
    global comment_id

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

    response = await authenticated_client.delete(f"/references/{reference1_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["reference"]["id"] == reference1_id

    response = await authenticated_client.delete(f"/references/{reference2_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["reference"]["id"] == reference2_id

    response = await authenticated_client.delete(f"/subtypes/{type1_id}.{subtype1_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["subtype"]["type_id"] == type1_id
    assert result["subtype"]["id"] == subtype1_id

    response = await authenticated_client.delete(f"/subtypes/{type2_id}.{subtype2_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["subtype"]["type_id"] == type2_id
    assert result["subtype"]["id"] == subtype2_id

    response = await authenticated_client.delete(f"/types/{type1_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["type"]["id"] == type1_id

    response = await authenticated_client.delete(f"/types/{type2_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result, dict)
    assert result["type"]["id"] == type2_id
