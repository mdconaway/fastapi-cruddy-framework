from typing import Any, Awaitable, Sequence, Type
from typing_extensions import Annotated
from collections.abc import Callable
from enum import Enum
from json import dumps, loads
from sys import modules
from logging import getLogger
from urllib.parse import urlparse, parse_qs
from asyncio import Future
from posixpath import join
from fastapi import status, APIRouter, Request
from fastapi.responses import PlainTextResponse
from strawberry import Schema, ID, field as strawberry_field, lazy as strawberry_lazy
from strawberry.extensions import QueryDepthLimiter
from strawberry.fastapi import GraphQLRouter
from strawberry.printer import print_schema
from strawberry.scalars import JSON
from strawberry.schema.config import StrawberryConfig
from strawberry.types import Info
from .inflector import pluralizer
from .schemas import UUID
from .test_helpers import BrowserTestClient, TestClient
from .util import dependency_list, filter_headers

logger = getLogger(__name__)
GQL_WHERE_REPLACEMENT_CHARACTER = "__"
HTTP_200_OK = status.HTTP_200_OK
HTTP_404_NOT_FOUND = status.HTTP_404_NOT_FOUND


def create_module_resolver(module_name: str, class_name: str):
    def resolver():
        if module_name in modules:
            return getattr(modules[module_name], class_name)
        return None

    return resolver


def generate_gql_loader_and_type(type: Any, module_path: str):
    class_loader = create_module_resolver(module_path, type)
    list_type = list[Annotated[type, strawberry_lazy(module_path)]]
    return class_loader, list_type


# convert all key-leading double underscores __ to the * character
# convert all remaning double underscores __ to the . character
def graphql_where_synthesizer(where: dict | list[dict]):
    if not isinstance(where, (dict, list)):
        return where

    if isinstance(where, list):
        return [graphql_where_synthesizer(x) for x in where]

    new_level = {}
    for key, value in where.items():
        str_key = str(key)
        next_level = (
            graphql_where_synthesizer(value)
            if isinstance(value, (dict, list))
            else value
        )
        new_key = str_key
        # replace leading __ with *
        if str_key.startswith(GQL_WHERE_REPLACEMENT_CHARACTER):
            new_key = str_key.replace(GQL_WHERE_REPLACEMENT_CHARACTER, "*", 1)
        # replace remaining __ with .
        new_key = new_key.replace(GQL_WHERE_REPLACEMENT_CHARACTER, ".")
        new_level[new_key] = next_level
    return new_level


class GraphQLRequestCache:
    def __init__(self) -> None:
        self.__internal_state: dict[str, Future] = {}
        self.__identity_cache: dict[type, dict[str, list[Any]]] = {}

    def _lookup_identity_for(self, class_type: type, identity_key: str | None):
        if identity_key is None or self.__identity_cache.get(class_type, None) is None:
            return None
        return self.__identity_cache[class_type].get(identity_key, None)

    def _store_identities(self, class_type: type, objects: list[Any]):
        if self.__identity_cache.get(class_type, None) is None:
            self.__identity_cache[class_type] = {}
        for obj in objects:
            # Need to figure out how to identify PK different than ID here...
            self.__identity_cache[class_type][getattr(obj, "id")] = obj

    async def get_resolved(
        self,
        from_record: type | None,
        cache_path: str,
        class_loader: Callable,
        try_identity_key: str | None,
        async_resolver_fn: Callable[[], Awaitable[Any]],
    ):
        class_type = class_loader()
        if try_identity_key is not None and from_record is not None:
            if (
                record := self._lookup_identity_for(
                    class_type=class_type,
                    identity_key=getattr(from_record, try_identity_key, None),
                )
            ) is not None:
                logger.debug("CACHE HIT: %s", cache_path)
                return [record]
        if (result := self.__internal_state.get(cache_path, None)) is not None:
            logger.debug("CACHE HIT: %s", cache_path)
            return await result
        future = Future()
        self.__internal_state[cache_path] = future
        try:
            logger.debug("CACHE MISS: %s", cache_path)
            result = await async_resolver_fn()
            listified_result = result if isinstance(result, list) else [result]
            self._store_identities(class_type=class_type, objects=listified_result)
            future.set_result(listified_result)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(e)
            future.set_exception(e)

        return await future


