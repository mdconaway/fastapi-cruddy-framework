"""
Main CLI entry point for fastapi-cruddy-framework
"""

import warnings
import click
import os
from pathlib import Path
from typing import Optional

# Suppress Pydantic warnings about Strawberry GraphQL types
warnings.filterwarnings(
    "ignore",
    message=".*is not a Python type.*Pydantic will allow any object with no validation.*",
    category=UserWarning,
    module="pydantic.*",
)

from .generators import (
    scaffold_project,
    generate_resource,
    generate_model,
    generate_controller,
)


@click.group()
@click.version_option(package_name="fastapi-cruddy-framework")
def cli():
    """FastAPI Cruddy Framework CLI - Scaffold and generate CRUD applications"""
    pass


@cli.command()
@click.argument("project_name")
@click.option(
    "--database",
    "-d",
    type=click.Choice(["sqlite", "postgresql", "mysql"]),
    default="sqlite",
    help="Database adapter to use (default: sqlite)",
)
@click.option(
    "--template",
    "-t",
    type=click.Choice(["minimal", "full"]),
    default="minimal",
    help="Project template to use (default: minimal)",
)
@click.option(
    "--directory",
    type=click.Path(),
    help="Directory to create the project in (default: current directory)",
)
def init(project_name: str, database: str, template: str, directory: Optional[str]):
    """Initialize a new FastAPI Cruddy Framework project."""
    target_dir = Path(directory) if directory else Path.cwd()
    project_path = target_dir / project_name

    if project_path.exists():
        click.echo(
            click.style(f"Error: Directory '{project_path}' already exists!", fg="red")
        )
        return

    click.echo(f"Creating new Cruddy project: {project_name}")
    click.echo(f"Database: {database}")
    click.echo(f"Template: {template}")
    click.echo(f"Location: {project_path}")

    try:
        scaffold_project(project_name, project_path, database, template)
        click.echo(
            click.style(
                f"✅ Successfully created project '{project_name}'!", fg="green"
            )
        )
        click.echo("\nNext steps:")
        click.echo(f"  cd {project_name}")
        click.echo("  poetry install")
        click.echo("  poetry run python main.py")
    except Exception as e:
        click.echo(click.style(f"Error creating project: {e}", fg="red"))


@cli.group()
def generate():
    """Generate various project components."""
    pass


@generate.command("resource")
@click.argument("resource_name")
@click.option(
    "--id-type",
    type=click.Choice(["int", "uuid", "str"]),
    default="int",
    help="ID type for the resource (default: int)",
)
@click.option(
    "--fields",
    help="Comma-separated list of fields (e.g., 'name:str,email:str,age:int')",
)
@click.option(
    "--relationships",
    help="Comma-separated list of relationships (e.g., 'posts:one-to-many,groups:many-to-many')",
)
def generate_resource_cmd(
    resource_name: str,
    id_type: str,
    fields: Optional[str],
    relationships: Optional[str],
):
    """Generate a complete resource with model, controller, and related files."""
    if not _in_cruddy_project():
        click.echo(
            click.style(
                "Error: Not in a Cruddy project directory. Run 'cruddy init' first.",
                fg="red",
            )
        )
        return

    try:
        field_list = _parse_fields(fields) if fields else []
        relationship_list = _parse_relationships(relationships) if relationships else []

        generate_resource(resource_name, id_type, field_list, relationship_list)
        click.echo(
            click.style(
                f"✅ Successfully generated resource '{resource_name}'!", fg="green"
            )
        )
        click.echo("\nGenerated files:")
        click.echo(f"  models/{resource_name.lower()}.py")
        click.echo(f"  resources/{resource_name.lower()}.py")
        click.echo(f"  controllers/{resource_name.lower()}.py")
    except Exception as e:
        click.echo(click.style(f"Error generating resource: {e}", fg="red"))


@generate.command("model")
@click.argument("model_name")
@click.option(
    "--id-type",
    type=click.Choice(["int", "uuid", "str"]),
    default="int",
    help="ID type for the model (default: int)",
)
@click.option(
    "--fields",
    help="Comma-separated list of fields (e.g., 'name:str,email:str,age:int')",
)
def generate_model_cmd(model_name: str, id_type: str, fields: Optional[str]):
    """Generate a model file."""
    if not _in_cruddy_project():
        click.echo(
            click.style(
                "Error: Not in a Cruddy project directory. Run 'cruddy init' first.",
                fg="red",
            )
        )
        return

    try:
        field_list = _parse_fields(fields) if fields else []
        generate_model(model_name, id_type, field_list)
        click.echo(
            click.style(f"✅ Successfully generated model '{model_name}'!", fg="green")
        )
        click.echo(f"Generated file: models/{model_name.lower()}.py")
    except Exception as e:
        click.echo(click.style(f"Error generating model: {e}", fg="red"))


@generate.command("controller")
@click.argument("controller_name")
def generate_controller_cmd(controller_name: str):
    """Generate a controller file."""
    if not _in_cruddy_project():
        click.echo(
            click.style(
                "Error: Not in a Cruddy project directory. Run 'cruddy init' first.",
                fg="red",
            )
        )
        return

    try:
        generate_controller(controller_name)
        click.echo(
            click.style(
                f"✅ Successfully generated controller '{controller_name}'!", fg="green"
            )
        )
        click.echo(f"Generated file: controllers/{controller_name.lower()}.py")
    except Exception as e:
        click.echo(click.style(f"Error generating controller: {e}", fg="red"))


def _in_cruddy_project() -> bool:
    """Check if we're in a Cruddy project directory."""
    # Check if we have pyproject.toml (indicating a project root)
    if not Path("pyproject.toml").exists():
        return False

    # Look for a nested directory structure that indicates a Cruddy project
    # Find any subdirectory that has the Cruddy structure
    for item in Path(".").iterdir():
        if item.is_dir() and not item.name.startswith("."):
            nested_path = item
            # Check if this nested directory has the Cruddy structure
            if all(
                (nested_path / d).exists()
                for d in ["models", "resources", "controllers"]
            ):
                return True

    return False


def _parse_fields(fields_str: str) -> list[tuple[str, str]]:
    """Parse field string into list of (name, type) tuples."""
    fields = []
    for field in fields_str.split(","):
        if ":" in field:
            name, field_type = field.strip().split(":", 1)
            fields.append((name.strip(), field_type.strip()))
        else:
            fields.append((field.strip(), "str"))
    return fields


def _parse_relationships(relationships_str: str) -> list[tuple[str, str]]:
    """Parse relationship string into list of (name, type) tuples."""
    relationships = []
    for rel in relationships_str.split(","):
        if ":" in rel:
            name, rel_type = rel.strip().split(":", 1)
            relationships.append((name.strip(), rel_type.strip()))
        else:
            relationships.append((rel.strip(), "one-to-many"))
    return relationships


def main():
    """Main CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
