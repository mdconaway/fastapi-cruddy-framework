import math
from typing import Any
from asyncio import gather
from logging import getLogger
from sqlalchemy import (
    update as _update,
    delete as _delete,
    or_,
    and_,
    not_,
    func,
    Cast,
    literal_column,
)
from sqlalchemy.dialects.postgresql import JSONB, array
from sqlalchemy.engine import Result
from sqlalchemy.sql import select, update
from sqlalchemy.sql.schema import Table, Column
from sqlalchemy.types import (
    ARRAY,
    BIGINT,
    BINARY,
    BLOB,
    BOOLEAN,
    CHAR,
    CLOB,
    DATE,
    DATETIME,
    DECIMAL,
    DOUBLE,
    DOUBLE_PRECISION,
    FLOAT,
    INT,
    INTEGER,
    JSON,
    NCHAR,
    NUMERIC,
    NVARCHAR,
    REAL,
    SMALLINT,
    TEXT,
    TIME,
    TIMESTAMP,
    UUID,
    VARBINARY,
    VARCHAR,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Double,
    Enum,
    Float,
    Integer,
    Interval,
    LargeBinary,
    MatchType,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    Unicode,
    UnicodeText,
    Uuid,
)
from sqlalchemy.orm import RelationshipProperty, ONETOMANY, MANYTOMANY
from sqlmodel import cast, inspect
from typing import Type
from pydantic_core import PydanticUndefined as Undefined
from pydantic.types import Json
from .schemas import (
    BulkDTO,
    CruddyModel,
)
from .adapters import BaseAdapter, SqliteAdapter, MysqlAdapter, PostgresqlAdapter
from .util import (
    get_pk,
    possible_id_types,
    possible_id_values,
    lifecycle_types,
    parse_and_coerce_to_utc_datetime,
    parse_datetime,
)

JSON_COLUMNS = (JSON, JSONB)
# The CAST MAP provides composite keys (lhs comparator|rhs value type) which map to a DB cast function
# An empty rhs value type means "all explicitly untracked" types should be cast as this
# def get_cast_type(v: Any):

QUERY_FORGE_CAST_MAP = {
    "*contains:dict": lambda v, model_attr: cast(v, model_attr.type),
    "*contains:list": lambda v, model_attr: cast(v, model_attr.type),
    "*contains:": lambda v, model_attr: cast(v, model_attr.type),
    "*contained_by:dict": lambda v, model_attr: cast(v, model_attr.type),
    "*contained_by:list": lambda v, model_attr: cast(v, model_attr.type),
    "*contained_by:": lambda v, model_attr: cast([v], model_attr.type),  # type: ignore
    "*has_key:": lambda v, *args: cast(v, VARCHAR),
    # The following are only supported by postgres... for now
    "*has_all:": lambda v, *args: array([v]),  # cast([v], ARRAY),  # type: ignore
    "*has_all:list": lambda v, *args: array(v),  # cast(v, ARRAY),
    "*has_any:": lambda v, *args: array([v]),  # cast([v], ARRAY),  # type: ignore
    "*has_any:list": lambda v, *args: array(v),  # cast(v, ARRAY),
}
TYPE_CAST_MAP = {
    "array": array,
    "ARRAY": ARRAY,
    "BIGINT": BIGINT,
    "BINARY": BINARY,
    "BLOB": BLOB,
    "BOOLEAN": BOOLEAN,
    "CHAR": CHAR,
    "CLOB": CLOB,
    "DATE": DATE,
    "DATETIME": DATETIME,
    "DECIMAL": DECIMAL,
    "DOUBLE": DOUBLE,
    "DOUBLE_PRECISION": DOUBLE_PRECISION,
    "FLOAT": FLOAT,
    "INT": INT,
    "INTEGER": INTEGER,
    "JSON": JSON,
    "NCHAR": NCHAR,
    "NUMERIC": NUMERIC,
    "NVARCHAR": NVARCHAR,
    "REAL": REAL,
    "SMALLINT": SMALLINT,
    "TEXT": TEXT,
    "TIME": TIME,
    "TIMESTAMP": TIMESTAMP,
    "UUID": UUID,
    "VARBINARY": VARBINARY,
    "VARCHAR": VARCHAR,
    "BigInteger": BigInteger,
    "Boolean": Boolean,
    "Date": Date,
    "DateTime": DateTime,
    "Double": Double,
    "Enum": Enum,
    "Float": Float,
    "Integer": Integer,
    "Interval": Interval,
    "LargeBinary": LargeBinary,
    "MatchType": MatchType,
    "Numeric": Numeric,
    "SmallInteger": SmallInteger,
    "String": String,
    "Text": Text,
    "Time": Time,
    "Unicode": Unicode,
    "UnicodeText": UnicodeText,
    "Uuid": Uuid,
}
QUERY_FORGE_COMMON = ("*eq", "*neq", "*gt", "*gte", "*lt", "*lte")
UNSUPPORTED_LIKE_COLUMNS = [
    "UUID",
    "INTEGER",
    "SMALLINT",
    "BIGINT",
    "REAL",
    "DOUBLE PRECISION",
    "SMALLSERIAL",
    "SERIAL",
    "BIGSERIAL",
    "DATE",
    "DATETIME",
    "TIMESTAMP",
    "TIME",
    "INTERVAL",
]