class GraphQLResolverService:
    header_blacklist: list[str] | None

    def __init__(self, header_blacklist: list[str] | None = None):
        self.header_blacklist = header_blacklist

    def get_virtual_client(self, info: Info):
        request_object: Request = info.context["request"]
        return BrowserTestClient(TestClient(request_object.app, use_cookies=False))

    def _extract_forwardable_information(self, info: Info) -> dict[str, Any]:
        request_object: Request = info.context["request"]
        headers = filter_headers(
            header_dict=dict(request_object.headers.items()),
            blacklist=self.header_blacklist,
        )
        return {"headers": headers}

    def _generate_internal_route(self, name: str, id: UUID | None):
        return f"/{name}" if id is None else f"/{name}/{id}"

    def _generate_query_params(
        self,
        where: Any | None = None,
        limit: int | None = None,
        page: int | None = None,
        sort: list[str] | None = None,
    ):
        query = []
        if where:
            query.append(f"where={dumps(where)}")
        if limit:
            query.append(f"limit={limit}")
        if page:
            query.append(f"page={page}")
        if sort:
            for item in sort:
                query.append(f"sort={item}")
        query_string = "&".join(query)
        return f"?{query_string}" if len(query_string) > 0 else ""

    def _format_context(
        self,
        type_name: str,
        route_generator: Callable | None = None,
        valid_selectors: dict[str, Callable] | None = None,
        graphql_resolver_name_override: str | None = None,
    ):
        plural_type_name = pluralizer.plural(type_name)  # type: ignore
        graphql_resolver_type = (
            plural_type_name
            if graphql_resolver_name_override is None
            else pluralizer.plural(graphql_resolver_name_override)  # type: ignore
        )
        if route_generator is None:

            def default_route(_):
                return plural_type_name

            route_generator = default_route

        if valid_selectors is None:
            valid_selectors = {}

        if "default" not in valid_selectors:
            valid_selectors["default"] = route_generator

        return (
            plural_type_name,
            graphql_resolver_type,
            valid_selectors,
        )

    def _format_and_merge_wheres(
        self, internal_where: list[str] | None, where: JSON | None
    ):
        synth_where = where
        if internal_where is not None:
            parsed_internal_where = loads(internal_where.pop())
            if where is None:
                synth_where = parsed_internal_where
            else:
                synth_where = {
                    "__and": [
                        parsed_internal_where,
                        where,
                    ]
                }

        send_where = (
            graphql_where_synthesizer(synth_where)
            if isinstance(synth_where, (dict, list))
            else synth_where
        )
        return send_where

    def _setup_cache_mapper(  # pylint: disable=too-many-arguments
        self,
        record: Any,
        info: Info,
        valid_selectors: dict[str, Callable],
        selector: str | None,
        id: ID | None,
        where: JSON | None,
        page: int | None,
        sort: list[str] | None,
        limit: int | None,
        try_identity_key: str | None,
    ):
        cache = info.context["cache"]
        if not isinstance(cache, GraphQLRequestCache):
            raise RuntimeError(
                "GraphQLRequestCache was not initialized properly in get_context"
            )
        if selector is None:
            selector = "default"
        if selector not in valid_selectors:
            raise ValueError(
                f"selector must be one of: [{','.join(valid_selectors.keys())}]"
            )
        execution_route_generator = valid_selectors[selector]
        parse_result = urlparse(str(execution_route_generator(record)))
        router_path = parse_result.path
        query = parse_qs(parse_result.query)
        send_where = self._format_and_merge_wheres(
            internal_where=query.get("where", None), where=where
        )
        if (actual_id := id) is not None:
            actual_id = UUID(hex=str(id))
        internal_route = self._generate_internal_route(name=router_path, id=actual_id)
        mapper_path = f"{internal_route}{self._generate_query_params(where=send_where, limit=limit,page=page, sort=sort)}"
        attempt_identity_key = (
            try_identity_key
            if (
                (not where)
                and (not page)
                and (not sort)
                and (not limit)
                and (selector == "default")
            )
            else None
        )
        return (cache, mapper_path, attempt_identity_key)

    def _create_dynamic_resolver(
        self,
        info: Info,
        local_client: BrowserTestClient,
        mapper_path: str,
        type_name: str,
        plural_type_name: str,
        is_singular: bool,
        id: ID | None,
        class_loader: Callable = lambda _: type,
    ):
        async def resolve_it():
            type_class = class_loader()
            forward = self._extract_forwardable_information(info)
            http_response = await local_client.get(
                mapper_path,
                **forward,
            )
            if http_response.status_code not in [HTTP_200_OK, HTTP_404_NOT_FOUND]:
                raise RuntimeError(
                    f"internal API path {mapper_path} responded with error code {http_response.status_code}"
                )
            if http_response.status_code == HTTP_404_NOT_FOUND:
                return []
            virtual_response = http_response.json()
            item_list: list = (
                [virtual_response[type_name]]
                if is_singular or id is not None
                else virtual_response[plural_type_name]
            )
            return [type_class(**item) for item in item_list]

        return resolve_it

    def generate_resolver(
        self,
        type_name: str,
        graphql_type: type = type,
        route_generator: Callable | None = None,
        valid_selectors: dict[str, Callable] | None = None,
        graphql_resolver_name_override: str | None = None,
        is_singular: bool = False,
        class_loader: Callable = lambda _: type,
        try_identity_key: str | None = None,
    ):
        uber_self = self
        (
            plural_type_name,
            graphql_resolver_type,
            valid_selectors,
        ) = self._format_context(
            type_name=type_name,
            route_generator=route_generator,
            valid_selectors=valid_selectors,
            graphql_resolver_name_override=graphql_resolver_name_override,
        )

        async def resolver(
            self,  # you can use self to reference the "record"
            info: Info,
            id: ID | None = None,
            where: JSON | None = None,
            limit: int | None = None,
            page: int | None = None,
            sort: list[str] | None = None,
            selector: str | None = None,
        ):
            cache, mapper_path, attempt_identity_key = uber_self._setup_cache_mapper(
                record=self,
                info=info,
                valid_selectors=valid_selectors,
                selector=selector,
                id=id,
                where=where,
                page=page,
                sort=sort,
                limit=limit,
                try_identity_key=try_identity_key,
            )

            return await cache.get_resolved(
                from_record=self,
                cache_path=mapper_path,
                class_loader=class_loader,
                try_identity_key=attempt_identity_key,
                async_resolver_fn=uber_self._create_dynamic_resolver(
                    info=info,
                    class_loader=class_loader,
                    id=id,
                    type_name=type_name,
                    plural_type_name=plural_type_name,
                    is_singular=is_singular,
                    mapper_path=mapper_path,
                    local_client=uber_self.get_virtual_client(info),
                ),
            )

        # THE RESOLVER NAME IS WHAT DETERMINES THE "KEY" IN THE GRAPHQL QUERY SCHEMA!!!
        return strawberry_field(
            resolver=resolver, name=graphql_resolver_type, graphql_type=graphql_type
        )


