"""
Code generators for FastAPI Cruddy Framework
"""

import os
from pathlib import Path
from typing import List, Tuple
from .templates import (
    PROJECT_TEMPLATES,
    MODEL_TEMPLATE,
    RESOURCE_TEMPLATE,
    CONTROLLER_TEMPLATE,
)


def scaffold_project(
    project_name: str,
    project_path: Path,
    database: str = "sqlite",
    template: str = "minimal",
) -> None:
    """Generate a new FastAPI Cruddy Framework project."""
    project_path.mkdir(parents=True, exist_ok=True)

    # Create the nested source directory structure
    source_path = project_path / project_name
    source_path.mkdir(exist_ok=True)

    # Create __init__.py for the main module
    (source_path / "__init__.py").touch()

    # Create directory structure within the nested module
    directories = [
        "models",
        "resources",
        "controllers",
        "config",
        "adapters",
        "policies",
        "schemas",
        "utils",
        "router",
        "services",
        "middleware",
    ]

    for directory in directories:
        (source_path / directory).mkdir(exist_ok=True)
        (source_path / directory / "__init__.py").touch()

    # Get template files based on selection
    template_files = PROJECT_TEMPLATES[template][database]

    # Write template files
    for file_path, content in template_files.items():
        # Root-level files (pyproject.toml, README.md, .env) go at project root
        if file_path in ["pyproject.toml", "README.md", ".env"]:
            full_path = project_path / file_path
        else:
            # All other files go in the nested source directory
            full_path = source_path / file_path

        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Replace placeholders in content
        content = content.replace("{{PROJECT_NAME}}", project_name)
        content = content.replace("{{PROJECT_NAME_UPPER}}", project_name.upper())
        content = content.replace("{{PROJECT_NAME_LOWER}}", project_name.lower())

        with open(full_path, "w") as f:
            f.write(content)


def generate_resource(
    resource_name: str,
    id_type: str = "int",
    fields: List[Tuple[str, str]] | None = None,
    relationships: List[Tuple[str, str]] | None = None,
) -> None:
    """Generate a complete resource with model, controller, and resource files."""
    if fields is None:
        fields = []
    if relationships is None:
        relationships = []

    # Ensure proper capitalization for class names
    capitalized_name = _capitalize_class_name(resource_name)

    # Get the project module path
    project_module_path = _get_project_module_path()
    if not project_module_path:
        raise Exception(
            "Could not find project module directory. Make sure you're in a Cruddy project root."
        )

    # Generate model first
    generate_model(resource_name, id_type, fields)

    # Generate controller
    generate_controller(resource_name)

    # Generate resource file in the correct nested path
    resource_path = project_module_path / "resources" / f"{resource_name.lower()}.py"

    # Build import line for ID type
    id_import = _get_id_type_import(id_type)
    id_import_line = f", {id_import}" if id_import else ""

    context = {
        "resource_name": capitalized_name,
        "resource_name_lower": resource_name.lower(),
        "resource_name_upper": resource_name.upper(),
        "project_name_lower": _get_project_name_lower(),
        "id_type": id_import,
        "id_type_name": _get_id_type_name(id_type),
        "id_type_import_line": id_import_line,
    }

    content = RESOURCE_TEMPLATE.format(**context)

    with open(resource_path, "w") as f:
        f.write(content)


def generate_model(
    model_name: str, id_type: str = "int", fields: List[Tuple[str, str]] | None = None
) -> None:
    """Generate a model file."""
    if fields is None:
        fields = []

    # Ensure proper capitalization for class names
    model_name = _capitalize_class_name(model_name)

    # Get the project module path
    project_module_path = _get_project_module_path()
    if not project_module_path:
        raise Exception(
            "Could not find project module directory. Make sure you're in a Cruddy project root."
        )

    model_path = project_module_path / "models" / f"{model_name.lower()}.py"

    # Generate field definitions for update/create models
    field_defs = []
    for field_name, field_type in fields:
        field_def = _generate_field_definition(
            field_name, field_type, for_view_model=False
        )
        field_defs.append(field_def)

    fields_content = (
        "    " + "\n    ".join(field_defs)
        if field_defs
        else "    pass  # Add your fields here"
    )

    # Generate field definitions for view model (all optional for columns parameter support)
    view_field_defs = []
    for field_name, field_type in fields:
        view_field_def = _generate_field_definition(
            field_name, field_type, for_view_model=True
        )
        view_field_defs.append(view_field_def)

    view_fields_content = (
        "    " + "\n    ".join(view_field_defs)
        if view_field_defs
        else "    pass  # Add your fields here"
    )

    # Check if Any import is needed based on field types
    needs_any_import = any(
        field_type.lower() in ["json", "any"] for _, field_type in fields
    )
    any_import = "\nfrom typing import Any" if needs_any_import else ""

    context = {
        "model_name": model_name,
        "model_name_lower": model_name.lower(),
        "model_name_upper": model_name.upper(),
        "base_class": _get_base_model_class(id_type),
        "fields": fields_content,
        "view_fields": view_fields_content,
        "any_import": any_import,
    }

    content = MODEL_TEMPLATE.format(**context)

    with open(model_path, "w") as f:
        f.write(content)


