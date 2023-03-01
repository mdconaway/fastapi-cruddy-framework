# This is a candidate to become a library. You're welcome Python community.
# Love,
# A Sails / Ember lover.

import asyncio
import math
import os
import sys
import glob
import importlib.util
import inflect
from os import path
from fastapi import APIRouter, Path, Query, Depends
from sqlalchemy import (
    update as _update,
    delete as _delete,
    or_,
    and_,
    not_,
    text,
    func,
    column,
)
from sqlalchemy.sql import select, update
from sqlalchemy.sql.schema import Table, Column, ForeignKey
from sqlalchemy.orm import (
    sessionmaker,
    declared_attr,
    RelationshipProperty,
    # selectinload,
    ONETOMANY,
    MANYTOMANY,
    MANYTOONE,
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from contextlib import asynccontextmanager
from sqlmodel import text, inspect
from sqlmodel.ext.asyncio.session import AsyncSession
from types import ModuleType
from typing import Union, TypeVar, Optional, Generic, List, Dict, Callable  # , Any
from pydantic import create_model
from pydantic.generics import GenericModel
from pydantic.types import Json
from sqlmodel import Field, SQLModel
from datetime import datetime
from .uuid import UUID, uuid7
# Look into this for making generic factories??
# https://shanenullain.medium.com/abstract-factory-in-python-with-generic-typing-b9ceca2bf89e

pluralizer = inflect.engine()

# -------------------------------------------------------------------------------------------
# END DATABASE UUID CLASSES
# -------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------
# SCHEMAS / MODELS
# -------------------------------------------------------------------------------------------
T = TypeVar("T")


class RelationshipConfig:
    orm_relationship: RelationshipProperty = None
    foreign_resource: "Resource" = None

    def __init__(self, orm_relationship=None, foreign_resource=None):
        self.orm_relationship = orm_relationship
        self.foreign_resource = foreign_resource


class CruddyGenericModel(GenericModel, Generic[T]):
    def __init__(self, *args, **kwargs):
        return super().__init__(*args, **kwargs)


class BulkDTO(CruddyGenericModel):
    total_pages: int
    total_records: int
    data: List


class MetaObject(CruddyGenericModel):
    page: int
    limit: int
    pages: int
    records: int


class PageResponse(CruddyGenericModel):
    # The response for a pagination query.
    meta: MetaObject
    data: List[T]


class ResponseSchema(SQLModel):
    # The response for a single object return
    data: Optional[T] = None


class CruddyModel(SQLModel):
    @declared_attr  # type: ignore
    def __tablename__(cls) -> str:
        return cls.__name__


class CruddyIntIDModel(CruddyModel):
    id: Optional[int] = Field(
        default=None,
        primary_key=True,
        index=True,
        nullable=False,
    )
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow}
    )
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class CruddyUUIDModel(CruddyModel):
    id: UUID = Field(
        default_factory=uuid7,
        primary_key=True,
        index=True,
        nullable=False,
    )
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow}
    )
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class ExampleUpdate(CruddyModel):
    updateable_field: str


class ExampleCreate(ExampleUpdate):
    create_only_field: str


class ExampleView(CruddyIntIDModel, ExampleCreate):
    pass


class Example(ExampleView, table=False):  # Set table=True on your app's core models
    db_only_field: str


# -------------------------------------------------------------------------------------------
# END SCHEMAS / MODELS
# -------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------
# CONTROLLER / ROUTER
# -------------------------------------------------------------------------------------------
def assemblePolicies(*args: (List)):
    merged = []
    for policy_set in args:
        for individual_policy in policy_set:
            merged.append(Depends(individual_policy))
    return merged


