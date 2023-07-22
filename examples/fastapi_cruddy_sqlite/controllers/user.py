from fastapi_cruddy_framework import CruddyController
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi_cruddy_framework import CruddyController
from examples.fastapi_cruddy_sqlite.policies.verify_session import verify_session
from examples.fastapi_cruddy_sqlite.policies.naive_auth import auth_user_session
from examples.fastapi_cruddy_sqlite.utils.dependency_list import dependency_list


class UserController(CruddyController):
    def setup(self):
        # You can extend controller actions here!
        # You can also access:
        # self.resource
        # self.repository
        # self.adapter
        # self.controller

        @self.controller.get(
            "/authorization",
            description="Authorizes a client, returning a cookie to establish a sesssion as well as the session object",
            response_model=dict,
            dependencies=dependency_list(verify_session, auth_user_session),
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
