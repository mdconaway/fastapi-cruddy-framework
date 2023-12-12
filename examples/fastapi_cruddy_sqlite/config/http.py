from examples.fastapi_cruddy_sqlite.config._base import Base
from pydantic import model_validator, AnyHttpUrl


class Http(Base):
    HTTP_PORT: int = 8000
    HTTP_CORS_ORIGINS: str | list[str] | list[AnyHttpUrl] = ["*"]

    @model_validator(mode="after")
    def assemble_cors_origins(self):
        if isinstance(
            self.HTTP_CORS_ORIGINS, str
        ) and not self.HTTP_CORS_ORIGINS.startswith("["):
            self.HTTP_CORS_ORIGINS = [
                i.strip() for i in self.HTTP_CORS_ORIGINS.split(",")
            ]
        elif isinstance(self.HTTP_CORS_ORIGINS, list):
            self.HTTP_CORS_ORIGINS = self.HTTP_CORS_ORIGINS
        else:
            raise ValueError(self.HTTP_CORS_ORIGINS)
        return self


http = Http()
