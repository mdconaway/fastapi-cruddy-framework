import inspect
from re import compile, Match
from typing import Type, Coroutine, Any, Callable
from pydantic.errors import PydanticErrorMixin
from sqlalchemy.orm import class_mapper, object_mapper
from datetime import datetime, timezone, timedelta
from .schemas import UUID


possible_id_types = Type[UUID] | Type[int] | Type[str]
possible_id_values = UUID | int | str
lifecycle_types = Callable[..., Coroutine[Any, Any, Any]] | None
EPOCH = datetime(1970, 1, 1)
# if greater than this, the number is in ms, if less than or equal it's in seconds
# (in seconds this is 11th October 2603, in ms it's 20th August 1970)
MS_WATERSHED = int(2e10)
# slightly more than datetime.max in ns - (datetime.max - EPOCH).total_seconds() * 1e9
MAX_NUMBER = int(3e20)
date_expr = r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})"
time_expr = (
    r"(?P<hour>\d{1,2}):(?P<minute>\d{1,2})"
    r"(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?"
    r"(?P<tzinfo>Z|[+-]\d{2}(?::?\d{2})?)?$"
)
date_re = compile(f"{date_expr}$")
time_re = compile(time_expr)
datetime_re = compile(f"{date_expr}[T ]{time_expr}")


class PydanticValueError(PydanticErrorMixin, ValueError):
    pass


class DateTimeError(PydanticValueError):
    msg_template = "invalid datetime format"


def get_numeric(
    value: str | bytes | int | float, native_expected_type: str
) -> None | int | float:
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except ValueError:
        return None
    except TypeError:
        raise TypeError(
            f"invalid type; expected {native_expected_type}, string, bytes, int or float"
        )


def from_unix_seconds(seconds: int | float) -> datetime:
    if seconds > MAX_NUMBER:
        return datetime.max
    elif seconds < -MAX_NUMBER:
        return datetime.min

    while abs(seconds) > MS_WATERSHED:
        seconds /= 1000
    dt = EPOCH + timedelta(seconds=seconds)
    return dt.replace(tzinfo=timezone.utc)


def _parse_timezone(value: str | None, error: Type[Exception]) -> None | int | timezone:
    if value == "Z":
        return timezone.utc
    elif value is not None:
        offset_mins = int(value[-2:]) if len(value) > 3 else 0
        offset = 60 * int(value[1:3]) + offset_mins
        if value[0] == "-":
            offset = -offset
        try:
            return timezone(timedelta(minutes=offset))
        except ValueError:
            raise error()
    else:
        return None


def parse_datetime(value: datetime | str | bytes | int | float) -> datetime:
    """
    Parse a datetime/int/float/string and return a datetime.datetime.

    This function supports time zone offsets. When the input contains one,
    the output uses a timezone with a fixed offset from UTC.

    Raise ValueError if the input is well formatted but not a valid datetime.
    Raise ValueError if the input isn't well formatted.
    """
    if isinstance(value, datetime):
        return value

    number = get_numeric(value, "datetime")
    if number is not None:
        return from_unix_seconds(number)

    if isinstance(value, bytes):
        value = value.decode()

    match: Match = datetime_re.match(value)  # type: ignore
    if match is None:
        raise DateTimeError("Invalid datetime", code=None)

    kw = match.groupdict()
    if kw["microsecond"]:
        kw["microsecond"] = kw["microsecond"].ljust(6, "0")

    tzinfo = _parse_timezone(kw.pop("tzinfo"), DateTimeError)
    kw_: dict[str, None | int | timezone] = {
        k: int(v) for k, v in kw.items() if v is not None
    }
    kw_["tzinfo"] = tzinfo

    try:
        return datetime(**kw_)  # type: ignore
    except ValueError:
        raise DateTimeError("Invalid datetime", code=None)


def get_pk(model):
    model_mapper = (
        class_mapper(model) if inspect.isclass(model) else object_mapper(model)
    )
    primary_key = model_mapper.primary_key[0].key
    return primary_key


def build_tz_aware_date(*args, **kwargs):
    tz = kwargs.pop("tz", timezone.utc)
    return datetime.now(*args, **kwargs, tz=tz)


def coerce_to_utc_datetime(v: datetime):
    if v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)

    return v.astimezone(timezone.utc)


def parse_and_coerce_to_utc_datetime(value: datetime | str | bytes | int | float):
    return coerce_to_utc_datetime(parse_datetime(value))


def validate_utc_datetime(
    value: datetime | str | bytes | int | float | None, allow_none: bool = False
):
    if allow_none and value is None:
        return None
    if value is None or (type(value) not in (datetime, str, bytes, int, float)):
        raise DateTimeError(f"Invalid datetime: {value}", code=None)
    return parse_and_coerce_to_utc_datetime(value)
