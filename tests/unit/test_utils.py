# TODO: Add docstrings to all test functions for better contributor documentation

from typing import Any, Union, Optional
from hypothesis import given, strategies as st
from pytest import mark, raises
from datetime import datetime, date, timezone
from fastapi import Request
from fastapi_cruddy_framework import CruddyModel, UUID, uuid7
from fastapi_cruddy_framework.util import (
    parse_and_coerce_to_utc_datetime,
    DateTimeError,
    estimate_simple_example,
    squash_type,
)


@mark.dependency()
async def test_utc_datetime_parser():
    assert (
        type(
            parse_and_coerce_to_utc_datetime(
                datetime(year=2012, month=2, day=1, hour=12, minute=46)
            )
        )
        is datetime
    )
    assert (
        type(
            parse_and_coerce_to_utc_datetime(
                str(datetime(year=2012, month=2, day=1, hour=12, minute=46))
            )
        )
        is datetime
    )

    with raises(DateTimeError) as exc_info:
        parse_and_coerce_to_utc_datetime("garbage")

    assert "Invalid datetime" in str(exc_info.value)


@mark.dependency()
async def test_estimate_none():
    assert estimate_simple_example(None) == None
    assert estimate_simple_example(Union[None, None]) == None
    assert estimate_simple_example(Optional[None]) == None


# Ensures that both timezone-aware and naive objects result in UTC-aware objects.
# If something isn't UTC-aware, it is treated as naive, then coerced to UTC.
@mark.dependency()
async def test_utc_datetime_timezone():
    aware = datetime(2012, 2, 1, 12, 46, tzinfo=timezone.utc)
    naive = datetime(2012, 2, 1, 12, 46)

    result_aware = parse_and_coerce_to_utc_datetime(aware)
    result_naive = parse_and_coerce_to_utc_datetime(naive)

    assert result_aware.tzinfo == timezone.utc
    assert result_naive.tzinfo == timezone.utc

    assert result_aware == aware
    assert result_naive.replace(tzinfo=None) == naive


# This uses Hypothesis to test a wide range of inputs with Date and Time with edges, ensuring everything is coerced to UTC, avoiding confusion.
@given(st.datetimes())
def test_parse_roundtrip(dt):
    string_version = dt.isoformat()
    parsed = parse_and_coerce_to_utc_datetime(string_version)
    assert parsed.tzinfo == timezone.utc
    assert parsed.replace(tzinfo=None) == dt


# Verifies compatibility with various ISO 8601 string formats common in APIs.
@mark.parametrize(
    "iso_string",
    [
        "2012-02-01T12:46:00Z",
        "2012-02-01 12:46:00+00:00",
        "2012-02-01T12:46:00.000123Z",
    ],
)
async def test_iso_string_variants(iso_string):
    result = parse_and_coerce_to_utc_datetime(iso_string)
    assert result.year == 2012
    assert result.tzinfo == timezone.utc


@mark.parametrize(
    "year,month,day",
    [
        (2024, 2, 29),
        (1999, 12, 31),
        (1970, 1, 1),
    ],
)
async def test_calendar_boundaries(year, month, day):
    dt = datetime(year, month, day, 12, 0)
    result = parse_and_coerce_to_utc_datetime(dt)
    assert result.day == day
    assert result.month == month


# This test is to check that if we pass an object with Date and Time then it shouldn't change it, similar to what happens when we pass a string.
# This'd help in ensuring that if pass an output of the function again, it doesn't change.
async def test_idempotency():
    initial = "2012-02-01 12:46:00"
    first_pass = parse_and_coerce_to_utc_datetime(initial)
    second_pass = parse_and_coerce_to_utc_datetime(first_pass)

    assert first_pass == second_pass
    assert first_pass.tzinfo == second_pass.tzinfo


@mark.dependency()
async def test_estimate_uuid():
    assert isinstance(UUID(estimate_simple_example(UUID)), UUID)
    assert isinstance(UUID(estimate_simple_example(Union[None, UUID])), UUID)
    assert isinstance(UUID(estimate_simple_example(Optional[UUID])), UUID)


