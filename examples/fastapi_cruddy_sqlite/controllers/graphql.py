from fastapi_cruddy_framework import GraphQLController
from examples.fastapi_cruddy_sqlite.models.query import Query
from examples.fastapi_cruddy_sqlite.policies.verify_session import verify_session

graphql_controller = GraphQLController(
    dependencies=[verify_session],
    root_query=Query,
)
