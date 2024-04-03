from typing import Any


def schema_example(value: Any):
    return {"json_schema_extra": {"example": value}}