@mark.dependency()
async def test_estimate_bool():
    assert estimate_simple_example(bool) == True
    assert estimate_simple_example(Union[None, bool]) == True
    assert estimate_simple_example(Optional[bool]) == True


@mark.dependency()
async def test_estimate_string():
    assert estimate_simple_example(str) == "string"
    assert estimate_simple_example(Union[None, str]) == "string"
    assert estimate_simple_example(Optional[str]) == "string"


@mark.dependency()
async def test_estimate_int():
    assert estimate_simple_example(int) == 1
    assert estimate_simple_example(Union[None, int]) == 1
    assert estimate_simple_example(Optional[int]) == 1
    assert str(estimate_simple_example(int)) == "1"
    assert str(estimate_simple_example(Union[None, int])) == "1"
    assert str(estimate_simple_example(Optional[int])) == "1"


@mark.dependency()
async def test_estimate_float():
    assert estimate_simple_example(float) == 1.0
    assert estimate_simple_example(Union[None, float]) == 1.0
    assert estimate_simple_example(Optional[float]) == 1.0
    assert str(estimate_simple_example(float)) == "1.0"
    assert str(estimate_simple_example(Union[None, float])) == "1.0"
    assert str(estimate_simple_example(Optional[float])) == "1.0"


@mark.dependency()
async def test_estimate_dict():
    assert estimate_simple_example(dict) == {}
    assert estimate_simple_example(Union[None, dict]) == {}
    assert estimate_simple_example(Optional[dict]) == {}


@mark.dependency()
async def test_estimate_list():
    assert estimate_simple_example(list) == []
    assert estimate_simple_example(Union[None, list]) == []
    assert estimate_simple_example(Optional[list]) == []


@mark.dependency()
async def test_estimate_complex_dict():
    assert estimate_simple_example(dict[str, Any]) == {}
    assert estimate_simple_example(Union[None, dict[str, Any]]) == {}
    assert estimate_simple_example(Optional[dict[str, Any]]) == {}


@mark.dependency()
async def test_estimate_complex_list():
    assert estimate_simple_example(list[str]) == []
    assert estimate_simple_example(Union[None, list[str]]) == []
    assert estimate_simple_example(Optional[list[str]]) == []


@mark.dependency()
async def test_estimate_complex_list_of_dict():
    assert estimate_simple_example(list[dict]) == []
    assert estimate_simple_example(Union[None, list[dict]]) == []
    assert estimate_simple_example(Optional[list[dict]]) == []


@mark.dependency()
async def test_estimate_tuple():
    assert isinstance(estimate_simple_example(tuple), list)
    assert isinstance(estimate_simple_example(Union[None, tuple]), list)
    assert isinstance(estimate_simple_example(Optional[tuple]), list)


@mark.dependency()
async def test_estimate_datetime():
    assert datetime.fromisoformat(str(estimate_simple_example(datetime)))
    assert datetime.fromisoformat(str(estimate_simple_example(Union[None, datetime])))
    assert datetime.fromisoformat(str(estimate_simple_example(Optional[datetime])))


@mark.dependency()
async def test_estimate_date():
    assert date.fromisoformat(str(estimate_simple_example(date)))
    assert date.fromisoformat(str(estimate_simple_example(Union[None, date])))
    assert date.fromisoformat(str(estimate_simple_example(Optional[date])))


@mark.dependency()
async def test_estimate_invalid():
    assert estimate_simple_example(Request) == None
    assert estimate_simple_example(Union[None, Request]) == None
    assert estimate_simple_example(Optional[Request]) == None


@mark.dependency()
async def test_type_squasher():
    assert squash_type(None) == None
    assert squash_type({}) == {}
    assert squash_type([]) == []
    assert isinstance(squash_type(datetime.now()), str)
    assert isinstance(squash_type(uuid7()), str)


@mark.dependency()
async def test_pydantic_undefined():
    class TestModel(CruddyModel):
        uuid: UUID

    example = estimate_simple_example(TestModel.model_fields["uuid"].annotation)
    assert isinstance(example, str)
    assert len(example) == 36
