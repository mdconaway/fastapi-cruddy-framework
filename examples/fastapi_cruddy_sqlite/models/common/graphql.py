from fastapi_cruddy_framework import generate_gql_loader_and_type

GROUP_CLASS_LOADER, GROUP_LIST_TYPE = generate_gql_loader_and_type(
    "GroupQL", "examples.fastapi_cruddy_sqlite.models.group"
)
POST_CLASS_LOADER, POST_LIST_TYPE = generate_gql_loader_and_type(
    "PostQL", "examples.fastapi_cruddy_sqlite.models.post"
)
SECTION_CLASS_LOADER, SECTION_LIST_TYPE = generate_gql_loader_and_type(
    "SectionQL", "examples.fastapi_cruddy_sqlite.models.section"
)
USER_CLASS_LOADER, USER_LIST_TYPE = generate_gql_loader_and_type(
    "UserQL", "examples.fastapi_cruddy_sqlite.models.user"
)
