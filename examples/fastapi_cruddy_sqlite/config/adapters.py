from typing import Literal
from examples.fastapi_cruddy_sqlite.config._base import Base


class Adapters(Base):
    # Sqlite config
    DATABASE_PATH: str = "temp.db"
    DATABASE_MODE: Literal["memory"] | Literal["file"] = "memory"
    REDIS_MODE: Literal["memory"] | Literal["redis"] = "memory"


adapters = Adapters()
