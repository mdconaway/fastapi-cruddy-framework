### Resource

The `Resource` class is the fundamental building block of fastapi-cruddy-framework. Your resource instances define the union of your models, resource "controller" (which is a fastapi router with baked-in CRUD logic), business policies, repository abstraction layer, any resource lifecycle hook, and database adapter. Fortunately for you, the user, everything is essentially ready-to-go out of the box.

Like [sails-ember-rest](https://github.com/mdconaway/sails-ember-rest) or [Ruby on Rails](https://rubyonrails.org/), you can now focus all of your development time on creating reusable policies (which contain your business logic that lies just above your CRUD endpoints), defining your models, and extending your resource controllers to add one-off actions like "login" or "change password".

Lifecycle actions allow you to alter query configurations or record data before or after it is persisted to a database, or perform some other task before replying to the user. All of your resources should be loaded by the [router factory](/concepts/router.md) to ensure that relationships and routes are resolved in the correct order. Don't forget, <b>only plug the master router into your application in the fastapi `startup` hook!</b>

<b>Resource Nuances:</b>

- Defining your policies is done at definition time!
- Lifecycle actions occur immediately before and after any database interaction your CRUD controllers make
- Lifecycle actions passed into the Resource constructor to interact with your queries or data <b>MUST</b> be `async` functions.
- Policies are run in the exact order in which they are included in the `list` sent to the resource definition.
- `policies_universal` apply to ALL CRUD routes, and always run <i>BEFORE</i> action specific policy chains.
- Action specific policies run <i>AFTER</i> all `policies_universal` have resolved successfully.
- Each endpoint is protected by `policies_universal` + `policies_<action>`.
- One-to-Many and Many-to-Many sub-routes (like /users/{id}/posts) will be protected by the policy chain: `user.policies_universal` + `user.policies_get_one` + `posts.policies_get_many`. Security, security, security!
- Blocking user REST modification of certain relationships via the default CRUD controller is also done at definition time!
- `protected_relationships`, `protected_create_relationships` and `protected_update_relationships` are `list[str]` types with each string indicating a one-to-many, many-to-one, or many-to-many relationship that should not be allowed to create or update via the default CRUD actions. (protected_relationships alone blocks BOTH)
- You should define your application-wide adapter elsewhere and pass it into the resource instance.
- Resources cannot span different databases.

<b>Available Policy Chain Definitions:</b>

- `policies_universal`
- `policies_create`
- `policies_update`
- `policies_delete`
- `policies_get_one`
- `policies_get_many`

<b>Available ASYNC Repository Level Lifecycle Hooks:</b>

- `lifecycle_before_create`
- `lifecycle_after_create`
- `lifecycle_before_update`
- `lifecycle_after_update`
- `lifecycle_before_delete`
- `lifecycle_after_delete`
- `lifecycle_before_get_one`
- `lifecycle_after_get_one`
- `lifecycle_before_get_all`
- `lifecycle_after_get_all`
- `lifecycle_before_set_relations`
- `lifecycle_after_set_relations`

<b>Available ASYNC Controller Level Lifecycle Hooks:</b>

- `lifecycle_before_controller_create`
- `lifecycle_after_controller_create`
- `lifecycle_before_controller_update`
- `lifecycle_after_controller_update`
- `lifecycle_before_controller_delete`
- `lifecycle_after_controller_delete`
- `lifecycle_before_controller_get_one`
- `lifecycle_after_controller_get_one`
- `lifecycle_before_controller_get_all`
- `lifecycle_after_controller_get_all`

<b>Available Relationship Blocks:</b>

- `protected_relationships`
- `protected_create_relationships`
- `protected_update_relationships`

<b>Updating Relationships:</b>

- You can update relationships via either CREATE or UPDATE actions against each base resource!

As you will discover, your resource's create and update models will automatically gain "shadow" properties where one-to-many and many-to-many relationships exist. These properties expect a client to send a list of IDs that specify the foreign records that relate to the target record. So - if a user is a member of many groups, and a group can have many users, you could update the users in a group by sending a property `"users": [1,2,3,4,5]` within the `group` payload object you send to the `POST /groups` or `PATCH /groups` routes/actions. It will all be clear when you look at the SWAGGER docs generated for your API.

<b>Repository Lifecycle hooks</b>

The following lifecycle hook methods, which can be defined in user-space code, receive the following information from fastapi-cruddy-framework:

`lifecycle_before_create` - Record without an ID. Values altered on this record in the lifecycle hook will be persisted to the DB.

`lifecycle_after_create` - Record with an ID, as returned from the database.

`lifecycle_before_update` - A key-values dictionary to be applied to the database, and the primary key id of the record which will be updated. Values altered in the dictionary will be applied to the DB update.

`lifecycle_after_update` - Record with an ID, as returned from the database

`lifecycle_before_delete` - Record with an ID, as returned from the database.

`lifecycle_after_delete` - Record with an ID, as returned from the database. This record no longer exists in the database.

`lifecycle_before_get_one` - A primary key value that will be used to fetch the record from the database, and a secondary where filter if one was used.

`lifecycle_after_get_one` - Record with an ID, as returned from the database.

`lifecycle_before_get_all` - Recieves a query configuration object. Any user-space modifications to this object will impact the query made by fastapi-cruddy-framework. This method is also invoked when a foreign Resource queries a relationship that affects the Resource where you plug in this hook.

`lifecycle_after_get_all` - Receives a BulkDTO object, containing the database objects retrieved by a get_all query, as well as the query metadata. This method is also invoked when a foreign Resource queries a relationship that affects the Resource where you plug in this hook.

`lifecycle_before_set_relations` - Receives a relationship configuration object which containts information about the record id affected, the relationship being altered, and the new list of relations for this relationship type.

```
{
    "id": id, # The database id whos relationship are about to be altered (of your defined PK type)
    "relation": relation, # The relationship that is about to change (string)
    "relations": relations # An array of foreign ids, or record dictionaries that will now define this relationship (Framework will attempt to discard old relations)
}
```

`lifecycle_after_set_relations` - Receives a completed mapping of the affected relational change, which can be used to echo changes to other databases or services.

```
{
    "model": model, # The CruddyModel affected by this relationship change
    "relation_conf": relation_conf, # The configuration object from lifecycle_before_set_relations
    "relation_type": MANYTOMANY, # An SQL Alchemy relationship-type identifier (MANYTOMANY or ONETOMANY)
    "related_table": foreign_table, # The table that ultimately represents the far-side of this relationship (not the join table!)
    "related_field": field_name, # The field on the related_table that represents the far side of the relationship
    "updated_db_count": result # The number of records now in the database associated with this relationship. If the number is different than the length of relation_conf.relations, you probably have a non-nullable field on the far-side of this relationship.
}
```

<b>Controller Lifecycle hooks</b>

The following lifecycle hook methods, which can be defined in user-space code, receive the following information from fastapi-cruddy-framework:

`lifecycle_before_controller_create` - request (a FastAPI Request), context (A mutable action context dictionary)

`lifecycle_after_controller_create` - request (a FastAPI Request), context (A mutable action context dictionary)

`lifecycle_before_controller_update` - request (a FastAPI Request), context (A mutable action context dictionary)

`lifecycle_after_controller_update` - request (a FastAPI Request), context (A mutable action context dictionary)

`lifecycle_before_controller_delete` - request (a FastAPI Request), context (A mutable action context dictionary)

`lifecycle_after_controller_delete` - request (a FastAPI Request), context (A mutable action context dictionary)

`lifecycle_before_controller_get_one` - request (a FastAPI Request), context (A mutable action context dictionary)

`lifecycle_after_controller_get_one` - request (a FastAPI Request), context (A mutable action context dictionary)

`lifecycle_before_controller_get_all` - request (a FastAPI Request), context (A mutable action context dictionary)

`lifecycle_after_controller_get_all` - request (a FastAPI Request), context (A mutable action context dictionary)

Resource Definition Options (And Defaults!):

```python
id_type: Type[int] | Type[UUID] = int,
# You SHOULD pass in 'adapter'
adapter: BaseAdapter | SqliteAdapter | MysqlAdapter | PostgresqlAdapter | None = None,
# The following adapter specific options will probably get removed. You don't need to pass them in.
# They exist solely in the event you are defining disparate resources and want the resources to
# automatically build their own adapters. This is probably not a great idea.
adapter_type: Literal["mysql", "postgresql"] = "postgresql",
db_mode: Literal["memory", "file"] = "memory",
db_path: str | None = None,
connection_uri="",
pool_size=4,
max_overflow=64,
# link_prefix will be applied at the beginning of each relationship link on each record.
# This can help with things like sub-domains, or CORS with your API, and will allow you
# to point your relationships endpoints at a complete URL. You could pass in something like
# https://api.mydomain.com, which would make a relationship link look like
# https://api.mydomain.com/resource/{id}/relationship
link_prefix="",
# Path specifies where this resource resides within the API. This is generated for you by
# default. Only change if you know what you are doing. Ember.js would expect a resource path
# to be the pluralized name of its base model. So a 'user' resource should be accessible at
# '/users', and all of its sub-routes and actions are nested under that route.
path: str = None,
# The "tags" list corresponds with the fastapi "tags" list. You can alter this if needed.
# It is defined for you initially as the singular name of your resource model. User -> 'user'
tags: list[str] = None,
# The next four options are mandatory. 'create_model' specifies the inner schema that is
# allowed to be sent to the create endpoint by a user. It will be auto-wrapped in a REST
# envelope schema. 'update_model ' specifies the inner schema that is allowed to be sent
# to the update endpoint by a user. It too will be auto-wrappted in a REST envelope schema.
# 'resource_model' is your base model, which includes all possible fields of your model and
# has table=True specified. 'response_schema' defines the fields of your model to return
# to the client during all CRUD transactions. 'response_schema' will be wrapped in REST
# envelope in both single and many responses. Only 'resource_model' should have a table!!
# All of your models should descend from CruddyModel, which is a simple SQLModel class.
resource_create_model: CruddyModel = ExampleCreate,
resource_update_model: CruddyModel = ExampleUpdate,
resource_model: CruddyModel = Example,
response_schema: CruddyModel = ExampleView,
# 'response_meta_schema' allows you to remap the "meta" values returned to the client for
# any paginated routes. You shouldn't NEED to change this, but you can if you want.
response_meta_schema: CruddyGenericModel = MetaObject,
# 'protected_relationships' will ban-hammer relationship fields specified from gaining
# an auto-magic create or update property. This will prevent users from creating or updating
# these relationships via the default CRUD actions. You will need to build other business logic
# to manage creating or changing protected relationships elsewhere in your application.
# Protected relationships will still be viewable at their designated GET routes.
# 'protected_create_relationships' and 'protected_update_relationships' only prevent embedded
# relational changes at the CREATE and UPDATE routes, respectively.
protected_relationships: list[str] = [],
protected_create_relationships: list[str] = [],
protected_update_relationships: list[str] = [],
# 'artificial_relationship_paths' will add an arbitrary list of sub-paths to each CRUD object's
# relationship "links" attribute. For example, adding "artificial_relationship_paths": ["fake"]
# would cause each object's "links" attribute to contain a key-value pair of:
# "fake": "<link_prefix>/<model>/{id}/fake"
# within its links object. This can be used to create arbitrarily complicated controller GET
# actions (that can handle nested or complex relationships) and then have those actions
# successfully mapped into the RestAdapter compliant links specification for each object instance.
artificial_relationship_paths: list[str] = [],
# The following options allow you to pass in your Sails.js-like policy chains, which will
# run before all of your endpoints (in the case of universal), or in front of only specific
# endpoints that match the action specified. These policies can be used for nearly any purpose,
# from triggering other APIs and services, protecting endpoints to ensure only the correct
# users can alter data, or to intercept and even modify data before it gets to a default CRUD
# action! (Like hashing a user's password based on the plain-text password they send to register)
policies_universal: Sequence[Callable] = [],
policies_create: Sequence[Callable] = [],
policies_update: Sequence[Callable] = [],
policies_delete: Sequence[Callable] = [],
policies_get_one: Sequence[Callable] = [],
policies_get_many: Sequence[Callable] = [],
# The disable_<endpoint> options allow app developers to simply abort automatic generation of select
# CRUD endpoints on the resource's controller. For instance, to make a write-once collection a
# developercould set disable_update to True, which would cause the resource to abort building a route
# for PATCH resource/{id}. Be aware of the overall impact of endpoints you totally disable!
disable_create: bool = False,
disable_update: bool = False,
disable_delete: bool = False,
disable_get_one: bool = False,
disable_get_many: bool = False,
# The disable_nested_objects flag prevents users from sending dictionaries inside of relationship arrays
# which the server will automatically unpack by default into an attempted create or update of the related
# resource. Any nested objects sent will still flow through the entire policy chain of the target resource!
# Any dictionary send with a primary key field will be handled as if it is an update. To create a new
# object via an embedded relationship, send the nested object without a primary key set!
disable_nested_objects: bool = False,
# Default limit will only set a limit on incoming queries if the user DOES NOT specify one. You should
# implement POLICIES to enforce a MAX limit, as you will ultimately have to re-use any max limit
# policies in your own custom controller functions for consistency. Max limit policies can be implemented
# by overriding any limit query parameter sent by the user with a maximum number if the user value is
# above whatever the max limit should be.
default_limit: int = 10,
# 'controller_extension' is the mount point for user-defined actions to-be-added to this resource's
# controller/router. Pass in your class definition and it will be instantiated at the appropriate
# time! See "CruddyController" example below!
controller_extension: CruddyController = None,
# The following REPOSITORY lifecycle hooks can each recieve an async function which will be invoked
# before or after the target lifecycle event. Generally, whatever values are passed to the lifecycle
# hook are alterable WITHIN the hook so that userspace code can alter the behavior of the lifecycle
# based on app level concerns. This allows apps to do things like: hash a user password, force certain
# relationships to always exist, force "many" queries to obey sensible limits, commit log entries,
# send messages to queues for processing based on CRUD events, or generally handle unforseen
# circumstances.
lifecycle_before_create: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_after_create: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_before_update: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_after_update: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_before_delete: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_after_delete: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_before_get_one: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_after_get_one: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_before_get_all: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_after_get_all: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_before_set_relations: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_after_set_relations: Callable[..., Coroutine[Any, Any, Any]] | None = None,
# The following CONTROLLER lifecycle hooks can each recieve an async function which will be invoked
# before or after the target lifecycle event. Generally, whatever values are passed to the lifecycle
# hook are alterable WITHIN the hook so that userspace code can alter the behavior of the lifecycle
# based on app level concerns. CONTROLLER lifecycles hooks will also receive the REQUEST context,
# allowing the hook to take actions that consider the user and their priveleges, while still
# interleaving that logic within the cruddy action.
lifecycle_before_controller_create: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_after_controller_create: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_before_controller_update: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_after_controller_update: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_before_controller_delete: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_after_controller_delete: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_before_controller_get_one: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_after_controller_get_one: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_before_controller_get_all: Callable[..., Coroutine[Any, Any, Any]] | None = None,
lifecycle_after_controller_get_all: Callable[..., Coroutine[Any, Any, Any]] | None = None,
```

Below is an example for creating a `user` resource. The best way to organize your app would be to place the definition for your user resource in a folder like `my_app/resources/user.py`, where the name of your application is `my_app`. As you saw earlier in the description for `CreateRouterFromResources` you would then load this user resource file by simply specifying `application_module=my_app` and `resource_path="resources"`. Your `fastapi-cruddy-framework` project would then auto-magically load your resource file(s), create dynamic routes to create, read, update, and delete this resource, and further create sub-routes within this resource to browse, query and update all of the relationships for your resource.

Example:

```python
from fastapi_cruddy_framework import Resource, UUID
from my_app.adapters import sqlite
from my_app.models.user import (
    User,
    UserCreate,
    UserUpdate,
    UserView,
)
from my_app.schemas.response import MetaObject
from my_app.policies.verify_session import verify_session
from my_app.policies.hash_user_password import (
    hash_user_password,
)


resource = Resource(
    id_type=UUID,
    adapter=sqlite,
    resource_update_model=UserUpdate,
    resource_create_model=UserCreate,
    resource_model=User,
    response_schema=UserView,
    response_meta_schema=MetaObject,
    protected_relationships=["posts"],
    policies_universal=[verify_session],
    policies_create=[hash_user_password]
)

# fin!
```

Easy, right?

<p align="right">(<a href="#readme-top">back to top</a>)</p>
