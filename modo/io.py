from pathlib import Path
import re
from typing import Mapping, Any
from linkml_runtime.loaders import (
    json_loader,
    yaml_loader,
    csv_loader,
    rdf_loader,
)
import smoc_schema.datamodel as model
from .api import MODO

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


def modo_add_element_from_dict(
    modo: MODO, obj_dict: Mapping, element_type: str
):
    """Add element to modo from dict"""
    part_of = obj_dict.get("part_of")
    data_file = obj_dict.get("data_file")
    for key in ["part_of", "data_file"]:
        drop = obj_dict.pop(key, None)
    element = yaml_loader.load(obj_dict, getattr(model, element_type))
    modo.add_element(element, data_file=data_file, part_of=part_of)


def build_modo_from_file(path: Path) -> MODO:
    """build a modo from a yaml or json file"""
    model_dict = parse_multiple_instances(path)
    if "MODO" not in model_dict.keys():
        raise ValueError("Input file must contain MODO + specifications")
    modo = MODO(**model_dict.pop("MODO"))
    for element_type, obj_dict in model_dict.items():
        modo_add_element_from_dict(modo, obj_dict, element_type)
    return modo
