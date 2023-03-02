<a name="readme-top"></a>

<!-- PROJECT LOGO -->
<div align="center">
  <h2 align="center">FastAPI - Cruddy Framework</h2>
  <a href="https://github.com/mdconaway/fastapi-cruddy-framework">
    <img src="https://raw.githubusercontent.com/mdconaway/fastapi-cruddy-framework/master/logo.png" alt="Logo" width="768" height="406">
  </a>
  <br/>
</div>

<!-- ABOUT THE PROJECT -->
## About Cruddy Framework

[![Product Name Screen Shot][product-screenshot]](https://github.com/mdconaway/fastapi-cruddy-framework)

Cruddy Framework is a companion library to FastAPI designed to bring the development productivity of Ruby on Rails, Ember.js or Sails.js to the FastAPI ecosystem. Many of the design patterns base themselves on Sails.js "policies," sails-ember-rest automatic CRUD routing, and Ember.js REST-Adapter feature sets. By default, data sent to and from the auto-magic CRUD routes are expected to conform to the Ember.js Rest Envelope / Linked-data specification. This specification is highly readable for front-end developers, allows for an expressive over-the-wire query syntax, and embeds self-describing relationship URL links in each over-the-wire record to help data stores automatically generate requests to fetch or update related records. This library is still in an alpha/beta phase, so use at your own risk. All CRUD actions and relationship types are currently supported, though there may be unexpected bugs. Please report any bugs under "issues."


TODO: All the documentation. See the examples folder for a quick reference of high level setup. It currently contains a fully functional fastapi server which uses fastapi-cruddy-framework and the sqlite adapter. It even shows how to override incoming post data to do things like hash a user's password during initial registration using a simple drop-in policy function.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ABOUT THE PROJECT -->
## Installation

The fastapi-cruddy-framework module can be installed using poetry...

```
poetry add fastapi-cruddy-framework
```

Or pip.

```
pip install fastapi-cruddy-framework
```

After that, you can import and use all of the classes outlined below.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CLASSES -->
## Cruddy Exports/Imports

Cruddy-framework provides users the following classes and helper functions to scaffold out a project. (For recommended project structure, see the "examples" folder in the Github repo)

```python
# MASTER ROUTER GENERATOR
CreateRouterFromResources
# RESOURCE AND REGISTRY
Resource
ResourceRegistry
CruddyResourceRegistry
# CONTROLLER HELPERS
ControllerCongifurator
# REPOSITORY
AbstractRepository
# DATABASE ADAPTERS
BaseAdapter
SqliteAdapter
MysqlAdapter
PostgresqlAdapter
# TYPES / MODELS / SCHEMAS
T
UUID
RelationshipConfig
CruddyGenericModel
BulkDTO,
MetaObject
PageResponse
ResponseSchema
CruddyModel
CruddyIntIDModel
CruddyUUIDModel
ExampleUpdate
ExampleCreate
ExampleView
Example
# MODULE LOADER HELPERS
getModuleDir
getDirectoryModules
# HELPERS
pluralizer
uuid6
uuid7
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### CreateRouterFromResources

This instance factory creates and returns a fully-wired fastapi `APIRouter` which sub-routes all `Resource` instances created in your project. Theoretically, you can create and mount multiple routers this way, but each router needs to be provided all of the `Resource` instances required to fully resolve the relationships it may care about. The recommended way to structure your project is to keep all resources required for a route set contained within a single folder. This factory is then provided the relative path to a resource set folder, starting with your applications `main` module, and will return the fully interconnected route set while also instantiating all of your resource modules. Typically, it is a good idea to import all of your router instances in your main module, as they will need to be "connected" to your fastapi server <i>WITHIN</i> the `startup` hook. This is critical, as the resource registry (discussed below) cannot fully resolve relationships until after SQLAlchemy is aware of all models. This occurs in-between launching your main module and the `startup` hook.

Example
```python
import my_app
from fastapi_cruddy_framework import CreateRouterFromResources
from fastapi import FastAPI, APIRouter


my_router: APIRouter = CreateRouterFromResources(
    # (REQUIRED) application_module is of "ModuleType" type, and should be a pointer to your main app module
    application_module=my_app, 
    # (OPTIONAL) resource_path is of "str" type, and should specify a relative path from application_module
    # to the location of your "resources" that will be auto-loaded and bundled under this router
    # tree.
    resource_path="resources",
    # (OPTIONAL) common_resource_name is of "str" type, and should describe the common export value in each
    # resource file where the router factory can find your "Resource" instances. Use this if you want to name
    # all of your resource objects something other than "resource"
    common_resource_name="resource"
)

app = FastAPI(title="My App", version="1")

@app.on_event("startup")
async def bootstrap():
  app.include_router(my_router)

# fin!
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[product-screenshot]: https://raw.githubusercontent.com/mdconaway/fastapi-cruddy-framework/master/screenshot.png