from abc import ABC, abstractmethod
import io
import os
from pathlib import Path
import re
import shutil
from typing import Any, ClassVar, Generator, Optional

from pydantic import Field, HttpUrl
from pydantic.dataclasses import dataclass
import s3fs
import zarr
import zarr.hierarchy as zh


from modos.helpers.schema import ElementType

ZARR_ROOT = Path("data.zarr")
S3_ADDRESSING_STYLE = os.getenv("S3_ADDRESSING_STYLE", "auto")


class Storage(ABC):
    @property
    @abstractmethod
    def path(self) -> Path:
        ...

    @property
    @abstractmethod
    def zarr(self) -> zh.Group:
        ...

    @abstractmethod
    def exists(self, target: Path) -> bool:
        ...

    @abstractmethod
    def put(self, source: Path, target: Path):
        ...

    @abstractmethod
    def remove(self, target: Path):
        ...

    @abstractmethod
    def list(self, target: Optional[Path]) -> Generator[Path, None, None]:
        ...

    @abstractmethod
    def open(self, target: Path) -> io.BufferedReader:
        ...

    @abstractmethod
    def update(self, source: Path, target: Path):
        """Updates target file based on source file. If source is inside modo it will be deleted afterwards."""
        ...

    def empty(self) -> bool:
        return len(self.zarr.attrs.keys()) == 0


class LocalStorage(Storage):
    def __init__(self, path: Path):
        self._path = Path(path)
        if (self.path / ZARR_ROOT).exists():
            self._zarr = zarr.convenience.open(str(self.path / ZARR_ROOT))
        else:
            self.path.mkdir(exist_ok=True)
            zarr_store = zarr.storage.DirectoryStore(
                str(self.path / ZARR_ROOT)
            )
            self._zarr = init_zarr(zarr_store)

    @property
    def zarr(self) -> zh.Group:
        return self._zarr

    @property
    def path(self) -> Path:
        return self._path

    def exists(self, target: Path) -> bool:
        return (self.path / target).exists()

    def list(self, target: Optional[Path] = None):
        path = self.path / (target or "")
        for path in path.glob("*"):
            if path.name.endswith(".zarr"):
                continue
            elif path.is_file():
                yield path
            for file in path.rglob("*"):
                if file.is_file():
                    yield file

    def open(self, target: Path) -> io.BufferedReader:
        return open(self.path / target, "rb")

    def remove(self, target: Path):
        if target.exists():
            target.unlink()
            print(f"INFO: Permanently deleted {target} from filesystem.")

    def put(self, source: Path, target: Path):
        shutil.copy(source, self.path / target)

    def update(self, source: Path, target: Path):
        self.put(source, target)
        self.remove(self.path / target)


@dataclass
class S3Path:
    """Pydantic Model for S3 URLs. Performs validation against amazon's official naming rules [1]_ [2]_

    .. [1] https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html
    .. [2] https://gist.github.com/rajivnarayan/c38f01b89de852b3e7d459cfde067f3f


    Examples
    --------
    >>> S3Path(url="s3://test/ex")
    S3Path(url='s3://test/ex')
    >>> S3Path(url='s3://?invalid-bucket-name!/def') # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
      ...
    pydantic_core._pydantic_core.ValidationError: 1 validation error for S3Path
    """

    _s3_pattern: ClassVar[re.Pattern[str]] = re.compile(
        r"^s3://"
        r"(?=[a-z0-9])"  # Bucket name must start with a letter or digit
        r"(?!(^xn--|sthree-|sthree-configurator|.+-s3alias$))"  # Bucket name must not start with xn--, sthree-, sthree-configurator or end with -s3alias
        r"(?!.*\.\.)"  # Bucket name must not contain two adjacent periods
        r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]"  # Bucket naming constraints
        r"(?<!\.-$)"  # Bucket name must not end with a period followed by a hyphen
        r"(?<!\.$)"  # Bucket name must not end with a period
        r"(?<!-$)"  # Bucket name must not end with a hyphen
        r"(/([a-zA-Z0-9._-]+/?)*)?$"  # key naming constraints
    )
    url: str = Field(
        ...,
        json_schema_extra={"strip_whitespace": True},  # type: ignore
        pattern=_s3_pattern,
        min_length=8,
        max_length=1023,
    )

    def s3_url_parts(self):
        path_parts = self.url[5:].split("/")
        bucket = path_parts.pop(0)
        key = "/".join(path_parts)
        return (bucket, key)

    @property
    def bucket(self) -> str:
        return self.s3_url_parts()[0]

    @property
    def key(self) -> str:
        return self.s3_url_parts()[1]