def _ControllerConfigManyToOne(
    controller: APIRouter = ...,
    repository: "AbstractRepository" = ...,
    id_type: Union[UUID, int] = ...,
    relationship_prop: str = ...,
    config: RelationshipConfig = ...,
    policies_universal: List = ...,
    policies_get_one: List = ...,
):
    col: Column = next(iter(config.orm_relationship.local_columns))
    far_side: ForeignKey = next(iter(col.foreign_keys))
    far_col: Column = far_side.column
    far_col_name = far_col.name
    near_col_name = col.name

    # Merge three policy sets onto this endpoint:
    # 1. Universal policies
    # 2. Primary resource policies
    # 3. Related resource policies
    @controller.get(
        f'/{"{id}"}/{relationship_prop}',
        response_model=config.foreign_resource.schemas["single"],
        response_model_exclude_none=True,
        dependencies=assemblePolicies(
            policies_universal,
            policies_get_one,
            config.foreign_resource.policies["get_one"],
        ),
    )
    async def get_many_to_one(
        id: id_type = Path(..., alias="id"),
        columns: List[str] = Query(None, alias="columns"),
    ):
        origin_record = await repository.get_by_id(id=id)

        # Consider raising 404 here and in get by ID
        if origin_record == None:
            return config.foreign_resource.schemas["single"](data=None)

        # Build a query to use foreign resource to find related objects
        where = {far_col_name: {"*eq": origin_record.dict()[near_col_name]}}

        # Collect the bulk data transfer object from the query
        result: BulkDTO = await config.foreign_resource.repository.get_all(
            page=1, limit=1, columns=columns, sort=None, where=where
        )

        # If we get a result, grab the first value. There should only be one in many to one.
        data = None
        if len(result.data) != 0:
            data = result.data[0]

        # Invoke the dynamically built model
        return config.foreign_resource.schemas["single"](data=data)


def _ControllerConfigOneToMany(
    controller: APIRouter = ...,
    repository: "AbstractRepository" = ...,
    id_type: Union[UUID, int] = ...,
    relationship_prop: str = ...,
    config: RelationshipConfig = ...,
    meta_schema=MetaObject,
    policies_universal: List = ...,
    policies_get_one: List = ...,
):
    far_col: Column = next(iter(config.orm_relationship.remote_side))
    col: Column = next(iter(config.orm_relationship.local_columns))
    far_col_name = far_col.name
    near_col_name = col.name

    # Merge three policy sets onto this endpoint:
    # 1. Universal policies
    # 2. Primary resource policies
    # 3. Related resource policies
    @controller.get(
        f'/{"{id}"}/{relationship_prop}',
        response_model=config.foreign_resource.schemas["many"],
        response_model_exclude_none=True,
        dependencies=assemblePolicies(
            policies_universal,
            policies_get_one,
            config.foreign_resource.policies["get_many"],
        ),
    )
    async def get_one_to_many(
        id: id_type = Path(..., alias="id"),
        page: int = 1,
        limit: int = 10,
        columns: List[str] = Query(None, alias="columns"),
        sort: List[str] = Query(None, alias="sort"),
        where: Json = Query(None, alias="where"),
    ):
        origin_record = await repository.get_by_id(id=id)

        # Consider raising 404 here and in get by ID
        if origin_record == None:
            return config.foreign_resource.schemas["many"](
                data=None,
                meta=meta_schema(**{"page": 0, "limit": 0, "pages": 0, "records": 0}),
            )

        # Build a query to use foreign resource to find related objects
        additional_where = {far_col_name: {"*eq": origin_record.dict()[near_col_name]}}
        if where != None:
            where = {"*and": [additional_where, where]}
        else:
            where = additional_where

        # Collect the bulk data transfer object from the query
        result: BulkDTO = await config.foreign_resource.repository.get_all(
            page=page, limit=limit, columns=columns, sort=sort, where=where
        )
        meta = {
            "page": page,
            "limit": limit,
            "pages": result.total_pages,
            "records": result.total_records,
        }
        return config.foreign_resource.schemas["many"](
            meta=meta_schema(**meta),
            data=result.data,
        )


