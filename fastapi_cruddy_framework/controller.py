from asyncio import gather
from fastapi import APIRouter, Path, Query, Depends, HTTPException, status
from sqlalchemy.sql.schema import Column, ForeignKey
from sqlalchemy.orm import (
    ONETOMANY,
    MANYTOMANY,
    MANYTOONE,
)
from typing import Any, Type, TYPE_CHECKING
from pydantic.types import Json
from .inflector import pluralizer
from .schemas import (
    RelationshipConfig,
    BulkDTO,
    MetaObject,
    PageResponse,
    ResponseSchema,
    CruddyModel,
    CruddyGenericModel,
)
from .util import possible_id_types, possible_id_values

if TYPE_CHECKING:
    from .repository import AbstractRepository
    from .resource import Resource
    from .adapters import BaseAdapter, MysqlAdapter, PostgresqlAdapter, SqliteAdapter

# -------------------------------------------------------------------------------------------
# RELATIONSHIP UTILITY FUNCTIONS
# -------------------------------------------------------------------------------------------


def GetRelationships(
    record: Type[CruddyModel], relation_config_map: dict[str, RelationshipConfig]
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
    id: possible_id_values,
    record: Type[CruddyModel],
    relation_config_map: dict[str, RelationshipConfig],
    repository: "AbstractRepository",
):
    relationship_lists = GetRelationships(record, relation_config_map)
    modified_records = 0
    awaitables = []
    for k, v in relationship_lists.items():
        name: str = k
        new_relations: list[possible_id_values] = v
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
    results: list[Any] = await gather(*awaitables, return_exceptions=True)
    for result_or_exc in results:
        if isinstance(result_or_exc, int):
            modified_records += result_or_exc
    return modified_records


# -------------------------------------------------------------------------------------------
# ACTION MAP (FOR REUSE IN CLIENT CODE)
# -------------------------------------------------------------------------------------------


