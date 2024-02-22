"""Basic CLI interface to create and interact with digital objects."""

# Use typer for CLI

from datetime import date
from enum import Enum
import json
import os
from pathlib import Path
from typing import Any, List, Mapping, Optional
from typing_extensions import Annotated

import click
from linkml_runtime.loaders import json_loader
from linkml_runtime.dumpers import json_dumper, rdflib_dumper
import modo_schema.datamodel as model
import typer
import zarr

from .api import MODO
from .helpers import ElementType
from .introspection import (
    get_enum_values,
    get_slots,
    get_slot_range,
    load_schema,
)
from .io import build_modo_from_file
from .storage import add_metadata_group, init_zarr


class RdfFormat(str, Enum):
    """Enumeration of RDF formats."""

    TURTLE = "turtle"
    RDF_XML = "xml"
    JSON_LD = "json-ld"


cli = typer.Typer(add_completion=False)


def prompt_for_slot(slot_name: str, prefix: str = "", optional: bool = False):
    """Prompt for a slot value."""
    slot_range = get_slot_range(slot_name)
    choices, default = None, None
    if slot_range == "datetime":
        default = date.today()
    elif load_schema().get_enum(slot_range):
        choices = click.Choice(get_enum_values(slot_range))
    elif optional:
        default = ""

    output = typer.prompt(
        f"{prefix}Enter a value for {slot_name}", default=default, type=choices
    )
    if output == "":
        output = None

    return output


def prompt_for_slots(
    target_class: type,
    whitelist: Optional[Mapping[str, List]] = None,
    # add dict with whitelist
) -> dict[str, Any]:
    """Prompt the user to provide values for the slots of input class.
    values of required fields can be whitelisted to repeat the prompt.

    Parameters
        ----------
        target_class
            Class to build
        whitelist
            Mapping with the name of a slot as key  and list of invalid entries as values.
    """

    entries = {}
    required_slots = set(get_slots(target_class, required_only=True))
    optional_slots = (
        set(get_slots(target_class, required_only=False)) - required_slots
    )

    # Always require identifiers if possible
    if "id" in optional_slots:
        optional_slots.remove("id")
        required_slots.add("id")

    for slot_name in required_slots:
        entries[slot_name] = prompt_for_slot(slot_name, prefix="(required) ")
        if entries[slot_name] is None:
            raise ValueError(f"Missing required slot: {slot_name}")
        if whitelist is not None and entries.get(slot_name) in whitelist.get(
            slot_name, []
        ):
            print(
                f"Invalid value: {slot_name} must differ from {whitelist[slot_name]}."
            )
            entries[slot_name] = prompt_for_slot(
                slot_name, prefix="(required) "
            )

    if optional_slots:
        for slot_name in optional_slots:
            entries[slot_name] = prompt_for_slot(
                slot_name,
                prefix="(optional) ",
                optional=True,
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
        modo = build_modo_from_file(from_file, object_directory)
        return
    elif meta:
        obj = json_loader.loads(meta, target_class=model.MODO)
    else:
        filled = prompt_for_slots(model.MODO)
        obj = model.MODO(**filled)

    attrs = obj.__dict__
    # Dump object to zarr metadata
    MODO(path=object_directory, **attrs)


@cli.command()
def remove(
    object_directory: Annotated[Path, typer.Argument(...)],
    element_id: Annotated[
        str,
        typer.Argument(
            ...,
            help="The identifying path within the digital object. Use modo show to check it.",
        ),
    ],
):
    """Removes the target element from the digital object, along with its files (if any) and links from other elements"""
    modo = MODO(object_directory)
    modo.remove_element(element_id)


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
    ] = None,
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
            help="Include a data file associated with the instance. The file must be in json or yaml format.",
        ),
    ] = None,
    data_file: Annotated[
        Optional[Path],
        typer.Option(
            "--data-file",
            "-d",
            help="Specify a data file to copy into the digital object and associate with the instance.",
        ),
    ] = None,
):
    """Add elements to a digital object. Files whose path is provided
    in the metadata will be added to the object's directory and the
    metadata will be updated."""

    typer.echo(f"Updating {object_directory}.", err=True)
    modo = MODO(object_directory)
    target_class = element_type.get_target_class()

    if from_file and meta:
        raise ValueError("Only one of --from-file or --meta can be used.")
    elif from_file:
        obj = parse_instances(from_file, target_class=target_class)
    elif meta:
        obj = json_loader.loads(meta, target_class=target_class)
    else:
        whitelist = {"id": [Path(id).name for id in modo.metadata.keys()]}
        filled = prompt_for_slots(target_class, whitelist)
        obj = target_class(**filled)

    modo.add_element(obj, data_file=data_file, part_of=parent)


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
    if os.path.exists(object_directory):
        obj = MODO(object_directory)
    else:
        raise ValueError(f"{object_directory} does not exists")
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
