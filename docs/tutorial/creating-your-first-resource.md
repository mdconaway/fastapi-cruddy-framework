# Creating Your First Resource

The `Resource` class is the fundamental building block of fastapi-cruddy-framework. Your resource instances define the union of your models, resource "controller" (which is a FastAPI router with baked-in CRUD logic), business policies, repository abstraction layer, any resource lifecycle hook, and database adapter.

Implementing resources is the first step towards Cruddy-ifying your service so let's go!

## Setup

Currently, *Cruddy* does not provide a CLI for scaffolding the application structure... but it will. Until then, let's perform these actions manually.

### Break apart the main.py

As you may recall, our application currently has a single file:

```Python title="fastapi_cruddy_demo/main.py"
--8<-- "docs_src/tutorial/hello_world.py"
```

---

But let's break that apart into two files to better separate concerns and prepare for growth:

```Python title="fastapi_cruddy_demo/main.py"
--8<-- "docs_src/tutorial/main1a.py"
```

Specifically, we've moved our router initialization to a new file called `application.py` nested under the `router/` directory.

```Python hl_lines="9-11" title="fastapi_cruddy_demo/router/application.py"
--8<-- "docs_src/tutorial/application_router1.py"
```

We've also replaced that tired old 'Hello World' route with a big person health check.

```Python hl_lines="14-17" title="fastapi_cruddy_demo/router/application.py"
--8<-- "docs_src/tutorial/application_router1.py"

```
!!! Note
    If you bring up your service now, it will not be healthy as we haven't implemented our datastore yet.

So far, so good right? If you're familiar with FastAPI there shouldn't be any surprises yet.

### Create an Adapter

