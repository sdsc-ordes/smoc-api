from abc import ABC, abstractmethod
from pathlib import Path
import shutil
from typing import Any

import s3fs
import zarr


from .helpers import ElementType

ZARR_ROOT = "data.zarr"


class Storage(ABC):
    @abstractmethod
    def exists(self, path: str) -> bool:
        ...

    @abstractmethod
    def put(self, source: str, target: str):
        ...

    @abstractmethod
    def remove(path: str):
        ...

    @abstractmethod
    def list(path: str):
        ...


class LocalStorage(Storage):
    def __init__(self, path: Path):
        self.path = Path(path)
        if (self.path / ZARR_ROOT).exists():
            self.zarr = zarr.convenience.open(str(self.path / ZARR_ROOT))
        else:
            self.zarr = init_zarr(path)

    def exists(self, path: str = ZARR_ROOT) -> bool:
        return (self.path / path).exists()

    def list(self):
        for path in self.path.glob("*"):
            if path.name.endswith(".zarr"):
                continue
            elif path.is_file():
                yield path
            for file in path.rglob("*"):
                if file.is_file():
                    yield file

    def remove(self, data_file: Path):
        if data_file.exists():
            data_file.unlink()
            print(f"INFO: Permanently deleted {data_file} from filesystem.")

    def put(self, source: Path, dest: Path):
        shutil.copy(source, self.path / dest)


class S3Storage(Storage):
    def __init__(
        self,
        path: Path,
        s3_endpoint: dict[str, Any],
        s3_kwargs: dict[str, Any],
    ):
        self.path = Path(path)
        self.endpoint = s3_endpoint
        s3_opts = s3_kwargs or {"anon": True}
        fs = s3fs.S3FileSystem(endpoint_url=s3_endpoint, **s3_opts)
        if fs.exists(str(self.path / ZARR_ROOT)):
            zarr_s3_opts = s3_opts | {"endpoint_url": s3_endpoint}

            self.zarr = zarr.convenience.open(
                f"s3://{path}/{ZARR_ROOT}",
                storage_options=zarr_s3_opts,
            )
        else:
            self.zarr = init_zarr(path, fs)

    def exists(self, path: str = ZARR_ROOT) -> bool:
        fs = self.zarr.store.fs
        return fs.exists(str(self.path / path))

    def list(self, path: str):
        fs = self.zarr.store.fs
        for path in fs.glob(f"{self.path}/*"):
            if Path(path).name.endswith(".zarr"):
                continue
            elif fs.isfile(path):
                yield Path(path)
            elif fs.isdir(path):
                for file in fs.find(path):
                    yield Path(file)

    def remove(self, data_file: Path):
        if self.zarr.store.fs.exists(data_file):
            self.zarr.store.fs.rm(str(data_file))
            print(
                f"INFO: Permanently deleted {data_file} from remote filesystem."
            )

    def put(self, source: Path, dest: Path):
        self.zarr.store.fs.put(source, self.path / Path(dest).parent)


# Initialize object's directory given the metadata graph
def init_zarr(store):
    data = zarr.hierarchy.group(store=store)
    elem_types = [t.value for t in ElementType]
    for elem_type in elem_types:
        data.create_group(elem_type)

    return data


def add_metadata_group(
    parent_group: zarr.hierarchy.Group, metadata: dict
) -> None:
    """Add input metadata dictionary to an existing zarr group."""
    # zarr groups cannot have slashes in their names
    group_name = metadata["id"].replace("/", "_")
    parent_group.create_group(group_name)
    # Fill attrs in the subject group for each predicate
    for key, value in metadata.items():
        if key == "id":
            continue
        parent_group[group_name].attrs[key] = value


def add_data(group: zarr.hierarchy.Group, data) -> None:
    """Add a numpy array to an existing zarr group."""
    group.create_dataset("data", data=data)


def list_zarr_items(
    group: zarr.hierarchy.Group,
) -> list[zarr.hierarchy.Group | zarr.core.Array]:
    """Recursively list all zarr groups and arrays"""
    found = []

    def list_all(path: str, elem):
        found.append((path, elem))

    group.visititems(list_all)
    return found
