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
---

2. Replace `@app.on_event("startup")` and `@app.on_event("shutdown")` with `lifespan` context manager.
- Upgrade your `main.py` file:
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
becomes
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
---

3. (Optional) As of December 2023, there is a known bug with sqlmodel 0.0.14 where type checking on TABLE models will complain, but will still work.
- For any models that have a corresponding database table by using `table=True` in the class declaration, modify the declaration to ignore class type checking:
```python
class Widget(CruddyModel, table=True):
    pass
```
becomes
```python
class Widget(CruddyModel, table=True):  # type: ignore
    pass
```
---

4. Schema `example` attribute has been moved to plural `examples`. Modify any use of `schema_extra` which declares `example` attribute.
- For any models that leverage  `schema_extra={"example": "some value}`:
```python
class Widget(CruddyModel):
    name: str = Field(schema_extra={"example": "Widget Name"})
```
becomes
```python
class Widget(CruddyModel):
    name: str = Field(schema_extra={"examples": ["Widget Name"]})
```
in order to maintain proper openapi.json / swagger examples.
---

5. `UTCDateTime` has been removed due to `pydantic` and `sqlalchemy` incompatibility with this custom type.
- Modify any model fields depending on cruddy's `UTCDateTime` to leverage the new `field_validator` named `validate_utc_datetime`:
```python
from typing import Optional
from sqlmodel import Field, Column, DateTime
from fastapi_cruddy_framework import CruddyModel, UTCDateTime


class Widget(CruddyModel):
    event_date: Optional[UTCDateTime] = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
```
becomes
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
---

6. `pydantic` 2+, and therefore `sqlmodel`, is more strict with `Optional` fields.
- Modify any models with `Optional` fields to conform to `pydantic` verison 2+'s stricter possible empty value declarations:
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
becomes
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
---

7. (Optional) Take advantage of new checkers and validators that ship with `fastapi-cruddy-framework`, courtesy of the [validator-collection](https://github.com/insightindustry/validator-collection/). For additional documentation on what is available, see that project's README. This change also provides an alternative to the pydantic `EmailStr` type which is no longer available for use in `pydantic` 2.0 + `sqlalchemy` 2.0.
- Modify any models that might now use `validator-collection` via importing cruddy's exports:
```python
# various imports ...

class Widget(CruddyModel):
    some_field: Optional[str] = Field(default=None)

    @field_validator("some_field", mode="before")
    @classmethod
    def validate_some_field(cls, v: str) -> str | None:
        # ... some custom e-mail address validation logic
        return v
```
becomes
```python
# various imports ...
from fastapi_cruddy_framework import field_checkers, field_validators, field_errors
# field_validators = validators
# field_checkers = checkers
# field_errors = errors


class Widget(CruddyModel):
    some_field: Optional[str] = Field(default=None)

    @field_validator("some_field", mode="before")
    @classmethod
    def validate_some_field(cls, v: str) -> str | None:
        return field_validators.email(v)
```
---

8. `pydantic` 2.0+ replaces `record.dict()` with `record.model_dump()`.
- Modify all calls to `.dict()` by replacing with `.model_dump()`:
```python
record_dict = record.dict()
```
becomes
```python
record_dict = record.model_dump()
```
---

9. `pydantic` 2.0+ moves the default `Undefined` field, and all other `fields`, to `pydantic_core`.
- Modify all references to `Undefined` or other fields:
 ```python
 from pydantic.fields import Undefined
 ```
 becomes
  ```python
 from pydantic_core import PydanticUndefined as Undefined
 ```
 This applies to all custom pydantic `fields`


 10. Model class level fields are no longer accessed via the private attribute `__fields__`.
 - Modify all references to `__fields__`:
```python
my_model.__fields__
```
becomes
```python
my_model.model_fields
```
---

11. Cruddy's `BulkDTO` type alters the `data` attribute's primary type, in accordance with the new return value from `sqlalchemy` 2.0+.
- Modify any code directly using a `BulkDTO` object to change type dependence:
```python
class BulkDTO(CruddyGenericModel):
    total_pages: int
    total_records: int
    limit: int
    page: int
    data: List[Row]
```
becomes
```python
class BulkDTO(CruddyGenericModel):
    total_pages: int
    total_records: int
    limit: int
    page: int
    data: Sequence[Row]
```
<p align="right">(<a href="#readme-top">back to top</a>)</p>
