from asyncio import gather
from fastapi import APIRouter, Path, Query, Depends
from sqlalchemy.sql.schema import Column, ForeignKey
from sqlalchemy.orm import (
    ONETOMANY,
    MANYTOMANY,
    MANYTOONE,
)
from typing import Union, List, Dict, TYPE_CHECKING
from pydantic.types import Json
from .schemas import (
    RelationshipConfig,
    BulkDTO,
    MetaObject,
    PageResponse,
    ResponseSchema,
    CruddyModel,
    ExampleUpdate,
    ExampleCreate,
)
from .util import possible_id_types

if TYPE_CHECKING:
    from .repository import AbstractRepository
    from .resource import Resource
    from .adapters import BaseAdapter, MysqlAdapter, PostgresqlAdapter, SqliteAdapter


# -------------------------------------------------------------------------------------------
# CONTROLLER / ROUTER
# -------------------------------------------------------------------------------------------


class CruddyController:
    controller: APIRouter = None
    repository: "AbstractRepository" = None
    resource: "Resource" = None
    adapter: Union[
        "BaseAdapter", "MysqlAdapter", "PostgresqlAdapter", "SqliteAdapter"
    ] = None

    def __init__(
        self,
        controller: APIRouter = ...,
        repository: "AbstractRepository" = ...,
        resource: "Resource" = ...,
        adapter: Union[
            "BaseAdapter", "MysqlAdapter", "PostgresqlAdapter", "SqliteAdapter"
        ] = ...,
    ):
        self.controller = controller
        self.repository = repository
        self.resource = resource
        self.adapter = adapter
        self.setup()

    def setup(self):
        # Override this method in your code!
        # This is the best place to add more methods to the resource controller!
        # By defining your controllers as classes, you can even share methods between resources, like a mixin!
        pass


def assemblePolicies(*args: (List)):
    merged = []
    for policy_set in args:
        for individual_policy in policy_set:
            merged.append(Depends(individual_policy))
    return merged


def _ControllerConfigManyToOne(
    controller: APIRouter = ...,
    repository: "AbstractRepository" = ...,
    id_type: possible_id_types = ...,
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

        tgt_id = origin_record.dict()[near_col_name]
        where = {far_col_name: {"*eq": tgt_id}}

        _lifecycle_before = None
        foreign_lifecycle_before = config.foreign_resource.repository.lifecycle[
            "before_get_one"
        ]
        foreign_lifecycle_after = config.foreign_resource.repository.lifecycle[
            "after_get_one"
        ]
        if foreign_lifecycle_before != None:

            async def _shimmed_lifecycle_before():
                await foreign_lifecycle_before(tgt_id)
                return

            _lifecycle_before = _shimmed_lifecycle_before

        # Collect the bulk data transfer object from the query
        result: BulkDTO = await config.foreign_resource.repository.get_all(
            page=1,
            limit=1,
            columns=columns,
            sort=None,
            where=where,
            _use_own_hooks=False,
            _lifecycle_before=_lifecycle_before,
        )

        # If we get a result, grab the first value. There should only be one in many to one.
        data = None
        if len(result.data) != 0:
            data = result.data[0]
            table_record = config.foreign_resource.repository.model(**data)
            if foreign_lifecycle_after != None:
                await foreign_lifecycle_after(table_record)
            data = table_record.dict()
        else:
            if foreign_lifecycle_after != None:
                await foreign_lifecycle_after(None)

        # Invoke the dynamically built model
        return config.foreign_resource.schemas["single"](data=data)


def _ControllerConfigOneToMany(
    controller: APIRouter = ...,
    repository: "AbstractRepository" = ...,
    id_type: possible_id_types = ...,
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
                data=[],
                meta=meta_schema(**{"page": 0, "limit": 0, "pages": 0, "records": 0}),
            )

        # Build a query to use foreign resource to find related objects
        additional_where = {far_col_name: {"*eq": origin_record.dict()[near_col_name]}}
        if where != None:
            repo_where = {"*and": [additional_where, where]}
        else:
            repo_where = additional_where

        _lifecycle_before = None
        foreign_lifecycle_before = config.foreign_resource.repository.lifecycle[
            "before_get_all"
        ]

        # This will shim the lifecycle hook so it does not see the relational portion of the query
        # but can still alter the general search object as if its a single resource query.
        # This is good because a lifecycle hook should only be concerned about its own resource.
        if foreign_lifecycle_before != None:

            async def _shimmed_lifecycle_before(query_conf):
                local_where = query_conf["where"]
                query_conf["where"] = where
                await foreign_lifecycle_before(query_conf)
                query_conf["where"] = local_where
                return

            _lifecycle_before = _shimmed_lifecycle_before

        # Collect the bulk data transfer object from the query
        result: BulkDTO = await config.foreign_resource.repository.get_all(
            page=page,
            limit=limit,
            columns=columns,
            sort=sort,
            where=repo_where,
            _lifecycle_before=_lifecycle_before,
            _lifecycle_after=config.foreign_resource.repository.lifecycle[
                "after_get_all"
            ],
            _use_own_hooks=False,
        )
        meta = {
            "page": result.page,
            "limit": result.limit,
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
    id_type: possible_id_types = ...,
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
            # the foreign resource must interact with its own lifecycle
            _lifecycle_before=config.foreign_resource.repository.lifecycle[
                "before_get_all"
            ],
            _lifecycle_after=config.foreign_resource.repository.lifecycle[
                "after_get_all"
            ],
        )
        meta = {
            "page": result.page,
            "limit": result.limit,
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
    id: possible_id_types = ...,
    record: CruddyModel = ...,
    relation_config_map: Dict[str, RelationshipConfig] = ...,
    repository: "AbstractRepository" = ...,
):
    relationship_lists = GetRelationships(record, relation_config_map)
    modified_records = 0
    awaitables = []
    for k, v in relationship_lists.items():
        name: str = k
        new_relations: List[possible_id_types] = v
        config: RelationshipConfig = relation_config_map[name]
        if config.orm_relationship.direction == MANYTOMANY:
            awaitables.append(
                repository.set_many_many_relations(
                    id=id, relation=name, relations=new_relations
                )
            )
        elif config.orm_relationship.direction == ONETOMANY:
            awaitables.append(
                repository.set_one_many_relations(
                    id=id, relation=name, relations=new_relations
                )
            )
    results = await gather(*awaitables, return_exceptions=True)
    for result_or_exc in results:
        if not isinstance(result_or_exc, Exception):
            modified_records += result_or_exc
    return modified_records


def ControllerCongifurator(
    controller: APIRouter = ...,
    repository: "AbstractRepository" = ...,
    id_type: possible_id_types = int,
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
            id=getattr(result, repository.primary_key),
            record=the_thing_with_rels,
            relation_config_map=relations,
            repository=repository,
        )
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
            id=getattr(result, repository.primary_key),
            record=the_thing_with_rels,
            relation_config_map=relations,
            repository=repository,
        )
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
            "page": result.page,
            "limit": result.limit,
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
