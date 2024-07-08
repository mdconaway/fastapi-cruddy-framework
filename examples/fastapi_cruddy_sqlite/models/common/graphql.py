from fastapi_cruddy_framework import generate_gql_loader_and_type

COMMENT_CLASS_LOADER, COMMENT_LIST_TYPE = generate_gql_loader_and_type(
    "CommentQL", "examples.fastapi_cruddy_sqlite.models.comment"
)
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
LABEL_CLASS_LOADER, LABEL_LIST_TYPE = generate_gql_loader_and_type(
    "LabelQL", "examples.fastapi_cruddy_sqlite.models.label"
)
TYPE_CLASS_LOADER, TYPE_LIST_TYPE = generate_gql_loader_and_type(
    "TypeQL", "examples.fastapi_cruddy_sqlite.models.type"
)
SUBTYPE_CLASS_LOADER, SUBTYPE_LIST_TYPE = generate_gql_loader_and_type(
    "SubTypeQL", "examples.fastapi_cruddy_sqlite.models.subtype"
)
REFERENCE_CLASS_LOADER, REFERENCE_LIST_TYPE = generate_gql_loader_and_type(
    "ReferenceQL", "examples.fastapi_cruddy_sqlite.models.reference"
)
