from typing import Any, Union, Optional
from pytest import mark, raises
from datetime import datetime, date
from fastapi import Request
from fastapi_cruddy_framework import UUID
from fastapi_cruddy_framework.util import (
    parse_and_coerce_to_utc_datetime,
    DateTimeError,
    estimate_simple_example,
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
    with raises(DateTimeError):
        parse_and_coerce_to_utc_datetime("garbage")


@mark.dependency()
async def test_estimate_none():
    assert estimate_simple_example(None) == None
    assert estimate_simple_example(Union[None, None]) == None
    assert estimate_simple_example(Optional[None]) == None


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
    assert estimate_simple_example(tuple) == []
    assert estimate_simple_example(Union[None, tuple]) == []
    assert estimate_simple_example(Optional[tuple]) == []


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