class Actions:
    def __init__(
        self,
        id_type: possible_id_types,
        single_name: str,
        repository: "AbstractRepository",
        create_model: Type[CruddyGenericModel],
        create_model_proxy: Type[CruddyModel],
        update_model: Type[CruddyGenericModel],
        update_model_proxy: Type[CruddyModel],
        single_schema: Type[CruddyGenericModel],
        many_schema: Type[CruddyGenericModel],
        meta_schema: Type[CruddyModel] | Type[CruddyGenericModel],
        relations: dict[str, RelationshipConfig],
        default_limit: int = 10,
    ):
        self.default_limit = default_limit

        async def create(data: create_model):
            the_thing_with_rels = getattr(data, single_name)
            the_thing = create_model_proxy(**the_thing_with_rels.model_dump())
            result = await repository.create(data=the_thing)
            relations_modified = await SaveRelationships(
                id=getattr(result, str(repository.primary_key)),
                record=the_thing_with_rels,
                relation_config_map=relations,
                repository=repository,
            )
            # Add error logic?
            return single_schema(**{"data": result})

        async def update(id: id_type = Path(..., alias="id"), *, data: update_model):
            the_thing_with_rels = getattr(data, single_name)
            the_thing = update_model_proxy(**the_thing_with_rels.model_dump())
            result = await repository.update(id=id, data=the_thing)
            # Add error logic?
            if result is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Record id {id} not found",
                )

            relations_modified = await SaveRelationships(
                id=getattr(result, str(repository.primary_key)),
                record=the_thing_with_rels,
                relation_config_map=relations,
                repository=repository,
            )

            return single_schema(**{"data": result})

        async def delete(
            id: id_type = Path(..., alias="id"),
        ):
            data = await repository.delete(id=id)

            # Add error logic?
            if data is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Record id {id} not found",
                )

            return single_schema(**{"data": data})

        async def get_by_id(
            id: id_type = Path(..., alias="id"),
            where: Json = Query(None, alias="where"),
        ):
            data = await repository.get_by_id(id=id, where=where)

            # Add error logic?
            if data is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Record id {id} not found",
                )

            return single_schema(**{"data": data})

        async def get_all(
            page: int = 1,
            limit: int = self.default_limit,
            columns: list[str] = Query(None, alias="columns"),
            sort: list[str] = Query(None, alias="sort"),
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
            return many_schema(**{"meta": meta_schema(**meta), "data": result.data})

        # These functions all have dynamic signatures, so are generated within __init__
        self.create = create
        self.update = update
        self.delete = delete
        self.get_by_id = get_by_id
        self.get_all = get_all


# -------------------------------------------------------------------------------------------
# CONTROLLER EXTENSION (FOR CLIENT USE)
# -------------------------------------------------------------------------------------------


class CruddyController:
    actions: Actions
    controller: APIRouter
    repository: "AbstractRepository"
    resource: "Resource"
    adapter: "BaseAdapter | MysqlAdapter | PostgresqlAdapter | SqliteAdapter"

    def __init__(
        self,
        actions: Actions,
        controller: APIRouter,
        repository: "AbstractRepository",
        resource: "Resource",
        adapter: "BaseAdapter | MysqlAdapter | PostgresqlAdapter | SqliteAdapter",
    ):
        self.actions = actions
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


# -------------------------------------------------------------------------------------------
# UTILITY FUNCTIONS FOR CONTROLLER CONFIGURATION
# -------------------------------------------------------------------------------------------


def assemblePolicies(*args: (list)):
    merged = []
    for policy_set in args:
        for individual_policy in policy_set:
            merged.append(Depends(individual_policy))
    return merged


def _ControllerConfigManyToOne(
    controller: APIRouter,
    repository: "AbstractRepository",
    id_type: possible_id_types,
    relationship_prop: str,
    config: RelationshipConfig,
    policies_universal: list,
    policies_get_one: list,
):
    col: Column = next(iter(config.orm_relationship.local_columns))  # type: ignore
    far_side: ForeignKey = next(iter(col.foreign_keys))
    far_col: Column = far_side.column
    far_col_name = far_col.name
    near_col_name = col.name
    resource_model_name = f"{repository.model.__name__}".lower()
    foreign_model_name = f"{config.foreign_resource.repository.model.__name__}".lower()

    # Merge three policy sets onto this endpoint:
    # 1. Universal policies
    # 2. Primary resource policies
    # 3. Related resource policies
    @controller.get(
        f'/{"{id}"}/{relationship_prop}',
        description=f"Get the '{foreign_model_name}' a '{resource_model_name}' belongs to",
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
        columns: list[str] = Query(None, alias="columns"),
        where: Json = Query(None, alias="where"),
    ):
        origin_record = await repository.get_by_id(id=id)

        # Consider raising 404 here and in get by ID
        if origin_record == None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Record {id} not found"
            )

        # Build a query to use foreign resource to find related objects

        tgt_id = origin_record.model_dump()[near_col_name]
        must_be = {far_col_name: {"*eq": tgt_id}}
        where = must_be if where is None else {"*and": [must_be, where]}

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
            data: Any = result.data[0]
            table_record = config.foreign_resource.repository.model(**data._mapping)
            if foreign_lifecycle_after != None:
                await foreign_lifecycle_after(table_record)
            data = table_record.model_dump()
        else:
            if foreign_lifecycle_after != None:
                await foreign_lifecycle_after(None)

        if data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
            )

        # Invoke the dynamically built model
        return config.foreign_resource.schemas["single"](**{"data": data})


def _ControllerConfigOneToMany(
    controller: APIRouter,
    repository: "AbstractRepository",
    id_type: possible_id_types,
    relationship_prop: str,
    config: RelationshipConfig,
    meta_schema: Type[CruddyModel] | Type[CruddyGenericModel] = MetaObject,
    policies_universal: list = [],
    policies_get_one: list = [],
    default_limit: int = 10,
):
    far_col: Column = next(iter(config.orm_relationship.remote_side))  # type: ignore
    col: Column = next(iter(config.orm_relationship.local_columns))  # type: ignore
    far_col_name = far_col.name
    near_col_name = col.name
    resource_model_name = f"{repository.model.__name__}".lower()
    foreign_model_name = pluralizer.plural(
        f"{config.foreign_resource.repository.model.__name__}".lower()
    )

    # Merge three policy sets onto this endpoint:
    # 1. Universal policies
    # 2. Primary resource policies
    # 3. Related resource policies
    @controller.get(
        f'/{"{id}"}/{relationship_prop}',
        description=f"Get all '{foreign_model_name}' belonging to a '{resource_model_name}'",
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
        limit: int = default_limit,
        columns: list[str] = Query(None, alias="columns"),
        sort: list[str] = Query(None, alias="sort"),
        where: Json = Query(None, alias="where"),
    ):
        origin_record = await repository.get_by_id(id=id)

        # Consider raising 404 here and in get by ID
        if origin_record == None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Record {id} not found"
            )

        # Build a query to use foreign resource to find related objects
        additional_where = {
            far_col_name: {"*eq": origin_record.model_dump()[near_col_name]}
        }
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
            **{"meta": meta_schema(**meta), "data": result.data}
        )


