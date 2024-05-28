from fastapi_cruddy_framework import SqliteAdapter
from examples.fastapi_cruddy_sqlite.config import adapters

sqlite = SqliteAdapter(
    db_path=adapters.DATABASE_PATH,
    mode=adapters.DATABASE_MODE,
)
