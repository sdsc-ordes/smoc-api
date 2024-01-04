"""Basic CLI interface to create and interact with digital objects."""

# Use typer for CLI

from enum import Enum
import json
from pathlib import Path
from typing import Any, Iterable, Optional
from typing_extensions import Annotated

from linkml_runtime.loaders import json_loader
from linkml_runtime.dumpers import json_dumper, rdflib_dumper
from smoc_schema.datamodel import Study
import typer
import zarr

from .api import MODO
from .helpers import ElementType
from .introspection import get_slots
from .io import parse_instances
from .storage import add_metadata_group, init_zarr


class RdfFormat(str, Enum):
    """Enumeration of RDF formats."""

    TURTLE = "turtle"
    RDF_XML = "xml"
    JSON_LD = "json-ld"


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
    object_directory: Annotated[Path, typer.Argument(...)],
    from_file: Annotated[
        Optional[Path],
        typer.Option(
            "--from-file",
            "-f",
            help="Create a digital object from a file. The file must be in json or yaml format.",
        ),
    ] = None,
    meta: Annotated[
        Optional[str],
        typer.Option(
            "--meta",
            "-m",
            help="Create instance from metadata provided as a json string.",
        ),
    ] = None,
):
    """Create a digital object.
    The object can be created interactively, or initiated
    from metadata provided in a file or as a json string.
    """
    typer.echo("Creating a digital object.", err=True)
    # Initialize object's directory
    if object_directory.exists():
        raise ValueError(f"Directory already exists: {object_directory}")

    # Obtain object's metadata and create object
    if from_file and meta:
        raise ValueError("Only one of --from-file or --data can be used.")
    elif from_file:
        obj = parse_instances(from_file, target_class=Study)
    elif meta:
        obj = json_loader.loads(meta, target_class=Study)
    else:
        filled = prompt_for_slots("Study")
        obj = Study(**filled)

    # Dump object to zarr metadata
    group = init_zarr(object_directory)
    attrs = json.loads(json_dumper.dumps(obj))
    add_metadata_group(group, attrs)


@cli.command()
def add(
    object_directory: Annotated[Path, typer.Argument(...)],
    element_type: Annotated[
        ElementType,
        typer.Argument(
            ...,
            help="Type of element to add to the digital object.",
        ),
    ],
    parent: Annotated[
        Optional[str],
        typer.Option(
            "--parent", "-p", help="Parent object in the zarr archive."
        ),
    ] = "/",
    meta: Annotated[
        Optional[str],
        typer.Option(
            "--meta",
            "-m",
            help="Create instance from metadata provided as a json string.",
        ),
    ] = None,
    from_file: Annotated[
        Optional[Path],
        typer.Option(
            "--from-file",
            "-f",
            help="Create instance from a file. The file must be in json or yaml format.",
        ),
    ] = None,
):
    """Add elements to a digital object. Files whose path is provided
    in the metadata will be added to the object's directory and the
    metadata will be updated."""

    typer.echo(f"Updating {object_directory}.", err=True)
    target_class = element_type.get_target_class()

    if from_file and meta:
        raise ValueError("Only one of --from-file or --meta can be used.")
    elif from_file:
        obj = parse_instances(from_file, target_class=target_class)
    elif meta:
        obj = json_loader.loads(meta, target_class=target_class)
    else:
        filled = prompt_for_slots(target_class.__name__)
        obj = target_class(**filled)

    modo = MODO(object_directory)
    modo.add_element(obj, data_file=from_file, part_of=parent)


@cli.command()
def show(
    object_directory: Annotated[Path, typer.Argument(...)],
    zarr: Annotated[
        bool,
        typer.Option(
            "--zarr",
            "-z",
            help="Show the structure of the zarr archive",
        ),
    ] = False,
    files: Annotated[
        bool,
        typer.Option(
            "--files",
            "-f",
            help="Show data files in the digital object.",
        ),
    ] = False,
):
    """Show the contents of a digital object."""
    obj = MODO(object_directory)
    if zarr:
        out = obj.list_arrays()
    elif files:
        out = "\n".join([str(path) for path in obj.list_files()])
    else:
        out = obj.show_contents()
    print(out)


@cli.command()
def publish(
    object_directory: Annotated[Path, typer.Argument(...)],
    output_format: Annotated[RdfFormat, typer.Option(...)] = RdfFormat.TURTLE,
    base_uri: Annotated[Optional[str], typer.Option(...)] = None,
):
    """Creates a semantic artifact allowing to publish
    a digital object as linked data. This artifact can be
    published as linked data.

    In the process, JSON metadata is converted to RDF and
    all relative paths are converted to URIs.
    """
    obj = MODO(object_directory)
    print(
        obj.knowledge_graph(uri_prefix=base_uri).serialize(
            format=output_format
        )
    )
