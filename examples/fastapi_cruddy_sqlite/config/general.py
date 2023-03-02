from examples.fastapi_cruddy_sqlite.config._base import Base


class General(Base):
    PROJECT_NAME: str = "fastapi_cruddy_sqlite"
    API_VERSION: str = "1"


general = General()
