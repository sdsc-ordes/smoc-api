"""Basic CLI interface to create and interact with digital objects."""

# Use typer for CLI

from pathlib import Path
from typing import Any, Iterable, Optional
from typing_extensions import Annotated

from linkml_runtime.loaders import json_loader
from linkml_runtime.dumpers import json_dumper
from smoc_schema.datamodel import Study
from .introspection import get_slots
from .io import parse_instances
import typer


cli = typer.Typer(add_completion=False)


def prompt_for_slot(slot_name: str, prefix: str = ""):
    """Prompt for a slot value."""
    return typer.prompt(f"{prefix}Enter a value for {slot_name}")


def prompt_for_slots(
    target_class: str,
) -> dict[str, Any]:
    """Prompt the user to provide values for the slots of input class."""

    entries = {}
    required_slots = set(get_slots(target_class, required_only=True))
    optional_slots = (
        set(get_slots(target_class, required_only=False)) - required_slots
    )

    entries["id"] = prompt_for_slot("id", prefix="(required) ")

    for slot_name in required_slots:
        entries[slot_name] = prompt_for_slot(slot_name, prefix="(required) ")
        if entries[slot_name] is None:
            raise ValueError(f"Missing required slot: {slot_name}")
    if optional_slots:
        for slot_name in optional_slots:
            entries[slot_name] = prompt_for_slot(
                slot_name, prefix="(optional) "
            )
    return entries


# Create command
@cli.command()
def create(
    from_file: Annotated[
        Optional[Path],
        typer.Option(
            "--from-file",
            "-f",
            help="Create instances from a file. The file must be in json, yaml, or csv format.",
        ),
    ] = None,
    data: Annotated[
        Optional[str],
        typer.Option(
            "--data",
            "-d",
            help="Create instances from a json string.",
        ),
    ] = None,
):
    """Create a digital object.
    The object can be created interactively, or initiated
    from a file or from a json string.
    """
    typer.echo("Creating a digital object.")
    if from_file and data:
        raise ValueError("Only one of --from-file or --data can be used.")
    elif from_file:
        obj = parse_instances(from_file, target_class=Study)
    elif data:
        obj = json_loader.loads(data, target_class=Study)
    else:
        filled = prompt_for_slots("Study")
        obj = Study(**filled)
    print(json_dumper.dumps(obj))

    # Inputs:
    # Name of the object (e.g. assay-xyz)
    #


# inspect command
@cli.command()
def show():
    """Show the contents of a digital object."""
    typer.echo("Inspect a digital object.")
