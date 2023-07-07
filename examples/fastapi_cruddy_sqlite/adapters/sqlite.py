from examples.fastapi_cruddy_sqlite.config import adapters
from fastapi_cruddy_framework import SqliteAdapter

if adapters.DATABASE_MODE != "memory" and adapters.DATABASE_MODE != "file":
    raise TypeError(
        f"{adapters.DATABASE_MODE} is not a valid sqlite adapter mode! Please choose 'memory' or 'file'"
    )

sqlite = SqliteAdapter(
    db_path=adapters.DATABASE_PATH,
    mode=adapters.DATABASE_MODE,
)
