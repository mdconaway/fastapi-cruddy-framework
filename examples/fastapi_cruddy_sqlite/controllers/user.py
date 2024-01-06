from pydantic.types import Json
from fastapi_cruddy_framework import CruddyController
from fastapi import Query, Request, Response, Path, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi_cruddy_framework import CruddyController
from examples.fastapi_cruddy_sqlite.policies.verify_session import verify_session
from examples.fastapi_cruddy_sqlite.policies.naive_auth import naive_auth
from examples.fastapi_cruddy_sqlite.utils.dependency_list import dependency_list
from examples.fastapi_cruddy_sqlite.config.general import general


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
        single_schema = self.resource.schemas["single"]
        many_schema = self.resource.schemas["many"]

        @self.controller.get(
            "/authorization",
            description="Authorizes a client, returning a cookie to establish a sesssion as well as the session object",
            response_model=dict,
            dependencies=dependency_list(verify_session, naive_auth),
        )
        async def get_authorization(request: Request):
            return JSONResponse(content=request.session)

        @self.controller.delete(
            "/authorization",
            description="Terminates a client session by clearing user attributes in session storage",
            response_model=dict,
            dependencies=dependency_list(verify_session),
        )
        async def delete_authorization(request: Request) -> Response:
            request.session.clear()
            return JSONResponse(content=request.session)

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

        # THIS ROUTE BINDING IS ONLY HERE FOR FRAMEWORK TESTS!!! You DON'T need to do this unless you ALSO want an alternate path to the overridden action!!
        self.controller.delete(
            "/purge/{id}",
            description=f"An overriden method to delete a user",
            response_model=single_schema,
            response_model_exclude_none=True,
            dependencies=dependency_list(verify_session),
        )(self.actions.delete)

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
            limit: int = general.DEFAULT_LIMIT,
            columns: list[str] = Query(None, alias="columns"),
            sort: list[str] = Query(None, alias="sort"),
            where: Json = Query(None, alias="where"),
        ):
            # You can do any pre-action logic required here, like persisting a file!
            return await self.actions.get_all(
                page=page, limit=limit, columns=columns, sort=sort, where=where
            )

        @self.controller.get(
            "/{id}/others",
            description="A fake relationship to everyone but self",
            response_model=many_schema,
            response_model_exclude_none=True,
            dependencies=dependency_list(verify_session),
        )
        async def get_fake_relationship(
            id: id_type = Path(..., alias="id"),
            page: int = 1,
            limit: int = general.DEFAULT_LIMIT,
            columns: list[str] = Query(None, alias="columns"),
            sort: list[str] = Query(None, alias="sort"),
            where: Json = Query(None, alias="where"),
        ):
            if where is None:
                where = []
            if isinstance(where, dict) and len(where) > 0:
                new_where_query = [where]
            elif isinstance(where, list):
                new_where_query = where
            else:
                new_where_query = []
            new_where_query.append({"id": {"*neq": str(id)}})
            # You can do any pre-action logic required here, like persisting a file!
            return await self.actions.get_all(
                page=page,
                limit=limit,
                columns=columns,
                sort=sort,
                where=new_where_query,
            )
