from pathlib import Path
import re
from typing import Any, Mapping, List

from linkml_runtime.loaders import (
    json_loader,
    yaml_loader,
    csv_loader,
    rdf_loader,
)
from linkml_runtime.dumpers import json_dumper
import smoc_schema.datamodel as model
from .api import MODO
from .helpers import dict_to_instance, class_from_name
from .cram import slice_cram
from .storage import add_metadata_group, init_zarr
import json


ext2loader = {
    "json": json_loader,
    r"ya?ml": yaml_loader,
    "csv": csv_loader,
    r"rdf|ttl|nt(riples)?": rdf_loader,
}


def get_loader(path: Path):
    """Get a loader based on the file extension using regex."""
    ext = path.suffix[1:]
    for pattern, loader in ext2loader.items():
        if re.match(pattern, ext):
            return loader
    return None


def parse_instance(path: Path, target_class):
    """Load a model of target_class from a file."""
    loader = get_loader(path)
    if not loader:
        raise ValueError(f"Unsupported file format: {path}")
    return loader.load(str(path), target_class)


def parse_multiple_instances(path: Path) -> List:
    """Load one or more model from file. Model types must be specified as @type"""
    loader = get_loader(path)
    if not loader:
        raise ValueError(f"Unsupported file format: {path}")
    elems = loader.load_as_dict(str(path))
    if not isinstance(elems, list):
        elems = [elems]
    instances = []
    for elem in elems:
        id = elem.pop("id")
        instances.append(dict_to_instance(elem, id))
    return instances


def build_modo_from_file(path: Path, object_directory: Path) -> MODO:
    """build a modo from a yaml or json file"""
    instances = parse_multiple_instances(Path(path))
    modo_inst = [
        instance for instance in instances if isinstance(instance, model.MODO)
    ]
    if len(modo_inst) != 1:
        raise ValueError(
            f"There must be exactly 1 MODO in the input file. Found {len(modo_inst)}"
        )
    # Dump object to zarr metadata
    group = init_zarr(Path(object_directory))
    attrs = json.loads(json_dumper.dumps(modo_inst[0]))
    add_metadata_group(group, attrs)
    modo = MODO(object_directory)
    for instance in instances:
        if not isinstance(instance, model.MODO):
            modo.add_element(instance)
    return modo


def slice(data: model.DataEntity, region: str) -> Any:
    """Returns a slice of the input data for the requested region.

    Parameters
    ----------
    data
        A data object in any supported format.
    region
        The region string in UCSC format (i.e. chr:start-end).
    """

    match str(data.data_format):
        case "CRAM":
            return slice_cram(data.data_path, region)
        case _:
            raise ValueError(f"Unsupported data format: {data.data_format}")
