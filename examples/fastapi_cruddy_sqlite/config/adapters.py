from examples.fastapi_cruddy_sqlite.config._base import Base


class Adapters(Base):
    # Sqlite config
    DATABASE_PATH: str = "temp.db"
    DATABASE_MODE: str = "memory"


adapters = Adapters()
