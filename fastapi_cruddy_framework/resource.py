# pyright: reportShadowedImports=false
import asyncio
from fastapi import APIRouter
from sqlalchemy.orm import (
    RelationshipProperty,
    # selectinload,
    ONETOMANY,
    MANYTOMANY,
)
from sqlmodel import inspect
from typing import Union, Optional, List, Dict, Callable, Literal, Type
from pydantic import create_model
from pydantic.generics import GenericModel
from .inflector import pluralizer
from .uuid import UUID
from .schemas import (
    RelationshipConfig,
    CruddyGenericModel,
    MetaObject,
    CruddyModel,
    ExampleUpdate,
    ExampleCreate,
    ExampleView,
    Example,
)
from .controller import ControllerCongifurator
from .repository import AbstractRepository
from .adapters import BaseAdapter, SqliteAdapter, MysqlAdapter, PostgresqlAdapter


# -------------------------------------------------------------------------------------------
# APPLICATION RESOURCE
# -------------------------------------------------------------------------------------------
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
        id_type: Union[Type[int], Type[UUID]] = int,
        adapter: Union[
            BaseAdapter, SqliteAdapter, MysqlAdapter, PostgresqlAdapter, None
        ] = None,
        adapter_type: Literal["mysql", "postgresql"] = "postgresql",
        db_mode: Literal["memory", "file"] = "memory",
        db_path: Union[str, None] = None,
        connection_uri="",
        pool_size=4,
        max_overflow=64,
        link_prefix="",
        path: str = None,
        tags: List[str] = None,
        resource_create_model: CruddyModel = ExampleCreate,
        resource_update_model: CruddyModel = ExampleUpdate,
        resource_model: CruddyModel = Example,
        response_schema: CruddyModel = ExampleView,
        response_meta_schema: CruddyGenericModel = MetaObject,
        protected_relationships: List[str] = [],
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

        if None != adapter:
            self.adapter = adapter
        elif None != db_path:
            self.adapter = SqliteAdapter(db_path=db_path, mode=db_mode)
        elif adapter_type == "postgresql":
            self.adapter = PostgresqlAdapter(connection_uri, pool_size, max_overflow)
        elif adapter_type == "mysql":
            self.adapter = MysqlAdapter(connection_uri, pool_size, max_overflow)

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
