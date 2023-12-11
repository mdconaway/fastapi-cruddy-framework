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
    T,
    RelationshipConfig,
    CruddyGenericModel,
    BulkDTO,
    MetaObject,
    PageResponse,
    ResponseSchema,
    CruddyModel,
    CruddyCreatedUpdatedSignature,
    CruddyCreatedUpdatedMixin,
    CruddyIntIDModel,
    CruddyUUIDModel,
    ExampleUpdate,
    ExampleCreate,
    ExampleView,
    Example,
    uuid7,
    UUID,
)
from .controller import Actions, CruddyController, ControllerConfigurator
from .repository import AbstractRepository
from .adapters import BaseAdapter, SqliteAdapter, MysqlAdapter, PostgresqlAdapter
from .resource import Resource, ResourceRegistry, CruddyResourceRegistry
from .router import getModuleDir, getDirectoryModules, CreateRouterFromResources
from .util import (
    get_pk,
    possible_id_types,
    lifecycle_types,
    build_tz_aware_date,
    parse_datetime,
    coerce_to_utc_datetime,
    parse_and_coerce_to_utc_datetime,
    validate_utc_datetime,
)
from .test_helpers import BrowserTestClient
from async_asgi_testclient import TestClient
from async_asgi_testclient.websocket import WebSocketSession

# -----------------------------------------------------------------
