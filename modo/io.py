from pathlib import Path
import re
from typing import Mapping, List
from linkml_runtime.loaders import (
    json_loader,
    yaml_loader,
    csv_loader,
    rdf_loader,
)
import smoc_schema.datamodel as model
from .api import MODO
from .helpers import class_from_name

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


def parse_instances(path: Path, target_class):
    """Load a model of target_class from a file."""
    loader = get_loader(path)
    if not loader:
        raise ValueError(f"Unsupported file format: {path}")
    return loader.load(str(path), target_class)


def parse_multiple_instances(path: Path) -> Mapping:
    """Load multiple objects from a file."""
    loader = get_loader(path)
    if not loader:
        raise ValueError(f"Unsupported file format: {path}")
    return loader.load_as_dict(str(path))


def add_element_from_dict(
    modo: MODO,
    obj_dict: Mapping,
    arg_keys: List[str] = ["part_of", "data_file"],
):
    """Add element to modo from dict"""
    args = {arg: obj_dict.pop(arg, None) for arg in arg_keys}
    element_type = obj_dict.pop("@type")
    element = yaml_loader.load(obj_dict, class_from_name(element_type))
    modo.add_element(element, **args)


def build_modo_from_file(path: Path) -> MODO:
    """build a modo from a yaml or json file"""
    model_dict = parse_multiple_instances(path)
    try:
        # expects one modo per yaml file. Should we add a check for this?
        modo_name = [
            key
            for key, value in model_dict.items()
            if "MODO" in value.get("@type")
        ][0]
    except IndexError:
        print("Input file must contain element of @type MODO")
    drop = model_dict[modo_name].pop("@type")
    modo = MODO(**model_dict.pop(modo_name))
    for name, obj_dict in model_dict.items():
        obj_dict["name"] = name
        add_element_from_dict(modo, obj_dict)
    return modo
