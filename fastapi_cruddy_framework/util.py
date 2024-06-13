import inspect
from typing import Type, Coroutine, Any, Callable, Union
from typing_extensions import get_args, get_origin
from datetime import date, datetime, timezone
from json import dumps, loads
from datetime import date, datetime, timezone, timedelta
from re import compile, Match
from fastapi import Request, WebSocket, Depends
from fastapi.requests import HTTPConnection
from fastapi.types import UnionType
from pydantic.errors import PydanticErrorMixin
from sqlalchemy.orm import class_mapper, object_mapper
from .schemas import UUID, uuid7


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


def dependency_list(*args):
    return [Depends(x) for x in args]


def filter_headers(header_dict: dict, blacklist: list[str] | None = None):
    blacklist = (
        [
            "host",
            "connection",
            "content-length",
            "sec-ch-ua",
            "accept",
            "content-type",
            "sec-ch-ua-mobile",
            "sec-ch-ua-platform",
            "origin",
            "sec-fetch-site",
            "sec-fetch-mode",
            "sec-fetch-dest",
            "referer",
            "accept-encoding",
            "accept-language",
        ]
        if blacklist is None
        else blacklist
    )
    for key in blacklist:
        if key in header_dict:
            del header_dict[key]
    return header_dict


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
        class_mapper(model) if inspect.isclass(model) else object_mapper(model)  # type: ignore
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


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return f"{obj}"
    return f"{obj}"


def to_json_string(thing):
    return dumps(thing, default=json_serial)


def to_json_object(thing):
    return loads(to_json_string(thing))


def get_state(
    connection: Request | WebSocket | HTTPConnection,
    key: str,
    default: Any | None = None,
) -> Any:
    return getattr(connection.state, key, default)


def set_state(
    connection: Request | WebSocket | HTTPConnection, key: str, value: Any
) -> None:
    setattr(connection.state, key, value)


def squash_type(value: Any):
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (bool, str, int, float)):
        return value
    if isinstance(value, (dict, list)):
        return to_json_object(value)
    return f"{value}"


def estimate_example_for_type(type_annotation: type[Any] | None):
    if type_annotation is None or not inspect.isclass(type_annotation):
        return None
    if issubclass(type_annotation, UUID):
        return f"{uuid7()}"
    if issubclass(type_annotation, bool):
        return True
    if issubclass(type_annotation, str):
        return "string"
    if issubclass(type_annotation, int):
        return 1
    if issubclass(type_annotation, float):
        return 1.0
    if issubclass(type_annotation, dict):
        return {}
    if issubclass(type_annotation, list):
        return []
    if issubclass(type_annotation, tuple):
        return []
    if issubclass(type_annotation, datetime):
        return datetime.now(tz=timezone.utc).isoformat()
    if issubclass(type_annotation, date):
        return date.today().isoformat()
    return None


def estimate_simple_example(annotation: Any | None) -> Any | None:
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        for arg in get_args(annotation):
            possible_example = estimate_example_for_type(arg)
            if possible_example is not None:
                return possible_example
            possible_example = estimate_simple_example(arg)
            if possible_example is not None:
                return possible_example
    if (possible_example := estimate_example_for_type(annotation)) is not None:
        return possible_example
    return estimate_example_for_type(origin)
