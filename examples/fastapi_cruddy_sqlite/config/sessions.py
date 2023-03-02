from examples.fastapi_cruddy_sqlite.config._base import Base
from pydantic import validator
from typing import Optional
import secrets


class Sessions(Base):
    SESSION_COOKIE_NAME: str = "fastapi_cruddy_sqlite"
    SESSION_SECRET_KEY: str = (
        "18c14c1sas4faa6c52ge6c817165b7a9563b82e6sdsdee5f1e4dac6cf63a77f6e4c6"
    )
    SESSION_MAX_AGE: int = 1

    @validator("SESSION_SECRET_KEY", pre=True)
    def validate_session_secret(cls, v: Optional[str]) -> str:
        if isinstance(v, str):
            return v
        return secrets.token_urlsafe(32)


sessions = Sessions()
