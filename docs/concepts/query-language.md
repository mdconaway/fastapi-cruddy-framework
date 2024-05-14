## Where Queries

Additional documentation will be added soon on complete functionality supported via the CRUD endpoint / AbstractRepository `where` parameter.

### NEW QUERY FEATURES

#### Column casting!

To cast a column to a different type during a query, send a where payload like one of the examples below.

A `tsvector` cast:

```python
where = {"column_name:tsvector:english": {"*websearch_to_tsquery": "foo or bar -baz"}}
```

The query stage's casting key name for `tsvector` should match the format `<column_name>:tsvector:<vector language>`.

`tsvector` is the most complicated form of casting, as it requires the cast type (tsvector) as well as the tsvector language (english, or another langauge) in the key definition.

`tsvector` then supports the following query operators at the next level: `*websearch_to_tsquery` and `*match`, both of which mirror the sqlalchemy docs regarding functionality.

To add a `tsvector` field to your cruddy data model, complete with proper indexing for performance, add the following to your table model class:

```python
# models/example.py
from typing import Any
from sqlmodel import Field, cast, func, Text
from sqlalchemy import Column, Index, literal_column
from sqlalchemy.dialects.postgresql import JSONB, UUID as psqlUUID
from fastapi_cruddy_framework import  CruddyModel, CruddyCreatedUpdatedMixin, UUID, uuid7


class ExampleUpdate(CruddyModel):
    data: Any = Field(
        schema_extra={
            "examples": [
                {
                    "some": {
                        "key": "value"
                    }
                }
            ]
        }
    )


class ExampleCreate(ExampleUpdate):
    pass


class Example(CruddyCreatedUpdatedMixin(), ExampleCreate, table=True):  # type: ignore
    id: UUID =  Field(
        sa_column=Column(
            psqlUUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False,
            default=uuid7,
        )
    )
    data: Any = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True, default=None),
    )
    __table_args__ = (
        Index("ix_Example_data_gin", "data", postgresql_using="gin"),
        Index('ix_Example_data_tsvector', func.to_tsvector(literal_column("'english'"), cast(data.sa_column, Text)), postgresql_using="gin"),
    )
```

A `Text` (or any other) cast:

```python
where = {"a_json_column_name:Text": {"*icontains": "some substring"}}
```

The query stage's casting key name should match the format `<column_name>:<cast type>`.

Generally cast types are straightforward and expect a query operator and input type that can be mapped to the column's casted type. Supported column cast types are:

```python
array
tsvector
BigInteger
Boolean
Date
DateTime
Double
Enum
Float
Integer
Interval
LargeBinary
MatchType
Numeric
SmallInteger
String
Text
Time
Unicode
UnicodeText
Uuid
ARRAY
BIGINT
BINARY
BLOB
BOOLEAN
CHAR
CLOB
DATE
DATETIME
DECIMAL
DOUBLE
DOUBLE_PRECISION
FLOAT
INT
INTEGER
JSON
NCHAR
NUMERIC
NVARCHAR
REAL
SMALLINT
TEXT
TIME
TIMESTAMP
UUID
VARBINARY
VARCHAR
```

#### Value casting!

Datetime value with timezone:

```python
where = {"datetime_column": {"*gt": {"*datetime": "2024-02-14T19:17:40.860657Z"}}}
```

Datetime value without timezone:

```python
where = {"datetime_column": {"*gt": {"*datetime_naive": "2024-02-14T19:17:40.860657Z"}}}
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>