def cast_column(model_attribute: Column, cast_to: str):
    castable_type = TYPE_CAST_MAP.get(cast_to, None)
    if castable_type is None:
        raise ValueError(
            f"'{cast_to}' is not a valid cast type. Available cast types: {', '.join(TYPE_CAST_MAP.keys())}"
        )
    return cast(model_attribute, castable_type)


LOGGER = getLogger(__file__)


# -------------------------------------------------------------------------------------------
# REPOSITORY MANAGER
# -------------------------------------------------------------------------------------------
class AbstractRepository:
    adapter: BaseAdapter | SqliteAdapter | MysqlAdapter | PostgresqlAdapter
    update_model: Type[CruddyModel]
    create_model: Type[CruddyModel]
    model: Type[CruddyModel]
    id_type: possible_id_types
    primary_key: str | None = None
    lifecycle: dict[str, lifecycle_types] = {
        "before_create": None,
        "after_create": None,
        "before_update": None,
        "after_update": None,
        "before_delete": None,
        "after_delete": None,
        "before_get_one": None,
        "after_get_one": None,
        "before_get_all": None,
        "after_get_all": None,
        "before_set_relations": None,
        "after_set_relations": None,
    }

    op_map: dict

    def __init__(
        self,
        adapter: BaseAdapter | SqliteAdapter | MysqlAdapter | PostgresqlAdapter,
        update_model: Type[CruddyModel],
        create_model: Type[CruddyModel],
        model: Type[CruddyModel],
        id_type: possible_id_types = int,
        lifecycle_before_create: lifecycle_types = None,
        lifecycle_after_create: lifecycle_types = None,
        lifecycle_before_update: lifecycle_types = None,
        lifecycle_after_update: lifecycle_types = None,
        lifecycle_before_delete: lifecycle_types = None,
        lifecycle_after_delete: lifecycle_types = None,
        lifecycle_before_get_one: lifecycle_types = None,
        lifecycle_after_get_one: lifecycle_types = None,
        lifecycle_before_get_all: lifecycle_types = None,
        lifecycle_after_get_all: lifecycle_types = None,
        lifecycle_before_set_relations: lifecycle_types = None,
        lifecycle_after_set_relations: lifecycle_types = None,
    ):
        self.adapter = adapter
        self.update_model = update_model
        self.create_model = create_model
        self.model = model
        self.id_type = id_type
        self.op_map = {
            "*and": and_,
            "*or": or_,
            "*not": not_,
        }
        self.lifecycle = {
            "before_create": lifecycle_before_create,
            "after_create": lifecycle_after_create,
            "before_update": lifecycle_before_update,
            "after_update": lifecycle_after_update,
            "before_delete": lifecycle_before_delete,
            "after_delete": lifecycle_after_delete,
            "before_get_one": lifecycle_before_get_one,
            "after_get_one": lifecycle_after_get_one,
            "before_get_all": lifecycle_before_get_all,
            "after_get_all": lifecycle_after_get_all,
            "before_set_relations": lifecycle_before_set_relations,
            "after_set_relations": lifecycle_after_set_relations,
        }

    def resolve(self):
        # Can't do this until all models are defined, otherwise mappers break
        self.primary_key = get_pk(self.model)

    async def create(self, data: CruddyModel) -> CruddyModel:
        # create user data
        async with self.adapter.getSession() as session:
            record = self.model(**data.model_dump())
            if self.lifecycle["before_create"]:
                await self.lifecycle["before_create"](record)
            session.add(record)
        if self.lifecycle["after_create"]:
            await self.lifecycle["after_create"](record)
        return record
        # return a value?

    async def get_by_id(self, id: possible_id_values, where: Json = None) -> Any | None:
        # retrieve user data by id
        async with self.adapter.getSession() as session:
            if self.lifecycle["before_get_one"]:
                await self.lifecycle["before_get_one"](id, where)
            query = select(self.model).where(
                and_(
                    getattr(self.model, str(self.primary_key)) == id,
                    *self.query_forge(model=self.model, where=where),
                )
            )
            result = (await session.execute(query)).scalar_one_or_none()
        if self.lifecycle["after_get_one"]:
            await self.lifecycle["after_get_one"](result)
        return result

    async def update(self, id: possible_id_values, data: CruddyModel):
        # update user data
        values = data.model_dump()
        if self.lifecycle["before_update"]:
            await self.lifecycle["before_update"](values, id)
        query = (
            _update(self.model)
            .where(getattr(self.model, str(self.primary_key)) == id)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        async with self.adapter.getSession() as session:
            result = await session.execute(query)
        if result.rowcount == 1:  # type: ignore
            updated_record = await self.get_by_id(id=id)
            if self.lifecycle["after_update"]:
                await self.lifecycle["after_update"](updated_record)
            return updated_record
        return None
        # return a value?

    async def delete(self, id: possible_id_values):
        # delete user data by id
        record = await self.get_by_id(id=id)
        if self.lifecycle["before_delete"]:
            await self.lifecycle["before_delete"](record)
        query = (
            _delete(self.model)
            .where(getattr(self.model, str(self.primary_key)) == id)
            .execution_options(synchronize_session="fetch")
        )
        async with self.adapter.getSession() as session:
            result = await session.execute(query)

        if result.rowcount == 1:  # type: ignore
            if self.lifecycle["after_delete"]:
                await self.lifecycle["after_delete"](record)
            return record
        return None
        # return a value?

    async def get_all(
        self,
        page: int = 1,
        limit: int = 10,
        columns: list[str] | None = None,
        sort: list[str] | None = None,
        where: Json = None,
        # possible lifecycle hooks from foreign resource
        _lifecycle_before: lifecycle_types = None,
        _lifecycle_after: lifecycle_types = None,
        _use_own_hooks: bool = True,
    ) -> BulkDTO:
        query_conf = {
            "page": page,
            "limit": limit,
            "columns": columns,
            "sort": sort,
            "where": where,
        }

        if _use_own_hooks:
            lifecycle_before = self.lifecycle["before_get_all"]
            lifecycle_after = self.lifecycle["after_get_all"]
        else:
            lifecycle_before = _lifecycle_before
            lifecycle_after = _lifecycle_after

        if lifecycle_before:
            # apps can alter user queries in this hook!!
            # use this hook to force things to be in a range, like limits!
            # setting conf.limit = 20 in user app code would alter the limit for
            # this query
            await lifecycle_before(query_conf)

        get_columns: list[str] = (
            query_conf["columns"]
            if query_conf["columns"] is not None and query_conf["columns"] != []
            else list(self.model.model_fields.keys())
        )
        if self.primary_key not in get_columns:
            get_columns.append(str(self.primary_key))

        select_items = [getattr(self.model, x) for x in get_columns]
        query = select(*select_items)

        if isinstance(query_conf["where"], dict) or isinstance(
            query_conf["where"], list
        ):
            query = query.filter(
                and_(*self.query_forge(model=self.model, where=query_conf["where"]))
            )

        # select sort dynamically
        if query_conf["sort"] is not None and query_conf["sort"] != []:
            # we need sort format data like this --> ['id asc','name desc', 'email']
            def splitter(sort_string: str):
                parts = sort_string.split(" ")
                getter = "asc"
                if len(parts) == 2:
                    getter = parts[1]
                return getattr(getattr(self.model, parts[0]), getter)

            sorts = [splitter(x) for x in query_conf["sort"]]
            for field in sorts:
                query = query.order_by(field())

        # count query
        count_query = select(func.count(1)).select_from(query)  # type: ignore
        offset_page = query_conf["page"] - 1
        # pagination
        query = query.offset(offset_page * query_conf["limit"]).limit(
            query_conf["limit"]
        )
        # total record

        async with self.adapter.getSession() as session1:
            async with self.adapter.getSession() as session2:
                results = await gather(
                    session1.execute(count_query),
                    session2.execute(query),
                    return_exceptions=False,
                )
                count: Result = results[0]
                records: Result = results[1]
                total_record = count.scalar() or 0
                result = records.fetchall()

        # possible pass in outside functions to map/alter data?
        # total page
        total_page = math.ceil(total_record / query_conf["limit"])
        result = BulkDTO(
            total_pages=total_page,
            total_records=total_record,
            page=query_conf["page"],
            limit=query_conf["limit"],
            data=result,
        )

        if lifecycle_after:
            await lifecycle_after(result)

        return result

    async def get_all_relations(
        self,
        id: possible_id_values,
        relation: str,
        relation_model: Type[CruddyModel],
        page: int = 1,
        limit: int = 10,
        columns: list[str] | None = None,
        sort: list[str] | None = None,
        where: Json = None,
        # the foreign repository's lifecycle hooks must be injected
        _lifecycle_before: lifecycle_types = None,
        _lifecycle_after: lifecycle_types = None,
    ) -> BulkDTO:
        # The related id column is mandatory or the join will explode
        relation_pk = get_pk(relation_model)

        query_conf = {
            "page": page,
            "limit": limit,
            "columns": columns,
            "sort": sort,
            "where": where,
        }

        if _lifecycle_before:
            await _lifecycle_before(query_conf)

        get_columns: list[str] = (
            query_conf["columns"]
            if query_conf["columns"] is not None and query_conf["columns"] != []
            else list(relation_model.model_fields.keys())
        )
        if relation_pk not in get_columns:
            get_columns.append(relation_pk)

        select_items = [getattr(relation_model, x) for x in get_columns]

        query = select(*select_items)

        query = query.join(getattr(self.model, relation))

        joinable = [getattr(self.model, str(self.primary_key)) == id]

        if isinstance(query_conf["where"], dict) or isinstance(
            query_conf["where"], list
        ):
            joinable.extend(
                self.query_forge(model=relation_model, where=query_conf["where"])
            )
        query = query.filter(and_(*joinable))

        # select sort dynamically
        if query_conf["sort"] is not None and query_conf["sort"] != []:
            # we need sort format data like this --> ['id asc','name desc', 'email']
            def splitter(sort_string: str):
                parts = sort_string.split(" ")
                getter = "asc"
                if len(parts) == 2:
                    getter = parts[1]
                return getattr(getattr(relation_model, parts[0]), getter)

            sorts = [splitter(x) for x in query_conf["sort"]]
            for field in sorts:
                query = query.order_by(field())

        # count query
        count_query = select(func.count(1)).select_from(query)  # type: ignore
        offset_page = query_conf["page"] - 1
        # pagination
        query = query.offset(offset_page * query_conf["limit"]).limit(
            query_conf["limit"]
        )
        # total record

        async with self.adapter.getSession() as session1:
            async with self.adapter.getSession() as session2:
                results = await gather(
                    session1.execute(count_query),
                    session2.execute(query),
                    return_exceptions=False,
                )
                count: Result = results[0]
                records: Result = results[1]
                total_record = count.scalar() or 0
                result = records.fetchall()

        # possible pass in outside functions to map/alter data?
        # total page
        total_page = math.ceil(total_record / query_conf["limit"])
        result = BulkDTO(
            total_pages=total_page,
            total_records=total_record,
            page=query_conf["page"],
            limit=query_conf["limit"],
            data=result,
        )

        if _lifecycle_after:
            await _lifecycle_after(result)
        return result

    # This one is rather "alchemy" because join tables aren't resources
    async def set_many_many_relations(
        self,
        id: possible_id_values,
        relation: str,
        relations: list[possible_id_values],
    ):
        relation_conf = {"id": id, "relation": relation, "relations": relations}

        if self.lifecycle["before_set_relations"]:
            await self.lifecycle["before_set_relations"](relation_conf)

        model_relation: RelationshipProperty = getattr(
            inspect(self.model).relationships, relation_conf["relation"]
        )
        pairs = list(model_relation.local_remote_pairs)  # type: ignore
        # origin_table: Table = None
        # origin_key: str = None
        join_table: Table | None = None
        join_table_origin_attr: str | None = None
        join_table_foreign_attr: str | None = None
        join_table_foreign: Table | None = None
        foreign_table: Table | None = None
        foreign_key: str | None = None
        for v in pairs:
            local: Column = v[0]  # type: ignore
            remote: Column = v[1]  # type: ignore
            if local.table.name == self.model.__tablename__:
                join_table = remote.table
                join_table_origin_attr = remote.key
                # origin_table = local.table
                # origin_key = local.key
                # This is the link from our origin model to the join table

            else:
                join_table_foreign_attr = remote.key
                join_table_foreign = remote.table
                foreign_table = local.table
                foreign_key = local.key
                # This is the link from the join table to the related model

        if join_table is None or foreign_table is None or join_table_foreign is None:
            raise TypeError("join table configuration is undefined")

        if join_table.name != join_table_foreign.name:
            raise TypeError("Relationship many to many tables are not the same type!")

        validation_target_col: Column = getattr(foreign_table.columns, str(foreign_key))
        # origin_id_col: Column = getattr(origin_table.columns, origin_key)
        join_origin_col: Column = getattr(
            join_table.columns, str(join_table_origin_attr)
        )
        join_foreign_col: Column = getattr(
            join_table.columns, str(join_table_foreign_attr)
        )
        validate_relation_ids = select(validation_target_col).where(
            validation_target_col.in_(relation_conf["relations"])
        )
        clear_relations_query = (
            join_table.delete()
            .where(join_origin_col == relation_conf["id"])
            .execution_options(synchronize_session="fetch")
        )
        async with self.adapter.getSession() as session:
            # origin_id = (await session.execute(validate_origin_id)).scalar_one_or_none()
            db_ids = (await session.execute(validate_relation_ids)).fetchall()
            insertable = [
                {
                    join_table_origin_attr: relation_conf["id"],
                    join_table_foreign_attr: f"{x._mapping[foreign_key]}",  # type: ignore
                }
                for x in db_ids
            ]
            create_relations_query = join_table.insert().values(
                insertable
            )  # .returning(join_foreign_col) # RETURNING DOESNT WORK ON ALL ADAPTERS
            await session.execute(clear_relations_query)

        async with self.adapter.getSession() as session:
            check_ids = [f"{x._mapping[foreign_key]}" for x in db_ids]  # type: ignore
            if len(insertable) > 0:
                await session.execute(create_relations_query)
                find_tgt_query = select(join_table).where(
                    and_(
                        join_origin_col == relation_conf["id"],
                        join_foreign_col.in_(check_ids),
                    )
                )
                count_query = select(func.count(1)).select_from(find_tgt_query)  # type: ignore
                result: int = (await session.execute(count_query)).scalar() or 0
            else:
                result = 0

        if self.lifecycle["after_set_relations"]:
            await self.lifecycle["after_set_relations"](
                {
                    "model": self.model,
                    "relation_conf": relation_conf,
                    "relation_type": MANYTOMANY,
                    "related_table": foreign_table,
                    "related_field": validation_target_col.name,
                    "updated_db_count": result,
                }
            )

        return result

    # There should probably be a configuration flag to disable this form of unsafe relationship update
    async def set_one_many_relations(
        self,
        id: possible_id_values,
        relation: str,
        relations: list[possible_id_values],
    ) -> int:
        relation_conf = {"id": id, "relation": relation, "relations": relations}

        if self.lifecycle["before_set_relations"]:
            await self.lifecycle["before_set_relations"](relation_conf)

        model_relation: RelationshipProperty = getattr(
            inspect(self.model).relationships, relation_conf["relation"]
        )
        pairs = list(model_relation.local_remote_pairs)  # type: ignore
        found = False
        related_model: Table | None = None
        far_col_name: str | None = None
        far_col: Column | None = None
        for v in pairs:
            local: Column = v[0]  # type: ignore
            remote: Column = v[1]  # type: ignore
            if local.table.name == self.model.__tablename__:
                related_model = remote.table
                far_col_name = remote.key
                far_col = remote
                found = True
                # origin_table = local.table
                # origin_key = local.key
                # This is the link from our origin model to the join table
        if (
            not found
            or related_model is None
            or far_col_name is None
            or far_col is None
        ):
            raise RuntimeError(
                "This should be impossible, but there was not a valid one-to-many relationship"
            )

        rel_pk, related_model_id = related_model.primary_key.columns.items()[0]

        clear_query = (
            update(table=related_model)
            .values({far_col_name: None})
            .where(far_col.in_([relation_conf["id"]]))
        )
        alter_query = (
            update(table=related_model)
            .values({far_col_name: relation_conf["id"]})
            .where(related_model_id.in_(relation_conf["relations"]))
            # .returning(related_model_id) # RETURNING DOESNT WORK ON ALL ADAPTERS
        )
        find_tgt_query = select(related_model).where(
            and_(
                far_col == relation_conf["id"],
                related_model_id.in_(relation_conf["relations"]),
            )
        )
        count_query = select(func.count(1)).select_from(find_tgt_query)  # type: ignore
        if far_col.nullable:
            async with self.adapter.getSession() as session:
                await session.execute(clear_query)
        else:
            LOGGER.warn(
                f"Unable to clear relations for {related_model.name}.{far_col_name}. Column does not allow null values"
            )
        async with self.adapter.getSession() as session:
            await session.execute(
                alter_query
            )  # .rowcount # also affected by removing returning
            alter_result: int = (await session.execute(count_query)).scalar() or 0

        if self.lifecycle["after_set_relations"]:
            await self.lifecycle["after_set_relations"](
                {
                    "model": self.model,
                    "relation_conf": relation_conf,
                    "relation_type": ONETOMANY,
                    "related_table": related_model,
                    "related_field": far_col_name,
                    "updated_db_count": alter_result,
                }
            )

        return alter_result

    # Initial, simple, query forge. Invalid attrs or ops are just dropped.
    # Improvements to make:
    # 1. Table joins for relationships.
    # 2. Make relationships searchable too!
    # 3. Maybe throw an error if a bad search field is sent? (Will help UI devs)
    # build an arbitrarily deep query with a JSON dictionary
    # a query object is a JSON object that generally looks like
    # all boolean operators, or field level operators, begin with a
    # * character. This will nearly always translate down to the sqlalchemy
    # level, where it is up to the model class to determine what operations
    # are possible on each model attribute.
    # The top level query object is an implicit AND.
    # To do an OR, the base key of the search must be *or, as below examples:
    # {"*or":{"first_name":"bilbo","last_name":"baggins"}}
    # {"*or":{"first_name":{"*contains":"bilbo"},"last_name":"baggins"}}
    # {"*or":{"first_name":{"*endswith":"bilbo"},"last_name":"baggins","*and":{"email":{"*contains":"@"},"first_name":{"*contains":"helga"}}}}
    # {"*or":{"first_name":{"*endswith":"bilbo"},"last_name":"baggins","*and":[{"email":{"*contains":"@"}},{"email":{"*contains":"helga"}}]}}
    # The following query would be an implicit *and:
    # [{"first_name":{"*endswith":"bilbo"}},{"last_name":"baggins"}]
    # As would the following query:
    # {"first_name":{"*endswith":"bilbo"},"last_name":"baggins"}
    # Initial support for JSON and JSON-like columns via "dot" notation can be performed in two ways
    # The first being as a lookup comparator. This approach supports standard equality checks and will cast the nested JSON value to that of
    # the comparison value. This is shown in the following query
    # [{"this.is.a.nested.json.value": { "*eq": 5 }}]
    # The second approach is to leverage a platform specific DB function. The following is a POSTGRES only function for
    # verifying that the lhs includes the rhs of the query
    # [{"this.is.a.nested.dict": {"*contains": {"sixthLevel": {"seventhLevel": "FOO"}} } }]
    # To perform "dot" notation on the top-level of a JSON-like column, simply place a period after the top-level keyname
    # [{"topLevel.": {"*contained_by": {"topLevel": {"nested": "value"}, "siblingTopLevel": {"this": "does not matter"}}} }]
    # This function needs to be extended to support "dot" notation in left hand keys to imply joined relation searchers
    def query_forge(
        self,
        model: Type[CruddyModel] | RelationshipProperty,
        where: dict[str, Any] | list[dict[str, Any]],
    ):
        level_criteria = []

        if not (isinstance(where, list) or isinstance(where, dict)):
            return []

        if isinstance(where, list):
            list_of_lists = [self.query_forge(model=model, where=x) for x in where]
            for l in list_of_lists:
                level_criteria += l
            return level_criteria

        for k, v in where.items():
            is_op = self.op_map[k] if k in self.op_map else False
            colon_parts = k.split(":")
            dot_parts = k.split(".")
            is_colon = len(colon_parts) > 1
            is_dot = len(dot_parts) > 1
            key_value = dot_parts[0] if is_dot else colon_parts[0]

            if is_op != False:
                if isinstance(v, dict):
                    level_criteria.append(
                        is_op(*self.query_forge(model=model, where=v))
                    )
                elif isinstance(v, list):
                    level_criteria.append(
                        is_op(*self.query_forge(model=model, where=v))
                    )
            else:
                if not hasattr(model, key_value):
                    raise ValueError(
                        f"Model {model.__name__} does not have a key/column of {key_value}"
                    )

                base_attribute: Column = getattr(model, key_value)
                model_attribute: Column | Cast | Any

                if is_colon and not is_dot:
                    cast_to = colon_parts[1]
                    if cast_to == "tsvector" and len(colon_parts) == 3:
                        cast_to_language = colon_parts[2]
                        model_attribute = func.to_tsvector(
                            literal_column(f"'{cast_to_language}'"),
                            cast(base_attribute, Text),
                        )
                    else:
                        model_attribute = cast_column(base_attribute, cast_to)
                else:
                    model_attribute = base_attribute

                if not isinstance(v, dict):
                    # Add type coerce fn?
                    has_like_attr = hasattr(model_attribute, "like")
                    unsupported_likes = (
                        str(model_attribute.type).upper() in UNSUPPORTED_LIKE_COLUMNS
                    )
                    maybe_supports_like = (
                        (not unsupported_likes) and has_like_attr and isinstance(v, str)
                    )
                    level_criteria.append(
                        model_attribute.like(v)
                        if maybe_supports_like
                        else model_attribute == v
                    )
                elif (
                    isinstance(v, dict)
                    and is_dot
                    and len(v.items()) == 1
                    and isinstance(
                        getattr(model, key_value, Undefined).type, JSON_COLUMNS  # type: ignore
                    )
                ):
                    [_, *json_path] = dot_parts
                    json_path_parts = tuple(
                        int(segment) if segment.isdigit() else segment
                        for segment in filter(lambda val: val != "", json_path)
                    )

                    k2 = list(v.keys())[0]
                    v2 = v[k2]
                    is_basic_comparison = k2 in QUERY_FORGE_COMMON

                    # Cast the rhs to support complex queries if needed
                    cast_fn = QUERY_FORGE_CAST_MAP.get(f"{k2}:{type(v2).__name__}")

                    # If there isn't a cast_fn set, let's see if there's a mapped 'catch_all' cast fn
                    # for the lhs provided
                    if cast_fn is None:
                        cast_fn = QUERY_FORGE_CAST_MAP.get(f"{k2}:")

                    # If there is a cast function for the value, let's run it
                    if cast_fn:
                        v2 = cast_fn(v2, model_attribute)

                    # Cast the lhs path based on comparator value when performing a direct comparison
                    # by default the value is cast as JSON
                    casted_path = model_attribute[json_path_parts].as_json()
                    if isinstance(v2, int) and is_basic_comparison:
                        casted_path = model_attribute[json_path_parts].as_integer()
                    elif isinstance(v2, bool) and is_basic_comparison:
                        casted_path = model_attribute[json_path_parts].as_boolean()
                    elif isinstance(v2, float) and is_basic_comparison:
                        casted_path = model_attribute[json_path_parts].as_float()
                    elif isinstance(v2, str) and is_basic_comparison:
                        casted_path = model_attribute[json_path_parts].as_string()

                    if isinstance(k2, str) and k2[0] == "*":
                        if k2 == "*eq":
                            level_criteria.append(casted_path == v2)
                        elif k2 == "*neq":
                            level_criteria.append(casted_path != v2)
                        elif k2 == "*gt":
                            level_criteria.append(casted_path > v2)
                        elif k2 == "*lt":
                            level_criteria.append(casted_path < v2)
                        elif k2 == "*gte":
                            level_criteria.append(casted_path >= v2)
                        elif k2 == "*lte":
                            level_criteria.append(casted_path <= v2)
                        elif hasattr(model_attribute, k2.replace("*", "")):
                            level_criteria.append(
                                getattr(casted_path, k2.replace("*", ""))(v2)
                            )
                elif isinstance(v, dict) and len(v.items()) == 1:
                    k2 = list(v.keys())[0]
                    v2 = v[k2]
                    if isinstance(v2, dict) and "*datetime" in v2:
                        v2 = parse_and_coerce_to_utc_datetime(v2["*datetime"])  # type: ignore
                    if isinstance(v2, dict) and "*datetime_naive" in v2:
                        v2 = parse_datetime(v2["*datetime_naive"])  # type: ignore
                    if (
                        isinstance(k2, str)
                        and not isinstance(v2, dict)
                        and k2[0] == "*"
                    ):
                        if k2 == "*eq":
                            level_criteria.append(model_attribute == v2)
                        elif k2 == "*neq":
                            level_criteria.append(model_attribute != v2)
                        elif k2 == "*gt":
                            level_criteria.append(model_attribute > v2)
                        elif k2 == "*lt":
                            level_criteria.append(model_attribute < v2)
                        elif k2 == "*gte":
                            level_criteria.append(model_attribute >= v2)
                        elif k2 == "*lte":
                            level_criteria.append(model_attribute <= v2)
                        elif k2 == "*websearch_to_tsquery" and is_colon:
                            level_criteria.append(
                                model_attribute.op("@@")(
                                    func.websearch_to_tsquery(
                                        v2, postgresql_regconfig="english"
                                    )
                                )
                            )
                        elif hasattr(model_attribute, k2.replace("*", "")):
                            # Probably need to add an "accepted" list of query action keys
                            level_criteria.append(
                                getattr(model_attribute, k2.replace("*", ""))(v2)
                            )

        return level_criteria
