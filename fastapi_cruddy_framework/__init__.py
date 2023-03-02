# This is a rails-like library. You're welcome Python community.
# Love,
# A Sails / Ember lover.
# -----------------------------------------------------------------
from .inflector import pluralizer
from .uuid import UUID, uuid7
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
)
from .controller import ControllerCongifurator
from .repository import AbstractRepository
from .adapters import BaseAdapter, SqliteAdapter, MysqlAdapter, PostgresqlAdapter
from .resource import Resource, ResourceRegistry, CruddyResourceRegistry
from .router import getModuleDir, getDirectoryModules, CreateRouterFromResources

# -----------------------------------------------------------------
