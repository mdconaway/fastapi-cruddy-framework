# FastAPI Cruddy Framework CLI

The FastAPI Cruddy Framework now includes a powerful CLI tool to help developers scaffold new projects and generate CRUD resources quickly and efficiently.

## Installation

The CLI is automatically available after installing the `fastapi-cruddy-framework` package:

```bash
pip install fastapi-cruddy-framework
```

## CLI Commands

### Initialize a New Project

Create a new FastAPI Cruddy Framework project with a single command:

```bash
cruddy init my_project
```

**Options:**
- `--database, -d`: Choose database adapter (`sqlite`, `postgresql`, `mysql`) - default: `sqlite`
- `--template, -t`: Choose project template (`minimal`, `full`) - default: `minimal`
- `--directory`: Specify target directory - default: current directory

**Examples:**

```bash
# Create a new SQLite project
cruddy init my_blog --database sqlite

# Create a PostgreSQL project
cruddy init my_api --database postgresql

# Create a project in a specific directory
cruddy init my_project --directory /path/to/projects
```

### Generate Resources

The CLI can generate complete CRUD resources or individual components.

#### Generate a Complete Resource

```bash
cruddy generate resource User --fields "name:str,email:str,age:int"
```

This creates:
- `models/user.py` - Database model with Create, Update, View, and Base classes
- `resources/user.py` - Resource configuration connecting model, controller, and repository
- `controllers/user.py` - Controller extension for custom endpoints

**Options:**
- `--id-type`: ID type for the resource (`int`, `uuid`, `str`) - default: `int`
- `--fields`: Comma-separated field definitions (e.g., `"name:str,email:str,age:int"`)
- `--relationships`: Comma-separated relationship definitions (e.g., `"posts:one-to-many,groups:many-to-many"`)

**Field Types Supported:**
- `str`, `string` - String fields
- `int`, `integer` - Integer fields
- `float` - Float fields
- `bool`, `boolean` - Boolean fields
- `datetime` - DateTime fields with timezone
- `date` - Date fields
- `time` - Time fields
- `uuid` - UUID fields
- `json` - JSON fields (uses `Any` type)
- `text` - Text fields (alias for `str`)

**Examples:**

```bash
# Basic user resource
cruddy generate resource User --fields "name:str,email:str,age:int"

# Blog post with UUID primary key
cruddy generate resource Post --id-type uuid --fields "title:str,content:text,published:bool,created_at:datetime"

# Product with relationships
cruddy generate resource Product --fields "name:str,price:float,description:text" --relationships "reviews:one-to-many,categories:many-to-many"
```

#### Generate Individual Components

**Generate a Model Only:**
```bash
cruddy generate model Product --fields "name:str,price:float,description:str"
```

**Generate a Controller Only:**
```bash
cruddy generate controller CustomEndpoints
```

## Project Structure

A generated project follows this structure:

```
my_project/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── .env                   # Environment variables
├── README.md              # Project documentation
├── adapters/              # Database adapter configuration
│   └── __init__.py
├── config/                # Application settings
│   └── __init__.py
├── controllers/           # Custom controller extensions
│   └── __init__.py
├── models/               # Database models
│   └── __init__.py
├── policies/             # Business logic policies
│   └── __init__.py
├── resources/            # Resource definitions
│   └── __init__.py
├── schemas/              # Response and validation schemas
│   └── __init__.py
└── utils/                # Utility functions
    └── __init__.py
```

## Generated Code Examples

### Model Example (`models/user.py`)

```python
"""
User model for FastAPI Cruddy Framework
"""
from fastapi_cruddy_framework import (
    CruddyModel,
    CruddyIntIDModel,
    CruddyCreatedUpdatedMixin,
    CruddyCreatedUpdatedSignature,
)
from sqlmodel import Field


class UserUpdate(CruddyModel):
    """Update model for User - contains fields that can be updated."""
    name: str
    email: str
    age: int


class UserCreate(UserUpdate):
    """Create model for User - extends update model with creation-only fields."""
    pass


class UserView(CruddyCreatedUpdatedSignature, CruddyIntIDModel):
    """View model for User - defines fields returned in API responses."""
    name: str | None = None
    email: str | None = None
    age: int | None = None


class User(CruddyCreatedUpdatedMixin(), CruddyIntIDModel, UserCreate, table=True):
    """Base User model with database table definition."""
    pass
```

