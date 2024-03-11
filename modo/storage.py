from pathlib import Path
import zarr


from .helpers import ElementType


# Initialize object's directory given the metadata graph
def init_zarr(root_directory: Path) -> zarr.Group:
    """Initialize object's directory and metadata structure."""
    root_directory.mkdir(exist_ok=True)
    store = zarr.DirectoryStore(str(root_directory / "data.zarr"))
    data = zarr.group(store=store)

    elem_types = [t.value for t in ElementType]
    for elem_type in elem_types:
        data.create_group(elem_type)

    return data


def add_metadata_group(parent_group: zarr.Group, metadata: dict) -> None:
    """Add input metadata dictionary to an existing zarr group."""
    # zarr groups cannot have slashes in their names
    group_name = metadata["id"].replace("/", "_")
    parent_group.create_group(group_name)
    # Fill attrs in the subject group for each predicate
    for key, value in metadata.items():
        if key == "id":
            continue
        parent_group[group_name].attrs[key] = value


def add_data(group: zarr.Group, data) -> None:
    """Add a numpy array to an existing zarr group."""
    group.create_dataset("data", data=data)


def list_zarr_items(group: zarr.Group) -> list[zarr.Group | zarr.Array]:
    """Recursively list all zarr groups and arrays"""
    found = []

    def list_all(path: str, elem):
        found.append((path, elem))

    group.visititems(list_all)
    return found
