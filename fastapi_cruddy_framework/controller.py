from typing import Any, Literal, Sequence, Type, TYPE_CHECKING
from asyncio import gather
from fastapi import (
    FastAPI,
    APIRouter,
    Request,
    Path,
    Query,
    Depends,
    HTTPException,
    status,
)
from .test_helpers import TestClient, BrowserTestClient
from sqlalchemy import Row
from sqlalchemy.sql.schema import Column, ForeignKey
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.orm import (
    RelationshipDirection,
    ONETOMANY,
    MANYTOMANY,
    MANYTOONE,
)
from pydantic.types import Json
from pydantic.fields import FieldInfo
from .inflector import pluralizer
from .schemas import (
    UUID,
    RelationshipConfig,
    BulkDTO,
    MetaObject,
    PageResponse,
    ResponseSchema,
    CruddyModel,
    CruddyGenericModel,
)
from .util import possible_id_types, possible_id_values, lifecycle_types

if TYPE_CHECKING:
    from .repository import AbstractRepository
    from .resource import Resource
    from .adapters import BaseAdapter, MysqlAdapter, PostgresqlAdapter, SqliteAdapter

DATA_KEY = "data"
META_KEY = "meta"
META_ID_KEY = "id"
META_RELATION_INFO_KEY = "relations"
META_NUM_RELATION_MODIFIED_KEY = "total_modified"
META_RELATED_RECORDS_KEY = "records"
META_FAILED_RECORDS_KEY = "invalid"
META_VALIDATION_MESSAGES_KEY = "messages"
# -------------------------------------------------------------------------------------------
# ACTION MAP (FOR REUSE IN CLIENT CODE)
# -------------------------------------------------------------------------------------------


