from examples.fastapi_cruddy_sqlite.config._base import Base
from pydantic import model_validator
from secrets import token_urlsafe


class Sessions(Base):
    SESSION_COOKIE_NAME: str = "fastapi_cruddy_sqlite"
    SESSION_SECRET_KEY: str | None = None
    SESSION_MAX_AGE: int = 1

    @model_validator(mode="after")
    def validate_session_secret(self):
        self.SESSION_SECRET_KEY = (
            self.SESSION_SECRET_KEY
            if isinstance(self.SESSION_SECRET_KEY, str)
            else token_urlsafe(32)
        )
        return self


sessions = Sessions()
