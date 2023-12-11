<a name="readme-top"></a>

<!-- PROJECT LOGO -->
<div align="center">
  <h2 align="center">FastAPI - Cruddy Framework: Migrating Versions</h2>
  <a href="https://github.com/mdconaway/fastapi-cruddy-framework">
    <img src="https://raw.githubusercontent.com/mdconaway/fastapi-cruddy-framework/master/logo.png" alt="Logo">
  </a>
  <br/>
</div>

<!-- Migration Guide -->

## Migration Guide

### `fastapi-cruddy-framework` 0.x.x -&gt; 1.x.x

#### Dependency Guides:
- [sqlalchemy 1-&gt;2](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html)
- [pydantic 1-&gt;2](https://docs.pydantic.dev/latest/migration/)

#### Code Mods Required:

1. Modify `BaseSettings` imports:
- Any project files using pydantic's `BaseSettings` ENV config model must shift their import target to `pydantic_settings`
```python
from pydantic import BaseSettings
```
becomes
```python
from pydantic_settings import BaseSettings
```


2. Replace `@app.on_event("startup")` and `@app.on_event("shutdown")` with `lifespan` context manager.
- Upgrade your `main.py` file to change:
```python
from fastapi import FastAPI
from myproject.router import application as application_router

app = FastAPI(title="My Project", version="0.0.0")


@app.on_event("startup")
async def bootstrap():
    app.include_router(application_router)


@app.on_event("shudtown")
async def shutdown():
    pass
```
to
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from myproject.router import application as application_router


async def bootstrap(application: FastAPI):
    application.include_router(application_router)


async def shutdown():
    pass


@asynccontextmanager
async def lifespan(application: FastAPI):
    await bootstrap(application)
    yield
    await shutdown()


app = FastAPI(
    title="My Project", version="0.0.0", lifespan=lifespan
)
```


3. (Optional) As of December 2023, there is a known bug with sqlmodel 0.0.14 where type checking on TABLE models will complain, but will still work.
- For any models that have a corresponding database table by using `table=True` in the class declaration, modify the declaration to ignore class type checking by changing:
```python
class Widget(CruddyModel, table=True):
    pass
```
to
```python
class Widget(CruddyModel, table=True):  # type: ignore
    pass
```


4. Schema `example` attribute has been moved to plural `examples`. Modify any use of `schema_extra` which declares `example` attribute.
- For any models that leverage  `schema_extra={"example": "some value}`, change:
```python
class Widget(CruddyModel):
    name: str = Field(schema_extra={"example": "Widget Name"})
```
to
```python
class Widget(CruddyModel):
    name: str = Field(schema_extra={"examples": ["Widget Name"]})
```
in order to maintain proper openapi.json / swagger examples.


5. `UTCDateTime` has been removed due to `pydantic` and `sqlalchemy` incompatibility with this custom type. Modify any model fields depending on cruddy's `UTCDateTime` to leverage the new `field_validator` named `validate_utc_datetime` by changing:
```python
from typing import Optional
from sqlmodel import Field, Column, DateTime
from fastapi_cruddy_framework import CruddyModel, UTCDateTime


class Widget(CruddyModel):
    event_date: Optional[UTCDateTime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
```
to
```python
from typing import Any, Optional
from datetime import datetime
from pydantic import field_validator
from sqlmodel import Field, Column, DateTime
from fastapi_cruddy_framework import CruddyModel, validate_utc_datetime


class Widget(CruddyModel):
    event_date: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=True,
            index=True,
            default=None,
        ),
    )

    @field_validator("event_date", mode="before")
    @classmethod
    def validate_event_date(cls, v: Any) -> datetime | None:
        return validate_utc_datetime(v, allow_none=True)
```


6. Modify any models with `Optional` fields to conform to `pydantic` verison 2+'s stricter possible empty value declarations by changing all instances of:
```python
from typing import Optional
from sqlmodel import Field
from fastapi_cruddy_framework import CruddyModel

# Style 1
class Widget(CruddyModel):
    name: Optional[str] = Field()


# Style 2
class Foo(CruddyModel):
    name: Optional[str]
```
to
```python

from typing import Optional
from sqlmodel import Field
from fastapi_cruddy_framework import CruddyModel


# Style 1
class Widget(CruddyModel):
    name: Optional[str] = Field(default=None)


# Style 2
class Foo(CruddyModel):
    name: Optional[str] = None
```
<p align="right">(<a href="#readme-top">back to top</a>)</p>
