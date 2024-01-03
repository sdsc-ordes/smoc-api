import json
import shutil
from pathlib import Path
from typing import Generator, Optional

from linkml_runtime.dumpers import json_dumper
import rdflib
from smoc_schema.datamodel import Assay, DataEntity, Sample
import zarr

from .introspection import get_haspart_property
from .rdf import attrs_to_graph
from .storage import add_metadata_group, init_zarr


class MODO:
    """Multi-Omics Digital Object
    A digital archive containing several multi-omics data and records.
    The archive contains:
    * A zarr file, with array-based data
    * A metadata file, with RDF metadata describing and pointing to the actual data
    * CRAM files, with genomic-interval data

    Examples
    --------
    >>> demo = MODO("data/ex1")

    # List identifiers of samples in the archive
    >>> demo.list_samples()
    ['http://example.org/bac1', 'http://example.org/bac2']

    # List files in the archive
    >>> sorted([file.name for file in demo.list_files()])
    ['demo1.cram', 'demo2.cram', 'ecoli_ref.fa', 'metadata.ttl']

    # Query the metadata graph to find the location of the
    # CRAM files for the sample bac1
    >>> bac1_files = demo.query('''
    ...   SELECT ?path
    ...   WHERE {
    ...   [] rdf:type smoc:CRAMFile ;
    ...     smoc:hasSample ex:bac1 ;
    ...     smoc:hasLocation ?path .
    ... }
    ... ''').serialize(format="csv").decode()
    """

    def __init__(self, path: Path, id_: Optional[str] = None):
        self.path: Path = Path(path)
        self.archive = init_zarr(self.path)
        if id_ is None:
            self.id_ = self.path.name

    @property
    def metadata(self) -> dict:
        # Auto refresh metadata to match data before reading
        zarr.consolidate_metadata(self.archive.store)
        root = zarr.open_consolidated(self.archive.store)

        if isinstance(root, zarr.Array):
            raise ValueError("Root must be a group. Empty archive?")

        # Get flat dictionary with all attrs, easier to search
        group_attrs = dict()
        for name, value in root.groups():
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
        import yaml

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
        return self.knowledge_graph.query(query)

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
        if data_file is not None:
            shutil.copy(data_file, self.path / data_file.name)
            element.location = str(data_file.name)

        # Link element to parent element
        if part_of is None:
            path = "/"
        else:
            path = part_of
            has_prop = get_haspart_property(element.__class__.__name__)
            # has_part is multivalued
            if has_prop not in self.archive[part_of].attrs:
                self.archive[part_of].attrs[has_prop] = []
            self.archive[part_of].attrs[has_prop].append(element.id)

        # Add element to metadata
        parent_group = self.archive[path]
        attrs = json.loads(json_dumper.dumps(element))
        add_metadata_group(parent_group, attrs)
