# pyright: reportShadowedImports=false
import asyncio
import re
from typing import Any, Sequence, TypedDict, Callable, Literal, Type
from fastapi import APIRouter
from sqlalchemy.orm import (
    RelationshipProperty,
    RelationshipDirection,
    ONETOMANY,
    MANYTOMANY,
)
from sqlmodel import Field, inspect
from enum import Enum
from pydantic import create_model
from pydantic_core import PydanticUndefinedType
from .inflector import pluralizer
from .schemas import (
    RelationshipConfig,
    CruddyGenericModel,
    MetaObject,
    CruddyModel,
    ExampleUpdate,
    ExampleCreate,
    ExampleView,
    Example,
    UUID,
    uuid7,
)
from .controller import (
    Actions,
    CruddyController,
    ControllerConfigurator,
    META_FAILED_RECORDS_KEY,
    META_RELATION_INFO_KEY,
    META_NUM_RELATION_MODIFIED_KEY,
    META_RELATED_RECORDS_KEY,
    META_VALIDATION_MESSAGES_KEY,
)
from .repository import AbstractRepository
from .adapters import BaseAdapter, SqliteAdapter, MysqlAdapter, PostgresqlAdapter
from .util import (
    possible_id_types,
    possible_id_values,
    lifecycle_types,
    estimate_simple_example,
    squash_type,
)


class SchemaDict(TypedDict):
    single: Type[CruddyGenericModel]
    many: Type[CruddyGenericModel]
    create: Type[CruddyGenericModel]
    create_relations: Type[CruddyModel]
    update: Type[CruddyGenericModel]
    update_relations: Type[CruddyModel]


