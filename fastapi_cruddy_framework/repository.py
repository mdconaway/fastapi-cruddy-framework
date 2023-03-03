import math
from sqlalchemy import (
    update as _update,
    delete as _delete,
    or_,
    and_,
    not_,
    func,
    column,
)
from sqlalchemy.sql import select, update
from sqlalchemy.sql.schema import Table, Column
from sqlalchemy.orm import RelationshipProperty
from sqlmodel import inspect
from typing import Union, List, Dict
from pydantic.types import Json
from .uuid import UUID
from .schemas import (
    RelationshipConfig,
    BulkDTO,
    CruddyModel,
)
from .adapters import BaseAdapter, SqliteAdapter, MysqlAdapter, PostgresqlAdapter


# -------------------------------------------------------------------------------------------
# REPOSITORY MANAGER
# -------------------------------------------------------------------------------------------
class AbstractRepository:
    adapter: Union[BaseAdapter, SqliteAdapter, MysqlAdapter, PostgresqlAdapter]
    update_model: CruddyModel
    create_model: CruddyModel
    model: CruddyModel
    id_type: Union[UUID, int]
    op_map: Dict

    def __init__(
        self,
        adapter: Union[
            BaseAdapter, SqliteAdapter, MysqlAdapter, PostgresqlAdapter
        ] = ...,
        update_model: CruddyModel = ...,
        create_model: CruddyModel = ...,
        model: CruddyModel = ...,
        id_type: Union[UUID, int] = int,
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

    async def create(self, data: CruddyModel) -> CruddyModel:
        # create user data
        async with self.adapter.getSession() as session:
            record = self.model(**data.dict())
            session.add(record)
        return record
        # return a value?

    async def get_by_id(self, id: Union[UUID, int]):
        # retrieve user data by id
        query = select(self.model).where(self.model.id == id)
        async with self.adapter.getSession() as session:
            result = (await session.execute(query)).scalar_one_or_none()
        return result

    async def update(self, id: Union[UUID, int], data: CruddyModel):
        # update user data
        query = (
            _update(self.model)
            .where(self.model.id == id)
            .values(**data.dict())
            .execution_options(synchronize_session="fetch")
        )
        async with self.adapter.getSession() as session:
            result = await session.execute(query)

        if result.rowcount == 1:
            return await self.get_by_id(id=id)

        return None
        # return a value?

    async def delete(self, id: Union[UUID, int]):
        # delete user data by id
        record = await self.get_by_id(id=id)
        query = (
            _delete(self.model)
            .where(self.model.id == id)
            .execution_options(synchronize_session="fetch")
        )
        async with self.adapter.getSession() as session:
            result = await session.execute(query)

        if result.rowcount == 1:
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
    ) -> BulkDTO:
        select_columns = (
            list(map(lambda x: column(x), columns))
            if columns is not None and columns != []
            else "*"
        )
        query = select(from_obj=self.model, columns=select_columns)

        if isinstance(where, dict) or isinstance(where, list):
            query = query.filter(and_(*self.query_forge(model=self.model, where=where)))

        # select sort dynamically
        if sort is not None and sort != []:
            # we need sort format data like this --> ['id asc','name desc', 'email']
            def splitter(sort_string: str):
                parts = sort_string.split(" ")
                getter = "asc"
                if len(parts) == 2:
                    getter = parts[1]
                return getattr(getattr(self.model, parts[0]), getter)

            sorts = list(map(splitter, sort))
            for field in sorts:
                query = query.order_by(field())

        # count query
        count_query = select(func.count(1)).select_from(query)
        offset_page = page - 1
        # pagination
        query = query.offset(offset_page * limit).limit(limit)
        # total record

        async with self.adapter.getSession() as session:
            total_record = (await session.execute(count_query)).scalar() or 0
            # result
            result = (await session.execute(query)).fetchall()

        # possible pass in outside functions to map/alter data?
        # total page
        total_page = math.ceil(total_record / limit)
        return BulkDTO(total_pages=total_page, total_records=total_record, data=result)

    async def get_all_relations(
        self,
        id: Union[UUID, int] = ...,
        relation: str = ...,
        relation_model: CruddyModel = ...,
        page: int = 1,
        limit: int = 10,
        columns: List[str] = None,
        sort: List[str] = None,
        where: Json = None,
    ) -> BulkDTO:
        # The related id column is mandatory or the join will explode
        if columns is None or len(columns) == 0:
            select_columns = list(
                map(
                    lambda x: getattr(relation_model, x),
                    relation_model.__fields__.keys(),
                )
            )
        else:
            # Add logic for non "id" primary key??
            if "id" not in columns:
                columns.append("id")
            select_columns = list(map(lambda x: getattr(relation_model, x), columns))

        query = select(from_obj=self.model, columns=select_columns)

        query = query.join(getattr(self.model, relation))

        # Add logic for non "id" primary key??
        joinable = [self.model.id == id]

        if isinstance(where, dict) or isinstance(where, list):
            joinable.append(*self.query_forge(model=relation_model, where=where))
        query = query.filter(and_(*joinable))

        # select sort dynamically
        if sort is not None and sort != []:
            # we need sort format data like this --> ['id asc','name desc', 'email']
            def splitter(sort_string: str):
                parts = sort_string.split(" ")
                getter = "asc"
                if len(parts) == 2:
                    getter = parts[1]
                return getattr(getattr(relation_model, parts[0]), getter)

            sorts = list(map(splitter, sort))
            for field in sorts:
                query = query.order_by(field())

        # count query
        count_query = select(func.count(1)).select_from(query)
        offset_page = page - 1
        # pagination
        query = query.offset(offset_page * limit).limit(limit)
        # total record

        async with self.adapter.getSession() as session:
            total_record = (await session.execute(count_query)).scalar() or 0
            # result
            result = (await session.execute(query)).fetchall()

        # possible pass in outside functions to map/alter data?
        # total page
        total_page = math.ceil(total_record / limit)
        return BulkDTO(total_pages=total_page, total_records=total_record, data=result)

    # This one is rather "alchemy" because join tables aren't resources
    async def set_many_many_relations(
        self,
        id: Union[UUID, int],
        relation: str = ...,
        relations: List[Union[UUID, int]] = ...,
    ):
        model_relation: RelationshipProperty = getattr(
            inspect(self.model).relationships, relation
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
        ).where(validation_target_col.in_(relations))
        clear_relations_query = (
            join_table.delete()
            .where(join_origin_col == id)
            .execution_options(synchronize_session="fetch")
        )

        async with self.adapter.getSession() as session:
            # origin_id = (await session.execute(validate_origin_id)).scalar_one_or_none()
            db_ids = (await session.execute(validate_relation_ids)).fetchall()
            insertable = list(
                map(
                    lambda x: {
                        join_table_origin_attr: id,
                        join_table_foreign_attr: f"{x._mapping[foreign_key]}",
                    },
                    db_ids,
                )
            )
            create_relations_query = (
                join_table.insert().values(insertable).returning(join_foreign_col)
            )
            await session.execute(clear_relations_query)
            if len(insertable) > 0:
                result = (await session.execute(create_relations_query)).rowcount
            else:
                result = 0

        return result

    # There should probably be a configuration flag to disable this form of unsafe relationship update
    async def set_one_many_relations(
        self,
        id: Union[UUID, int],
        relation: str = ...,
        relations: List[Union[UUID, int]] = ...,
    ):
        model_relation: RelationshipProperty = getattr(
            inspect(self.model).relationships, relation
        )
        related_model = model_relation.foreign_resource.repository.model
        related_model_id: Column = getattr(related_model, "id")
        far_col: Column = next(iter(model_relation.orm_relationship.remote_side))
        far_col_name = far_col.name

        clear_query = (
            update(table=related_model)
            .values({far_col_name: None})
            .where(far_col.in_([id]))
        )
        alter_query = (
            update(table=related_model)
            .values({far_col_name: id})
            .where(related_model_id.in_(relations))
            .returning(related_model_id)
        )

        async with self.adapter.getSession() as session:
            if far_col.nullable:
                await session.execute(clear_query)
            else:
                print(
                    f"Unable to clear relations for {related_model.__name__}.{far_col_name}. Column does not allow null values"
                )
            alter_result = (await session.execute(alter_query)).rowcount

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
