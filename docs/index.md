<style>
.md-content .md-typeset h1 { display: none; }
</style>

## FASTAPI - Cruddy Framework

<p align="center">
  <a href="https://github.com/mdconaway/fastapi-cruddy-framework">
    <img src="https://raw.githubusercontent.com/mdconaway/fastapi-cruddy-framework/master/logo.png" alt="Logo">
  </a>
  <br/>
</p>

<p align="center">
    <em>There's the right way, the wrong way, and the Cruddy way... which is just the right way, but FASTER.</em>
</p>

<p align="center">
<a href="https://github.com/mdconaway/fastapi-cruddy-framework/actions?query=workflow%3ATest" target="_blank">
    <img src="https://github.com/mdconaway/fastapi-cruddy-framework/workflows/Test/badge.svg" alt="Test">
</a>
<a href="https://github.com/mdconaway/fastapi-cruddy-framework/actions?query=workflow%3APublish" target="_blank">
    <img src="https://github.com/mdconaway/fastapi-cruddy-framework/workflows/Publish/badge.svg" alt="Publish">
</a>
<a href="https://coverage-badge.samuelcolvin.workers.dev/redirect/mdconaway/fastapi-cruddy-framework" target="_blank">
    <img src="https://coverage-badge.samuelcolvin.workers.dev/mdconaway/fastapi-cruddy-framework.svg" alt="Coverage">
<a href="https://pypi.org/project/fastapi-cruddy-framework" target="_blank">
    <img src="https://img.shields.io/pypi/v/fastapi-cruddy-framework?color=%2334D058&label=pypi%20package" alt="Package version">
</a>
</p>

---

**Documentation**: <a href="" target="_blank">TODO: HOST DOCS HERE</a>

**Source Code**: <a href="https://github.com/mdconaway/fastapi-cruddy-framework" target="_blank">https://github.com/mdconaway/fastapi-cruddy-framework</a>

---

`fastapi-cruddy-framework` is a companion library to [FastAPI](https://fastapi.tiangolo.com/) designed to bring the development productivity of [Ruby on Rails](https://rubyonrails.org/), [Ember.js](https://emberjs.com/) or [Sails.js](https://sailsjs.com/) to the [FastAPI](https://fastapi.tiangolo.com/) ecosystem. Many of the design patterns base themselves on [Sails.js](https://sailsjs.com/) "policies," [Sails.js](https://sailsjs.com/) model lifecycle events, [sails-ember-rest](https://github.com/mdconaway/sails-ember-rest) automatic CRUD routing, and [Ember.js](https://emberjs.com/) [REST-Adapter](https://api.emberjs.com/ember-data/release/classes/RESTAdapter) feature sets.

The key features are:

- **Feels Familiar**: Brings all the best design patterns from [Ruby on Rails](https://rubyonrails.org/), [Ember.js](https://emberjs.com/) and [Sails.js](https://sailsjs.com/) to the [FastAPI](https://fastapi.tiangolo.com/) ecosystem.
- **Convention Over Configuration**: By creating a resource, your service immediately receives automatic CRUD routing, entry points to apply logic to every route request via policies, and request/response modeling.
- **Async First**: Cruddy will leverage the event loop whenever possible to keep things snappy.
- **Standardized**: By default, data sent to and from the auto-magic CRUD routes are expected to conform to the [Ember.js](https://emberjs.com/) Rest Envelope and Linked-data relationship specification.
- **Built on FastAPI Favorites**: In addition to leveraging the [FastAPI](https://fastapi.tiangolo.com/) framework itself, Cruddy depends on (SQLModel)[https://sqlmodel.tiangolo.com/], (SQLAlchemy)[https://www.sqlalchemy.org/], and (Pydantic)[https://docs.pydantic.dev/latest/] so you can continue using the dependencies you're probably already using

## FastAPI, SQLModel, Pydantic and SQL Alchemy Compatibility

`fastapi-cruddy-framework` was originally developed against FastAPI &lt;= 0.99.1, sqlmodel &lt;= 0.0.12, pydantic &lt; 2.0.0, and sqlalchemy &lt; 2.0.0. However, beginning with `fastapi-cruddy-framework` version 1.x.x+, all major dependencies have been shifted forward to target FastAPI 0.100.0+, sqlmodel 0.0.14+, pydantic 2.0.0+, and sqlalchemy 2.0.0+. Therefore, when using this library, please note the following library compatibility chart:

### `fastapi-cruddy-framework@0.x.x`

- FastAPI &lt;= 0.99.1
- SQLModel &lt;= 0.0.12
- pydantic &lt; 2.0.0
- sqlalchemy &lt; 2.0.0

### `fastapi-cruddy-framework@1.x.x`

- FastAPI &gt;= 0.100.0
- SQLModel &gt;= 0.0.14
- pydantic &gt;= 2.0.0
- sqlalchemy &gt;= 2.0.0

Moving between `fastapi-cruddy-framework` versions? See the [migration guides](https://github.com/mdconaway/fastapi-cruddy-framework/blob/master/migrating_versions.md).

## Installation

<div class="termy">

```console
$ poetry add fastapi-cruddy-framework
• Installing fastapi-cruddy-framework (1.1.0)

Writing lock file
```

</div>