### Resource Example (`resources/user.py`)

```python
"""
User resource for FastAPI Cruddy Framework
"""
from fastapi_cruddy_framework import Resource
from my_project.adapters.application import adapter
from my_project.models.user import (
    User,
    UserCreate,
    UserUpdate,
    UserView,
)
from my_project.controllers.user import UserController


resource = Resource(
    adapter=adapter,
    id_type=int,
    resource_model=User,
    resource_create_model=UserCreate,
    resource_update_model=UserUpdate,
    response_schema=UserView,
    controller_extension=UserController,
    # Add your policies, lifecycle hooks, and other configurations here
    # policies_universal=[example_policy],
    # protected_relationships=["example_relation"],
)
```

### Controller Example (`controllers/user.py`)

```python
"""
User controller extensions for FastAPI Cruddy Framework
"""
from fastapi_cruddy_framework import CruddyController
from fastapi import Depends


class UserController(CruddyController):
    """Extended controller for User resource."""

    def setup(self):
        """Setup custom routes and extend default CRUD functionality."""
        # Example custom route:
        @self.controller.get(
            "/example",
            summary="Example custom endpoint",
            description="This is an example of how to add custom endpoints",
        )
        async def custom_example():
            return {"message": "Hello from User!"}

        # Example of extending default actions:
        # original_create = self.actions.create
        #
        # async def enhanced_create(request, data):
        #     # Add custom logic before creation
        #     result = await original_create(request, data)
        #     # Add custom logic after creation
        #     return result
        #
        # self.actions.create = enhanced_create
```

## Getting Started

1. **Create a new project:**
   ```bash
   cruddy init my_blog --database sqlite
   cd my_blog
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Generate a resource:**
   ```bash
   cruddy generate resource Post --fields "title:str,content:text,published:bool"
   ```

4. **Run the application:**
   ```bash
   python main.py
   ```

5. **Access the API documentation:**
   ```
   http://localhost:8000/docs
   ```

## Database Support

The CLI supports three database adapters:

### SQLite (Default)
- Perfect for development and small applications
- No additional setup required
- File-based or in-memory options

### PostgreSQL
- Production-ready relational database
- Requires PostgreSQL server and `psycopg2-binary`
- Advanced features like full-text search

### MySQL
- Popular relational database
- Requires MySQL server and `PyMySQL`
- Good performance and scalability

## Advanced Usage

### Custom Policies
Add business logic policies to your resources:

```python
# In your resource file
from ..policies.auth import require_authentication

resource = Resource(
    # ... other config
    policies_universal=[require_authentication],
    policies_create=[additional_create_policy],
)
```

### Lifecycle Hooks
Add hooks to execute code before/after CRUD operations:

```python
async def before_user_create(data):
    # Hash password before saving
    data.password = hash_password(data.password)

resource = Resource(
    # ... other config
    lifecycle_before_create=before_user_create,
)
```

### Protected Relationships
Prevent certain relationships from being modified via API:

```python
resource = Resource(
    # ... other config
    protected_relationships=["admin_notes"],
    protected_create_relationships=["system_metadata"],
)
```

## Tips and Best Practices

1. **Start with the minimal template** - You can always add features later
2. **Use meaningful field names** - They become your API field names
3. **Consider ID types carefully** - UUIDs for public APIs, integers for internal tools
4. **Add validation in your models** - Use Pydantic validators for business rules
5. **Organize policies by function** - Keep authentication, authorization, and validation separate
6. **Use lifecycle hooks for side effects** - Logging, notifications, caching, etc.
7. **Test your resources** - The framework provides excellent test helpers

## Need Help?

- Check the main [FastAPI Cruddy Framework documentation](README.md)
- Look at the [example server](examples/fastapi_cruddy_sqlite/) for advanced patterns
- File issues on [GitHub](https://github.com/mdconaway/fastapi-cruddy-framework)

The CLI tool makes it incredibly fast to scaffold production-ready CRUD applications with FastAPI. Happy coding!
