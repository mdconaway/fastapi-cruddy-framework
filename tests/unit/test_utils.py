from pytest import mark, raises
from datetime import datetime
from fastapi_cruddy_framework.util import (
    parse_and_coerce_to_utc_datetime,
    DateTimeError,
)


@mark.asyncio
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
