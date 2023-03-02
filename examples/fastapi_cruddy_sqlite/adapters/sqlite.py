from examples.fastapi_cruddy_sqlite.config import adapters
from fastapi_cruddy_framework import SqliteAdapter

sqlite = SqliteAdapter(
    db_path=adapters.DATABASE_PATH,
    mode=adapters.DATABASE_MODE,
)
