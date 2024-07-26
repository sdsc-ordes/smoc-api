"""Basic CLI interface to create and interact with digital objects."""

# Use typer for CLI

from datetime import date
from enum import Enum
import os
from pathlib import Path
from typing import Any, List, Mapping, Optional
from typing_extensions import Annotated

import click
from linkml_runtime.loaders import json_loader
import modos_schema.datamodel as model
import sys
import typer
import zarr

from .api import MODO
from .helpers.schema import (
    UserElementType,
    get_enum_values,
    get_slots,
    get_slot_range,
    load_schema,
)
from .remote import list_endpoints
from .genomics.htsget import HtsgetConnection
from .genomics.region import Region
from .io import parse_instance
from .storage import connect_s3


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
    exclude: Optional[Mapping[str, List]] = None,
    # add dict with exclude
) -> dict[str, Any]:
    """Prompt the user to provide values for the slots of input class.
    values of required fields can be excluded to repeat the prompt.

    Parameters
        ----------
        target_class
            Class to build
        exclude
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
        if exclude and entries.get(slot_name) in exclude.get(slot_name, []):
            print(
                f"Invalid value: {slot_name} must differ from {exclude[slot_name]}."
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
    endpoint: Annotated[
        Optional[str],
        typer.Option(
            "--endpoint",
            "-e",
            help="Create remote instance on modos endpoint. Must point to a valid url",
        ),
    ] = None,
    from_file: Annotated[
        Optional[Path],
        typer.Option(
            "--from-file",
            "-f",
            help="Create a modo from a file. The file must be in json or yaml format.",
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
    """Create a modo interactively or from a file."""
    typer.echo("Creating a digital object.", err=True)
    # Initialize object's directory
    if object_directory.exists():
        raise ValueError(f"Directory already exists: {object_directory}")

    if endpoint:
        s3 = list_endpoints(endpoint)["s3"]  # type: ignore
        fs = connect_s3(s3, {"anon": True})  # type: ignore
        if fs.exists(object_directory):
            raise ValueError(
                f"Remote directory already exists: {object_directory}"
            )

    # Obtain object's metadata and create object
    if from_file and meta:
        raise ValueError("Only one of --from-file or --data can be used.")
    elif from_file:
        modo = MODO.from_file(from_file, object_directory, endpoint=endpoint)
        return
    elif meta:
        obj = json_loader.loads(meta, target_class=model.MODO)
    else:
        filled = prompt_for_slots(model.MODO)
        obj = model.MODO(**filled)

    attrs = obj.__dict__
    # Dump object to zarr metadata
    MODO(path=object_directory, endpoint=endpoint, **attrs)


@cli.command()
def remove(
    object_directory: Annotated[Path, typer.Argument(...)],
    element_id: Annotated[
        str,
        typer.Argument(
            ...,
            help="The identifier within the modo. Use modos show to check it.",
        ),
    ],
    endpoint: Annotated[
        Optional[str],
        typer.Option(
            "--endpoint",
            "-e",
            help="Url to modos endpoint managing the digital object.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Skip confirmation for file deletion and allow deletion of the root object.",
        ),
    ] = False,
):
    """Removes an element and its files from the modo."""
    modo = MODO(object_directory, endpoint=endpoint)
    if element_id == modo.path.name:
        if force:
            modo.remove_object()
        else:
            raise ValueError(
                "Cannot delete root object. If you want to delete the entire MODOS, use --force."
            )
    else:
        element = modo.zarr[element_id]
        rm_path = element.attrs.get("data_path", [])
        if isinstance(element, zarr.hierarchy.Group) and len(rm_path) > 0:
            if not force:
                delete = typer.confirm(
                    f"Removing {element_id} will permanently delete {rm_path}.\n Please confirm that you want to continue?"
                )
                if not delete:
                    print(f"Stop removing element {element_id}!")
                    raise typer.Abort()
        modo.remove_element(element_id)


@cli.command()
def add(
    object_directory: Annotated[Path, typer.Argument(...)],
    element_type: Annotated[
        UserElementType,
        typer.Argument(
            ...,
            help="Type of element to add to the digital object.",
        ),
    ],
    endpoint: Annotated[
        Optional[str],
        typer.Option(
            "--endpoint",
            "-e",
            help="Url to modos endpoint managing the digital object.",
        ),
    ] = None,
    parent: Annotated[
        Optional[str],
        typer.Option(
            "--parent", "-p", help="Parent object in the zarr store."
        ),
    ] = None,
    element: Annotated[
        Optional[str],
        typer.Option(
            "--element",
            "-e",
            help="Create instance from element metadata provided as a json string.",
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
    source_file: Annotated[
        Optional[Path],
        typer.Option(
            "--source-file",
            "-s",
            help="Specify a data file (if any) to copy into the digital object and associate with the instance.",
        ),
    ] = None,
):
    """Add elements to a modo."""

    typer.echo(f"Updating {object_directory}.", err=True)
    modo = MODO(object_directory, endpoint=endpoint)
    target_class = element_type.get_target_class()

    if from_file and element:
        raise ValueError("Only one of --from-file or --element can be used.")
    elif from_file:
        obj = parse_instance(from_file, target_class=target_class)
    elif element:
        obj = json_loader.loads(element, target_class=target_class)
    else:
        exclude = {"id": [Path(id).name for id in modo.metadata.keys()]}
        filled = prompt_for_slots(target_class, exclude)
        obj = target_class(**filled)

    modo.add_element(obj, source_file=source_file, part_of=parent)


@cli.command()
def show(
    object_directory: Annotated[Path, typer.Argument(...)],
    endpoint: Annotated[
        Optional[str],
        typer.Option(
            "--endpoint",
            "-e",
            help="Url to modos endpoint managing the digital object.",
        ),
    ] = None,
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
    """Show the contents of a modo."""
    if endpoint:
        obj = MODO(object_directory, endpoint=endpoint)
    elif os.path.exists(object_directory):
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
    endpoint: Annotated[
        Optional[str],
        typer.Option(
            "--endpoint",
            "-e",
            help="Url to modos endpoint managing the digital object.",
        ),
    ] = None,
):
    """Export a modo as linked data. Turns all paths into URIs."""
    obj = MODO(object_directory, endpoint=endpoint)
    print(
        obj.knowledge_graph(uri_prefix=base_uri).serialize(
            format=output_format
        )
    )


@cli.command()
def stream(
    file_path: Annotated[
        str,
        typer.Argument(
            ...,
            help="The path to the file to stream . Use modos show --files to check it.",
        ),
    ],
    endpoint: Annotated[
        str,
        typer.Option(
            "--endpoint",
            "-e",
            help="Url to modos endpoint managing the digital object.",
        ),
    ],
    region: Annotated[
        Optional[str],
        typer.Option(
            "--region",
            "-r",
            help="Restrict stream to genomic region (chr:start-end).",
        ),
    ] = None,
):
    """Stream genomic file from a remote modo into stdout.


    Example:
    modos stream -s3 http://localhost/s3 my-bucket/ex-modo/demo1.cram
    """
    _region = Region.from_ucsc(region) if region else None

    # NOTE: bucket is not included in htsget paths
    source = Path(*Path(file_path).parts[1:])
    htsget_endpoint = ...

    con = HtsgetConnection(htsget_endpoint, source, _region)
    with con.open() as f:
        for chunk in f:
            sys.stdout.buffer.write(chunk)


# Generate a click group to autogenerate docs via sphinx-click:
# https://github.com/tiangolo/typer/issues/200#issuecomment-795873331

typer_click_object = typer.main.get_command(cli)
