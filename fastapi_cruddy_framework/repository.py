import math
from dateutil.parser import parse
from dateutil.tz import UTC
from asyncio import gather
from logging import getLogger
from sqlalchemy import (
    update as _update,
    delete as _delete,
    or_,
    and_,
    not_,
    func,
    column,
)
from sqlalchemy.engine import Result
from sqlalchemy.sql import select, update
from sqlalchemy.sql.schema import Table, Column
from sqlalchemy.orm import RelationshipProperty, ONETOMANY, MANYTOMANY
from sqlmodel import inspect
from typing import Union, List, Dict
from pydantic.types import Json
from .schemas import (
    BulkDTO,
    CruddyModel,
)
from .adapters import BaseAdapter, SqliteAdapter, MysqlAdapter, PostgresqlAdapter
from .util import get_pk, possible_id_types, lifecycle_types


def exists(something):
    return something != None


LOGGER = getLogger(__file__)


# -------------------------------------------------------------------------------------------
# REPOSITORY MANAGER
# -------------------------------------------------------------------------------------------
class AbstractRepository:
    adapter: Union[BaseAdapter, SqliteAdapter, MysqlAdapter, PostgresqlAdapter]
    update_model: CruddyModel
    create_model: CruddyModel
    model: CruddyModel
    id_type: possible_id_types
    primary_key: str = None
    lifecycle: Dict[str, lifecycle_types] = {
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

    op_map: Dict

    def __init__(
        self,
        adapter: Union[
            BaseAdapter, SqliteAdapter, MysqlAdapter, PostgresqlAdapter
        ] = ...,
        update_model: CruddyModel = ...,
        create_model: CruddyModel = ...,
        model: CruddyModel = ...,
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
            record = self.model(**data.dict())
            if exists(self.lifecycle["before_create"]):
                await self.lifecycle["before_create"](record)
            session.add(record)
        if exists(self.lifecycle["after_create"]):
            await self.lifecycle["after_create"](record)
        return record
        # return a value?

    async def get_by_id(self, id: possible_id_types):
        # retrieve user data by id
        query = select(self.model).where(getattr(self.model, self.primary_key) == id)
        async with self.adapter.getSession() as session:
            if exists(self.lifecycle["before_get_one"]):
                await self.lifecycle["before_get_one"](id)
            result = (await session.execute(query)).scalar_one_or_none()
        if exists(self.lifecycle["after_get_one"]):
            await self.lifecycle["after_get_one"](result)
        return result

    async def update(self, id: possible_id_types, data: CruddyModel):
        # update user data
        values = data.dict()
        if exists(self.lifecycle["before_update"]):
            await self.lifecycle["before_update"](values, id)
        query = (
            _update(self.model)
            .where(getattr(self.model, self.primary_key) == id)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        async with self.adapter.getSession() as session:
            result = await session.execute(query)
        if result.rowcount == 1:
            updated_record = await self.get_by_id(id=id)
            if exists(self.lifecycle["after_update"]):
                await self.lifecycle["after_update"](updated_record)
            return updated_record
        return None
        # return a value?

    async def delete(self, id: possible_id_types):
        # delete user data by id
        record = await self.get_by_id(id=id)
        if exists(self.lifecycle["before_delete"]):
            await self.lifecycle["before_delete"](record)
        query = (
            _delete(self.model)
            .where(getattr(self.model, self.primary_key) == id)
            .execution_options(synchronize_session="fetch")
        )
        async with self.adapter.getSession() as session:
            result = await session.execute(query)

        if result.rowcount == 1:
            if exists(self.lifecycle["after_delete"]):
                await self.lifecycle["after_delete"](record)
            return record
        return None
        # return a value?

    async def get_all(
        self,
        page: int = 1,
        limit: int = 10,
        columns: List[str] = None,
        sort: List[str] = None,
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

        if exists(lifecycle_before):
            # apps can alter user queries in this hook!!
            # use this hook to force things to be in a range, like limits!
            # setting conf.limit = 20 in user app code would alter the limit for
            # this query
            await lifecycle_before(query_conf)

        select_columns = (
            list(map(lambda x: column(x), query_conf["columns"]))
            if query_conf["columns"] is not None and query_conf["columns"] != []
            else "*"
        )
        query = select(from_obj=self.model, columns=select_columns)

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

            sorts = list(map(splitter, query_conf["sort"]))
            for field in sorts:
                query = query.order_by(field())

        # count query
        count_query = select(func.count(1)).select_from(query)
        offset_page = query_conf["page"] - 1
        # pagination
        query = query.offset(offset_page * query_conf["limit"]).limit(
            query_conf["limit"]
        )
        # total record

        async with self.adapter.getSession() as session:
            results = await gather(
                *[session.execute(count_query), session.execute(query)],
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

        if exists(lifecycle_after):
            await lifecycle_after(result)

        return result

    async def get_all_relations(
        self,
        id: possible_id_types = ...,
        relation: str = ...,
        relation_model: CruddyModel = ...,
        page: int = 1,
        limit: int = 10,
        columns: List[str] = None,
        sort: List[str] = None,
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

        if exists(_lifecycle_before):
            await _lifecycle_before(query_conf)

        if query_conf["columns"] is None or len(query_conf["columns"]) == 0:
            select_columns = list(
                map(
                    lambda x: getattr(relation_model, x),
                    relation_model.__fields__.keys(),
                )
            )
        else:
            if relation_pk not in query_conf["columns"]:
                query_conf["columns"].append(relation_pk)
            select_columns = list(
                map(lambda x: getattr(relation_model, x), query_conf["columns"])
            )

        query = select(from_obj=self.model, columns=select_columns)

        query = query.join(getattr(self.model, relation))

        joinable = [getattr(self.model, self.primary_key) == id]

        if isinstance(query_conf["where"], dict) or isinstance(
            query_conf["where"], list
        ):
            joinable.append(
                *self.query_forge(model=relation_model, where=query_conf["where"])
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

            sorts = list(map(splitter, query_conf["sort"]))
            for field in sorts:
                query = query.order_by(field())

        # count query
        count_query = select(func.count(1)).select_from(query)
        offset_page = query_conf["page"] - 1
        # pagination
        query = query.offset(offset_page * query_conf["limit"]).limit(
            query_conf["limit"]
        )
        # total record

        async with self.adapter.getSession() as session:
            results = await gather(
                *[session.execute(count_query), session.execute(query)],
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

        if exists(_lifecycle_after):
            await _lifecycle_after(result)

        return result

    # This one is rather "alchemy" because join tables aren't resources
    async def set_many_many_relations(
        self,
        id: possible_id_types,
        relation: str = ...,
        relations: List[possible_id_types] = ...,
    ):
        relation_conf = {"id": id, "relation": relation, "relations": relations}

        if exists(self.lifecycle["before_set_relations"]):
            await self.lifecycle["before_set_relations"](relation_conf)

        model_relation: RelationshipProperty = getattr(
            inspect(self.model).relationships, relation_conf["relation"]
        )
        pairs = list(model_relation.local_remote_pairs)
        # origin_table: Table = None
        # origin_key: str = None
        join_table: Table = None
        join_table_origin_attr: str = None
        join_table_foreign_attr: str = None
        join_table_foreign: Table = None
        foreign_table: Table = None
        foreign_key: str = None
        for v in pairs:
            local: Column = v[0]
            remote: Column = v[1]
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

        if join_table.name != join_table_foreign.name:
            raise TypeError("Relationship many to many tables are not the same type!")

        validation_target_col: Column = getattr(foreign_table.columns, foreign_key)
        # origin_id_col: Column = getattr(origin_table.columns, origin_key)
        join_origin_col: Column = getattr(join_table.columns, join_table_origin_attr)
        join_foreign_col: Column = getattr(join_table.columns, join_table_foreign_attr)
        # validate_origin_id = select(from_obj=origin_table, columns=[origin_id_col]).where(origin_id_col == id)
        validate_relation_ids = select(
            from_obj=foreign_table, columns=[validation_target_col]
        ).where(validation_target_col.in_(relation_conf["relations"]))
        clear_relations_query = (
            join_table.delete()
            .where(join_origin_col == relation_conf["id"])
            .execution_options(synchronize_session="fetch")
        )

        async with self.adapter.getSession() as session:
            # origin_id = (await session.execute(validate_origin_id)).scalar_one_or_none()
            db_ids = (await session.execute(validate_relation_ids)).fetchall()
            insertable = list(
                map(
                    lambda x: {
                        join_table_origin_attr: relation_conf["id"],
                        join_table_foreign_attr: f"{x._mapping[foreign_key]}",
                    },
                    db_ids,
                )
            )
            create_relations_query = join_table.insert().values(
                insertable
            )  # .returning(join_foreign_col) # RETURNING DOESNT WORK ON ALL ADAPTERS
            await session.execute(clear_relations_query)

            check_ids = list(map(lambda x: f"{x._mapping[foreign_key]}", db_ids))
            if len(insertable) > 0:
                await session.execute(create_relations_query)
                find_tgt_query = select(join_table).where(
                    and_(
                        join_origin_col == relation_conf["id"],
                        join_foreign_col.in_(check_ids),
                    )
                )
                count_query = select(func.count(1)).select_from(find_tgt_query)
                result = (await session.execute(count_query)).scalar() or 0
            else:
                result = 0

        if exists(self.lifecycle["after_set_relations"]):
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
        id: possible_id_types,
        relation: str = ...,
        relations: List[possible_id_types] = ...,
    ):
        relation_conf = {"id": id, "relation": relation, "relations": relations}

        if exists(self.lifecycle["before_set_relations"]):
            await self.lifecycle["before_set_relations"](relation_conf)

        model_relation: RelationshipProperty = getattr(
            inspect(self.model).relationships, relation_conf["relation"]
        )
        pairs = list(model_relation.local_remote_pairs)
        found = False
        for v in pairs:
            local: Column = v[0]
            remote: Column = v[1]
            if local.table.name == self.model.__tablename__:
                related_model: Table = remote.table
                far_col_name: str = remote.key
                far_col = remote
                found = True
                # origin_table = local.table
                # origin_key = local.key
                # This is the link from our origin model to the join table
        if not found:
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
        count_query = select(func.count(1)).select_from(find_tgt_query)
        async with self.adapter.getSession() as session:
            if far_col.nullable:
                await session.execute(clear_query)
            else:
                LOGGER.warn(
                    f"Unable to clear relations for {related_model.name}.{far_col_name}. Column does not allow null values"
                )

            await session.execute(
                alter_query
            )  # .rowcount # also affected by removing returning
            alter_result = (await session.execute(count_query)).scalar() or 0

        if exists(self.lifecycle["after_set_relations"]):
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
    # This function needs to be extended to support "dot" notation in left hand keys to imply joined relation searchers
    def query_forge(
        self,
        model: Union[CruddyModel, RelationshipProperty],
        where: Union[Dict, List[Dict]],
    ):
        level_criteria = []
        if not (isinstance(where, list) or isinstance(where, dict)):
            return []
        if isinstance(where, list):
            list_of_lists = list(
                map(lambda x: self.query_forge(model=model, where=x), where)
            )
            for l in list_of_lists:
                level_criteria += l
            return level_criteria
        for k, v in where.items():
            isOp = False
            if k in self.op_map:
                isOp = self.op_map[k]
            if isinstance(v, dict) and isOp != False:
                level_criteria.append(isOp(*self.query_forge(model=model, where=v)))
            elif isinstance(v, list) and isOp != False:
                level_criteria.append(isOp(*self.query_forge(model=model, where=v)))
            elif not isinstance(v, dict) and not isOp and hasattr(model, k):
                level_criteria.append(getattr(model, k).like(v))
            elif (
                isinstance(v, dict)
                and not isOp
                and hasattr(model, k)
                and len(v.items()) == 1
            ):
                k2 = list(v.keys())[0]
                v2 = v[k2]
                mattr = getattr(model, k)
                if isinstance(v2, dict) and "*datetime" in v2:
                    v2 = parse(v2["*datetime"], tzinfos=[UTC])
                if isinstance(k2, str) and not isinstance(v2, dict) and k2[0] == "*":
                    if k2 == "*eq":
                        level_criteria.append(mattr == v2)
                    elif k2 == "*neq":
                        level_criteria.append(mattr != v2)
                    elif k2 == "*gt":
                        level_criteria.append(mattr > v2)
                    elif k2 == "*lt":
                        level_criteria.append(mattr < v2)
                    elif k2 == "*gte":
                        level_criteria.append(mattr >= v2)
                    elif k2 == "*lte":
                        level_criteria.append(mattr <= v2)
                    elif hasattr(mattr, k2.replace("*", "")):
                        # Probably need to add an "accepted" list of query action keys
                        level_criteria.append(getattr(mattr, k2.replace("*", ""))(v2))
        return level_criteria