class S3Storage(Storage):
    def __init__(
        self,
        path: str,
        s3_endpoint: HttpUrl,
        s3_kwargs: Optional[dict[str, Any]] = None,
    ):
        self._path = S3Path(url=path)
        self.endpoint = s3_endpoint
        s3_opts = s3_kwargs or {"anon": True}
        fs = connect_s3(s3_endpoint, s3_opts)
        if fs.exists(str(self.path / ZARR_ROOT)):
            zarr_s3_opts = s3_opts | {"endpoint_url": str(s3_endpoint)}

            self._zarr = zarr.convenience.open(
                f"{self._path.url}/{ZARR_ROOT}",
                storage_options=zarr_s3_opts,
            )
        else:
            fs.mkdirs(self.path, exist_ok=True)
            zarr_store = zarr.storage.FSStore(
                str(self.path / ZARR_ROOT), fs=fs
            )
            self._zarr = init_zarr(zarr_store)

    @property
    def path(self) -> Path:
        return Path(f"{self._path.bucket}/{self._path.key}")

    @property
    def zarr(self) -> zh.Group:
        return self._zarr

    def exists(self, target: Path = ZARR_ROOT) -> bool:
        fs = self.zarr.store.fs
        return fs.exists(str(self.path / target))

    def list(
        self, target: Optional[Path] = None
    ) -> Generator[Path, None, None]:
        fs = self.zarr.store.fs
        path = self.path / (target or "")
        for node in fs.glob(f"{path}/*"):
            if Path(node).name.endswith(".zarr"):
                continue
            elif fs.isfile(node):
                yield Path(node)
            elif fs.isdir(node):
                for file in fs.find(node):
                    yield Path(file)

    def open(self, target: Path) -> io.BufferedReader:
        return self.zarr.store.fs.open(str(self.path / target))

    def remove(self, target: Path):
        if self.zarr.store.fs.exists(target):
            self.zarr.store.fs.rm(str(target))
            print(
                f"INFO: Permanently deleted {target} from remote filesystem."
            )

    def put(self, source: Path, target: Path):
        self.zarr.store.fs.put_file(source, self.path / Path(target))

    def update(self, source: Path, target: Path):
        if self.exists(source):
            self.zarr.store.fs.mv(source, self.path / Path(target))
        else:
            self.put(source, target)


# Initialize object's directory given the metadata graph
def init_zarr(zarr_store: zarr.storage.Store) -> zh.Group:
    """Initialize object's directory and metadata structure."""
    data = zh.group(store=zarr_store)
    elem_types = [t.value for t in ElementType]
    for elem_type in elem_types:
        data.create_group(elem_type)

    return data


def connect_s3(
    endpoint: HttpUrl, s3_kwargs: dict[str, Any]
) -> s3fs.S3FileSystem:
    return s3fs.S3FileSystem(
        endpoint_url=str(endpoint),
        config_kwargs={"s3": {"addressing_style": S3_ADDRESSING_STYLE}},
        **s3_kwargs,
    )


def add_metadata_group(parent_group: zh.Group, metadata: dict) -> None:
    """Add input metadata dictionary to an existing zarr group."""
    # zarr groups cannot have slashes in their names
    group_name = metadata["id"].replace("/", "_")
    parent_group.create_group(group_name)
    # Fill attrs in the subject group for each predicate
    for key, value in metadata.items():
        if key == "id":
            continue
        parent_group[group_name].attrs[key] = value


def add_data(group: zh.Group, data) -> None:
    """Add a numpy array to an existing zarr group."""
    group.create_dataset("data", data=data)


def list_zarr_items(
    group: zh.Group,
) -> list[zh.Group | zarr.core.Array]:
    """Recursively list all zarr groups and arrays"""
    found = []

    def list_all(path: str, elem):
        found.append((path, elem))

    group.visititems(list_all)
    return found