class Actions:
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
    }
    default_limit: int
    relations: dict[str, RelationshipConfig]
    repository: "AbstractRepository"

    def __init__(
        self,
        id_type: possible_id_types,
        single_name: str,
        disable_nested_objects: bool,
        repository: "AbstractRepository",
        create_model: Type[CruddyGenericModel],
        create_model_proxy: Type[CruddyModel],
        update_model: Type[CruddyGenericModel],
        update_model_proxy: Type[CruddyModel],
        single_schema: Type[CruddyGenericModel],
        many_schema: Type[CruddyGenericModel],
        meta_schema: Type[CruddyModel] | Type[CruddyGenericModel],
        relations: dict[str, RelationshipConfig],
        lifecycle: dict[str, lifecycle_types],
        default_limit: int = 10,
    ):
        self.default_limit = default_limit
        self.lifecycle = lifecycle
        self.relations = relations
        self.repository = repository
        self.disable_nested_objects = disable_nested_objects

        async def create(request: Request, data: create_model):
            the_thing_with_rels: CruddyGenericModel = getattr(data, single_name)
            context_data = {DATA_KEY: the_thing_with_rels, META_KEY: None}
            # If there is a user space lifecycle hook, run it (allows context mutations)
            if self.lifecycle["before_create"]:
                await self.lifecycle["before_create"](request, context_data)
            # Update the many-to-one relationships
            (
                single_num_relations_modified,
                single_relations_modified,
                single_field_failures,
                single_failure_responses,
            ) = await self.save_single_relationships(
                request=request,
                record=the_thing_with_rels,
            )
            # Trim off the relationships prior to saving the core object
            the_thing = create_model_proxy(**the_thing_with_rels.model_dump())
            # Update the operating context
            context_data[DATA_KEY] = the_thing
            context_data[META_KEY] = {
                META_RELATION_INFO_KEY: {
                    META_NUM_RELATION_MODIFIED_KEY: single_num_relations_modified,
                    META_RELATED_RECORDS_KEY: single_relations_modified,
                    META_FAILED_RECORDS_KEY: single_field_failures,
                    META_VALIDATION_MESSAGES_KEY: single_failure_responses,
                }
            }
            # Create the core object in the repository
            result = await repository.create(data=context_data[DATA_KEY])
            # Update the operating context
            context_data[DATA_KEY] = result
            # Udate many-to-many and one-to-many relationships
            (
                num_relations_modified,
                relations_modified,
                field_failures,
                failure_responses,
            ) = await self.save_list_relationships(
                request=request,
                id=getattr(result, str(repository.primary_key)),
                record=the_thing_with_rels,
            )
            # Add error logic?
            # Update the operating context
            context_data[META_KEY][META_RELATION_INFO_KEY][
                META_NUM_RELATION_MODIFIED_KEY
            ] += num_relations_modified
            context_data[META_KEY][META_RELATION_INFO_KEY][META_RELATED_RECORDS_KEY] = {
                **context_data[META_KEY][META_RELATION_INFO_KEY][
                    META_RELATED_RECORDS_KEY
                ],
                **relations_modified,
            }
            context_data[META_KEY][META_RELATION_INFO_KEY][META_FAILED_RECORDS_KEY] = {
                **context_data[META_KEY][META_RELATION_INFO_KEY][
                    META_FAILED_RECORDS_KEY
                ],
                **field_failures,
            }
            context_data[META_KEY][META_RELATION_INFO_KEY][
                META_VALIDATION_MESSAGES_KEY
            ] = {
                **context_data[META_KEY][META_RELATION_INFO_KEY][
                    META_VALIDATION_MESSAGES_KEY
                ],
                **failure_responses,
            }
            # If there is a user space lifecycle hook, run it (allows context mutations)
            if self.lifecycle["after_create"]:
                await self.lifecycle["after_create"](request, context_data)
            # Return the final result to the FastAPI serializer
            return single_schema(**context_data)

        async def update(
            request: Request, id: id_type = Path(..., alias="id"), *, data: update_model
        ):
            the_thing_with_rels: CruddyGenericModel = getattr(data, single_name)
            context_data = {DATA_KEY: the_thing_with_rels, META_KEY: {META_ID_KEY: id}}
            # If there is a user space lifecycle hook, run it (allows context mutations)
            if self.lifecycle["before_update"]:
                await self.lifecycle["before_update"](request, context_data)
            # If the hosting app altered the id, grab it
            _id = context_data[META_KEY][META_ID_KEY]
            # Update the many-to-one relationships
            (
                single_num_relations_modified,
                single_relations_modified,
                single_field_failures,
                single_failure_responses,
            ) = await self.save_single_relationships(
                request=request,
                record=the_thing_with_rels,
            )
            # Trim off the relationships prior to saving the core object
            the_thing = update_model_proxy(**the_thing_with_rels.model_dump())
            # Update the operating context
            context_data[DATA_KEY] = the_thing
            context_data[META_KEY] = {
                META_RELATION_INFO_KEY: {
                    META_NUM_RELATION_MODIFIED_KEY: single_num_relations_modified,
                    META_RELATED_RECORDS_KEY: single_relations_modified,
                    META_FAILED_RECORDS_KEY: single_field_failures,
                    META_VALIDATION_MESSAGES_KEY: single_failure_responses,
                }
            }
            # Update the core object in the repository
            result: CruddyModel | None = await repository.update(
                id=_id, data=context_data[DATA_KEY]
            )
            # Add error logic?
            if result is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Record id {id} not found",
                )
            # Update the operating context
            context_data[DATA_KEY] = result
            # Udate many-to-many and one-to-many relationships
            (
                num_relations_modified,
                relations_modified,
                field_failures,
                failure_responses,
            ) = await self.save_list_relationships(
                request=request,
                id=getattr(result, str(repository.primary_key)),
                record=the_thing_with_rels,
            )
            # Add error logic?
            # Update the operating context
            context_data[META_KEY][META_RELATION_INFO_KEY][
                META_NUM_RELATION_MODIFIED_KEY
            ] += num_relations_modified
            context_data[META_KEY][META_RELATION_INFO_KEY][META_RELATED_RECORDS_KEY] = {
                **context_data[META_KEY][META_RELATION_INFO_KEY][
                    META_RELATED_RECORDS_KEY
                ],
                **relations_modified,
            }
            context_data[META_KEY][META_RELATION_INFO_KEY][META_FAILED_RECORDS_KEY] = {
                **context_data[META_KEY][META_RELATION_INFO_KEY][
                    META_FAILED_RECORDS_KEY
                ],
                **field_failures,
            }
            context_data[META_KEY][META_RELATION_INFO_KEY][
                META_VALIDATION_MESSAGES_KEY
            ] = {
                **context_data[META_KEY][META_RELATION_INFO_KEY][
                    META_VALIDATION_MESSAGES_KEY
                ],
                **failure_responses,
            }
            # If there is a user space lifecycle hook, run it (allows context mutations)
            if self.lifecycle["after_update"]:
                await self.lifecycle["after_update"](request, context_data)
            # Return the final result to the FastAPI serializer
            return single_schema(**context_data)

        async def delete(
            request: Request,
            id: id_type = Path(..., alias="id"),
        ):
            context_data = {
                DATA_KEY: id,
                META_KEY: None,
            }
            # If there is a user space lifecycle hook, run it (allows context mutations)
            if self.lifecycle["before_delete"]:
                await self.lifecycle["before_delete"](request, context_data)
            # Delete the core object in the repository
            data = await repository.delete(id=context_data[DATA_KEY])
            # Add error logic?
            if data is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Record id {id} not found",
                )
            # Update the operating context
            context_data[DATA_KEY] = data
            # If there is a user space lifecycle hook, run it (allows context mutations)
            if self.lifecycle["after_delete"]:
                await self.lifecycle["after_delete"](request, context_data)
            # Return the final result to the FastAPI serializer
            return single_schema(**context_data)

        async def get_by_id(
            request: Request,
            id: id_type = Path(..., alias="id"),
            where: Json = Query(None, alias="where"),
        ):
            context_data = {
                DATA_KEY: {
                    "id": id,
                    "where": where,
                },
                META_KEY: None,
            }
            # If there is a user space lifecycle hook, run it (allows context mutations)
            if self.lifecycle["before_get_one"]:
                await self.lifecycle["before_get_one"](request, context_data)
            # Find the core object in the repository
            data = await repository.get_by_id(**context_data[DATA_KEY])
            # Add error logic?
            if data is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Record id {id} not found",
                )
            # Update the operating context
            context_data[DATA_KEY] = data
            # If there is a user space lifecycle hook, run it (allows context mutations)
            if self.lifecycle["after_get_one"]:
                await self.lifecycle["after_get_one"](request, context_data)
            # Return the final result to the FastAPI serializer
            return single_schema(**context_data)

        async def get_all(
            request: Request,
            page: int = 1,
            limit: int = self.default_limit,
            columns: list[str] = Query(None, alias="columns"),
            sort: list[str] = Query(None, alias="sort"),
            where: Json = Query(None, alias="where"),
        ):
            context_data = {
                DATA_KEY: {
                    "page": page,
                    "limit": limit,
                    "columns": columns,
                    "sort": sort,
                    "where": where,
                },
                META_KEY: None,
            }
            # If there is a user space lifecycle hook, run it (allows context mutations)
            if self.lifecycle["before_get_all"]:
                await self.lifecycle["before_get_all"](request, context_data)
            # Find the core objects in the repository
            result: BulkDTO = await repository.get_all(**context_data[DATA_KEY])
            # Update the operating context
            context_data[DATA_KEY] = result.data
            context_data[META_KEY] = {
                "page": result.page,
                "limit": result.limit,
                "pages": result.total_pages,
                "records": result.total_records,
            }
            # If there is a user space lifecycle hook, run it (allows context mutations)
            if self.lifecycle["after_get_all"]:
                await self.lifecycle["after_get_all"](request, context_data)
            # Return the final result to the FastAPI serializer
            return many_schema(
                **{
                    DATA_KEY: context_data[DATA_KEY],
                    META_KEY: meta_schema(**context_data[META_KEY]),
                }
            )

        # These functions all have dynamic signatures, so are generated within __init__
        self.create = create
        self.update = update
        self.delete = delete
        self.get_by_id = get_by_id
        self.get_all = get_all

    def convert_to_field_type(self, info: FieldInfo, value: Any):
        if issubclass(UUID, info.annotation):  # type: ignore
            return UUID(value)
        if issubclass(int, info.annotation):  # type: ignore
            return int(value)
        return value

    def get_relationships(
        self,
        record: CruddyModel | CruddyGenericModel,
        relationship_directions: list[RelationshipDirection],
    ):
        relation_config_map = self.relations
        record_relations = {}
        for k, v in relation_config_map.items():
            direction = v.orm_relationship.direction
            if (
                direction in relationship_directions
                and hasattr(record, k)
                and getattr(record, k) != None
            ):
                record_relations[k] = getattr(record, k)
        return record_relations

    async def create_or_update_relation(
        self, request: Request, resource: "Resource", data: dict
    ):
        app: FastAPI = request.app
        client = BrowserTestClient(client=TestClient(app, use_cookies=False))
        routing_path = f"{resource._resource_path}"
        view_model: type[CruddyModel] = resource._response_schema
        pk = resource.repository.primary_key
        payload_key = resource._model_name_single
        payload = {payload_key: data}
        query_value = str(request.query_params)
        query_string = f"?{query_value}" if len(query_value) > 0 else ""
        try:
            _id = data.get(pk, None)
            if _id is None:
                response = await client.post(
                    f"{routing_path}{query_string}",
                    headers=dict(request.headers.items()),
                    json=payload,
                )
                if response.status_code == status.HTTP_200_OK:
                    response_json: dict = response.json()
                    obj: dict = response_json.get(payload_key, {})
                    value = f"{obj.get(pk, '')}"
                    return True, value, view_model(**obj).model_dump(), None
                else:
                    return False, data, None, response.json()
            response = await client.patch(
                f"{routing_path}/{_id}{query_string}",
                headers=dict(request.headers.items()),
                json=payload,
            )
            if response.status_code == status.HTTP_200_OK:
                response_json: dict = response.json()
                obj: dict = response_json.get(payload_key, {})
                value = f"{obj.get(pk, '')}"
                return True, value, view_model(**obj).model_dump(), None
            else:
                return False, data, None, response.json()
        except Exception:
            return False, data, None, None

    async def save_list_relationships(
        self,
        request: Request,
        id: possible_id_values,
        record: CruddyModel | CruddyGenericModel,
    ):
        relation_config_map = self.relations
        repository = self.repository
        disable_nested_objects = self.disable_nested_objects
        relationships = self.get_relationships(record, [MANYTOMANY, ONETOMANY])
        modified_relational_count = 0
        awaitables = []
        overall_failures = {}
        overall_failed_responses = {}
        modified_records = {}
        for k, v in relationships.items():
            name: str = k
            new_relations: list[Any] = v
            settled_relations: list[possible_id_values] = []
            config: RelationshipConfig = relation_config_map[name]
            foreign_resource: "Resource" = config.foreign_resource
            inner_awaitables = []
            inner_modified_records = []
            field_failures = []
            field_responses = []
            if isinstance(new_relations, list):
                for relation in new_relations:
                    if not isinstance(relation, dict):
                        settled_relations.append(relation)
                    elif not disable_nested_objects:
                        inner_awaitables.append(
                            self.create_or_update_relation(
                                request=request,
                                resource=foreign_resource,
                                data=relation,
                            )
                        )
            if len(inner_awaitables) > 0:
                results = await gather(*inner_awaitables, return_exceptions=True)
                for success, value, related_record, err_response in results:
                    if success == True and isinstance(value, str):
                        settled_relations.append(value)
                        inner_modified_records.append(related_record)
                    else:
                        field_failures.append(value)
                        field_responses.append(err_response)
            if config.orm_relationship.direction == MANYTOMANY:
                awaitables.append(
                    repository.set_many_many_relations(
                        id=id, relation=name, relations=settled_relations
                    )
                )
            elif config.orm_relationship.direction == ONETOMANY:
                # technically, the below line will force newly created relations, or updated records, to shift
                # their relationship pointer to the master record `id`, regardless of what the client had
                # specified in the body of that record's update
                # (there will be a moment where it could violate the relationship)
                awaitables.append(
                    repository.set_one_many_relations(
                        id=id, relation=name, relations=settled_relations
                    )
                )
            if len(field_failures) > 0:
                overall_failures[name] = field_failures
            if len(field_responses) > 0:
                overall_failed_responses[name] = field_responses
            if len(inner_modified_records) > 0:
                modified_records[name] = inner_modified_records
        results: list[Any] = await gather(*awaitables, return_exceptions=True)
        for result_or_exc in results:
            if isinstance(result_or_exc, int):
                modified_relational_count += result_or_exc
        return (
            modified_relational_count,
            modified_records,
            overall_failures,
            overall_failed_responses,
        )

    async def save_single_relationships(
        self,
        request: Request,
        record: CruddyModel | CruddyGenericModel,
    ):
        relation_config_map = self.relations
        disable_nested_objects = self.disable_nested_objects
        relationships = self.get_relationships(record, [MANYTOONE])
        modified_relational_count = 0
        overall_failures = {}
        overall_failed_responses = {}
        modified_records = {}
        for k, v in relationships.items():
            name: str = k
            new_relation: dict | str | int = v
            settled_relation: Literal[False] | possible_id_values = False
            config: RelationshipConfig = relation_config_map[name]
            foreign_resource: "Resource" = config.foreign_resource
            field_failures = []
            field_responses = []
            if isinstance(new_relation, dict) and not disable_nested_objects:
                (
                    success,
                    value,
                    related_record,
                    err_response,
                ) = await self.create_or_update_relation(
                    request=request, resource=foreign_resource, data=new_relation
                )
                if success is True and isinstance(value, str):
                    settled_relation = value
                    modified_records[name] = related_record
                else:
                    field_failures.append(value)
                    field_responses.append(err_response)
            elif isinstance(new_relation, (str, int)):
                settled_relation = new_relation
            if settled_relation is not False:
                # No async required, just re-tag the record key
                key = config.orm_relationship.key
                local_column = next(iter(config.orm_relationship.local_columns))
                key = str(local_column.key)
                setattr(
                    record,
                    key,
                    self.convert_to_field_type(
                        record.model_fields[key], settled_relation
                    ),
                )
                modified_relational_count += 1
            if len(field_failures) > 0:
                overall_failures[name] = field_failures
            if len(field_responses) > 0:
                overall_failed_responses[name] = field_responses
        return (
            modified_relational_count,
            modified_records,
            overall_failures,
            overall_failed_responses,
        )


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

    @property
    def router(self):
        return self.controller


# -------------------------------------------------------------------------------------------
# UTILITY FUNCTIONS FOR CONTROLLER CONFIGURATION
# -------------------------------------------------------------------------------------------


def assemblePolicies(*args: (Sequence)):
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
    col: ColumnElement = next(iter(config.orm_relationship.local_columns))
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
        origin_record: CruddyModel | None = await repository.get_by_id(id=id)

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
        data: dict[str, Any] | None = None
        if len(result.data) != 0:
            row_data: Row = result.data[0]
            table_record: CruddyModel = config.foreign_resource.repository.model(
                **row_data._mapping
            )
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
        return config.foreign_resource.schemas["single"](**{DATA_KEY: data})


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
    far_col: ColumnElement = next(iter(config.orm_relationship.remote_side))
    col: ColumnElement = next(iter(config.orm_relationship.local_columns))
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
        origin_record: CruddyModel | None = await repository.get_by_id(id=id)

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
            **{META_KEY: meta_schema(**meta), DATA_KEY: result.data}
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
            **{META_KEY: meta_schema(**meta), DATA_KEY: result.data}
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
