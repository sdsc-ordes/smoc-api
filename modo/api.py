from datetime import date
import json
from pathlib import Path
import shutil
from typing import Generator, Optional
import yaml

from linkml_runtime.dumpers import json_dumper
import rdflib
from smoc_schema.datamodel import Assay, DataEntity, Sample, Study
import zarr

from .introspection import get_haspart_property
from .rdf import attrs_to_graph
from .storage import add_metadata_group, init_zarr, list_zarr_items


class MODO:
    """Multi-Omics Digital Object
    A digital archive containing several multi-omics data and records.
    The archive contains:
    * A zarr file, array-based data and metadata pointing to arrays and data files
    * CRAM files, with genomic-alignments data

    Examples
    --------
    >>> demo = MODO("data/ex")

    # List identifiers of samples in the archive
    >>> demo.list_samples()
    ['ex/demo-assay/demo1/bac1']

    # List files in the archive
    >>> sorted([file.name for file in demo.list_files()])
    ['demo1.cram', 'demo2.cram', 'ecoli_ref.fa', 'metadata.ttl']

    """

    def __init__(
        self,
        path: Path,
        id_: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        start_date: date = date.today(),
        completion_date: Optional[date] = None,
    ):
        self.path: Path = Path(path)
        self.archive = init_zarr(self.path)
        # Opened existing object
        try:
            self.id_ = next(self.archive.groups())[0]
        # Creating from scratch
        except StopIteration:
            if id_ is None:
                self.id_ = self.path.name
            self.add_element(
                Study(
                    self.id_,
                    start_date=str(start_date),
                    completion_date=str(completion_date)
                    if completion_date
                    else None,
                    name=name,
                    description=description,
                )
            )

    @property
    def metadata(self) -> dict:
        # Auto refresh metadata to match data before reading
        zarr.consolidate_metadata(self.archive.store)
        root = zarr.open_consolidated(self.archive.store)

        if isinstance(root, zarr.Array):
            raise ValueError("Root must be a group. Empty archive?")

        # Get flat dictionary with all attrs, easier to search
        group_attrs = dict()
        for name, value in list_zarr_items(root):
            group_attrs[name] = dict(value.attrs)
        return group_attrs

    def knowledge_graph(
        self, uri_prefix: Optional[str] = None
    ) -> rdflib.Graph:
        """Return an RDF graph of the metadata. All identifiers
        are converted to valid URIs if needed."""
        if uri_prefix is None:
            uri_prefix = f"file://{self.path.name}/"
        kg = attrs_to_graph(self.metadata, uri_prefix=uri_prefix)
        return kg

    def show_contents(self):
        """human-readable print of the object's contents"""
        meta = self.metadata
        # Pretty print metadata contents as yaml

        return yaml.dump(meta, sort_keys=False)

    def list_files(self) -> Generator[Path, None, None]:
        """Lists files in the archive recursively (except for the zarr file)."""
        for path in self.path.glob("*"):
            if path.name.endswith(".zarr"):
                continue
            elif path.is_file():
                yield path
            for file in path.rglob("*"):
                yield file

    def list_arrays(self):
        """Lists arrays in the archive recursively."""
        return self.archive.tree()

    def query(self, query: str):
        """Use SPARQL to query the metadata graph"""
        return self.knowledge_graph().query(query)

    def list_samples(self):
        """Lists samples in the archive."""
        res = self.query("SELECT ?s WHERE { ?s a smoc_schema:Sample }")
        samples = []
        for row in res:
            for val in row:
                samples.append(
                    str(val).removeprefix(f"file://{self.path.name}")
                )
        return samples

    def add_element(
        self,
        element: DataEntity | Sample | Assay,
        data_file: Optional[Path] = None,
        part_of: Optional[str] = None,
    ):
        """Add an element to the archive.
        If a data file is provided, it will be added to the archive.
        If the element is part of another element, the parent metadata
        will be updated."""

        # Copy data file to archive and update location in metadata
        data_path = Path(data_file)
        if data_file is not None:
            shutil.copy(data_file, self.path / data_path.name)
            element.location = str(data_path.name)

        # Link element to parent element
        if part_of is None:
            path = "/"
        else:
            path = part_of
            has_prop = get_haspart_property(element.__class__.__name__)
            # has_part is multivalued
            if has_prop not in self.archive[part_of].attrs:
                self.archive[part_of].attrs[has_prop] = []
            self.archive[part_of].attrs[has_prop] += [element.id]

        # Add element to metadata
        parent_group = self.archive[path]
        attrs = json.loads(json_dumper.dumps(element))
        add_metadata_group(parent_group, attrs)
        zarr.consolidate_metadata(self.archive.store)