def context_getter():
    return {"cache": GraphQLRequestCache()}


class GraphQLController:
    controller: APIRouter
    graphql_controller: GraphQLRouter
    _root_query: Type
    _internal_schema: Schema
    _max_results: int
    _max_depth: int
    _path: str
    _auto_camel_case: bool

    def __init__(
        self,
        dependencies: Sequence[Callable],
        root_query: Type,
        max_results: int = 500,
        max_depth: int = 3,
        tags: list[str | Enum] | None = None,
        path: str = "/graphql",
        expose_schema: bool = True,
        auto_camel_case: bool = False,
        context_getter: Callable = context_getter,
    ):
        tags = ["graphql"] if tags is None else tags
        self.controller = APIRouter(
            prefix="",
            tags=tags,
            dependencies=dependency_list(*dependencies),
        )
        self._root_query = root_query
        self._max_results = max_results
        self._max_depth = max_depth
        self._path = path
        self._auto_camel_case = auto_camel_case
        self.graphql_controller = GraphQLRouter(
            self.__get_schema(),
            context_getter=context_getter,
            path=join("/", path),
        )
        self.controller.include_router(self.graphql_controller)
        if expose_schema:
            self.__setup_schema_printer()

    def __setup_schema_printer(self):
        @self.controller.get(
            join("/", self._path, "schema"), response_class=PlainTextResponse
        )
        async def get_schema() -> str:
            return print_schema(self.__get_schema())

    def __get_schema(self):
        if hasattr(self, "_internal_schema"):
            return self._internal_schema

        self._internal_schema = Schema(
            self._root_query,
            config=StrawberryConfig(
                auto_camel_case=self._auto_camel_case,
                relay_max_results=self._max_results,
            ),
            extensions=[
                QueryDepthLimiter(max_depth=self._max_depth),
            ],
        )

        return self._internal_schema

    @property
    def router(self):
        return self.controller
