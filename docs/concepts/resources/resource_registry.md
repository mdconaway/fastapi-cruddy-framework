### ResourceRegistry

The `ResourceRegistry` class should be invisible to the average user. There are no input parameters when creating a registry, and by default Cruddy defines its own library-internal registry. The registry exists to perform the following functions:

- Maintain a map of all resources available to `fastapi-cruddy-framework`
- Trigger `resolve` for all resources after SQL Alchemy finishes computing the relationship properties on each SQLModel.
- Plugin to the `Resource` class, so that each `Resource` you define can automatically call `ResourceRegistry.register()` when you define it. This is all "under the hood".

### CruddyResourceRegistry

The `CruddyResourceRegistry` is a framework-created instance of the `ResourceRegistry` class, exposed as an export so that application builders can acquire framework component instance references dynamically. It manages all of the resources and other subordinate components the active Cruddy framework is aware of.

This framework internal registry instance is extremely helpful for looking up resource, controller, and model classes and instances <i>without</i> causing a litany of circular import issues in app code. Due to the asynchronous nature of how cruddy framework must initialize, application developers should use the `CruddyResourceRegistry` to "lookup" objects in any app code that needs to use a fully functional framework instance.

What's a good example of where this is useful? Acquiring a resource's repository instance from within a policy so you can run database checks <i>before</i> a CRUD action occurs. There are many other applicable scenarios. See example, below.

```python
# This is an example policy file that could live in your project at policies/load_user_into_session.py
from fastapi import Request
from fastapi_cruddy_framework import AbstractRepository, CruddyResourceRegistry, BulkDTO

async def load_user_into_session(request: Request):
    some_value = "that identifies a user"
    user_repository: AbstractRepository = CruddyResourceRegistry.get_repository_by_name(model_name="User")
    repo_dto: BulkDTO = await user_repository.get_all(limit=1, where={"some_field": some_value})
    if len(repo_dto.data) == 0:
        raise Exception("User not found!")
    request.session.update({"user": repo_dto.data.pop()})
```

The available registry lookup function signatures are:

- `get_model_by_name(model_name: str) -> CruddyModel | None]`
- `get_relationships_by_name(model_name: str) -> dict | None`
- `get_resource_by_name(model_name: str) -> Resource | None`
- `get_repository_by_name(model_name: str) -> AbstractRepository | None`
- `get_controller_by_name(model_name: str) -> APIRouter | None`
- `get_controller_extension_by_name(model_name: str) -> CruddyController | None`

Make sure that the `model_name` string you pass to the registry EXACTLY mirrors the class name for your base table `CruddyModel`. So for a model with a class of `User` you would pass in `model_name="User"`. Pay attention to the capitalization!

<p align="right">(<a href="#readme-top">back to top</a>)</p>
