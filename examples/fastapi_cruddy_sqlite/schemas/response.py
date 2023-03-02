from fastapi_cruddy_framework import CruddyGenericModel


# This is an example of how to "remap" the metadata in a paged response.
# The inputs in the first "init" are fixed, based on what CRUDDY returns,
# and these inputs can be "remapped" to the new meta object via the
# super()__init__ method, where the CRUDDY inputs can be mapped to the
# new base class attributes.
class MetaObject(CruddyGenericModel):
    page: int
    limit: int
    pages: int
    records: int

    def __init__(
        self,
        page: int = 0,
        limit: int = 0,
        pages: int = 0,
        records: int = 0,
    ):
        super().__init__(page=page, limit=limit, pages=pages, records=records)
