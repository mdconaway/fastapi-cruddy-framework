### CruddyController

The `CruddyController` is a base class with a single method `setup` that applications can leverage to "extend" the default CRUD route controllers as needed. This class is needed to control application flow during the resolution boot cycle, and to allow you to share methods between resources like a mixin. Controllers should generally be placed within a project folder named "controllers". Controller classes can be imported in your resource file, and passed to the resource at definition time. Don't worry, the `Resource` class will create a controller instance for you!

Example `my_app/controllers/User.py`:

```python
from fastapi import Depends
from fastapi_cruddy_framework import CruddyController, CruddyGenericModel
from my_app.policies.verify_session import verify_session

class HelloSchema(CruddyGenericModel):
    hello: str = "world"

class UserController(CruddyController):
    def setup(self):
        # You can extend controller actions here!
        # You can also access:
        # self.actions
        # self.resource
        # self.repository
        # self.adapter
        # self.controller
        @self.controller.get(
            "/hello", response_model=HelloSchema, dependencies=[Depends(verify_session)]
        )
        async def hello():
            return HelloSchema(hello="world")
```

Example Continued `my_app/resources/User.py`:

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
from my_app.controllers.user import UserController
from my_app.policies.verify_session import verify_session
from my_app.policies.hash_user_password import (
    hash_user_password,
)


resource = Resource(
    adapter=sqlite,
    response_schema=UserView,
    response_meta_schema=MetaObject,
    resource_update_model=UserUpdate,
    resource_create_model=UserCreate,
    resource_model=User,
    protected_relationships=["posts"],
    id_type=UUID,
    policies_universal=[verify_session],
    policies_create=[hash_user_password],
    controller_extension=UserController
)
```

Notice that you don't need to instantiate your controller!

`CruddyController` extension classes passed to the `Resource` definition will be `setup()` <i>BEFORE</i> the auto-generated CRUD routes but <i>AFTER</i> SQL Alchemy has resolved model relationships. This ensures that your user-defined routes receive priority for incoming HTTP requests. If extension classes were not loaded first, then the CRUD handlers would almost always intercept the incoming request first.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