def _ControllerConfigManyToMany(
    controller: APIRouter,
    repository: "AbstractRepository",
    id_type: possible_id_types,
    relationship_prop: str,
    config: RelationshipConfig,
    meta_schema: Type[CruddyModel] | Type[CruddyGenericModel] = MetaObject,
    policies_universal: list = [],
    policies_get_one: list = [],
    default_limit: int = 10,
):
    far_model: Type[CruddyModel] = config.foreign_resource.repository.model
    resource_model_name = f"{repository.model.__name__}".lower()
    foreign_model_name = pluralizer.plural(
        f"{config.foreign_resource.repository.model.__name__}".lower()
    )

    # Merge three policy sets onto this endpoint:
    # 1. Universal policies
    # 2. Primary resource policies
    # 3. Related resource policies
    @controller.get(
        f'/{"{id}"}/{relationship_prop}',
        description=f"Get all '{foreign_model_name}' related to a '{resource_model_name}'",
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
        limit: int = default_limit,
        columns: list[str] = Query(None, alias="columns"),
        sort: list[str] = Query(None, alias="sort"),
        where: Json = Query(None, alias="where"),
    ):
        # Consider raising 404 here and in get by ID
        if await repository.get_by_id(id=id) == None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Record {id} not found"
            )

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
            **{"meta": meta_schema(**meta), "data": result.data}
        )


# -------------------------------------------------------------------------------------------
# CONTROLLER CONFIGURATOR
# Binds routes to controller actions based on application configuration
# -------------------------------------------------------------------------------------------


def ControllerConfigurator(
    controller: APIRouter,
    repository: "AbstractRepository",
    single_name: str,
    plural_name: str,
    actions: Actions,
    relations: dict[str, RelationshipConfig],
    id_type: possible_id_types = int,
    single_schema: Type[CruddyGenericModel] = ResponseSchema,
    many_schema: Type[CruddyGenericModel] = PageResponse,
    meta_schema: Type[CruddyModel] | Type[CruddyGenericModel] = MetaObject,
    policies_universal=[],
    policies_create=[],
    policies_update=[],
    policies_delete=[],
    policies_get_one=[],
    policies_get_many=[],
    disable_create=False,
    disable_update=False,
    disable_delete=False,
    disable_get_one=False,
    disable_get_many=False,
) -> APIRouter:
    if not disable_create:
        controller.post(
            "",
            description=f"Create a single '{single_name}'",
            response_model=single_schema,
            response_model_exclude_none=True,
            dependencies=assemblePolicies(policies_universal, policies_create),
        )(actions.create)

    if not disable_update:
        controller.patch(
            "/{id}",
            description=f"Update a single '{single_name}'",
            response_model=single_schema,
            response_model_exclude_none=True,
            dependencies=assemblePolicies(policies_universal, policies_update),
        )(actions.update)

    if not disable_delete:
        controller.delete(
            "/{id}",
            description=f"Delete a single '{single_name}'",
            response_model=single_schema,
            response_model_exclude_none=True,
            dependencies=assemblePolicies(policies_universal, policies_delete),
        )(actions.delete)

    if not disable_get_one:
        controller.get(
            "/{id}",
            description=f"Fetch a single '{single_name}'",
            response_model=single_schema,
            response_model_exclude_none=True,
            dependencies=assemblePolicies(policies_universal, policies_get_one),
        )(actions.get_by_id)

    if not disable_get_many:
        controller.get(
            "",
            description=f"Fetch many '{plural_name}'",
            response_model=many_schema,
            response_model_exclude_none=True,
            dependencies=assemblePolicies(policies_universal, policies_get_many),
        )(actions.get_all)

    # Add relationship link endpoints starting here...
    # Maybe add way to disable these getters?
    # Maybe add way to wrangle this unknown number of functions into the actions map?
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
                default_limit=actions.default_limit,
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
                default_limit=actions.default_limit,
            )
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
