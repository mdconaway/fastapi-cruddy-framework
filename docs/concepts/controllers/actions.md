### Actions

The `Actions` class contains all the business logic for the <i>base</i> CRUD actions that are wired into a controller's route tree based on the framework options used. Each resource / controller will generate its own unique CRUD actions instance, and make this object available to user-space `CruddyController` instance, which are described in more detail [here](/concepts/controllers). Actions that are deferred from routing automatically (using option flags such as `disable_create`) are still generated for each resource's actions map, which makes those functions available in the `CruddyController` setup function.

Available actions:

```python
async def create(data: create_model)

async def update(id: id_type = Path(..., alias="id"), *, data: update_model)

async def delete(
    id: id_type = Path(..., alias="id"),
)

async def get_by_id(
    id: id_type = Path(..., alias="id"),
    where: Json = Query(None, alias="where"),
)

async def get_all(
    page: int = 1,
    limit: int = 10,
    columns: list[str] = Query(None, alias="columns"),
    sort: list[str] = Query(None, alias="sort"),
    where: Json = Query(None, alias="where"),
)
```

You can re-use CRUD actions in your controllers as follows:

```python
from pydantic.types import Json
from fastapi_cruddy_framework import CruddyController
from fastapi import Query, Path, HTTPException, status
from fastapi_cruddy_framework import CruddyController, dependency_list
from examples.fastapi_cruddy_sqlite.policies.verify_session import verify_session


class UserController(CruddyController):
    def setup(self):
        # You can extend controller actions here!
        # You can also access:
        # self.actions
        # self.resource
        # self.repository
        # self.adapter
        # self.controller
        id_type = self.resource._id_type
        many_schema = self.resource.schemas["many"]

        # You can tap into the controller's CRUD actions map in the following ways:
        # 1. Override the action key
        old_delete = self.actions.delete

        async def new_delete(id: id_type = Path(..., alias="id"), confirm: str = "N"):
            if confirm == "Y":
                return await old_delete(id=id)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You must confirm you want to delete this record by setting the 'confirm' parameter to 'Y'",
                )

        self.actions.delete = new_delete

        # 2. Provide a new route to an existing function (notice, no @ symbol!)
        self.controller.get(
            "/all",
            description="Another way to get many users",
            response_model=many_schema,
            response_model_exclude_none=True,
            dependencies=dependency_list(verify_session),
        )(self.actions.get_all)

        # 3. Re-use within your own function
        @self.controller.get(
            "/everything",
            description="Yet another way to get many users",
            response_model=many_schema,
            response_model_exclude_none=True,
            dependencies=dependency_list(verify_session),
        )
        async def get_all_again(
            page: int = 1,
            limit: int = 10,
            columns: list[str] = Query(None, alias="columns"),
            sort: list[str] = Query(None, alias="sort"),
            where: Json = Query(None, alias="where"),
        ):
            return await self.actions.get_all(
                page=page, limit=limit, columns=columns, sort=sort, where=where
            )

```

<p align="right">(<a href="#readme-top">back to top</a>)</p>