def _ControllerConfigManyToMany(
    controller: APIRouter = ...,
    repository: "AbstractRepository" = ...,
    id_type: Union[UUID, int] = ...,
    relationship_prop: str = ...,
    config: RelationshipConfig = ...,
    meta_schema=MetaObject,
    policies_universal: List = ...,
    policies_get_one: List = ...,
):
    far_model: CruddyModel = config.foreign_resource.repository.model

    # Merge three policy sets onto this endpoint:
    # 1. Universal policies
    # 2. Primary resource policies
    # 3. Related resource policies
    @controller.get(
        f'/{"{id}"}/{relationship_prop}',
        response_model=config.foreign_resource.schemas["many"],
        response_model_exclude_none=True,
        dependencies=assemblePolicies(
            policies_universal,
            policies_get_one,
            config.foreign_resource.policies["get_many"],
        ),
    )
    async def get_many_to_many(
        id: id_type = Path(..., alias="id"),
        page: int = 1,
        limit: int = 10,
        columns: List[str] = Query(None, alias="columns"),
        sort: List[str] = Query(None, alias="sort"),
        where: Json = Query(None, alias="where"),
    ):
        # Collect the bulk data transfer object from the query
        result: BulkDTO = await repository.get_all_relations(
            id=id,
            relation=relationship_prop,
            relation_model=far_model,
            page=page,
            limit=limit,
            columns=columns,
            sort=sort,
            where=where,
        )
        meta = {
            "page": page,
            "limit": limit,
            "pages": result.total_pages,
            "records": result.total_records,
        }
        return config.foreign_resource.schemas["many"](
            meta=meta_schema(**meta),
            data=result.data,
        )


def GetRelationships(
    record: CruddyModel, relation_config_map: Dict[str, RelationshipConfig]
):
    record_relations = {}
    for k, v in relation_config_map.items():
        direction = v.orm_relationship.direction
        if (
            (direction == MANYTOMANY or direction == ONETOMANY)
            and hasattr(record, k)
            and getattr(record, k) != None
        ):
            record_relations[k] = getattr(record, k)
    return record_relations


async def SaveRelationships(
    id: Union[UUID, int] = ...,
    record: CruddyModel = ...,
    relation_config_map: Dict[str, RelationshipConfig] = ...,
    repository: "AbstractRepository" = ...,
):
    relationship_lists = GetRelationships(record, relation_config_map)
    modified_records = 0
    for k, v in relationship_lists.items():
        name: str = k
        new_relations: List[Union[UUID, int]] = v
        config: RelationshipConfig = relation_config_map[name]
        if config.orm_relationship.direction == MANYTOMANY:
            modified_records += await repository.set_many_many_relations(
                id=id, relation=name, relations=new_relations
            )
        elif config.orm_relationship.direction == ONETOMANY:
            modified_records += await repository.set_one_many_relations(
                id=id, relation=config, relations=new_relations
            )
    return modified_records


