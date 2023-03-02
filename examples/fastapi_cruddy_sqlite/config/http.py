from examples.fastapi_cruddy_sqlite.config._base import Base
from pydantic import validator, AnyHttpUrl
from typing import Union, List


class Http(Base):
    HTTP_PORT: int = 8000
    HTTP_CORS_ORIGINS: Union[List[str], List[AnyHttpUrl]] = ["*"]

    @validator("HTTP_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)


http = Http()
