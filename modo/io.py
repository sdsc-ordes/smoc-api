from pathlib import Path
import re

from linkml_runtime.loaders import (
    json_loader,
    yaml_loader,
    csv_loader,
    rdf_loader,
)

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
    """Load a Study from a file."""
    loader = get_loader(path)
    if not loader:
        raise ValueError(f"Unsupported file format: {path}")
    return loader.load(path)
