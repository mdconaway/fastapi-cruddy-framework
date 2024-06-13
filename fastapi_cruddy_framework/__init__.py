# -----------------------------------------------------------------
# This is a rails-like library. You're welcome Python community.
# Love,
# A Sails / Ember lover.
# -----------------------------------------------------------------
from validator_collection import (
    checkers as field_checkers,
    validators as field_validators,
    errors as field_errors,
)
from .inflector import pluralizer
from .schemas import (
    BROADCAST_EVENT,
    CONTROL_EVENT,
    ROOM_EVENT,
    CLIENT_EVENT,
    KILL_SOCKET_BY_ID,
    KILL_SOCKET_BY_CLIENT,
    KILL_ROOM_BY_ID,
    JOIN_SOCKET_BY_ID,
    JOIN_SOCKET_BY_CLIENT,
    LEAVE_SOCKET_BY_ID,
    LEAVE_SOCKET_BY_CLIENT,
    CLIENT_MESSAGE_EVENT,
    DISCONNECT_EVENT,
    T,
    CruddyGQLDateTime,
    CruddyGQLObject,
    CruddyGQLArray,
    RelationshipConfig,
    CruddyGenericModel,
    BulkDTO,
    MetaObject,
    PageResponse,
    ResponseSchema,
    CruddyModel,
    CruddyCreatedUpdatedSignature,
    CruddyCreatedUpdatedGQLOverrides,
    CruddyCreatedUpdatedMixin,
    CruddyGQLOverrides,
    CruddyIntIDModel,
    CruddyUUIDModel,
    CruddyStringIDModel,
    ExampleUpdate,
    ExampleCreate,
    ExampleView,
    Example,
    SocketMessage,
    SocketRoomConfiguration,
    uuid7,
    UUID,
)
from .pubsub import PubSub
from .websocket_manager import WebsocketConnectionManager
from .controller import Actions, CruddyController, ControllerConfigurator
from .repository import AbstractRepository
from .adapters import (
    BaseAdapter,
    SqliteAdapter,
    MysqlAdapter,
    PostgresqlAdapter,
    RedisAdapter,
)
from .graphql import (
    GraphQLController,
    GraphQLRequestCache,
    GraphQLResolverService,
    create_module_resolver,
    graphql_where_synthesizer,
    generate_gql_loader_and_type,
    GQL_WHERE_REPLACEMENT_CHARACTER,
)
from .resource import Resource, ResourceRegistry, CruddyResourceRegistry
from .router import getModuleDir, getDirectoryModules, CreateRouterFromResources
from .util import (
    possible_id_types,
    lifecycle_types,
    get_pk,
    build_tz_aware_date,
    parse_datetime,
    coerce_to_utc_datetime,
    parse_and_coerce_to_utc_datetime,
    validate_utc_datetime,
    json_serial,
    to_json_string,
    to_json_object,
    get_state,
    set_state,
    dependency_list,
)
from .security import CruddyHTTPBearer
from .test_helpers import BrowserTestClient
from async_asgi_testclient import TestClient
from async_asgi_testclient.websocket import WebSocketSession

# -----------------------------------------------------------------
