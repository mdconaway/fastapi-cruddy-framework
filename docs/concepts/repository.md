## AbstractRepository

The `AbstractRepository` is a helpful way to interact with the data layer of your models. It contains all of the underlying functions that the `Resource` and `Controller` objects use to query, create, update, and delete your database information. Each `Resource` you define will automatically create an `AbstractRepository` instance that manages it. This can be accessed in your application at `your_resource_instance.repository`. The methods available to you via this repository instance are:

```python
# User functions accessible from any resource's 'AbstractRepository'
async def create(data: CruddyModel)

async def get_by_id(id: UUID | int | str)

async def update(id: UUID | int | str, data: CruddyModel)

async def delete(id: UUID | int | str)

async def get_all(page: int = 1, limit: int = 10, columns: list[str] = None, sort: list[str] = None, where: Json = None)

async def get_all_relations(id: UUID | int | str = ..., relation: str = ..., relation_model: CruddyModel = ..., page: int = 1, limit: int = 10, columns: list[str] = None, sort: list[str] = None, where: Json = None)

async def set_many_many_relations(id: UUID | int | str, relation: str = ..., relations: list[UUID | int | str] = ...)

async def set_one_many_relations(id: UUID | int | str, relation: str = ..., relations: list[UUID | int | str] = ...)
```

Generally, these functions do about what you would expect them to do. More documentation will be added to describe their function soon. Please read nuances below, however, as it applies to how x-to-Many relationships are managed via the automatic CRUD routes.

<b>Important AbstractRepository Nuances</b>

- `set_many_many_relations` and `set_one_many_relations` both destroy and then re-create the x-to-Many relationships they target. If a `user` with the id of 1 was a member of `groups` 1, 2, and 3, then calling `await user_repository.set_many_many_relations(1, 'groups', [4,5,6])` would result in `user` 1 being a member of only groups 4,5, and 6 after execution. Client applications should be aware of this functionality, and always send ALL relationships that should still exist during any relational updates.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
