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

<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[product-screenshot]: https://raw.githubusercontent.com/mdconaway/fastapi-cruddy-framework/master/screenshot.png