# -------------------------------------------------------------------------------------------
# APPLICATION RESOURCE
# -------------------------------------------------------------------------------------------
class Resource:
    _registry: "ResourceRegistry"
    _link_prefix: str = ""
    _relations: dict[str, RelationshipConfig] = {}
    _relational_getters: list[str] = []
    _resource_path: str = "/example"
    _tags: list[str | Enum] = ["example"]
    _create_schema: Type[CruddyModel]
    _update_schema: Type[CruddyModel]
    _response_schema: Type[CruddyModel]
    _meta_schema: Type[CruddyModel] | Type[CruddyGenericModel]
    _id_type: possible_id_types = int
    _model_name_single: str
    _model_name_plural: str
    _on_resolution: Callable | None = None
    _artificial_relationship_paths: list[str]
    _default_limit: int
    adapter: BaseAdapter | SqliteAdapter | MysqlAdapter | PostgresqlAdapter
    actions: Actions
    repository: AbstractRepository
    controller: APIRouter
    controller_extension: Type[CruddyController] | None = None
    link_identity: Callable[..., str]
    policies: dict[str, Sequence[Callable]]
    disabled_endpoints: dict[str, bool]
    disabled_relationship_getters: list[str]
    disable_nested_objects: bool
    schemas: SchemaDict
    controller_lifecycles: dict[str, lifecycle_types]

    def __init__(
        self,
        # Only id_type, adapter, resource_create_model, resource_update_model, resource_model, and response_schema are required
        id_type: Type[int] | Type[UUID] | Type[str] = int,
        adapter: (
            BaseAdapter | SqliteAdapter | MysqlAdapter | PostgresqlAdapter | None
        ) = None,
        resource_create_model: Type[CruddyModel] = ExampleCreate,
        resource_update_model: Type[CruddyModel] = ExampleUpdate,
        resource_model: Type[CruddyModel] = Example,
        response_schema: Type[CruddyModel] = ExampleView,
        # None of the following arguments are required. But they allow you to do powerful things!
        response_meta_schema: Type[CruddyModel] | Type[CruddyGenericModel] = MetaObject,
        # the adapter type only has two options because sqlite will take priority if its options are set
        adapter_type: Literal["mysql", "postgresql"] = "postgresql",
        db_mode: Literal["memory", "file"] = "memory",
        db_path: str | None = None,
        connection_uri="",
        pool_size=4,
        max_overflow=64,
        link_prefix="",
        path: str | None = None,
        tags: list[str | Enum] | None = None,
        protected_relationships: list[str] = [],
        protected_create_relationships: list[str] = [],
        protected_update_relationships: list[str] = [],
        artificial_relationship_paths: list[str] = [],
        policies_universal: Sequence[Callable] = [],
        policies_create: Sequence[Callable] = [],
        policies_update: Sequence[Callable] = [],
        policies_delete: Sequence[Callable] = [],
        policies_get_one: Sequence[Callable] = [],
        policies_get_many: Sequence[Callable] = [],
        custom_sql_identity_function: Callable[..., Any] | None = None,
        custom_link_identity: Callable[..., str] | None = None,
        disable_create: bool = False,
        disable_update: bool = False,
        disable_delete: bool = False,
        disable_get_one: bool = False,
        disable_get_many: bool = False,
        disable_relationship_getters: list[str] = [],
        disable_nested_objects: bool = False,
        default_limit: int = 10,
        use_model_defaults: bool = True,
        # Repository lifecycle actions
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
        # Controller lifecycle actions
        lifecycle_before_controller_create: lifecycle_types = None,
        lifecycle_after_controller_create: lifecycle_types = None,
        lifecycle_before_controller_update: lifecycle_types = None,
        lifecycle_after_controller_update: lifecycle_types = None,
        lifecycle_before_controller_delete: lifecycle_types = None,
        lifecycle_after_controller_delete: lifecycle_types = None,
        lifecycle_before_controller_get_one: lifecycle_types = None,
        lifecycle_after_controller_get_one: lifecycle_types = None,
        lifecycle_before_controller_get_all: lifecycle_types = None,
        lifecycle_after_controller_get_all: lifecycle_types = None,
        controller_extension: Type[CruddyController] | None = None,
    ):
        possible_tag = f"{resource_model.__name__}".lower()
        possible_path = f"/{pluralizer.plural(possible_tag)}"  # type: ignore
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
        self._relational_getters = []
        self._protected_relationships = protected_relationships
        self._protected_create_relationships = protected_create_relationships
        self._protected_update_relationships = protected_update_relationships
        self._artificial_relationship_paths = artificial_relationship_paths
        self._default_limit = default_limit

        self.link_identity = (
            custom_link_identity
            if custom_link_identity is not None
            else self._default_link_identity
        )

        self.policies = {
            "universal": policies_universal,
            "create": policies_create,
            "update": policies_update,
            "delete": policies_delete,
            "get_one": policies_get_one,
            "get_many": policies_get_many,
        }

        self.disabled_endpoints = {
            "create": disable_create,
            "update": disable_update,
            "delete": disable_delete,
            "get_one": disable_get_one,
            "get_many": disable_get_many,
        }

        self.disabled_relationship_getters = disable_relationship_getters

        self.controller_lifecycles = {
            "before_create": lifecycle_before_controller_create,
            "after_create": lifecycle_after_controller_create,
            "before_update": lifecycle_before_controller_update,
            "after_update": lifecycle_after_controller_update,
            "before_delete": lifecycle_before_controller_delete,
            "after_delete": lifecycle_after_controller_delete,
            "before_get_one": lifecycle_before_controller_get_one,
            "after_get_one": lifecycle_after_controller_get_one,
            "before_get_all": lifecycle_before_controller_get_all,
            "after_get_all": lifecycle_after_controller_get_all,
        }

        self.disable_nested_objects = disable_nested_objects

        if None != adapter:
            self.adapter = adapter  # type: ignore
        elif None != db_path:
            self.adapter = SqliteAdapter(db_path=str(db_path), mode=db_mode)
        elif adapter_type == "postgresql":
            self.adapter = PostgresqlAdapter(connection_uri, pool_size, max_overflow)
        elif adapter_type == "mysql":
            self.adapter = MysqlAdapter(connection_uri, pool_size, max_overflow)

        self.repository = AbstractRepository(
            adapter=self.adapter,  # type: ignore
            update_model=resource_update_model,
            create_model=resource_create_model,
            model=resource_model,
            view_model=response_schema,
            _resource=self,
            use_model_defaults=use_model_defaults,
            id_type=id_type,
            custom_sql_identity_function=custom_sql_identity_function,
            lifecycle_before_create=lifecycle_before_create,
            lifecycle_after_create=lifecycle_after_create,
            lifecycle_before_update=lifecycle_before_update,
            lifecycle_after_update=lifecycle_after_update,
            lifecycle_before_delete=lifecycle_before_delete,
            lifecycle_after_delete=lifecycle_after_delete,
            lifecycle_before_get_one=lifecycle_before_get_one,
            lifecycle_after_get_one=lifecycle_after_get_one,
            lifecycle_before_get_all=lifecycle_before_get_all,
            lifecycle_after_get_all=lifecycle_after_get_all,
            lifecycle_before_set_relations=lifecycle_before_set_relations,
            lifecycle_after_set_relations=lifecycle_after_set_relations,
        )

        self.controller = APIRouter(prefix=self._resource_path, tags=self._tags)

        if controller_extension != None and issubclass(
            controller_extension, CruddyController
        ):
            self.controller_extension = controller_extension

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

    def _format_example_id(self, value: Any):
        return int(str(value)) if self.repository.id_type == int else str(value)

    def _setup_example_id(self, id: str | UUID | int | bytes):
        example_id = id
        response_schema: Type[CruddyModel] = self._response_schema
        possible_id = response_schema.model_fields.get(
            self.repository.primary_key or "id", None
        )
        if possible_id is not None and issubclass(
            self.repository.id_type, possible_id.annotation  # type: ignore
        ):
            if possible_id.json_schema_extra is not None:
                possible_id_examples = possible_id.json_schema_extra.get(
                    "examples", None
                )
                if not isinstance(possible_id_examples, list):
                    possible_id_examples = []
                possible_id_example = possible_id.json_schema_extra.get("example", None)
                if possible_id_example is None and len(possible_id_examples) > 0:
                    possible_id_example = possible_id_examples[0]
                if possible_id_example is not None:
                    example_id = possible_id_example
                elif possible_id.default is not None and not isinstance(
                    possible_id.default, PydanticUndefinedType
                ):
                    example_id = possible_id.default
                elif possible_id.default_factory is not None:
                    temp_example = possible_id.default_factory()
                    if not isinstance(temp_example, PydanticUndefinedType):
                        example_id = temp_example
                possible_id.json_schema_extra.update(
                    {"example": self._format_example_id(example_id)}
                )
            else:
                possible_id.json_schema_extra = {  # type: ignore
                    "example": self._format_example_id(example_id)
                }
        return example_id

    def _setup_support_classes(self, id: Any):
        view_example_dict = {}
        link_object = {}
        false_create_attrs = {}
        false_update_attrs = {}
        response_schema: Type[CruddyModel] = self._response_schema
        create_protected_relationships = (
            self._protected_relationships + self._protected_create_relationships
        )
        update_protected_relationships = (
            self._protected_relationships + self._protected_update_relationships
        )
        for k, v in response_schema.model_fields.items():
            default_example = None
            if v.json_schema_extra is not None:
                possible_examples = v.json_schema_extra.get("examples", None)
                possible_example = v.json_schema_extra.get("example", None)
                if isinstance(possible_examples, list) and len(possible_examples) > 0:
                    default_example = possible_examples[0]
                elif possible_example is not None:
                    default_example = possible_example
            elif v.default is not None and not isinstance(
                v.default, PydanticUndefinedType
            ):
                default_example = v.default
            elif v.default_factory is not None:
                default_example = v.default_factory()
                if isinstance(default_example, PydanticUndefinedType):
                    default_example = None
            if default_example is None:
                default_example = estimate_simple_example(v.annotation)
            view_example_dict[k] = squash_type(default_example)
        view_example_dict["links"] = {}

        for k, v in self._relations.items():
            rel_def = self._derive_shadow_relationship(
                v.orm_relationship.direction, v.foreign_resource._id_type
            )
            if k not in create_protected_relationships:
                false_create_attrs[k] = rel_def
            if k not in update_protected_relationships:
                false_update_attrs[k] = rel_def
            if k in self.disabled_relationship_getters:
                continue
            self._relational_getters.append(k)
            ex_link = self._single_link(
                id=self.link_identity(view_example_dict), relationship=k
            )
            link_object[k] = (
                str,
                Field(schema_extra={"json_schema_extra": {"example": ex_link}}),
            )
            view_example_dict["links"][k] = ex_link

        for item in self._artificial_relationship_paths:
            ex_link = self._single_link(
                id=self.link_identity(view_example_dict), relationship=item
            )
            link_object[item] = (
                str,
                Field(schema_extra={"json_schema_extra": {"example": ex_link}}),
            )
            view_example_dict["links"][item] = ex_link
        link_object["__base__"] = CruddyModel

        return link_object, view_example_dict, false_create_attrs, false_update_attrs

    # The response schema factory
    # Converting this section to a plugin pattern will allow
    # other response formats, like JSON API.
    # Alterations will also require ControllerConfigurator
    # to be modified somehow...
    def generate_internal_schemas(self):
        self.repository.resolve()
        response_schema: Type[CruddyModel] = self._response_schema
        create_schema = self._create_schema
        update_schema = self._update_schema
        response_meta_schema = self._meta_schema
        resource_model_name = f"{self.repository.model.__name__}".lower()
        resource_model_plural = pluralizer.plural(resource_model_name)  # type: ignore
        resource_response_name = response_schema.__name__
        resource_create_name = create_schema.__name__
        resource_update_name = update_schema.__name__

        self._model_name_single = resource_model_name
        self._model_name_plural = resource_model_plural

        # Attempt to align swagger example uuids if possible (non-critical)
        example_id = uuid7() if self.repository.id_type == UUID else 123
        if self.repository.id_type != int:
            example_id = str(example_id)
        example_id = self._setup_example_id(example_id)

        # Create shared link model
        link_object, view_example_dict, false_create_attrs, false_update_attrs = (
            self._setup_support_classes(example_id)
        )

        LinkModel = create_model(f"{resource_model_name}Links", **link_object)
        # End shared link model

        SingleCreateSchema = create_model(
            f"{resource_create_name}Proxy", __base__=create_schema, **false_create_attrs
        )

        # Create record envelope schema
        SingleCreateEnvelope = create_model(
            f"{resource_create_name}Envelope",
            __base__=CruddyGenericModel,
            **{
                resource_model_name: (SingleCreateSchema, ...),
            },  # type: ignore
        )
        # End create record envelope schema

        SingleUpdateSchema = create_model(
            f"{resource_update_name}Proxy", __base__=update_schema, **false_update_attrs
        )

        # Update record envelope schema
        SingleUpdateEnvelope = create_model(
            f"{resource_update_name}Envelope",
            __base__=CruddyGenericModel,
            **{
                resource_model_name: (SingleUpdateSchema, ...),
            },  # type: ignore
        )
        # End update record envelope schema

        # Single record schema with embedded links
        SingleSchemaLinked = create_model(
            f"{resource_response_name}Linked",
            links=(LinkModel, None),
            __base__=response_schema,  # type: ignore
        )
        # End single record schema with embedded links

        # Single record return payload (for get/{id})
        SingleSchemaEnvelope = create_model(
            f"{resource_response_name}Envelope",
            __base__=CruddyGenericModel,
            **{
                resource_model_name: (
                    SingleSchemaLinked,
                    Field(
                        schema_extra={
                            "json_schema_extra": {"example": view_example_dict}
                        }
                    ),
                ),
                "meta": (
                    dict[str, Any] | None,
                    Field(
                        default=None,
                        schema_extra={
                            "json_schema_extra": {
                                "example": {
                                    META_RELATION_INFO_KEY: {
                                        META_NUM_RELATION_MODIFIED_KEY: 0,
                                        META_RELATED_RECORDS_KEY: {},
                                        META_FAILED_RECORDS_KEY: {},
                                        META_VALIDATION_MESSAGES_KEY: {},
                                    }
                                }
                            }
                        },
                    ),
                ),
            },  # type: ignore
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
                resource_model_plural: (
                    list[SingleSchemaLinked],
                    Field(
                        schema_extra={
                            "json_schema_extra": {"example": [view_example_dict]}
                        }
                    ),
                ),
            },  # type: ignore
            meta=(response_meta_schema, ...),
        )

        old_many_init = ManySchemaEnvelope.__init__
        local_resource = self

        def new_many_init(self, *args, **kwargs):
            old_many_init(
                self,
                *args,
                **{
                    resource_model_plural: (
                        [
                            SingleSchemaLinked(
                                **x._mapping,
                                links=local_resource._link_builder(  # type: ignore
                                    fields=x._mapping
                                ),
                            )
                            for x in kwargs["data"]
                        ]
                        if resource_model_plural not in kwargs
                        else kwargs[resource_model_plural]
                    ),
                    "data": kwargs["data"] if "data" in kwargs else [],
                    "meta": kwargs["meta"],
                },
            )

        ManySchemaEnvelope.__init__ = new_many_init
        # End many records return payload

        # Expose the following schemas for further use
        self.schemas = {  # type: ignore
            "single": SingleSchemaEnvelope,
            "many": ManySchemaEnvelope,
            "create": SingleCreateEnvelope,
            "create_relations": SingleCreateSchema,
            "update": SingleUpdateEnvelope,
            "update_relations": SingleUpdateSchema,
        }

    def _derive_shadow_relationship(
        self, direction: RelationshipDirection, id_type: Any
    ):
        return (
            (
                list[id_type | dict] | None,
                None,
            )
            if direction in [MANYTOMANY, ONETOMANY]
            else (
                dict | id_type | None,
                None,
            )
        )

    def _default_link_identity(self, fields: dict[str, Any]):
        if self.repository.primary_key is None:
            raise RuntimeError("Resource was not properly initialized!")
        id = fields[self.repository.primary_key]
        if (self.repository.id_type == UUID and type(id) == str) and not "-" in id:
            id = re.sub(r"(\S{8})(\S{4})(\S{4})(\S{4})(.*)", r"\1-\2-\3-\4-\5", id)
        return id

    def _link_builder(
        self, fields: dict[str, Any]
    ):  # id: possible_id_values, fields: dict[str, Any]):
        # During "many" lookups, and depending on DB type, the id value return is a mapping
        # from the DB, so the id value is not properly "dasherized" into UUID format. This
        # REGEX fixes the issue without adding the CPU overhead of transforming each row
        # into a record instance.
        id = self.link_identity(fields)
        new_link_object = {}
        for k in self._relational_getters:
            new_link_object[k] = self._single_link(id=id, relationship=k)
        for item in self._artificial_relationship_paths:
            new_link_object[item] = self._single_link(id=id, relationship=item)
        return new_link_object

    def _single_link(self, id: possible_id_values = "", relationship: str = ""):
        return f"{self._link_prefix}{self._resource_path}/{id}/{relationship}"

    def _create_schema_arg_handler(self, single_schema_linked, resource_model_name):
        def data_destructure(data):
            if data == None:
                return {}
            elif hasattr(data, "_mapping"):
                return data._mapping
            if hasattr(data, "model_dump") and callable(data.model_dump):
                return data.model_dump()
            return data

        def handle_data_or_none(args: dict | None):
            if args == None:
                return {"data": None}

            key_count = len(args.items())

            if key_count == 0:
                return {"data": None}

            meta = args.get("meta", None)

            if resource_model_name in args:
                return {
                    resource_model_name: args[resource_model_name],
                    "meta": meta,
                    "data": None,
                }

            if key_count == 1 and args["data"] == None:
                return {"data": None, "meta": meta}

            thing_to_convert = data_destructure(args["data"])
            # id = thing_to_convert[self.repository.primary_key]
            return {
                resource_model_name: single_schema_linked(
                    **thing_to_convert,
                    links=self._link_builder(fields=thing_to_convert),  # id=id,
                ),
                "meta": meta,
                "data": None,
            }

        return handle_data_or_none

    def resolve(self):
        self.actions = Actions(
            id_type=self._id_type,
            disable_nested_objects=self.disable_nested_objects,
            single_name=self._model_name_single,
            repository=self.repository,
            create_model=self.schemas["create"],
            create_model_proxy=self._create_schema,
            update_model=self.schemas["update"],
            update_model_proxy=self._update_schema,
            single_schema=self.schemas["single"],
            many_schema=self.schemas["many"],
            meta_schema=self._meta_schema,
            relations=self._relations,
            default_limit=self._default_limit,
            lifecycle=self.controller_lifecycles,
        )

        if self.controller_extension != None and issubclass(
            self.controller_extension, CruddyController
        ):
            self.controller_extension(
                actions=self.actions,
                controller=self.controller,
                repository=self.repository,
                resource=self,
                adapter=self.adapter,
            )

        ControllerConfigurator(
            id_type=self._id_type,
            single_name=self._model_name_single,
            plural_name=self._model_name_plural,
            controller=self.controller,
            repository=self.repository,
            actions=self.actions,
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
            disable_create=self.disabled_endpoints["create"],
            disable_update=self.disabled_endpoints["update"],
            disable_delete=self.disabled_endpoints["delete"],
            disable_get_one=self.disabled_endpoints["get_one"],
            disable_get_many=self.disabled_endpoints["get_many"],
            disable_relationship_getters=self.disabled_relationship_getters,
        )

        if callable(self._on_resolution):
            self._on_resolution()

    @staticmethod
    def _set_registry(reg: "ResourceRegistry"):
        Resource._registry = reg

    @staticmethod
    def _set_link_prefix(prefix: str):
        Resource._link_prefix = prefix