def generate_controller(controller_name: str) -> None:
    """Generate a controller file."""
    # Ensure proper capitalization for class names
    controller_name = _capitalize_class_name(controller_name)

    # Get the project module path
    project_module_path = _get_project_module_path()
    if not project_module_path:
        raise Exception(
            "Could not find project module directory. Make sure you're in a Cruddy project root."
        )

    controller_path = (
        project_module_path / "controllers" / f"{controller_name.lower()}.py"
    )

    context = {
        "controller_name": controller_name,
        "controller_name_lower": controller_name.lower(),
        "controller_name_upper": controller_name.upper(),
    }

    content = CONTROLLER_TEMPLATE.format(**context)

    with open(controller_path, "w") as f:
        f.write(content)


def _get_project_module_path() -> Path | None:
    """Find the project module path (the nested directory containing source code)."""
    # Look for a nested directory that has the Cruddy structure
    for item in Path(".").iterdir():
        if item.is_dir() and not item.name.startswith("."):
            nested_path = item
            # Check if this nested directory has the Cruddy structure
            if all(
                (nested_path / d).exists()
                for d in ["models", "resources", "controllers"]
            ):
                return nested_path
    return None


def _get_project_name_lower() -> str:
    """Get the lowercase project name from the current directory structure."""
    project_module_path = _get_project_module_path()
    if project_module_path:
        return project_module_path.name
    # Fallback to current directory name if can't find project module
    return Path(".").resolve().name.lower()


def _get_id_type_import(id_type: str) -> str:
    """Get the import statement for the ID type."""
    if id_type == "uuid":
        return "UUID"
    elif id_type == "str":
        return ""  # str is built-in
    else:  # int
        return ""  # int is built-in


def _get_id_type_name(id_type: str) -> str:
    """Get the type name for the ID."""
    if id_type == "uuid":
        return "UUID"
    elif id_type == "str":
        return "str"
    else:  # int
        return "int"


def _get_base_model_class(id_type: str) -> str:
    """Get the base model class based on ID type."""
    if id_type == "uuid":
        return "CruddyUUIDModel"
    elif id_type == "str":
        return "CruddyStringIDModel"
    else:  # int
        return "CruddyIntIDModel"


def _capitalize_class_name(name: str) -> str:
    """Ensure class names are properly capitalized according to Python conventions."""
    # Convert to title case (first letter of each word capitalized)
    # Then remove spaces/underscores to create PascalCase
    words = name.replace("_", " ").replace("-", " ").split()
    return "".join(word.capitalize() for word in words)


def _generate_field_definition(
    field_name: str, field_type: str, for_view_model: bool = False
) -> str:
    """Generate a field definition line."""
    type_mapping = {
        "str": "str",
        "string": "str",
        "int": "int",
        "integer": "int",
        "float": "float",
        "bool": "bool",
        "boolean": "bool",
        "datetime": "datetime",
        "date": "date",
        "time": "time",
        "uuid": "UUID",
        "json": "Any",
        "text": "str",
    }

    python_type = type_mapping.get(field_type.lower(), "str")

    # For view models, all fields should be optional to support "columns" parameter
    if for_view_model:
        python_type = f"{python_type} | None"
        default = " = None"
    # For other models, add optional type annotation for non-basic fields
    elif field_type.lower() not in ["int", "str", "float", "bool"]:
        python_type = f"{python_type} | None"
        default = " = None"
    else:
        default = ""

    return f"{field_name}: {python_type}{default}"