def ControllerCongifurator(
    controller: APIRouter = ...,
    repository: "AbstractRepository" = ...,
    id_type: Union[UUID, int] = int,
    single_name: str = ...,
    plural_name: str = ...,
    single_schema=ResponseSchema,
    many_schema=PageResponse,
    meta_schema=MetaObject,
    update_model=ExampleUpdate,
    update_model_proxy=ExampleUpdate,
    create_model=ExampleCreate,
    create_model_proxy=ExampleCreate,
    relations: Dict[str, RelationshipConfig] = ...,
    policies_universal=[],
    policies_create=[],
    policies_update=[],
    policies_delete=[],
    policies_get_one=[],
    policies_get_many=[],
) -> APIRouter:
    @controller.post(
        "",
        response_model=single_schema,
        response_model_exclude_none=True,
        dependencies=assemblePolicies(policies_universal, policies_create),
    )
    async def create(data: create_model):
        the_thing_with_rels = getattr(data, single_name)
        the_thing = create_model_proxy(**the_thing_with_rels.dict())
        result = await repository.create(data=the_thing)
        relations_modified = await SaveRelationships(
            id=result.id,
            record=the_thing_with_rels,
            relation_config_map=relations,
            repository=repository,
        )
        # print(f"modified {relations_modified} relationships")
        # Add error logic?
        return single_schema(data=result)

    @controller.patch(
        "/{id}",
        response_model=single_schema,
        response_model_exclude_none=True,
        dependencies=assemblePolicies(policies_universal, policies_update),
    )
    async def update(id: id_type = Path(..., alias="id"), *, data: update_model):
        the_thing_with_rels = getattr(data, single_name)
        the_thing = update_model_proxy(**the_thing_with_rels.dict())
        result = await repository.update(id=id, data=the_thing)
        relations_modified = await SaveRelationships(
            id=result.id,
            record=the_thing_with_rels,
            relation_config_map=relations,
            repository=repository,
        )
        # print(f"modified {relations_modified} relationships")
        # Add error logic?
        return single_schema(data=result)

    @controller.delete(
        "/{id}",
        response_model=single_schema,
        response_model_exclude_none=True,
        dependencies=assemblePolicies(policies_universal, policies_delete),
    )
    async def delete(
        id: id_type = Path(..., alias="id"),
    ):
        data = await repository.delete(id=id)
        # Add error logic?
        return single_schema(data=data)

    @controller.get(
        "/{id}",
        response_model=single_schema,
        response_model_exclude_none=True,
        dependencies=assemblePolicies(policies_universal, policies_get_one),
    )
    async def get_by_id(id: id_type = Path(..., alias="id")):
        data = await repository.get_by_id(id=id)
        return single_schema(data=data)

    @controller.get(
        "",
        response_model=many_schema,
        response_model_exclude_none=True,
        dependencies=assemblePolicies(policies_universal, policies_get_many),
    )
    async def get_all(
        page: int = 1,
        limit: int = 10,
        columns: List[str] = Query(None, alias="columns"),
        sort: List[str] = Query(None, alias="sort"),
        where: Json = Query(None, alias="where"),
    ):
        result: BulkDTO = await repository.get_all(
            page=page, limit=limit, columns=columns, sort=sort, where=where
        )
        meta = {
            "page": page,
            "limit": limit,
            "pages": result.total_pages,
            "records": result.total_records,
        }
        return many_schema(
            meta=meta_schema(**meta),
            data=result.data,
        )

    # Add relationship link endpoints starting here...

    for key, config in relations.items():
        if config.orm_relationship.direction == ONETOMANY:
            _ControllerConfigOneToMany(
                controller=controller,
                repository=repository,
                id_type=id_type,
                relationship_prop=key,
                config=config,
                meta_schema=meta_schema,
                policies_universal=policies_universal,
                policies_get_one=policies_get_one,
            )
        elif config.orm_relationship.direction == MANYTOMANY:
            _ControllerConfigManyToMany(
                controller=controller,
                repository=repository,
                id_type=id_type,
                relationship_prop=key,
                config=config,
                meta_schema=meta_schema,
                policies_universal=policies_universal,
                policies_get_one=policies_get_one,
            )
            # print("To Implement: Many to Many Through Association Object")
        elif config.orm_relationship.direction == MANYTOONE:
            _ControllerConfigManyToOne(
                controller=controller,
                repository=repository,
                id_type=id_type,
                relationship_prop=key,
                config=config,
                policies_universal=policies_universal,
                policies_get_one=policies_get_one,
            )

    return controller


# -------------------------------------------------------------------------------------------
# END CONTROLLER / ROUTER
# -------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------
# REPOSITORY MANAGER
# -------------------------------------------------------------------------------------------
class AbstractRepository:
    adapter: "PostgresqlAdapter"
    update_model: CruddyModel
    create_model: CruddyModel
    model: CruddyModel
    id_type: Union[UUID, int]
    op_map: Dict

    def __init__(
        self,
        adapter: "PostgresqlAdapter" = ...,
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

    async def create(self, data: CruddyModel):
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
    ):
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
    ):
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
        relation: RelationshipConfig = ...,
        relations: List[Union[UUID, int]] = ...,
    ):
        related_model = relation.foreign_resource.repository.model
        related_model_id: Column = getattr(related_model, "id")
        far_col: Column = next(iter(relation.orm_relationship.remote_side))
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