# This needs a lot of work...
class ResourceRegistry:
    _resolver_invoked: bool = False
    _resolver_completed: bool = False
    _resources: list[Resource] = []
    _base_models: dict[str, Type[CruddyModel]] = {}
    _rels_via_models: dict[str, dict] = {}
    _resources_via_models: dict[str, Resource] = {}

    def __init__(self):
        self._resolver_invoked = False
        self._resolver_completed = False
        self._resources = []
        self._base_models = {}
        self._rels_via_models = {}
        self._resources_via_models = {}

    # Returns a CruddyModel tracked by Class name by the registry
    def get_model_by_name(self, model_name: str) -> Type[CruddyModel]:
        model = self._base_models.get(model_name, None)
        if model is None:
            raise RuntimeError(
                f"Model {model_name} was not loaded in the Cruddy registry"
            )
        return model

    # Returns a dictionary configuration of all relationships identified for a model's Class name
    def get_relationships_by_name(self, model_name: str) -> dict:
        rels = self._rels_via_models.get(model_name, None)
        if rels is None:
            raise RuntimeError(
                f"Relationships for model {model_name} were not loaded in the Cruddy registry"
            )
        return rels

    # Returns a fully-wired resource instance tracked by its core model's Class name
    def get_resource_by_name(self, model_name: str) -> Resource:
        resource = self._resources_via_models.get(model_name, None)
        if resource is None:
            raise RuntimeError(
                f"Resource for {model_name} was not loaded in the Cruddy registry"
            )
        return resource

    # Returns a fully-configured repository instance tracked by its core model's Class name
    def get_repository_by_name(self, model_name: str) -> AbstractRepository:
        resource = self.get_resource_by_name(model_name=model_name)
        return resource.repository

    # Returns a FastAPI APIRouter instance tracked by its core model's Class name
    def get_controller_by_name(self, model_name: str) -> APIRouter:
        resource = self.get_resource_by_name(model_name=model_name)
        return resource.controller

    # Returns a CruddyController class tracked by its core model's Class name
    def get_controller_extension_by_name(
        self, model_name: str
    ) -> Type[CruddyController]:
        resource = self.get_resource_by_name(model_name=model_name)
        if resource.controller_extension is None:
            raise RuntimeError(
                f"Controller extension class for {model_name} was not loaded in the Cruddy registry (Did you pass one to your resource?)"
            )
        return resource.controller_extension

    # This method needs to build all the lists and dictionaries
    # needed to efficiently search between models to conduct relational
    # joins and controller expansion. Is invoked by each resource as it
    # is created.
    def register(self, res: Resource):
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

            # This loop will inject relationships into all resources that need them
            for relation in relationships:
                rel_map[relation.key] = relation
                # this seems unsafe...
                target_resource_name = relation.entity.class_.__name__
                target_resource = self._resources_via_models[target_resource_name]
                resource.inject_relationship(
                    relationship=relation, foreign_resource=target_resource
                )

            self._rels_via_models[map_name] = rel_map
            # generating schemas will also cause the repository classes to resolve (needed for primary key determination)
            resource.generate_internal_schemas()

        # Build routes
        # These have to be separated to ensure all schemas are ready from generate_internal_schemas()
        for resource in self._resources:
            resource.resolve()

        self._resolver_completed = True
        # Clear this debouncer so any future dynamic resources can try to resolve
        self._resolver_invoked = False

    def is_ready(self):
        return self._resolver_completed


CruddyResourceRegistry = ResourceRegistry()

Resource._set_registry(reg=CruddyResourceRegistry)
