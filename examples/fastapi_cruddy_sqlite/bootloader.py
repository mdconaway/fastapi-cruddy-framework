import uvicorn
from examples.fastapi_cruddy_sqlite.config import http


def start():
    uvicorn.run(
        "examples.fastapi_cruddy_sqlite.main:app",
        host="0.0.0.0",
        port=http.HTTP_PORT,
        reload=True,
    )
