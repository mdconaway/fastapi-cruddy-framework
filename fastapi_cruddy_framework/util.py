import inspect
from sqlalchemy.orm import class_mapper, object_mapper
from typing import Union, Optional, Coroutine, Any, Callable
from .uuid import UUID


def get_pk(model):
    model_mapper = (
        class_mapper(model) if inspect.isclass(model) else object_mapper(model)
    )
    primary_key = model_mapper.primary_key[0].key
    return primary_key


possible_id_types = Union[UUID, int, str]

lifecycle_types = Optional[Callable[..., Coroutine[Any, Any, Any]]]