# -------------------------------------------------------------------------------------------
# END REPOSITORY MANAGER
# -------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------
# POSTGRESQL ADAPTER
# -------------------------------------------------------------------------------------------
# The default adapter for CruddyResource
class PostgresqlAdapter:
    engine: Union[AsyncEngine, None] = None

    def __init__(self, connection_uri="", pool_size=4, max_overflow=64):
        self.engine = create_async_engine(
            connection_uri,
            echo=True,
            future=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )

    # Since this returns an async generator, to use it elsewhere, it
    # should be invoked using the following syntax.
    #
    # async with postgresql.getSession() as session:
    #
    # which will iterate through the generator context and yield the
    # product into a local variable named session.
    # Coding this method in this way also means classes interacting
    # with the adapter dont have to handle commiting thier
    # transactions, or rolling them back. It will happen here after
    # the yielded context cedes control of the event loop back to
    # the adapter. If the database explodes, the rollback happens.

    def asyncSessionGenerator(self):
        return sessionmaker(
            autocommit=False,
            autoflush=False,
            future=True,
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def getSession(self):
        try:
            asyncSession = self.asyncSessionGenerator()
            async with asyncSession() as session:
                yield session
                await session.commit()
        except:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def addPostgresqlExtension(self) -> None:
        query = text("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        async with self.getSession() as session:
            await session.execute(query)


# -------------------------------------------------------------------------------------------
# END POSTGRESQL ADAPTER
# -------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------
# APPLICATION RESOURCE
# -------------------------------------------------------------------------------------------
# Next step: Allow overrides for response format and controller configurator?


class Resource:
    _registry: "ResourceRegistry" = None
    _link_prefix: str = ""
    _relations: Dict[str, RelationshipConfig] = {}
    _resource_path: str = "/example"
    _tags: List[str] = ["example"]
    _create_schema: CruddyModel = None
    _update_schema: CruddyModel = None
    _response_schema: CruddyModel = None
    _meta_schema: CruddyGenericModel = None
    _id_type: Union[UUID, int] = int
    _model_name_single: str = None
    _model_name_plural: str = None
    _on_resolution: Union[Callable, None] = None
    adapter: PostgresqlAdapter = None
    repository: AbstractRepository = None
    controller: APIRouter = None
    policies: Dict[str, List[Callable]] = None
    schemas: Dict[str, GenericModel] = None

    def __init__(
        self,
        adapter=None,
        connection_uri="",
        pool_size=4,
        max_overflow=64,
        link_prefix="",
        path: str = None,
        tags: List[str] = None,
        response_schema=ExampleView,
        response_meta_schema=MetaObject,
        resource_update_model=ExampleUpdate,
        resource_create_model=ExampleCreate,
        resource_model: CruddyModel = Example,
        protected_relationships: List[str] = [],
        id_type=int,
        policies_universal: List[Callable] = [],
        policies_create: List[Callable] = [],
        policies_update: List[Callable] = [],
        policies_delete: List[Callable] = [],
        policies_get_one: List[Callable] = [],
        policies_get_many: List[Callable] = [],
    ):
        possible_tag = f"{resource_model.__name__}".lower()
        possible_path = f"/{pluralizer.plural(possible_tag)}"
        self._on_resolution = None
        self._link_prefix = link_prefix
        self._resource_path = possible_path if path == None else path
        self._tags = [possible_tag] if tags == None else tags
        self._response_schema = response_schema
        self._update_schema = resource_update_model
        self._create_schema = resource_create_model
        self._meta_schema = response_meta_schema
        self._id_type = id_type
        self._relations = {}
        self._protected_relationships = protected_relationships

        self.policies = {
            "universal": policies_universal,
            "create": policies_create,
            "update": policies_update,
            "delete": policies_delete,
            "get_one": policies_get_one,
            "get_many": policies_get_many,
        }

        if None == adapter:
            self.adapter = PostgresqlAdapter(connection_uri, pool_size, max_overflow)
        else:
            self.adapter = adapter

        self.repository = AbstractRepository(
            adapter=self.adapter,
            update_model=resource_update_model,
            create_model=resource_create_model,
            model=resource_model,
            id_type=id_type,
        )

        self.controller = APIRouter(prefix=self._resource_path, tags=self._tags)

        self._registry.register(res=self)

    # This function will expand the controller to perform additional
    # actions like loading relationships, or inserting links?
    # Potential to hoist additional routes for relational sub-routes
    # on the CRUD controller? Does that require additional policies??
    def inject_relationship(
        self, relationship: RelationshipProperty, foreign_resource: "Resource"
    ):
        self._relations[f"{relationship.key}"] = RelationshipConfig(
            orm_relationship=relationship, foreign_resource=foreign_resource
        )

    def set_local_link_prefix(self, prefix: str):
        self._link_prefix = prefix

    # The response schema factory
    # Converting this section a plugin pattern will allow
    # other response formats, like JSON API.
    # Alterations will also require ControllerConfigurator
    # to be modified somehow...

    def generate_internal_schemas(self):
        local_resource = self
        response_schema = self._response_schema
        create_schema = self._create_schema
        update_schema = self._update_schema
        response_meta_schema = self._meta_schema
        resource_model_name = f"{self.repository.model.__name__}".lower()
        resource_model_plural = pluralizer.plural(resource_model_name)
        resource_response_name = response_schema.__name__
        resource_create_name = create_schema.__name__
        resource_update_name = update_schema.__name__

        self._model_name_single = resource_model_name
        self._model_name_plural = resource_model_plural

        # Create shared link model
        link_object = {}
        false_attrs = {}
        for k, v in self._relations.items():
            link_object[k] = (str, ...)
            if (
                v.orm_relationship.direction == MANYTOMANY
                or v.orm_relationship.direction == ONETOMANY
            ) and k not in self._protected_relationships:
                false_attrs[k] = (Optional[List[v.foreign_resource._id_type]], None)
        link_object["__base__"] = CruddyGenericModel

        LinkModel = create_model(f"{resource_model_name}Links", **link_object)
        # End shared link model

        SingleCreateSchema = create_model(
            f"{resource_create_name}Proxy", __base__=create_schema, **false_attrs
        )

        # Create record envelope schema
        SingleCreateEnvelope = create_model(
            f"{resource_create_name}Envelope",
            __base__=CruddyGenericModel,
            **{
                resource_model_name: (SingleCreateSchema, ...),
            },
        )
        # End create record envelope schema

        SingleUpdateSchema = create_model(
            f"{resource_update_name}Proxy", __base__=update_schema, **false_attrs
        )

        # Update record envelope schema
        SingleUpdateEnvelope = create_model(
            f"{resource_update_name}Envelope",
            __base__=CruddyGenericModel,
            **{
                resource_model_name: (SingleUpdateSchema, ...),
            },
        )
        # End update record envelope schema

        # Single record schema with embedded links
        SingleSchemaLinked = create_model(
            f"{resource_response_name}Linked",
            links=(Optional[LinkModel], None),
            __base__=response_schema,
        )
        # End single record schema with embedded links

        # Single record return payload (for get/{id})
        SingleSchemaEnvelope = create_model(
            f"{resource_response_name}Envelope",
            __base__=CruddyGenericModel,
            **{
                resource_model_name: (Optional[Union[SingleSchemaLinked, None]], None),
            },
        )

        handle_data_or_none = self._create_schema_arg_handler(
            single_schema_linked=SingleSchemaLinked,
            resource_model_name=resource_model_name,
        )
        old_single_init = SingleSchemaEnvelope.__init__

        def new_single_init(self, *args, **kwargs):
            old_single_init(
                self,
                *args,
                **handle_data_or_none(kwargs),
            )

        SingleSchemaEnvelope.__init__ = new_single_init
        # End single record return payload

        # Many records return payload (for get/ and queries with "where")
        ManySchemaEnvelope = create_model(
            f"{resource_response_name}List",
            __base__=CruddyGenericModel,
            **{
                resource_model_plural: (Optional[List[SingleSchemaLinked]], None),
            },
            meta=(response_meta_schema, ...),
        )

        old_many_init = ManySchemaEnvelope.__init__

        def new_many_init(self, *args, **kwargs):
            old_many_init(
                self,
                *args,
                **{
                    resource_model_plural: list(
                        map(
                            lambda x: SingleSchemaLinked(
                                **x._mapping,
                                links=local_resource._link_builder(id=x._mapping["id"]),
                            ),
                            kwargs["data"],
                        )
                    )
                    if resource_model_plural not in kwargs
                    else kwargs[resource_model_plural],
                    "data": kwargs["data"] if "data" in kwargs else [],
                    "meta": kwargs["meta"],
                },
            )

        ManySchemaEnvelope.__init__ = new_many_init
        # End many records return payload

        # Expose the following schemas for further use

        self.schemas = {
            "single": SingleSchemaEnvelope,
            "many": ManySchemaEnvelope,
            "create": SingleCreateEnvelope,
            "create_relations": SingleCreateSchema,
            "update": SingleUpdateEnvelope,
            "update_relations": SingleUpdateSchema,
        }

    def _link_builder(self, id: Union[UUID, int] = None):
        str_id = f"{id}"
        new_link_object = {}
        for k, v in self._relations.items():
            new_link_object[
                k
            ] = f"{self._link_prefix}{self._resource_path}/{str_id}/{k}"
        return new_link_object

    def _create_schema_arg_handler(self, single_schema_linked, resource_model_name):
        def data_destructure(data):
            if data == None:
                return {}
            elif hasattr(data, "_mapping"):
                return data._mapping
            if hasattr(data, "dict") and callable(data.dict):
                return data.dict()
            return data

        def handle_data_or_none(args):
            if args == None:
                return {"data": None}

            key_count = len(args.items())

            if key_count == 0:
                return {"data": None}

            if resource_model_name in args:
                return {resource_model_name: args[resource_model_name], "data": None}

            if key_count == 1 and args["data"] == None:
                return {"data": None}

            thing_to_convert = data_destructure(args["data"])
            id = thing_to_convert["id"]
            return {
                resource_model_name: single_schema_linked(
                    **thing_to_convert,
                    links=self._link_builder(id=id),
                ),
                "data": None,
            }

        return handle_data_or_none

    def resolve(self):
        self.controller = ControllerCongifurator(
            controller=self.controller,
            repository=self.repository,
            id_type=self._id_type,
            single_name=self._model_name_single,
            plural_name=self._model_name_plural,
            create_model=self.schemas["create"],
            create_model_proxy=self._create_schema,
            update_model=self.schemas["update"],
            update_model_proxy=self._update_schema,
            single_schema=self.schemas["single"],
            many_schema=self.schemas["many"],
            meta_schema=self._meta_schema,
            relations=self._relations,
            policies_universal=self.policies["universal"],
            policies_create=self.policies["create"],
            policies_update=self.policies["update"],
            policies_delete=self.policies["delete"],
            policies_get_one=self.policies["get_one"],
            policies_get_many=self.policies["get_many"],
        )

        if callable(self._on_resolution):
            self._on_resolution()

    @staticmethod
    def _set_registry(reg: "ResourceRegistry" = ...):
        Resource._registry = reg

    @staticmethod
    def _set_link_prefix(prefix: str):
        Resource._link_prefix = prefix


# This needs a lot of work...
class ResourceRegistry:
    _resolver_invoked: bool = False
    _resources: List[Resource] = []
    _base_models: Dict[str, CruddyModel] = {}
    _rels_via_models: Dict[str, Dict] = {}
    _resources_via_models: Dict[str, Resource] = {}

    def __init__(self):
        self._resolver_invoked = False
        self._resources = []
        self._base_models = {}
        self._rels_via_models = {}
        self._resources_via_models = {}

    # This method needs to build all the lists and dictionaries
    # needed to efficiently search between models to conduct relational
    # joins and controller expansion. Is invoked by each resource as it
    # is created.
    def register(self, res: Resource = None):
        base_model = res.repository.model
        map_name = base_model.__name__
        self._base_models[map_name] = base_model
        self._resources_via_models[map_name] = res
        self._resources.append(res)
        loop = asyncio.get_event_loop()
        # Debounce resolving the registry to the next event loop cycle to
        # to allow SQL Alchemy to finish mapping relationships
        if self._resolver_invoked == False:
            loop.call_soon_threadsafe(self.resolve)
        self._resolver_invoked = True

    # This method can't be invoked until SQL Alchemy is done lazily
    # building the ORM class mappers. Until that action is complete,
    # relationships cannot be discovered via the inspector.
    # May require some thought to setup correctly. Needs to occur
    # after mapper construction, but before FastAPI "swaggers"
    # the API.
    def resolve(self):
        # Solve schemas
        for resource in self._resources:
            # Get the table model the resource uses
            base_model = resource.repository.model
            # Get the human friendly name for this model
            map_name = base_model.__name__
            # Inspect the fully loaded model class for relationships
            relationships = inspect(base_model).relationships
            rel_map = {}

            for relation in relationships:
                rel_map[relation.key] = relation
                # this seems unsafe...
                target_resource_name = relation.entity.class_.__name__
                target_resource = self._resources_via_models[target_resource_name]
                resource.inject_relationship(
                    relationship=relation, foreign_resource=target_resource
                )

            self._rels_via_models[map_name] = rel_map
            resource.generate_internal_schemas()

        # Build routes
        # These have to be separated to ensure all schemas are ready
        for resource in self._resources:
            resource.resolve()

        # Clear this debouncer so any future dynamic resources can try to resolve
        self._resolver_invoked = False


CruddyResourceRegistry = ResourceRegistry()
Resource._set_registry(reg=CruddyResourceRegistry)

# -------------------------------------------------------------------------------------------
# END APPLICATION RESOURCE
# -------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------
# APPLICATION ROUTER / HELPERS
# -------------------------------------------------------------------------------------------
def getModuleDir(application_module) -> str:
    return path.dirname(os.path.abspath(application_module.__file__))


def getDirectoryModules(
    application_module: ModuleType = ..., sub_module_path="resources"
):
    app_root = getModuleDir(application_module)
    app_root_name = path.split(app_root)[1]
    normalized_sub_path = os.path.normpath(sub_module_path)
    submodule_tokens = normalized_sub_path.split(os.sep)
    modules = glob.glob(path.join(app_root, sub_module_path, "*.py"))
    full_module_base = [app_root_name] + submodule_tokens
    loaded_modules = []
    for m in modules:
        file_name = path.basename(m)
        module_name = os.path.splitext(file_name)[0]
        if "__init__" != module_name:
            m_module_tokens = full_module_base + [module_name]
            full_module_name = ".".join(m_module_tokens)
            spec = importlib.util.spec_from_file_location(full_module_name, m)
            abstract_module = importlib.util.module_from_spec(spec)
            loaded_modules.append((module_name, abstract_module))
            sys.modules[full_module_name] = abstract_module
            spec.loader.exec_module(abstract_module)
    return loaded_modules


def CreateRouterFromResources(
    application_module: ModuleType = ...,
    resource_path: str = "resources",
    common_resource_name: str = "resource",
) -> APIRouter:
    modules = getDirectoryModules(
        application_module=application_module, sub_module_path=resource_path
    )
    router = APIRouter()

    # We delay binding routes to the router until all resources are ready
    for m in modules:
        module = m[1]
        resource = getattr(module, common_resource_name)

        def setup(router: APIRouter = router, resource: "Resource" = resource):
            router.include_router(getattr(resource, "controller"))

        resource._on_resolution = setup

    return router


# -------------------------------------------------------------------------------------------
# END APPLICATION ROUTER / HELPERS
# -------------------------------------------------------------------------------------------
