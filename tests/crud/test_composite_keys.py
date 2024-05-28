from pytest import mark
from fastapi import status
from fastapi_cruddy_framework import BrowserTestClient

type1_id = None
type2_id = None
subtype1_id = None
subtype2_id = None
reference1_id = None
reference2_id = None


@mark.dependency()
async def test_setup(authenticated_client: BrowserTestClient):
    global type1_id
    global type2_id
    global subtype1_id
    global subtype2_id
    global reference1_id
    global reference2_id

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


@mark.dependency(depends=["test_setup"])
async def test_composite_reads(authenticated_client: BrowserTestClient):
    global type1_id
    global type2_id
    global subtype1_id
    global subtype2_id
    global reference1_id
    global reference2_id

    response = await authenticated_client.get(f"/references/{reference1_id}/subtype")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["subtype"], dict)
    assert result["subtype"]["type_id"] == type1_id
    assert result["subtype"]["id"] == subtype1_id
    assert f"{type1_id}.{subtype1_id}" in result["subtype"]["links"]["references"]

    response = await authenticated_client.get(f"/references/{reference2_id}/subtype")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["subtype"], dict)
    assert result["subtype"]["type_id"] == type2_id
    assert result["subtype"]["id"] == subtype2_id
    assert f"{type2_id}.{subtype2_id}" in result["subtype"]["links"]["references"]

    response = await authenticated_client.get(
        f"/subtypes/{type1_id}.{subtype1_id}/references"
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["references"], list)
    assert len(result["references"]) == 1
    assert isinstance(result["references"][0], dict)
    assert result["references"][0]["id"] == reference1_id
    assert result["references"][0]["type_id"] == type1_id
    assert result["references"][0]["subtype_id"] == subtype1_id

    response = await authenticated_client.get(
        f"/subtypes/{type2_id}.{subtype2_id}/references"
    )
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["references"], list)
    assert len(result["references"]) == 1
    assert isinstance(result["references"][0], dict)
    assert result["references"][0]["id"] == reference2_id
    assert result["references"][0]["type_id"] == type2_id
    assert result["references"][0]["subtype_id"] == subtype2_id


@mark.dependency(depends=["test_composite_reads"])
async def test_disable_relationship_getters(authenticated_client: BrowserTestClient):
    global type1_id
    global type2_id
    global subtype1_id
    global subtype2_id
    global reference1_id
    global reference2_id

    response = await authenticated_client.get(f"/types/{type1_id}/references")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = await authenticated_client.get(f"/types/{type1_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["type"], dict)
    assert result["type"]["id"] == type1_id
    assert isinstance(result["type"]["links"], dict)
    link_dict: dict = result["type"]["links"]
    assert "references" not in link_dict.keys()

    response = await authenticated_client.get(f"/references/{reference1_id}/type")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = await authenticated_client.get(f"/references/{reference1_id}")
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert isinstance(result["reference"], dict)
    assert result["reference"]["id"] == reference1_id
    assert isinstance(result["reference"]["links"], dict)
    link_dict: dict = result["reference"]["links"]
    assert "type" not in link_dict.keys()


@mark.dependency(depends=["test_disable_relationship_getters"])
async def test_cleanup(authenticated_client: BrowserTestClient):
    global type1_id
    global type2_id
    global subtype1_id
    global subtype2_id
    global reference1_id
    global reference2_id

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