An adapter can be loosely described as a shared interface to an external resource or service. With regard to a `Resource`, we need to define a database adapter. For this, *Cruddy* provides three options: `MysqlAdapter`, `PostgresAdapter`, and `SqliteAdapter`. Additionally, a `RedisAdapter` is provided for websocket support and `BaseAdapter` is available for creating your own SQLAlchemy backed adapter (we know you're out there Oracle users)

For ease of use and setup, we're going to use an in-memory SQLite instance for now. You can create the following adapter file like so:

```Python title="fastapi_cruddy_demo/adapters/sqlite.py"
--8<-- "docs_src/tutorial/sqlite_in-memory_adapter.py"

```

### Create a Model

Now that we have a way for the pending resource to communicate with the datastore, we need to model the data. Additionally we need to define the interfaces used to CREATE, UPDATE, and READ the data. At the end of the day, these models are just SQLModel and Pydantic so, if you have experience with these libraries, they should look very familiar.

To add more context with the way the CRUD Router works, it needs an update, create, and base model. If you always structure model files in this order, you can extend from the minimal number of attrs that can be updated, all the way up to the maximal attrs in the base model. CRUD JSON serialization schemas are also exposed for modification, and it makes sense to keep your response schemas defined in the same location as the view model used to represent records to the client.

Let's create a new file in a new directory to hold this configuration:

```Python title="fastapi_cruddy_demo/models/post.py"
--8<-- "docs_src/tutorial/post_model1.py"

```

There's a lot going on here so let's step through it starting with the import statement from `fastapi_cruddy_framework`.

```Python hl_lines="3-10" title="fastapi_cruddy_demo/models/post.py"
--8<-- "docs_src/tutorial/post_model1.py"

```

*Cruddy* provides base classes to wrap SQLModel and Pydantic functionality to help standardize your models. Additionally, mixins and validation helpers are provided to further reduce model repetitive configuration.

* `CruddyModel` names your model's table the name of the model itself, so in this case our SQLite table would be called `Post`
* `CruddyUUIDModel` extends `CruddyModel` to define a primary key in the database of type `UUID`
* `CruddyCreatedUpdatedMixin` adds `created_at` and `updated_at` fields coerced to UTC and defaulted to 'now' when a record is created / updated respectively (useful for table models)
* `CruddyCreatedUpdatedSignature` extends `CruddyModel` with fields `created_at` and `updated_at` of type `datetime` (useful for View-related interfaces)
* `validate_utc_datetime` unsurprisingly validates `datetime` fields

---

```Python hl_lines="15-22" title="fastapi_cruddy_demo/models/post.py"
--8<-- "docs_src/tutorial/post_model1.py"

```

To aide with the automated documentation generation, we create an example record at the top of the file to reference and a helper, `schema_example`, to wrap each field value.

---

```Python hl_lines="25-47" title="fastapi_cruddy_demo/models/post.py"
--8<-- "docs_src/tutorial/post_model1.py"

```

The "Update" model variant describes all fields that can be affected by a
client's PATCH action. Generally, the update model should have the fewest
number of available fields for a client to manipulate.

All field definitions on this model can be referenced in SQLModel's documentation.

---

```Python hl_lines="50-51" title="fastapi_cruddy_demo/models/post.py"
--8<-- "docs_src/tutorial/post_model1.py"

```

The "Create" model variant expands on the update model, above, and adds
any new fields that may be writeable only the first time a record is
generated. This allows the POST action to accept update-able fields, as
well as one-time writeable fields.

Specifically in this example, we're not adding any additional fields so the information that can be updated and also be initialized.

---

```Python hl_lines="54-64" title="fastapi_cruddy_demo/models/post.py"
--8<-- "docs_src/tutorial/post_model1.py"

```

The "View" model describes all fields that should typically be present
in any JSON responses to the client. This should, at a minimum, include
the identity field for the model, as well as any server-side fields that
are important but tamper resistant, such as created_at or updated_at
fields. This should be used when defining single responses and paged
responses. To support column clipping, all fields need to be optional.

---

```Python hl_lines="67-68" title="fastapi_cruddy_demo/models/post.py"
--8<-- "docs_src/tutorial/post_model1.py"

```

The "Base" model describes the actual table as it should be reflected in
the datastore. It is generally unsafe to use this model in actions, or
in JSON representations, as it may contain hidden fields like passwords
or other server-internal state or tracking information. Keep your "Base"
models separated from all other interactive derivations.

Take note that our model is really slim here thanks to a mixture of *Cruddy*'s provided helpers and reused fields from our previous model definitions.

---

That concludes your first model file, congrats! Now that we have a way to communicate with our database (adapter) and a way to structure our data (model) we can *finally* create our first resource.

### Create a Resource

Our last step is to create a new file in a new directory to define a *Cruddy* `Resource` for a `Post`:

```Python title="fastapi_cruddy_demo/resources/post.py"
--8<-- "docs_src/tutorial/post_resource1.py"

```

Notice that we're providing the adapter and models we've just defined so *Cruddy* knows how to generate the CRUD endpoints for this resource. Additionally, to aide in API generation, we've provided the primary key type `UUID` and a `default_limit` for record pagination.

### Initialize the DB

Ideally in production you will use a library like [Alembic](https://alembic.sqlalchemy.org/en/latest/index.html) to manage your database migrations. For now, we're going to leverage a helper function on the SQLite adapter to setup a clean database for us each time the service spins up.

```Python hl_lines="9" title="fastapi_cruddy_demo/main.py"
--8<-- "docs_src/tutorial/main1b.py"
```

## Result

If you're still following along, your effort will now be rewarded. If you haven't already, run ```poetry run fastapi dev fastapi_cruddy_demo/main.py``` and open your browser at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs){: .external-link target='_blank'}.

You should see generated routes for:

* `POST /posts` - Create a Post
* `GET /posts` - Find Posts
* `PATCH /posts/{id}` - Update a Post
* `DELETE /posts/{id}` - Delete a Post
* `GET /posts/{id}` - Get a Post

Try out the the `Create` endpoint. You should see the sample record defined in your Post model file just dying to be created!
