# -----------------------------------------------------------------
# This is a rails-like library. You're welcome Python community.
# Love,
# A Sails / Ember lover.
# -----------------------------------------------------------------
from pydantic.types import AwareDatetime
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
    CruddyIntIDModel,
    CruddyUUIDModel,
    ExampleUpdate,
    ExampleCreate,
    ExampleView,
    Example,
    uuid4,
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
    coerce_to_utc_datetime,
)
from .test_helpers import BrowserTestClient
from async_asgi_testclient import TestClient
from async_asgi_testclient.websocket import WebSocketSession

# -----------------------------------------------------------------
