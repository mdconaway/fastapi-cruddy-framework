import inspect
from datetime import datetime, timezone
from sqlalchemy.orm import class_mapper, object_mapper
from typing import Type, Union, Optional, Coroutine, Any, Callable
from .uuid import UUID


def get_pk(model):
    model_mapper = (
        class_mapper(model) if inspect.isclass(model) else object_mapper(model)
    )
    primary_key = model_mapper.primary_key[0].key
    return primary_key


def build_tz_aware_date(*args, **kwargs):
    if len(args) > 0 or len(kwargs) > 0:
        return datetime.now(*args, **kwargs)
    return datetime.now(timezone.utc)


def coerce_to_utc_datetime(v: datetime):
    if v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)

    return v.astimezone(timezone.utc)


possible_id_types = Union[Type[UUID], Type[int], Type[str]]

possible_id_values = Union[UUID, int, str]

lifecycle_types = Optional[Callable[..., Coroutine[Any, Any, Any]]]
