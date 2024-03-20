from strawberry import type as strawberry_type
from examples.fastapi_cruddy_sqlite.services.graphql_resolver import graphql_resolver
from examples.fastapi_cruddy_sqlite.models.common.graphql import (
    GROUP_LIST_TYPE,
    GROUP_CLASS_LOADER,
    POST_LIST_TYPE,
    POST_CLASS_LOADER,
    SECTION_LIST_TYPE,
    SECTION_CLASS_LOADER,
    USER_LIST_TYPE,
    USER_CLASS_LOADER,
)


@strawberry_type
class Query:
    user = graphql_resolver.generate_resolver(
        type_name="user",
        graphql_type=USER_LIST_TYPE,
        class_loader=USER_CLASS_LOADER,
    )
    post = graphql_resolver.generate_resolver(
        type_name="post",
        graphql_type=POST_LIST_TYPE,
        class_loader=POST_CLASS_LOADER,
    )
    section = graphql_resolver.generate_resolver(
        type_name="section",
        graphql_type=SECTION_LIST_TYPE,
        class_loader=SECTION_CLASS_LOADER,
    )
    group = graphql_resolver.generate_resolver(
        type_name="group",
        graphql_type=GROUP_LIST_TYPE,
        class_loader=GROUP_CLASS_LOADER,
    )
