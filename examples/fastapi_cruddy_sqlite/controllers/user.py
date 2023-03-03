from fastapi import Depends
from fastapi_cruddy_framework import CruddyController, CruddyGenericModel
from examples.fastapi_cruddy_sqlite.policies.verify_session import verify_session


class HelloSchema(CruddyGenericModel):
    hello: str = "world"


class UserController(CruddyController):
    def setup(self):
        # You can extend controller actions here!
        # You can also access:
        # self.resource
        # self.repository
        # self.adapter
        # self.controller
        @self.controller.get(
            "/hello", response_model=HelloSchema, dependencies=[Depends(verify_session)]
        )
        async def hello():
            return HelloSchema(hello="world")
